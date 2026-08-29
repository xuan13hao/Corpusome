#!/usr/bin/env python3
# ==========================================================================
# 05_validate.py  —  Technical validation: QC, PCoA, PERMANOVA-style R2, figure
#
# Writes to $OUT_DIR:
#   validation_qc_counts.csv, validation_permanova.json, fig_technical_validation.png
# ==========================================================================
import os, json
import numpy as np, pandas as pd
from scipy.spatial.distance import pdist, squareform
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.environ["OUT_DIR"]; SEED = int(os.environ.get("CORPUS_SEED", "0"))
np.random.seed(SEED)

cat = pd.read_parquet(os.path.join(OUT, "corpus_metadata_catalog.parquet"))

# ---- QC ----
qc = cat.groupby(['modality','source','body_site']).size().rename('n_samples').reset_index()
qc.to_csv(os.path.join(OUT, "validation_qc_counts.csv"), index=False)
dup = int(cat['sample_uid'].duplicated().sum())
completeness = {c: round(float(cat[c].notna().mean()), 3)
                for c in ['body_site','host_age','host_sex','subject_id','country','disease']}
print(f"[validate] dup sample_uid={dup}; completeness={completeness}")

# ---- ordination helpers ----
def pcoa_bray(X, k=2):
    D = squareform(pdist(X.values, metric='braycurtis'))
    n = D.shape[0]; J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D**2) @ J
    w, V = np.linalg.eigh(B); idx = np.argsort(w)[::-1]; w, V = w[idx], V[:, idx]
    coords = V[:, :k] * np.sqrt(np.maximum(w[:k], 0))
    return coords, np.maximum(w[:k], 0) / w[w > 0].sum(), D

def permanova_r2(D, groups):
    groups = np.asarray(groups); n = len(groups)
    ss_total = (D**2).sum() / (2 * n); ss_within = 0.0
    for g in np.unique(groups):
        i = np.where(groups == g)[0]
        if len(i) < 2: continue
        ss_within += (D[np.ix_(i, i)]**2).sum() / (2 * len(i))
    return 1 - ss_within / ss_total

def strat_subsample(meta, idx_col, group_col, cap=400):
    keep = []
    for _, g in meta.groupby(group_col):
        ids = list(g[idx_col])
        keep += list(np.random.choice(ids, cap, replace=False)) if len(ids) > cap else ids
    return keep

# ---- shotgun ordination ----
sp = pd.read_parquet(os.path.join(OUT, "corpus_shotgun_species_relab.parquet")).set_index('sample_uid')
sm = pd.read_csv(os.path.join(OUT, "corpus_shotgun_metadata.csv")).set_index('sample_uid')
sm = sm.loc[sm.index.intersection(sp.index)]
ks = strat_subsample(sm.reset_index(), 'sample_uid', 'body_site')
Xs = sp.loc[ks]; Xs = Xs.loc[Xs.sum(axis=1) > 0]
site_s = sm.loc[Xs.index, 'body_site']; study_s = sm.loc[Xs.index, 'study']
cs, ve_s, Ds = pcoa_bray(Xs)
r2_site_s = permanova_r2(Ds, site_s.values); r2_study_s = permanova_r2(Ds, study_s.values)

# ---- 16S ordination ----
g16 = pd.read_parquet(os.path.join(OUT, "corpus_16s_genus_relab.parquet")).set_index('sample_id')
m16 = pd.read_csv(os.path.join(OUT, "corpus_16s_metadata.csv")); m16['sample_id'] = m16['sample_id'].astype(str)
m16 = m16.set_index('sample_id'); g16.index = g16.index.astype(str)
common = g16.index.intersection(m16.index); g16 = g16.loc[common]; m16 = m16.loc[common]
k16 = strat_subsample(m16.reset_index(), 'sample_id', 'body_site')
X16 = g16.loc[k16]; X16 = X16.loc[X16.sum(axis=1) > 0]
site16 = m16.loc[X16.index, 'body_site']; src16 = m16.loc[X16.index, 'source']
c16, ve16, D16 = pcoa_bray(X16)
r2_site16 = permanova_r2(D16, site16.values); r2_src16 = permanova_r2(D16, src16.values)

perm = {"shotgun": {"R2_body_site": round(float(r2_site_s), 4), "R2_study": round(float(r2_study_s), 4),
                    "n_subsample": int(len(Xs))},
        "16S": {"R2_body_site": round(float(r2_site16), 4), "R2_source": round(float(r2_src16), 4),
                "n_subsample": int(len(X16))},
        "duplicate_sample_ids": dup, "metadata_completeness": completeness,
        "note": "PERMANOVA-style R2 (SS_between/SS_total) on Bray-Curtis, stratified subsample."}
json.dump(perm, open(os.path.join(OUT, "validation_permanova.json"), "w"), indent=1)
print(f"[validate] R2: {json.dumps(perm['shotgun'])} {json.dumps(perm['16S'])}")

# ---- figure ----
sites = ['stool','oral','skin','respiratory','urogenital','milk']
pal = dict(zip(sites, ['#4C72B0','#DD8452','#55A868','#C44E52','#8172B3','#937860']))
fig, ax = plt.subplots(2, 2, figsize=(9.2, 8.2)); axA, axB, axC, axD = ax.ravel()

piv = cat.pivot_table(index='body_site', columns='modality', values='sample_uid', aggfunc='count', fill_value=0)
piv = piv.reindex([s for s in sites if s in piv.index]); xp = np.arange(len(piv))
for off, mod, col in [(-0.15,'shotgun','#3B6BA5'), (0.15,'16S','#E0A458')]:
    v = piv.get(mod, pd.Series(0, index=piv.index)).astype(float).replace(0, np.nan)
    axA.vlines(xp+off, 1, v, color=col, lw=1.4, alpha=.8); axA.scatter(xp+off, v, s=26, color=col, label=mod, zorder=3)
axA.set_yscale('log'); axA.set_ylim(1, 6e4); axA.set_xticks(xp); axA.set_xticklabels(piv.index, rotation=30, ha='right')
axA.set_ylabel('samples (log scale)'); axA.set_title('a  Sample counts by body site and modality', loc='left', fontsize=9)
axA.legend(frameon=False, fontsize=6)
for panel, coords, ve, labels, palette, title in [
    (axB, cs, ve_s, site_s.values, pal, 'b  Shotgun tier: species PCoA (Bray-Curtis)'),
    (axC, c16, ve16, site16.values, pal, 'c  16S tier: genus PCoA, by body site'),
    (axD, c16, ve16, src16.values, {'AGP':'#2A9D8F','MGnify':'#E76F51'}, 'd  16S tier: same ordination, by source')]:
    for s in dict.fromkeys(labels):
        m = labels == s
        panel.scatter(coords[m,0], coords[m,1], s=6, alpha=.55, color=palette.get(s,'#888'), label=s, linewidths=0)
    panel.set_xlabel(f"PCo1 ({ve[0]*100:.1f}%)"); panel.set_ylabel(f"PCo2 ({ve[1]*100:.1f}%)")
    panel.set_xticks([]); panel.set_yticks([]); panel.set_title(title, loc='left', fontsize=9)
    panel.legend(frameon=False, fontsize=5.5, markerscale=1.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_technical_validation.png"), dpi=300, bbox_inches='tight')
print("[validate] wrote fig_technical_validation.png; done.")
