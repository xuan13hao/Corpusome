#!/usr/bin/env python3
"""
Draw 6 individual figures (no assembly):
  fig_technical_validation_a.png  – lollipop: sample counts by body site & modality
  fig_technical_validation_b.png  – shotgun species PCoA (Bray-Curtis)
  fig_technical_validation_c.png  – 16S genus PCoA, by body site
  fig_technical_validation_d.png  – 16S genus PCoA, by source
  fig_expanded_composition_a.png  – corpus growth v1.0 vs v1.1 by body site
  fig_expanded_composition_b.png  – 16S tier sources

Usage:
    python3 redraw_figures.py

Requirements: numpy, pandas, scipy, matplotlib
"""
import os
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA = "/home/xuan/microbiome_corpus_v1.1_release/data"
DOCS = "/home/xuan/microbiome_corpus_v1.1_release/documents"

# ── Style ─────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":     "Arial",
    "axes.labelsize":  12,        # x/y axis label font size
    "xtick.labelsize": 12,        # x tick label font size
    "ytick.labelsize": 12,        # y tick label font size
})
DPI  = 300
SEED = 0
np.random.seed(SEED)

# ── Body-site order & colour palette ─────────────────────────────────────────
SITES = ['stool', 'oral', 'skin', 'respiratory', 'urogenital', 'milk']
PAL   = dict(zip(SITES, ['#4C72B0', '#DD8452', '#55A868',
                          '#C44E52', '#8172B3', '#937860']))

# ── Helpers ───────────────────────────────────────────────────────────────────
def pcoa_bray(X, k=2):
    """Bray-Curtis PCoA; returns (coords, variance_explained)."""
    D  = squareform(pdist(X.values, metric='braycurtis'))
    n  = D.shape[0]
    J  = np.eye(n) - np.ones((n, n)) / n
    B  = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx  = np.argsort(w)[::-1]
    w, V = w[idx], V[:, idx]
    coords = V[:, :k] * np.sqrt(np.maximum(w[:k], 0))
    return coords, np.maximum(w[:k], 0) / w[w > 0].sum()

def strat_subsample(meta, idx_col, group_col, cap=400):
    """Stratified random subsample (cap samples per group)."""
    keep = []
    for _, g in meta.groupby(group_col):
        ids = list(g[idx_col])
        keep += (list(np.random.choice(ids, cap, replace=False))
                 if len(ids) > cap else ids)
    return keep

