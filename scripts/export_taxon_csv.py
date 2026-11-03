#!/usr/bin/env python3
"""
export_taxon_csv.py — export the Taxa-page analysis as CSV files so the figures
can be re-drawn externally.

Outputs (under exports/):
  taxa_prevalence_abundance_long.csv
      Tidy, ONE row per (tier, taxon, body_site): prevalence and mean relative
      abundance for EVERY genus (16S) and species (shotgun). No prevalence filter.
  taxa_top_by_bodysite.csv
      The dominant-taxa-per-body-site table behind the stacked bar (top 12 per
      body site + an "Other" remainder), with mean relative abundance.

Both are computed directly from the release relative-abundance tables.

Usage:
    python3 scripts/export_taxon_csv.py
"""
import os
import csv
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
OUT  = os.path.join(REPO, "exports")
CATALOG = os.path.join(DATA, "metadata", "corpus_metadata_catalog_expanded.parquet")

TOP_N = 12

TIERS = {
    "16S": {
        "relab": os.path.join(DATA, "16s/corpus_16s_genus_relab_expanded.parquet"),
        "relab_id": "sample_id", "catalog_key": "local", "prefix": "g__",
        "rank": "genus",
    },
    "shotgun": {
        "relab": os.path.join(DATA, "shotgun/corpus_shotgun_species_relab.parquet"),
        "relab_id": "sample_uid", "catalog_key": "sample_uid", "prefix": "s__",
        "rank": "species",
    },
}


def body_site_map(cat, key):
    k = (cat["sample_uid"].astype(str).str.split(":", n=1).str[-1]
         if key == "local" else cat["sample_uid"].astype(str))
    return dict(zip(k, cat["body_site"]))


def accumulate(relab_path, id_col, prefix, id2site):
    pf = pq.ParquetFile(relab_path)
    feats = [c for c in pf.schema.names if c.startswith(prefix)]
    nfeat = len(feats)
    sums, nz, n = {}, {}, {}
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


def clean(t):
    return t.replace("g__", "").replace("s__", "").replace("_", " ")


def main():
    os.makedirs(OUT, exist_ok=True)
    cat = pd.read_parquet(CATALOG, columns=["sample_uid", "body_site"])

    long_rows = []
    top_rows = []

    for tier, cfg in TIERS.items():
        print(f"{tier}: computing …")
        id2site = body_site_map(cat, cfg["catalog_key"])
        feats, sums, nz, n = accumulate(cfg["relab"], cfg["relab_id"], cfg["prefix"], id2site)
        sites = sorted(n, key=lambda s: -n[s])
        mean = {s: sums[s] / n[s] for s in sites}
        prev = {s: nz[s] / n[s] for s in sites}

        # full long table (all taxa x all body sites)
        for i, taxon in enumerate(feats):
            for s in sites:
                long_rows.append({
                    "tier": tier,
                    "rank": cfg["rank"],
                    "taxon": taxon,
                    "taxon_name": clean(taxon),
                    "body_site": s,
                    "n_samples_in_site": n[s],
                    "prevalence": round(float(prev[s][i]), 6),
                    "mean_relative_abundance": round(float(mean[s][i]), 8),
                })

        # top taxa per body site (stacked bar source)
        for s in sites:
            order = np.argsort(mean[s])[::-1]
            covered = 0.0
            rank = 0
            for j in order[:TOP_N]:
                if mean[s][j] <= 0:
                    break
                rank += 1
                covered += float(mean[s][j])
                top_rows.append({
                    "tier": tier, "body_site": s, "rank": rank,
                    "taxon": feats[j], "taxon_name": clean(feats[j]),
                    "mean_relative_abundance": round(float(mean[s][j]), 8),
                    "mean_relative_abundance_pct": round(float(mean[s][j]) * 100, 4),
                })
            other = max(0.0, float(mean[s].sum()) - covered)
            top_rows.append({
                "tier": tier, "body_site": s, "rank": rank + 1,
                "taxon": "Other", "taxon_name": "Other",
                "mean_relative_abundance": round(other, 8),
                "mean_relative_abundance_pct": round(other * 100, 4),
            })

    f1 = os.path.join(OUT, "taxa_prevalence_abundance_long.csv")
    with open(f1, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(long_rows[0].keys()))
        w.writeheader(); w.writerows(long_rows)

    f2 = os.path.join(OUT, "taxa_top_by_bodysite.csv")
    with open(f2, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(top_rows[0].keys()))
        w.writeheader(); w.writerows(top_rows)

    print(f"\nWrote {os.path.relpath(f1, REPO)}  ({len(long_rows)} rows)")
    print(f"Wrote {os.path.relpath(f2, REPO)}  ({len(top_rows)} rows)")


if __name__ == "__main__":
    main()
