#!/usr/bin/env python3
# ==========================================================================
# 03b_mgnify_full_download.py  —  Resumable, memory-bounded, all-levels pull
# of study-level SSU taxonomy tables from EBI MGnify.
#
# Design goals (per user request):
#   * SLOW / gentle: one study at a time, configurable delay, retries+backoff.
#   * MEMORY < 4 GB: never hold more than one study in RAM; each study's full
#     lineage table is written straight to its own parquet, then freed.
#   * RESUMABLE: a manifest.csv records every study's status; on restart we skip
#     studies already marked 'ok' (and whose parquet exists). Kill it anytime —
#     completed studies persist and the next run continues where it stopped.
#   * ALL LEVELS: we store each study's FULL lineage table (rows = complete
#     taxonomic lineage string sk__..;..;g__..;s__.., cols = samples, values =
#     counts). No rank collapse here — every level is preserved losslessly.
#     Rank-specific tables (phylum..species) are derived later at merge time.
#
# Usage:
#   python 03b_mgnify_full_download.py [--limit N] [--delay SEC] [--studies CSV]
# Outputs (under $DATA_DIR/mgnify_full/):
#   tables/{MGYS}.parquet   per-study lineage×samples counts
#   manifest.csv            resumable progress log (one row per study attempted)
# ==========================================================================
import os, sys, time, json, argparse, io
import pandas as pd, requests

API = "https://www.ebi.ac.uk/metagenomics/api/v1"
DATA = os.environ.get("DATA_DIR", "data")
WORK = os.path.join(DATA, "mgnify_full")
TABLES = os.path.join(WORK, "tables")
MANIFEST = os.path.join(WORK, "manifest.csv")
os.makedirs(TABLES, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=0, help="max NEW studies this run (0 = all remaining)")
ap.add_argument("--delay", type=float, default=0.5, help="seconds between studies (gentle)")
ap.add_argument("--studies", default=None, help="target study CSV (needs 'accession','body_sites')")
args = ap.parse_args()

STUDIES_CSV = args.studies or os.path.join(DATA, "..", "handoff", "mgnify_target_studies.csv")

SITE_MAP = {"gut": "stool", "oral": "oral", "skin": "skin",
            "respiratory": "respiratory", "urogenital": "urogenital"}

def load_manifest():
    if os.path.exists(MANIFEST):
        m = pd.read_csv(MANIFEST, dtype=str)
        # keep the LAST attempt per study (retries append new rows)
        m = m.drop_duplicates("accession", keep="last").set_index("accession")
        return m.to_dict("index")
    return {}

def append_manifest(row):
    """Append one row, creating header if new. Flushed immediately (crash-safe)."""
    hdr = not os.path.exists(MANIFEST)
    pd.DataFrame([row]).to_csv(MANIFEST, mode="a", header=hdr, index=False)

def session():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s

def get_json(s, url, tries=4, timeout=90):
    for i in range(tries):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None

def pick_ssu_table(downloads):
    """Choose the combined SSU rRNA taxonomy table (full resolution, not phylum-only,
    not fungal ITS/UNITE). Prefer the highest pipeline version."""
    best = None
    for d in downloads.get("data", []):
        did = d.get("id", "")
        low = did.lower()
        if not low.endswith(".tsv"): continue
        if "taxonomy_abundances" not in low: continue
        if "phylum" in low or "itsonedb" in low or "unite" in low: continue
        # version: trailing _vX.Y before .tsv
        ver = 0.0
        for tok in low.replace(".tsv", "").split("_"):
            if tok.startswith("v") and tok[1:].replace(".", "").isdigit():
                try: ver = float(tok[1:])
                except ValueError: pass
        link = (d.get("links", {}) or {}).get("self")
        if link and (best is None or ver > best[2]):
            best = (did, link, ver)
    return best  # (table_id, url, version) or None

def download_tsv(s, url, tries=4, timeout=180):
    for i in range(tries):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(2.0 * (i + 1))
    return None

def main():
    tgt = pd.read_csv(STUDIES_CSV, dtype=str)
    if "samples_count" in tgt.columns:
        tgt["_n"] = pd.to_numeric(tgt["samples_count"], errors="coerce").fillna(0)
        tgt = tgt.sort_values("_n", ascending=False)
    done = load_manifest()
    s = session()
    new = 0
    total = len(tgt)
    for i, row in enumerate(tgt.itertuples(), 1):
        acc = row.accession
        pq = os.path.join(TABLES, f"{acc}.parquet")
        # resume: skip studies already OK with a parquet on disk
        if acc in done and done[acc].get("status") == "ok" and os.path.exists(pq):
            continue
        if args.limit and new >= args.limit:
            print(f"[mgnify-full] reached --limit {args.limit}; stopping (resumable).")
            break
        # first listed body site -> controlled vocab
        sites = str(getattr(row, "body_sites", "") or "").split("|")
        body_site = SITE_MAP.get(sites[0].strip().lower(), sites[0].strip().lower() if sites else "")
        rec = {"accession": acc, "body_site": body_site, "table_id": "", "version": "",
               "n_samples": 0, "n_taxa": 0, "status": "", "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            dl = get_json(s, f"{API}/studies/{acc}/downloads")
            if not dl:
                rec["status"] = "no_downloads"; append_manifest(rec); continue
            pick = pick_ssu_table(dl)
            if not pick:
                rec["status"] = "no_ssu_table"; append_manifest(rec); continue
            tid, url, ver = pick
            txt = download_tsv(s, url)
            if not txt:
                rec["status"] = "download_failed"; append_manifest(rec); continue
            # parse: first col = lineage, rest = samples. Memory: one study only.
            df = pd.read_csv(io.StringIO(txt), sep="\t")
            df = df.rename(columns={df.columns[0]: "lineage"}).set_index("lineage")
            # prefix sample columns with study accession -> global sample_id
            df.columns = [f"{acc}:{c}" for c in df.columns]
            df = df.astype("float32")
            df.to_parquet(pq)  # rows=lineage (all levels), cols=samples
            rec.update({"table_id": tid, "version": ver,
                        "n_samples": df.shape[1], "n_taxa": df.shape[0], "status": "ok"})
            append_manifest(rec)
            new += 1
            del df
            if new % 25 == 0:
                print(f"[mgnify-full] {new} new studies done (at {i}/{total}: {acc}, "
                      f"{rec['n_samples']} samples)")
        except Exception as e:
            rec["status"] = f"error:{type(e).__name__}"
            append_manifest(rec)
        time.sleep(args.delay)
    # summary
    m = load_manifest()
    ok = sum(1 for v in m.values() if v.get("status") == "ok")
    nsamp = sum(int(v.get("n_samples", 0) or 0) for v in m.values() if v.get("status") == "ok")
    print(f"[mgnify-full] session added {new}. Cumulative: {ok} studies OK, "
          f"{nsamp} samples, {len(m)} attempted of {total}.")

if __name__ == "__main__":
    main()