def save(fig, name):
    path = os.path.join(DOCS, name)
    fig.savefig(path, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  saved → {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Load data (shared by multiple panels)
# ─────────────────────────────────────────────────────────────────────────────
print("Loading metadata catalog …")
cat = pd.read_parquet(
    os.path.join(DATA, "metadata/corpus_metadata_catalog_expanded.parquet"))
cat = cat[cat['source'] != 'MGnify'].copy()   # exclude 12-study demonstrator subset

print("Loading shotgun data …")
sp = pd.read_parquet(
    os.path.join(DATA, "shotgun/corpus_shotgun_species_relab.parquet")
).set_index('sample_uid')
sm = pd.read_csv(
    os.path.join(DATA, "shotgun/corpus_shotgun_metadata.csv")
).set_index('sample_uid')
sm     = sm.loc[sm.index.intersection(sp.index)]
ks     = strat_subsample(sm.reset_index(), 'sample_uid', 'body_site')
Xs     = sp.loc[ks]
Xs     = Xs.loc[Xs.sum(axis=1) > 0]
site_s = sm.loc[Xs.index, 'body_site']
print(f"  shotgun subsample: {len(Xs)} samples; computing PCoA …")
cs, ve_s = pcoa_bray(Xs)

print("Loading 16S data …")
g16 = pd.read_parquet(
    os.path.join(DATA, "16s/corpus_16s_genus_relab_expanded.parquet")
).set_index('sample_id')
m16 = pd.read_csv(
    os.path.join(DATA, "16s/corpus_16s_metadata_expanded.csv"), low_memory=False)
m16['sample_id'] = m16['sample_id'].astype(str)
m16 = m16.set_index('sample_id')
m16 = m16[m16['source'] != 'MGnify'].copy()   # exclude 12-study demonstrator subset
g16.index = g16.index.astype(str)
common = g16.index.intersection(m16.index)
g16 = g16.loc[common]
m16 = m16.loc[common]
k16    = strat_subsample(m16.reset_index(), 'sample_id', 'body_site')
X16    = g16.loc[k16]
X16    = X16.loc[X16.sum(axis=1) > 0]
site16 = m16.loc[X16.index, 'body_site']
src16  = m16.loc[X16.index, 'source']
print(f"  16S subsample: {len(X16)} samples; computing PCoA …")
c16, ve16 = pcoa_bray(X16)

# ─────────────────────────────────────────────────────────────────────────────
# fig_technical_validation_a — lollipop: sample counts by body site & modality
# ─────────────────────────────────────────────────────────────────────────────
print("Drawing fig_technical_validation_a …")
piv    = cat.pivot_table(index='body_site', columns='modality',
                         values='sample_uid', aggfunc='count', fill_value=0)
piv    = piv.reindex([s for s in SITES if s in piv.index])
totals = piv.sum(axis=1)
xp     = np.arange(len(piv))

fig, ax = plt.subplots(figsize=(5.5, 4.5))
for off, mod, col in [(-0.15, 'shotgun', '#3B6BA5'), (0.15, '16S', '#E0A458')]:
    v = piv.get(mod, pd.Series(0, index=piv.index)).astype(float).replace(0, np.nan)
    ax.vlines(xp + off, 1, v, color=col, lw=1.4, alpha=.8)
    ax.scatter(xp + off, v, s=26, color=col, label=mod, zorder=3)

# Annotate total count centred between the two stems (avoids being mistaken for
# the 16S-only value when the orange lollipop is taller)
for i, site in enumerate(piv.index):
    shot = piv.get('shotgun', pd.Series(0, index=piv.index)).get(site, 0)
    s16  = piv.get('16S',     pd.Series(0, index=piv.index)).get(site, 0)
    ymax = max(shot, s16) if max(shot, s16) > 0 else 1
    ax.annotate(f"n={int(totals[site]):,}", xy=(i, ymax),
                xytext=(0, 6), textcoords='offset points',
                ha='center', va='bottom', fontsize=7.5, color='#333333')

ax.set_yscale('log')
ax.set_ylim(1, 3e5)
ax.set_xticks(xp)
ax.set_xticklabels(piv.index, rotation=30, ha='right')
ax.set_ylabel('samples (log scale)')
ax.legend(frameon=False, fontsize=9)
fig.tight_layout()
save(fig, "fig_technical_validation_a.png")

# ─────────────────────────────────────────────────────────────────────────────
# fig_technical_validation_b — shotgun species PCoA (Bray-Curtis), by body site
# ─────────────────────────────────────────────────────────────────────────────
print("Drawing fig_technical_validation_b …")
fig, ax = plt.subplots(figsize=(5, 4.5))
for s in dict.fromkeys(site_s.values):
    m = site_s.values == s
    ax.scatter(cs[m, 0], cs[m, 1], s=6, alpha=.55,
               color=PAL.get(s, '#888'), label=s, linewidths=0)
ax.set_xlabel(f"PCo1 ({ve_s[0] * 100:.1f}%)")
ax.set_ylabel(f"PCo2 ({ve_s[1] * 100:.1f}%)")
ax.set_xticks([])
ax.set_yticks([])
ax.legend(frameon=False, fontsize=8, markerscale=2)
fig.tight_layout()
save(fig, "fig_technical_validation_b.png")

# ─────────────────────────────────────────────────────────────────────────────
# fig_technical_validation_c — 16S genus PCoA, by body site
# ─────────────────────────────────────────────────────────────────────────────
print("Drawing fig_technical_validation_c …")
fig, ax = plt.subplots(figsize=(5, 4.5))
for s in dict.fromkeys(site16.values):
    m = site16.values == s
    ax.scatter(c16[m, 0], c16[m, 1], s=6, alpha=.55,
               color=PAL.get(s, '#888'), label=s, linewidths=0)
ax.set_xlabel(f"PCo1 ({ve16[0] * 100:.1f}%)")
ax.set_ylabel(f"PCo2 ({ve16[1] * 100:.1f}%)")
ax.set_xticks([])
ax.set_yticks([])
ax.legend(frameon=False, fontsize=8, markerscale=2)
fig.tight_layout()
save(fig, "fig_technical_validation_c.png")

# ─────────────────────────────────────────────────────────────────────────────
# fig_technical_validation_d — 16S genus PCoA, by source
# ─────────────────────────────────────────────────────────────────────────────
print("Drawing fig_technical_validation_d …")
src_pal = {'AGP': '#2A9D8F', 'MGnify_full': '#457B9D'}
src_labels = {'AGP': 'AGP', 'MGnify_full': 'MGnify'}
fig, ax = plt.subplots(figsize=(5, 4.5))
for s in dict.fromkeys(src16.values):
    if s not in src_pal:
        continue
    m = src16.values == s
    ax.scatter(c16[m, 0], c16[m, 1], s=6, alpha=.55,
               color=src_pal[s], label=src_labels[s], linewidths=0)
ax.set_xlabel(f"PCo1 ({ve16[0] * 100:.1f}%)")
ax.set_ylabel(f"PCo2 ({ve16[1] * 100:.1f}%)")
ax.set_xticks([])
ax.set_yticks([])
ax.legend(frameon=False, fontsize=8, markerscale=2)
fig.tight_layout()
save(fig, "fig_technical_validation_d.png")

# ─────────────────────────────────────────────────────────────────────────────
# fig_expanded_composition_a — sample counts by body site (v1.1)
# ─────────────────────────────────────────────────────────────────────────────
print("Drawing fig_expanded_composition_a …")

# body-site counts computed from filtered catalog (MGnify demo subset excluded)
v11  = cat.groupby('body_site')['sample_uid'].count().to_dict()
x2   = np.arange(len(SITES))
vals = [v11.get(s, 1) for s in SITES]
fig, ax = plt.subplots(figsize=(6, 4.5))
ax.bar(x2, vals, width=0.55, color='#2E5FA3', alpha=0.85, zorder=2)

ax.set_yscale('log')
ax.set_ylim(1, 3e5)
ax.set_xticks(x2)
ax.set_xticklabels(SITES, rotation=30, ha='right')
ax.set_ylabel('samples (log scale)')
ax.yaxis.grid(True, which='both', alpha=0.3, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
save(fig, "fig_expanded_composition_a.png")

# ─────────────────────────────────────────────────────────────────────────────
# fig_expanded_composition_b — 16S tier sources (horizontal bars)
# ─────────────────────────────────────────────────────────────────────────────
print("Drawing fig_expanded_composition_b …")

# 16S source counts (MGnify demo subset excluded; MGnify_full displayed as "MGnify")
sources_16s = {
    'AGP':    6716,
    'MGnify': 156866,   # MGnify_full renamed
}
src_names  = list(sources_16s.keys())
src_vals   = [sources_16s[k] for k in src_names]
src_colors = ['#E0943A', '#3B7EC0']

fig, ax = plt.subplots(figsize=(6, 3.0))
bars = ax.barh(src_names, src_vals, color=src_colors, height=0.5, zorder=2)
for bar, val in zip(bars, src_vals):
    ax.text(val * 1.04, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va='center', ha='left', fontsize=10)

ax.set_xscale('log')
ax.set_xlim(1, 5e5)
ax.set_xlabel('samples (log scale)')
ax.xaxis.grid(True, which='both', alpha=0.3, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
save(fig, "fig_expanded_composition_b.png")

print("\nAll 6 figures written.")
