#!/usr/bin/env python3
"""Figure 3 — technical validation (4 panels), figures4papers style.
A) counts by body site x modality (log);  B) shotgun species PCoA;
C) 16S genus PCoA by body site;            D) 16S genus PCoA by source.
Real Bray-Curtis PCoA on a seeded body-site-stratified subsample."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f4p_style import apply_publication_style, finalize_figure, BODY_SITE_COLORS, MODALITY_COLORS, PALETTE
import numpy as np, pandas as pd, pyarrow.parquet as pq
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt

apply_publication_style(font_size=12)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(REPO, "data"); OUT = os.path.join(REPO, "manuscript", "figures")
os.makedirs(OUT, exist_ok=True)
SEED, CAP = 0, 300
rng = np.random.default_rng(SEED)
cat = pd.read_parquet(os.path.join(DATA, "metadata/corpus_metadata_catalog_expanded.parquet"))

def bs_map(key):
    k = (cat["sample_uid"].astype(str).str.split(":", n=1).str[-1] if key == "local"
         else cat["sample_uid"].astype(str))
    return dict(zip(k, cat.body_site)), dict(zip(k, cat.source))

def pcoa(relab, idc, prefix, key):
    b2, s2 = bs_map(key)
    pf = pq.ParquetFile(relab); feats = [c for c in pf.schema.names if c.startswith(prefix)]
    # choose stratified ids first
    ids_site = {}
    for batch in pf.iter_batches(batch_size=4000, columns=[idc]):
        for sid in batch.to_pandas()[idc].astype(str):
            bs = b2.get(sid)
            if bs: ids_site.setdefault(bs, []).append(sid)
    keep = set()
    for bs, ids in ids_site.items():
        ids = np.array(ids)
        sel = ids if len(ids) <= CAP else ids[rng.choice(len(ids), CAP, replace=False)]
        keep.update(sel.tolist())
    # load those rows
    rows = []
    for batch in pf.iter_batches(batch_size=4000):
        df = batch.to_pandas(); df[idc] = df[idc].astype(str)
        sub = df[df[idc].isin(keep)]
        if len(sub): rows.append(sub)
    X = pd.concat(rows, ignore_index=True)
    ids = X[idc].astype(str).values
    M = X[feats].to_numpy(dtype=np.float64, na_value=0.0)
    ok = M.sum(axis=1) > 0; M, ids = M[ok], ids[ok]
    D = squareform(pdist(M, metric="braycurtis")); n = len(D)
    J = np.eye(n) - np.ones((n, n))/n; B = -0.5*J@(D**2)@J
    w, V = np.linalg.eigh(B); o = np.argsort(w)[::-1]; w, V = w[o], V[:, o]
    C = V[:, :2]*np.sqrt(np.maximum(w[:2], 0)); ve = np.maximum(w[:2], 0)/w[w>0].sum()
    site = np.array([b2[i] for i in ids]); src = np.array([s2[i] for i in ids])
    return C, ve, site, src

print("PCoA: shotgun …"); Cs, ves, site_s, _ = pcoa(os.path.join(DATA,"shotgun/corpus_shotgun_species_relab.parquet"),"sample_uid","s__","sample_uid")
print("PCoA: 16S …");     C6, ve6, site6, src6 = pcoa(os.path.join(DATA,"16s/corpus_16s_genus_relab_expanded.parquet"),"sample_id","g__","local")

fig, axes = plt.subplots(2, 2, figsize=(10.5, 9.2))
(axA, axB), (axC, axD) = axes

# ── Panel A: counts by body site x modality ──────────────────────────────────
stats = json.load(open(os.path.join(REPO,"docs","data","stats.json")))["corpus"]["body_site_x_modality"]
sites = ["stool","respiratory","oral","skin","urogenital","brain","milk"]
x = np.arange(len(sites)); w = 0.4
y16 = [stats["16S"].get(s,0) or 0 for s in sites]
ysg = [stats["shotgun"].get(s,0) or 0 for s in sites]
axA.bar(x-w/2, [v if v>0 else np.nan for v in y16], w, color=MODALITY_COLORS["16S"], edgecolor="black", linewidth=1.2, label="16S", zorder=3)
axA.bar(x+w/2, [v if v>0 else np.nan for v in ysg], w, color=MODALITY_COLORS["shotgun"], edgecolor="black", linewidth=1.2, label="Shotgun", zorder=3)
axA.set_yscale("log"); axA.set_ylim(1,3e5); axA.set_xticks(x)
axA.set_xticklabels([s.capitalize() for s in sites], rotation=30, ha="right")
axA.set_ylabel("Samples (log scale)"); axA.legend(loc="upper right")
axA.yaxis.grid(True, which="major", color="#e5e7eb", zorder=0); axA.set_axisbelow(True)

def scatter(ax, C, site, ve, order):
    for s in order:
        m = site == s
        if m.any():
            ax.scatter(C[m,0], C[m,1], s=10, alpha=0.6, linewidths=0,
                       color=BODY_SITE_COLORS.get(s,"#888"), label=s.capitalize())
    ax.set_xlabel(f"PCo1 ({ve[0]*100:.1f}%)"); ax.set_ylabel(f"PCo2 ({ve[1]*100:.1f}%)")
    ax.set_xticks([]); ax.set_yticks([])

# ── Panel B: shotgun PCoA by body site ───────────────────────────────────────
scatter(axB, Cs, site_s, ves, ["stool","oral","skin","urogenital","respiratory","milk"])
axB.legend(loc="best", markerscale=2, handletextpad=0.2, labelspacing=0.3)

# ── Panel C: 16S PCoA by body site ───────────────────────────────────────────
scatter(axC, C6, site6, ve6, ["stool","oral","skin","respiratory","urogenital"])
axC.legend(loc="best", markerscale=2, handletextpad=0.2, labelspacing=0.3)

# ── Panel D: 16S PCoA by source ──────────────────────────────────────────────
SRC_COL = {"AGP": PALETTE["teal"], "MGnify_full": PALETTE["blue_main"], "MGnify": PALETTE["neutral"]}
SRC_LAB = {"AGP": "AGP", "MGnify_full": "MGnify (full)", "MGnify": "MGnify (selective)"}
for s in ["MGnify_full","AGP","MGnify"]:
    m = src6 == s
    if m.any():
        axD.scatter(C6[m,0], C6[m,1], s=10, alpha=0.55, linewidths=0, color=SRC_COL[s], label=SRC_LAB[s])
axD.set_xlabel(f"PCo1 ({ve6[0]*100:.1f}%)"); axD.set_ylabel(f"PCo2 ({ve6[1]*100:.1f}%)")
axD.set_xticks([]); axD.set_yticks([]); axD.legend(loc="best", markerscale=2)

for ax, lab in [(axA,"A"),(axB,"B"),(axC,"C"),(axD,"D")]:
    ax.text(-0.14, 1.04, lab, transform=ax.transAxes, fontsize=16, fontweight="bold", va="top")

paths = finalize_figure(fig, os.path.join(OUT,"Figure3_validation"))
print("saved:", *paths)
print(f"shotgun PCoA n={len(site_s)} ve={ves[:2]}; 16S PCoA n={len(site6)} ve={ve6[:2]}")
