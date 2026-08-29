#!/usr/bin/env python3
# ==========================================================================
# 03_16s_mgnify.py  —  16S TIER, PART B: MGnify body-site demonstrator
#
# Pulls 12 amplicon studies from the EBI MGnify REST API (3 each for skin,
# oral, respiratory, urogenital) to add non-stool body-site breadth, collapses
# SSU OTU taxonomy to GENUS, and writes:
#   $DATA_DIR/mgnify_16s_demo_genus_table.parquet
#   $DATA_DIR/mgnify_16s_demo_metadata.csv
#   $DATA_DIR/mgnify_16s_demo_manifest.csv
#
# The 12 studies are the fixed demonstrator set used to build corpus v1.0.
# The full 774-study catalogue (mgnify_human_bodysite_studies.csv) is the
# documented expansion index for scaling this tier.
# ==========================================================================
import os, time, io
from collections import OrderedDict
import numpy as np, pandas as pd, requests

DATA = os.environ["DATA_DIR"]
API = "https://www.ebi.ac.uk/metagenomics/api/v1"
MAX_PER = int(os.environ.get("MGNIFY_MAX_PER_STUDY", "200"))
SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

# Fixed demonstrator set: (MGYS accession, harmonized body_site)
STUDIES = [
    ("MGYS00001295", "skin"), ("MGYS00001818", "skin"), ("MGYS00005533", "skin"),
    ("MGYS00002356", "oral"), ("MGYS00002146", "oral"), ("MGYS00002400", "oral"),
    ("MGYS00006509", "respiratory"), ("MGYS00006284", "respiratory"), ("MGYS00006497", "respiratory"),
    ("MGYS00000942", "urogenital"), ("MGYS00001069", "urogenital"), ("MGYS00001373", "urogenital"),
]

def get_json(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None

def genus_from_lineage(lin):
    # MGnify SSU_OTU.tsv taxonomy string: "sk__..;k__..;p__..;c__..;o__..;f__..;g__..;s__.."
    parts = [p.strip() for p in lin.replace("Root;", "").split(";") if p.strip()]
    g = next((p for p in parts if p.startswith("g__")), None)
    if g and not g.endswith("__"):
        return g
    resolved = [p for p in parts if not p.endswith("__")]
    return f"Unassigned_{resolved[-1]}" if resolved else "Unassigned"

def pull_analysis_otu(mgya):
    # Locate the SSU OTU TSV download for an analysis and parse -> genus counts.
    dl = get_json(f"{API}/analyses/{mgya}/downloads")
    if not dl:
        return None
    target = None
    for d in dl.get("data", []):
        lbl = (d.get("attributes", {}).get("description", {}) or {}).get("label", "") or ""
        did = d.get("id", "")
        if did.endswith("SSU_OTU.tsv") or ("OTU" in did.upper() and did.endswith(".tsv")) or "taxonomic assignments" in lbl.lower():
            target = d.get("links", {}).get("self") or f"{API}/analyses/{mgya}/file/{did}"
            break
    if not target:
        return None
    try:
        txt = SESSION.get(target, timeout=90).text
    except Exception:
        return None
    # TSV: OTU_id, count, lineage (no header, tab-separated)
    genus = {}
    for line in txt.splitlines():
        f = line.split("\t")
        if len(f) < 3:
            continue
        try:
            cnt = float(f[1])
        except ValueError:
            continue
        g = genus_from_lineage(f[-1])
        genus[g] = genus.get(g, 0.0) + cnt
    return genus

manifest, rows, meta_rows = [], {}, []
for mgys, site in STUDIES:
    seen = pulled = 0; page = 1
    while pulled < MAX_PER:
        js = get_json(f"{API}/studies/{mgys}/analyses", {"page": page, "page_size": 50})
        if not js or not js.get("data"):
            break
        for a in js["data"]:
            seen += 1
            if pulled >= MAX_PER:
                break
            mgya = a["id"]
            g = pull_analysis_otu(mgya)
            if not g:
                continue
            sid = f"{mgys}:{mgya}"
            rows[sid] = g
            meta_rows.append(dict(sample_id=sid, mgnify_analysis=mgya, study_accession=mgys,
                                  body_site=site, modality="16S", source="MGnify",
                                  pipeline="MGnify SSU OTU", region="16S"))
            pulled += 1
        if not js.get("links", {}).get("next"):
            break
        page += 1
        time.sleep(0.3)
    manifest.append(dict(study_accession=mgys, body_site=site,
                         n_analyses_seen=seen, n_samples_pulled=pulled))
    print(f"[mgnify] {mgys} ({site}): pulled {pulled}")

# assemble samples x genus
all_g = sorted(set().union(*[set(v) for v in rows.values()])) if rows else []
tab = pd.DataFrame(0.0, index=list(rows), columns=all_g)
for sid, g in rows.items():
    for k, v in g.items():
        tab.at[sid, k] = v
tab.index.name = "sample_id"
tab.to_parquet(os.path.join(DATA, "mgnify_16s_demo_genus_table.parquet"))
pd.DataFrame(meta_rows).to_csv(os.path.join(DATA, "mgnify_16s_demo_metadata.csv"), index=False)
pd.DataFrame(manifest).to_csv(os.path.join(DATA, "mgnify_16s_demo_manifest.csv"), index=False)
print(f"[mgnify] genus table: {tab.shape}; done.")
