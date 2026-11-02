#!/usr/bin/env python3
"""
build_taxon_stats.py — per-taxon, per-body-site statistics for the website,
computed from the real relative-abundance tables.

Produces, for every genus (16S tier) and species (shotgun tier):
  - prevalence      : fraction of samples in a body site where the taxon is present (>0)
  - mean_relab      : mean relative abundance of the taxon across samples in a body site

Outputs:
    docs/js/taxon_data.js
        TAXON_STATS : [{taxon, tier, sites:{<body_site>:[prevalence, mean_relab]}}]
                      (Taxon browser — searchable/sortable table)
        TOP_TAXA    : {<tier>:{<body_site>:[{taxon, mean_relab}, ...top N..., Other]}}
                      (per-body-site stacked bar of dominant taxa)
    docs/data/taxon_stats.json  (same content, canonical JSON)

Nothing is synthetic: every number is a direct aggregate of the release tables.

Usage:
    python3 scripts/build_taxon_stats.py
"""
import os
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
DOCS = os.path.join(REPO, "docs")
CATALOG = os.path.join(DATA, "metadata", "corpus_metadata_catalog_expanded.parquet")

TOP_N = 12                 # dominant taxa per body site for the stacked bar
MIN_MAX_PREV = 0.01        # keep a taxon in the browser if it reaches >=1% prevalence
                           # in at least one body site (keeps the payload small/meaningful)

TIERS = {
    "16S": {
        "relab": os.path.join(DATA, "16s/corpus_16s_genus_relab_expanded.parquet"),
        "relab_id": "sample_id",
        "catalog_key": "local",       # sample_uid without "SOURCE:" prefix
        "prefix": "g__",
    },
    "shotgun": {
        "relab": os.path.join(DATA, "shotgun/corpus_shotgun_species_relab.parquet"),
        "relab_id": "sample_uid",
        "catalog_key": "sample_uid",
        "prefix": "s__",
    },
}


def body_site_map(cat, key):
    if key == "local":
        k = cat["sample_uid"].astype(str).str.split(":", n=1).str[-1]
    else:
        k = cat["sample_uid"].astype(str)
    return dict(zip(k, cat["body_site"]))


def accumulate(relab_path, id_col, prefix, id2site):
    """Stream the parquet; return per-body-site column sums, nonzero counts, and
    sample counts (memory-safe)."""
    pf = pq.ParquetFile(relab_path)
    feats = [c for c in pf.schema.names if c.startswith(prefix)]
    sums, nz, n = {}, {}, {}
    nfeat = len(feats)
    for batch in pf.iter_batches(batch_size=4000, columns=[id_col] + feats):
        df = batch.to_pandas()
        sites = df[id_col].astype(str).map(id2site)
        X = df[feats].to_numpy(dtype=np.float64, na_value=0.0)
        present = (X > 0)
        for bs in pd.unique(sites.dropna()):
            mask = (sites == bs).to_numpy()
            if not mask.any():
                continue
            sums.setdefault(bs, np.zeros(nfeat)); sums[bs] += X[mask].sum(axis=0)
            nz.setdefault(bs, np.zeros(nfeat));   nz[bs]   += present[mask].sum(axis=0)
            n[bs] = n.get(bs, 0) + int(mask.sum())
    return feats, sums, nz, n


def main():
    cat = pd.read_parquet(CATALOG, columns=["sample_uid", "body_site"])
    taxon_stats = []
    top_taxa = {}

    for tier, cfg in TIERS.items():
        print(f"\n=== {tier} tier ===")
        id2site = body_site_map(cat, cfg["catalog_key"])
        feats, sums, nz, n = accumulate(cfg["relab"], cfg["relab_id"], cfg["prefix"], id2site)
        sites = sorted(n, key=lambda s: -n[s])
        print(f"  features={len(feats)}  body sites={ {s:n[s] for s in sites} }")

        mean = {s: sums[s] / n[s] for s in sites}          # mean relative abundance
        prev = {s: nz[s] / n[s] for s in sites}            # prevalence

        # ---- Taxon browser rows ----
        kept = 0
        for i, taxon in enumerate(feats):
            maxprev = max(prev[s][i] for s in sites)
            if maxprev < MIN_MAX_PREV:
                continue
            row_sites = {}
            for s in sites:
                p = round(float(prev[s][i]), 3)
                m = round(float(mean[s][i]), 5)
                if p > 0:
                    row_sites[s] = [p, m]
            if row_sites:
                taxon_stats.append({"taxon": taxon, "tier": tier, "sites": row_sites})
                kept += 1
        print(f"  taxa kept in browser (>= {MIN_MAX_PREV:.0%} prevalence somewhere): {kept}")

        # ---- Top taxa per body site (stacked bar) ----
        top_taxa[tier] = {}
        for s in sites:
            order = np.argsort(mean[s])[::-1]
            top = [{"taxon": feats[j], "mean_relab": round(float(mean[s][j]), 5)}
                   for j in order[:TOP_N] if mean[s][j] > 0]
            covered = sum(t["mean_relab"] for t in top)
            other = max(0.0, round(float(mean[s].sum()) - covered, 5))
            top.append({"taxon": "Other", "mean_relab": other})
            top_taxa[tier][s] = top

    meta = {
        "generated_by": "scripts/build_taxon_stats.py",
        "top_n": TOP_N,
        "browser_min_max_prevalence": MIN_MAX_PREV,
        "note": ("prevalence = fraction of samples in the body site where the taxon is "
                 "present (>0); mean_relab = mean relative abundance across samples in "
                 "the body site. Computed directly from the release relab tables."),
    }

    with open(os.path.join(DOCS, "js", "taxon_data.js"), "w") as fh:
        fh.write("/* Auto-generated by scripts/build_taxon_stats.py — real data, do not edit */\n")
        fh.write("const TAXON_META = " + json.dumps(meta) + ";\n")
        fh.write("const TAXON_STATS = " + json.dumps(taxon_stats) + ";\n")
        fh.write("const TOP_TAXA = " + json.dumps(top_taxa) + ";\n")

    with open(os.path.join(DOCS, "data", "taxon_stats.json"), "w") as fh:
        json.dump({"_meta": meta, "taxon_stats": taxon_stats, "top_taxa": top_taxa}, fh, indent=1)

    sz = os.path.getsize(os.path.join(DOCS, "js", "taxon_data.js"))
    print(f"\nTAXON_STATS rows: {len(taxon_stats)} | taxon_data.js = {sz/1024:.0f} KB")
    print("TOP_TAXA tiers/sites:", {t: list(d.keys()) for t, d in top_taxa.items()})


if __name__ == "__main__":
    main()
