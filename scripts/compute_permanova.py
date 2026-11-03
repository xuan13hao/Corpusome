#!/usr/bin/env python3
"""
compute_permanova.py — technical-validation PERMANOVA-style R2 on the v1.2 release,
using the EXACT protocol of pipeline/scripts/05_validate.py
(Bray-Curtis; R2 = SS_between/SS_total; stratified subsample, cap 400 per group),
repeated over 20 seeds to report median + 95% interval.

Also computes a source-balanced 16S run (cap per body_site x source) for the
source-stratified comparison described in the manuscript.
"""
import os, json
import numpy as np, pandas as pd, pyarrow.parquet as pq
from scipy.spatial.distance import pdist, squareform

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
cat = pd.read_parquet(os.path.join(DATA, "metadata/corpus_metadata_catalog_expanded.parquet"))

def maps(key):
    k = (cat.sample_uid.astype(str).str.split(":", n=1).str[-1] if key == "local"
         else cat.sample_uid.astype(str))
    return (dict(zip(k, cat.body_site)), dict(zip(k, cat.source)), dict(zip(k, cat.study)))

def permanova_r2(D, groups):                 # identical formula to 05_validate.py
    groups = np.asarray(groups); n = len(groups)
    ss_total = (D**2).sum() / (2*n); ss_within = 0.0
    for g in np.unique(groups):
        i = np.where(groups == g)[0]
        if len(i) < 2: continue
        ss_within += (D[np.ix_(i, i)]**2).sum() / (2*len(i))
    return 1 - ss_within/ss_total

def load_ids(relab, idc, prefix):
    pf = pq.ParquetFile(relab); feats = [c for c in pf.schema.names if c.startswith(prefix)]
    return pf, feats

def matrix_for(pf, feats, idc, wanted):
    rows = []
    for b in pf.iter_batches(batch_size=4000):
        df = b.to_pandas(); df[idc] = df[idc].astype(str)
        sub = df[df[idc].isin(wanted)]
        if len(sub): rows.append(sub)
    X = pd.concat(rows, ignore_index=True)
    ids = X[idc].astype(str).values
    M = X[feats].to_numpy(dtype=np.float64, na_value=0.0)
    ok = M.sum(1) > 0
    return M[ok], ids[ok]

def ids_by(relab, idc, prefix, keyfn):
    pf = pq.ParquetFile(relab); feats = [c for c in pf.schema.names if c.startswith(prefix)]
    groups = {}
    for b in pf.iter_batches(batch_size=4000, columns=[idc]):
        for sid in b.to_pandas()[idc].astype(str):
            g = keyfn(sid)
            if g is not None: groups.setdefault(g, []).append(sid)
    return pf, feats, groups

def run(relab, idc, prefix, key, factors, strat="body_site", cap=400, seeds=range(20)):
    b2, s2, st2 = maps(key)
    facmap = {"body_site": b2, "source": s2, "study": st2}
    stratfn = (lambda sid: b2.get(sid)) if strat == "body_site" else \
              (lambda sid: (b2.get(sid), s2.get(sid)) if b2.get(sid) and s2.get(sid) else None)
    pf, feats, groups = ids_by(relab, idc, prefix, stratfn)
    out = {f: [] for f in factors}; ns = []
    for seed in seeds:
        rng = np.random.default_rng(seed); keep = set()
        for g, ids in groups.items():
            ids = np.array(ids)
            sel = ids if len(ids) <= cap else ids[rng.choice(len(ids), cap, replace=False)]
            keep.update(sel.tolist())
        M, ids = matrix_for(pf, feats, idc, keep)
        D = squareform(pdist(M, metric="braycurtis")); ns.append(len(ids))
        for f in factors:
            out[f].append(permanova_r2(D, np.array([facmap[f].get(i) for i in ids])))
    res = {f: {"median": round(float(np.median(out[f])), 4),
               "ci_lo": round(float(np.percentile(out[f], 2.5)), 4),
               "ci_hi": round(float(np.percentile(out[f], 97.5)), 4)} for f in factors}
    res["n_median"] = int(np.median(ns)); res["n_seeds"] = len(list(seeds))
    return res

G16 = os.path.join(DATA, "16s/corpus_16s_genus_relab_expanded.parquet")
SP  = os.path.join(DATA, "shotgun/corpus_shotgun_species_relab.parquet")

print("16S  (stratify by body_site, cap 400, 20 seeds):")
r16 = run(G16, "sample_id", "g__", "local", ["body_site", "source"], strat="body_site")
print(" ", json.dumps(r16))
print("16S  (stratify by body_site x source, cap 400 — source-balanced):")
r16b = run(G16, "sample_id", "g__", "local", ["body_site", "source"], strat="bs_src")
print(" ", json.dumps(r16b))
print("shotgun (stratify by body_site, cap 400, 20 seeds):")
rsg = run(SP, "sample_uid", "s__", "sample_uid", ["body_site", "study"], strat="body_site")
print(" ", json.dumps(rsg))

json.dump({"16S_bodysite_strat": r16, "16S_source_balanced": r16b, "shotgun_bodysite_strat": rsg},
          open(os.path.join(REPO, "documents", "validation_permanova_v1.2.json"), "w"), indent=1)
print("\nratio 16S body_site/source (body-site strat):",
      round(r16["body_site"]["median"]/r16["source"]["median"], 1))
print("ratio 16S body_site/source (source-balanced):",
      round(r16b["body_site"]["median"]/r16b["source"]["median"], 1))
