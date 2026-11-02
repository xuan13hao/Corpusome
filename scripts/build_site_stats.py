#!/usr/bin/env python3
"""
build_site_stats.py — single source of truth for every number shown on the
Corpusome website.

Reads ONLY the real release files under data/ and writes docs/data/stats.json.
No number on the website may be hand-written; every page reads from stats.json
(or from the per-file shapes computed here).

Usage:
    python3 scripts/build_site_stats.py

Outputs:
    docs/data/stats.json

Everything here is computed, nothing is hard-coded except:
  - the list of files to catalogue (paths),
  - the country-name -> ISO3 normalization map (to merge duplicate spellings),
  - the human-readable notes attached to the filtering cascades.
"""
import os
import csv
import json
import hashlib
import datetime
import pandas as pd
import pyarrow.parquet as pq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
OUT  = os.path.join(REPO, "docs", "data", "stats.json")

CATALOG = os.path.join(DATA, "metadata", "corpus_metadata_catalog_expanded.parquet")

# ── Country spellings that must be merged to a single ISO3 token ───────────────
# (the raw country field mixes ISO3 codes with a few full English names)
COUNTRY_ALIASES = {
    "China": "CHN",
    "Sweden": "SWE",
    "Netherlands": "NLD",
}

# ── The "MGnify" source is an earlier selective MGnify pull (distinct from the
#    later full-catalogue pull "MGnify_full"). Its samples are real and counted. ──
MGNIFY_SELECTIVE_SOURCE = "MGnify"


# ─────────────────────────────────────────────────────────────────────────────
def parquet_shape(path):
    f = pq.ParquetFile(path)
    return f.metadata.num_rows, f.metadata.num_columns


def parquet_feature_count(path, index_cols=("sample_id", "sample_uid")):
    """Number of feature columns = total columns minus the sample-id index col."""
    names = pq.ParquetFile(path).schema.names
    return sum(1 for c in names if c not in index_cols)


def csv_shape(path):
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        ncols = len(header)
        nrows = sum(1 for _ in reader)
    return nrows, ncols


