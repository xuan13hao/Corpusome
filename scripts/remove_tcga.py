#!/usr/bin/env python3
"""
remove_tcga.py — remove the TCGA Poore-2020 cohort (retracted 2024) from the
release data files. TCGA (1,549 samples, source=TCGA_Poore2020) is Kraken2-only,
so only the catalogue, the Kraken2 genus table and the shotgun metadata change;
the MetaPhlAn species / 16S genus feature tables are untouched.

After this, run build_site_stats.py, build_taxon_stats.py, build_manifest.py to
regenerate all derived outputs.
"""
import os
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(REPO, "data", *p)

def main():
    # 1) catalogue (parquet + csv)
    for ext, reader, writer in [
        ("parquet", pd.read_parquet, lambda df, p: df.to_parquet(p, index=False)),
        ("csv", lambda p: pd.read_csv(p, low_memory=False), lambda df, p: df.to_csv(p, index=False)),
    ]:
        p = D("metadata", f"corpus_metadata_catalog_expanded.{ext}")
        df = reader(p); n0 = len(df)
        df = df[df["source"] != "TCGA_Poore2020"].copy()
        writer(df, p)
        print(f"catalog.{ext}: {n0} -> {len(df)}")

    # 2) shotgun metadata csv
    p = D("shotgun", "corpus_shotgun_metadata.csv")
    df = pd.read_csv(p, low_memory=False); n0 = len(df)
    df = df[df["source"] != "TCGA_Poore2020"].copy()
    df.to_csv(p, index=False)
    print(f"shotgun_metadata.csv: {n0} -> {len(df)}")

    # 3) Kraken2 genus table (keep BALF, drop TCGA rows)
    p = D("shotgun", "corpus_kraken2_genus_relab.parquet")
    df = pd.read_parquet(p); n0 = len(df)
    idc = df.columns[0]
    df = df[~df[idc].astype(str).str.startswith("TCGA:")].copy()
    df.to_parquet(p, index=False)
    print(f"kraken2_genus_relab.parquet: {n0} -> {len(df)} (kept BALF)")

    print("\nTCGA removed. Now run: build_site_stats.py, build_taxon_stats.py, build_manifest.py")

if __name__ == "__main__":
    main()
