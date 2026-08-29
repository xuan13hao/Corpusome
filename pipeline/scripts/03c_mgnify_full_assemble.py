#!/usr/bin/env python3
# ==========================================================================
# 03c_mgnify_full_assemble.py  —  Assemble per-study MGnify lineage tables into
# multi-level relative-abundance corpus tables (ALL ranks), memory-bounded.
#
# Input : $DATA_DIR/mgnify_full/tables/*.parquet  (rows = full SILVA lineage,
#         cols = "{MGYS}:{run}", values = counts)  + manifest.csv
# Output: $OUT_DIR/multilevel_mgnify_full/corpus_mgnify_{rank}_relab.parquet
#         + $OUT_DIR/mgnify_full_metadata.csv
#
# Two passes per rank keep memory < 4 GB on 157k samples:
#   pass 1  count per-taxon prevalence (n samples with count>0) across all studies
#   -> keep taxa present in >= max(PREV_MIN_N, PREV_FRAC * n_samples)
#   pass 2  build samples × kept-taxa relative-abundance blocks (one study in RAM
#           at a time), concatenate, write parquet.
# Rank label = terminal token at that rank (e.g. g__Bacteroides), so the SILVA
# vocabulary aligns across reference DBs / pipeline versions.
# ==========================================================================
import os, glob, gc
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data"); OUT = os.environ.get("OUT_DIR", "output")
PREV_FRAC = float(os.environ.get("PREV_FRAC", "0.005")); PREV_MIN_N = int(os.environ.get("PREV_MIN_N", "10"))
WORK = os.path.join(DATA, "mgnify_full", "tables")
DST = os.path.join(OUT, "multilevel_mgnify_full"); os.makedirs(DST, exist_ok=True)

RANK_PREFIX = {"phylum": "p__", "class": "c__", "order": "o__", "family": "f__", "genus": "g__"}
files = sorted(glob.glob(os.path.join(WORK, "*.parquet")))
print(f"[assemble] {len(files)} study tables")

def rank_label(lineage, prefix):
    """Terminal taxon name at `prefix` rank, or None if absent/empty."""
    for seg in lineage.split(";"):
        seg = seg.strip()
        if seg.startswith(prefix):
            return seg if len(seg) > len(prefix) else None  # drop empty 'g__'
    return None

# ---- metadata (from manifest body_site mapping, one row per sample) ----
man = pd.read_csv(os.path.join(DATA, "mgnify_full", "manifest.csv"), dtype=str)
man = man.drop_duplicates("accession", keep="last")
site_of = dict(zip(man["accession"], man["body_site"]))

def study_rank_frame(f, prefix):
    """Return samples×taxa (terminal-token) DataFrame for one study at a rank."""
    df = pd.read_parquet(f)                 # lineage × samples
    labels = [rank_label(str(l), prefix) for l in df.index]
    df = df.assign(_lab=labels).dropna(subset=["_lab"])
    if df.empty:
        return None
    agg = df.groupby("_lab").sum()          # taxa × samples
    return agg.T                            # samples × taxa

for rank, prefix in RANK_PREFIX.items():
    # ---- pass 1: global prevalence ----
    prev = {}
    n_samples = 0
    for f in files:
        t = study_rank_frame(f, prefix)
        if t is None: continue
        n_samples += t.shape[0]
        pc = (t > 0).sum(axis=0)
        for k, v in pc.items():
            prev[k] = prev.get(k, 0) + int(v)
        del t
    thr = max(PREV_MIN_N, int(PREV_FRAC * n_samples))
    keep = sorted([k for k, v in prev.items() if v >= thr])
    print(f"[assemble] {rank}: {n_samples} samples, {len(prev)} taxa -> {len(keep)} kept (thr>={thr})")
    if not keep:
        continue
    keep_idx = {k: i for i, k in enumerate(keep)}
    # ---- pass 2: build relative-abundance blocks on kept taxa only ----
    blocks = []
    sample_ids = []
    for f in files:
        t = study_rank_frame(f, prefix)
        if t is None: continue
        # relative abundance per sample over ALL taxa (not just kept), then subset
        rs = t.sum(axis=1).replace(0, np.nan)
        t = t.div(rs, axis=0).fillna(0.0)
        # matrix on kept columns
        M = np.zeros((t.shape[0], len(keep)), dtype="float32")
        cols = [c for c in t.columns if c in keep_idx]
        if cols:
            ci = [keep_idx[c] for c in cols]
            M[:, ci] = t[cols].to_numpy(dtype="float32")
        blocks.append(M)
        sample_ids.extend(list(t.index))
        del t, M; gc.collect()
    big = np.vstack(blocks); del blocks; gc.collect()
    out = pd.DataFrame(big, columns=keep); out.insert(0, "sample_id", sample_ids)
    out.to_parquet(os.path.join(DST, f"corpus_mgnify_{rank}_relab.parquet"), index=False)
    print(f"[assemble] wrote corpus_mgnify_{rank}_relab.parquet {out.shape}")
    del big, out; gc.collect()

# ---- metadata (sample order from a produced rank table) ----
ref = None
for rank in ["genus", "family", "phylum"]:
    p = os.path.join(DST, f"corpus_mgnify_{rank}_relab.parquet")
    if os.path.exists(p):
        ref = pd.read_parquet(p, columns=["sample_id"]); break
if ref is not None:
    meta = ref.copy()
    meta["study_accession"] = meta["sample_id"].str.split(":").str[0]
    meta["body_site"] = meta["study_accession"].map(site_of)
    meta["modality"] = "16S"; meta["source"] = "MGnify_full"; meta["pipeline"] = "MGnify SSU"
    meta.to_csv(os.path.join(OUT, "mgnify_full_metadata.csv"), index=False)
    print(f"[assemble] metadata: {meta.shape}; per body_site:")
    print(meta["body_site"].value_counts().to_dict())
print("[assemble] done.")