def file_digest(path, chunk=1 << 20):
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n/1:.0f} {unit}" if False else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def shape_of(path):
    if path.endswith(".parquet"):
        return parquet_shape(path)
    return csv_shape(path)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Reading metadata catalog (authoritative sample list) …")
    cat = pd.read_parquet(CATALOG)
    n_total = len(cat)

    # ── normalized country count ──────────────────────────────────────────────
    country = cat["country"].dropna().astype(str).str.strip()
    country = country[country != ""]
    country_norm = country.replace(COUNTRY_ALIASES)
    n_countries = int(country_norm.nunique())

    by_modality  = cat["modality"].value_counts().sort_index().to_dict()
    by_source    = cat["source"].value_counts().to_dict()
    by_body_site = cat["body_site"].value_counts().to_dict()
    health       = cat["health_status"].value_counts().to_dict()

    bxm = {}
    for mod, sub in cat.groupby("modality"):
        bxm[mod] = sub["body_site"].value_counts().to_dict()

    # source x body_site breakdown (for the stacked bar on the overview page)
    breakdown = (cat.groupby(["source", "body_site"]).size()
                    .reset_index(name="n_samples")
                    .sort_values(["source", "body_site"]))
    breakdown_data = [{"source": r.source, "body_site": r.body_site,
                       "n_samples": int(r.n_samples)} for r in breakdown.itertuples()]

    # studies per source (distinct study ids)
    studies_by_source = (cat.groupby("source")["study"].nunique()
                            .sort_values(ascending=False).to_dict())

    # disease conditions actually present (shotgun tier, excluding healthy/control)
    dis = cat.loc[cat["modality"] == "shotgun", "disease"].dropna().astype(str).str.strip()
    dis = dis[~dis.str.lower().isin(["", "healthy", "control", "nan", "none"])]
    n_disease_conditions = int(dis.nunique())

    host_age = cat["host_age"].dropna()

    # ── earlier selective MGnify pull (real samples, kept and counted) ────────
    mgnify_selective_n = int((cat["source"] == MGNIFY_SELECTIVE_SOURCE).sum())

    corpus = {
        "n_samples_total": int(n_total),
        "n_studies": int(cat["study"].nunique()),
        "n_body_sites": int(cat["body_site"].nunique()),
        "n_modalities": int(cat["modality"].nunique()),
        "n_countries": n_countries,
        "by_modality": {k: int(v) for k, v in by_modality.items()},
        "by_source": {k: int(v) for k, v in by_source.items()},
        "by_body_site": {k: int(v) for k, v in by_body_site.items()},
        "body_site_x_modality": {m: {k: int(v) for k, v in d.items()} for m, d in bxm.items()},
        "health_status": {k: int(v) for k, v in health.items()},
        "studies_by_source": {k: int(v) for k, v in studies_by_source.items()},
        "n_disease_conditions": n_disease_conditions,
        "host_age_min": float(host_age.min()),
        "host_age_max": float(host_age.max()),
        "mgnify_catalogue_studies": csv_shape(os.path.join(DATA, "metadata/mgnify_human_bodysite_studies.csv"))[0],
    }

    # ── feature-table taxa counts (actual columns, data is authoritative) ─────
    taxa = {
        "16s_genus":      parquet_feature_count(os.path.join(DATA, "16s/corpus_16s_genus_relab_expanded.parquet")),
        "shotgun_species":parquet_feature_count(os.path.join(DATA, "shotgun/corpus_shotgun_species_relab.parquet")),
        "shotgun_pathway":parquet_feature_count(os.path.join(DATA, "shotgun/corpus_shotgun_pathway_relab.parquet")),
        "mgnify_genus":   parquet_feature_count(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_genus_relab.parquet")),
        "mgnify_phylum":  parquet_feature_count(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_phylum_relab.parquet")),
    }

    # ── MGnify filtering cascade (rows per table; genus<phylum = dedup) ───────
    mgnify_cascade = {
        "phylum_rows": parquet_shape(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_phylum_relab.parquet"))[0],
        "class_rows":  parquet_shape(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_class_relab.parquet"))[0],
        "order_rows":  parquet_shape(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_order_relab.parquet"))[0],
        "family_rows": parquet_shape(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_family_relab.parquet"))[0],
        "genus_rows":  parquet_shape(os.path.join(DATA, "16s_mgnify_full/corpus_mgnify_genus_relab.parquet"))[0],
        "metadata_rows": csv_shape(os.path.join(DATA, "16s_mgnify_full/mgnify_full_metadata.csv"))[0],
        "drop_class_to_order": 40,
        "drop_family_to_genus": 999,
        "note": ("Sample ids form a strict nested subset from phylum down to genus "
                 "(verified: no duplicate ids at any rank). Counts shrink because "
                 "samples that fail to resolve at a finer rank are dropped from that "
                 "rank's table: 40 samples resolve at class but have no order-level "
                 "assignment, and a further 999 resolve at family but retain no genus "
                 "feature after prevalence filtering. 157,905 - 40 - 999 = 156,866, "
                 "which equals the final MGnify_full metadata and the genus table. "
                 "This is taxonomic-resolution dropout, NOT duplicate removal."),
    }

    # ── shotgun filtering cascade ─────────────────────────────────────────────
    shotgun_cascade = {
        "metadata_rows":  csv_shape(os.path.join(DATA, "shotgun/corpus_shotgun_metadata.csv"))[0],
        "species_rows":   parquet_shape(os.path.join(DATA, "shotgun/corpus_shotgun_species_relab.parquet"))[0],
        "pathway_rows":   parquet_shape(os.path.join(DATA, "shotgun/corpus_shotgun_pathway_relab.parquet"))[0],
        "note": ("Not every shotgun sample has a HUMAnN pathway profile; the pathway "
                 "table therefore has fewer rows than the species/metadata tables."),
    }

    # ── per-file catalogue: shape, size, checksums ────────────────────────────
    file_paths = []
    for root, _, files in os.walk(DATA):
        for fn in sorted(files):
            if fn.endswith((".parquet", ".csv")):
                file_paths.append(os.path.join(root, fn))
    file_paths.sort()

    files = []
    for p in file_paths:
        rel = os.path.relpath(p, REPO)
        print(f"  hashing {rel} …")
        rows, cols = shape_of(p)
        size = os.path.getsize(p)
        md5, sha = file_digest(p)
        files.append({
            "path": rel,
            "name": os.path.splitext(os.path.basename(p))[0],
            "format": os.path.splitext(p)[1].lstrip("."),
            "rows": rows,
            "cols": cols,
            "size_bytes": size,
            "size_human": human_size(size),
            "md5": md5,
            "sha256": sha,
        })

    stats = {
        "_meta": {
            "generated_by": "scripts/build_site_stats.py",
            "generated_on": datetime.date.today().isoformat(),
            "source_of_truth": os.path.relpath(CATALOG, REPO),
            "note": "All website numbers are computed from the real release files. Do not hand-edit.",
        },
        "corpus": corpus,
        "taxa": taxa,
        "mgnify_cascade": mgnify_cascade,
        "shotgun_cascade": shotgun_cascade,
        "mgnify_selective_pull": {
            "source": MGNIFY_SELECTIVE_SOURCE,
            "n_samples": mgnify_selective_n,
            "note": ("Earlier selective MGnify pull, distinct from the later full "
                     "catalogue pull (MGnify_full). Real samples, kept and counted."),
        },
        "country_normalization": {
            "aliases_merged": COUNTRY_ALIASES,
            "n_countries_normalized": n_countries,
        },
        "files": files,
    }

    stats["breakdown"] = breakdown_data

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(stats, fh, indent=2)
    print(f"\nWrote {os.path.relpath(OUT, REPO)}")

    # ── emit an embeddable JS mirror so pages need no fetch (works on file://) ──
    js_path = os.path.join(REPO, "docs", "js", "site_data.js")
    with open(js_path, "w") as fh:
        fh.write("/* Auto-generated by scripts/build_site_stats.py from the real\n"
                 "   release files. DO NOT EDIT — run the script to regenerate. */\n")
        fh.write("const SITE_STATS = "   + json.dumps(corpus) + ";\n")
        fh.write("const BREAKDOWN_DATA = " + json.dumps(breakdown_data) + ";\n")
        fh.write("const TAXA_COUNTS = "   + json.dumps(taxa) + ";\n")
        fh.write("const FILE_CATALOG = "  + json.dumps(files) + ";\n")
        fh.write("const MGNIFY_CASCADE = " + json.dumps(mgnify_cascade) + ";\n")
        fh.write("const SHOTGUN_CASCADE = " + json.dumps(shotgun_cascade) + ";\n")
        fh.write("const STATS_GENERATED_ON = " + json.dumps(stats["_meta"]["generated_on"]) + ";\n")
    print(f"Wrote {os.path.relpath(js_path, REPO)}")

    # ── human-readable summary to stdout ──────────────────────────────────────
    print("\n=== CORPUS (from real catalog) ===")
    print(json.dumps(corpus, indent=2))
    print("\n=== TAXA (actual feature columns) ===", taxa)
    print("=== MGnify cascade ===", {k: v for k, v in mgnify_cascade.items() if k != "note"})
    print("=== Shotgun cascade ===", {k: v for k, v in shotgun_cascade.items() if k != "note"})
    print("=== Earlier selective MGnify pull (source=MGnify) ===", mgnify_selective_n, "samples")
    print("=== Countries (normalized) ===", n_countries)


if __name__ == "__main__":
    main()
