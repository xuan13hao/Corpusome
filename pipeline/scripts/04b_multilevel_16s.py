#!/usr/bin/env python3
# ==========================================================================
# 04b_multilevel_16s.py  —  Derive phylum/class/order/family relative-abundance
# tables for the 16S tier by re-aggregating the raw-count union genus table
# (its column labels carry the full Greengenes lineage). No re-download.
# Writes to $OUT_DIR/multilevel/16s/. The genus table (with unassigned taxa)
# remains corpus_16s_genus_relab.parquet from 04_harmonize.py.
# ==========================================================================
import os, re, gc
import numpy as np, pandas as pd

OUT = os.environ["OUT_DIR"]
PREV_FRAC = float(os.environ.get("PREV_FRAC", "0.005")); PREV_MIN_N = int(os.environ.get("PREV_MIN_N", "10"))
os.makedirs(os.path.join(OUT, "multilevel", "16s"), exist_ok=True)

cnt = pd.read_parquet(os.path.join(OUT, "corpus_16s_genus_counts.parquet")).set_index("sample_id")
cnt.index = cnt.index.astype(str)

RANKS = {"phylum": "p__", "class": "c__", "order": "o__", "family": "f__"}
def rank_label(col, marker):
    if col == "Unassigned" or col.startswith("Unassigned"):
        return None  # unresolved lineages excluded from clean rank tables
    keep = []
    for p in col.split(";"):
        keep.append(p.strip())
        if p.strip().startswith(marker):
            return ";".join(keep)
    return None

def relab_prev(df):
    ra = df.div(df.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    thr = max(PREV_MIN_N, int(PREV_FRAC * len(ra)))
    keep = (ra > 0).sum(axis=0); keep = keep[keep >= thr].index
    return ra[keep], thr

for rank, marker in RANKS.items():
    groups = {}
    for c in cnt.columns:
        lab = rank_label(c, marker)
        if lab is not None:
            groups.setdefault(lab, []).append(c)
    tab = pd.DataFrame({lab: cnt[cols].sum(axis=1) for lab, cols in groups.items()}, index=cnt.index)
    ra, thr = relab_prev(tab)
    ra.reset_index().to_parquet(os.path.join(OUT, "multilevel", "16s", f"corpus_16s_{rank}_relab.parquet"), index=False)
    print(f"[16s-multilevel] {rank:8s}: {ra.shape[0]} x {ra.shape[1]} (prev thr>={thr})")
    del tab, ra; gc.collect()
print("[16s-multilevel] done.")
