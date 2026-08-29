#!/usr/bin/env python3
# ==========================================================================
# 04c_multilevel_shotgun.py  —  Relative-abundance + prevalence-filter the
# shotgun multi-level rank tables produced by 01b_shotgun_multilevel.R
# ($DATA_DIR/multilevel/shotgun/cmd_<rank>_relab.csv.gz) into
# $OUT_DIR/multilevel/shotgun/corpus_shotgun_<rank>_relab.parquet.
# ==========================================================================
import os, gc
import numpy as np, pandas as pd

DATA = os.environ["DATA_DIR"]; OUT = os.environ["OUT_DIR"]
PREV_FRAC = float(os.environ.get("PREV_FRAC", "0.005")); PREV_MIN_N = int(os.environ.get("PREV_MIN_N", "10"))
srcd = os.path.join(DATA, "multilevel", "shotgun"); dstd = os.path.join(OUT, "multilevel", "shotgun")
os.makedirs(dstd, exist_ok=True)

def relab_prev(df):
    ra = df.div(df.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    thr = max(PREV_MIN_N, int(PREV_FRAC * len(ra)))
    keep = (ra > 0).sum(axis=0); keep = keep[keep >= thr].index
    return ra[keep], thr

for rank in ["phylum", "class", "order", "family", "genus", "species"]:
    f = os.path.join(srcd, f"cmd_{rank}_relab.csv.gz")
    if not os.path.exists(f):
        print(f"[shotgun-multilevel] {rank}: source missing, skipped"); continue
    df = pd.read_csv(f).set_index("sample_uid")
    ra, thr = relab_prev(df)
    ra.reset_index().to_parquet(os.path.join(dstd, f"corpus_shotgun_{rank}_relab.parquet"), index=False)
    print(f"[shotgun-multilevel] {rank:8s}: {ra.shape[0]} x {ra.shape[1]} (prev thr>={thr})")
    del df, ra; gc.collect()
print("[shotgun-multilevel] done.")
