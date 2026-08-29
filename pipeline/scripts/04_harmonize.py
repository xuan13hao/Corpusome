#!/usr/bin/env python3
# ==========================================================================
# 04_harmonize.py  —  Harmonize both tiers into the released corpus tables.
#
# Reads the raw per-source outputs from $DATA_DIR, writes final corpus tables
# to $OUT_DIR:
#   corpus_shotgun_species_relab.parquet   (RA, prevalence-filtered)
#   corpus_shotgun_pathway_relab.parquet
#   corpus_shotgun_metadata.csv
#   corpus_16s_genus_relab.parquet          (union vocab, RA, prevalence-filtered)
#   corpus_16s_genus_counts.parquet         (union vocab, raw counts, unfiltered)
#   corpus_16s_metadata.csv
#   corpus_metadata_catalog.csv / .parquet  (all sources, controlled schema)
#
# Feature spaces are kept SEPARATE (two tiers); modality is metadata.
# Prevalence filter: keep feature present (>0) in >= max(PREV_MIN_N, PREV_FRAC*n).
# ==========================================================================
import os, json, gc
import numpy as np, pandas as pd

DATA = os.environ["DATA_DIR"]; OUT = os.environ["OUT_DIR"]
PREV_FRAC = float(os.environ.get("PREV_FRAC", "0.005"))
PREV_MIN_N = int(os.environ.get("PREV_MIN_N", "10"))

SITE_MAP = {
    'stool':'stool','feces':'stool','fecal':'stool','gut':'stool','large intestine':'stool',
    'oral':'oral','oralcavity':'oral','oral cavity':'oral','saliva':'oral',
    'skin':'skin','hair':'skin',
    'vagina':'urogenital','urogenital':'urogenital','reproductive':'urogenital','vaginal':'urogenital',
    'nasal':'respiratory','nasalcavity':'respiratory','nose':'respiratory','respiratory':'respiratory',
    'nasopharyngeal':'respiratory','milk':'milk',
}
def norm_site(x):
    return np.nan if pd.isna(x) else SITE_MAP.get(str(x).strip().lower(), str(x).strip().lower())

def relab_prevfilter(df, key):
    """df: samples x features (index=sample id). Returns RA + prevalence-filtered."""
    X = df.copy(); X.index = X.index.astype(str)
    rs = X.sum(axis=1)
    ra = X.div(rs.replace(0, np.nan), axis=0).fillna(0.0)
    prev = (ra > 0).sum(axis=0); thr = max(PREV_MIN_N, int(PREV_FRAC * len(ra)))
    keep = prev[prev >= thr].index
    return ra[keep], thr

# ================= SHOTGUN =================
sp = pd.read_csv(os.path.join(DATA, "cmd_species_relab.csv.gz")).set_index("sample_uid")
sp_ra, thr_sp = relab_prevfilter(sp, "sample_uid")
sp_ra.reset_index().to_parquet(os.path.join(OUT, "corpus_shotgun_species_relab.parquet"), index=False)
print(f"[harmonize] shotgun species: {sp_ra.shape} (prev thr>={thr_sp})"); del sp, sp_ra; gc.collect()

pw = pd.read_csv(os.path.join(DATA, "cmd_pathway_relab.csv.gz")).set_index("sample_uid")
pw_ra, thr_pw = relab_prevfilter(pw, "sample_uid")
pw_ra.reset_index().to_parquet(os.path.join(OUT, "corpus_shotgun_pathway_relab.parquet"), index=False)
print(f"[harmonize] shotgun pathway: {pw_ra.shape} (prev thr>={thr_pw})"); del pw, pw_ra; gc.collect()

cmd_meta = pd.read_csv(os.path.join(DATA, "cmd_shotgun_metadata.csv"), low_memory=False)
if 'sample_uid' not in cmd_meta.columns:
    cmd_meta['sample_uid'] = cmd_meta['study_name'].astype(str) + ':' + cmd_meta['sample_id'].astype(str)
cmd_meta['body_site'] = cmd_meta['body_site'].map(norm_site)
shotgun_std = pd.DataFrame({
    'sample_uid': cmd_meta['sample_uid'].astype(str), 'source':'curatedMetagenomicData',
    'study': cmd_meta['study_name'], 'modality':'shotgun', 'body_site': cmd_meta['body_site'],
    'region': np.nan, 'pipeline':'MetaPhlAn3 + HUMAnN (cMD 3.18)',
    'host_age': pd.to_numeric(cmd_meta.get('age'), errors='coerce'), 'host_sex': cmd_meta.get('gender'),
    'subject_id': cmd_meta.get('subject_id'), 'country': cmd_meta.get('country'),
    'sequencing_platform': cmd_meta.get('sequencing_platform'), 'disease': cmd_meta.get('disease'),
    'study_condition': cmd_meta.get('study_condition')})
shotgun_std.to_csv(os.path.join(OUT, "corpus_shotgun_metadata.csv"), index=False)

# ================= 16S =================
agp_g = pd.read_parquet(os.path.join(DATA, "agp_genus_table.parquet"))
mgn_g = pd.read_parquet(os.path.join(DATA, "mgnify_16s_demo_genus_table.parquet"))
agp_g.index = agp_g.index.astype(str); mgn_g.index = mgn_g.index.astype(str)
all_genera = sorted(set(agp_g.columns) | set(mgn_g.columns))
print(f"[harmonize] 16S genera: AGP {agp_g.shape[1]}, MGnify {mgn_g.shape[1]}, "
      f"union {len(all_genera)}, shared {len(set(agp_g.columns) & set(mgn_g.columns))}")
genus16 = pd.concat([agp_g.reindex(columns=all_genera, fill_value=0),
                     mgn_g.reindex(columns=all_genera, fill_value=0)], axis=0)
genus16.index.name = 'sample_id'
genus16.reset_index().to_parquet(os.path.join(OUT, "corpus_16s_genus_counts.parquet"), index=False)
g16_ra, thr16 = relab_prevfilter(genus16, "sample_id")
g16_ra.reset_index().to_parquet(os.path.join(OUT, "corpus_16s_genus_relab.parquet"), index=False)
print(f"[harmonize] 16S genus RA: {g16_ra.shape} (prev thr>={thr16})")

# 16S metadata
agp_m = pd.read_csv(os.path.join(DATA, "agp_16s_metadata.csv"), low_memory=False)
if 'sample_id' not in agp_m.columns:
    agp_m = agp_m.rename(columns={agp_m.columns[0]: 'sample_id'})  # tolerate 'Unnamed: 0'
agp_m['body_site'] = agp_m['body_site'].map(norm_site)
agp_m2 = pd.DataFrame({'sample_id': agp_m['sample_id'].astype(str), 'source':'AGP', 'study':'Qiita_10317',
    'modality':'16S', 'body_site': agp_m['body_site'], 'region': agp_m.get('region','V4 (515F/806R)'),
    'pipeline': agp_m.get('pipeline','Greengenes 13_8 closed-ref'),
    'host_age': pd.to_numeric(agp_m.get('host_age'), errors='coerce'),
    'host_sex': agp_m.get('host_sex'), 'subject_id': agp_m.get('host_subject_id')})
mgn_m = pd.read_csv(os.path.join(DATA, "mgnify_16s_demo_metadata.csv"), low_memory=False)
mgn_m['body_site'] = mgn_m['body_site'].map(norm_site)
mgn_m2 = pd.DataFrame({'sample_id': mgn_m['sample_id'].astype(str), 'source':'MGnify',
    'study': mgn_m['study_accession'], 'modality':'16S', 'body_site': mgn_m['body_site'],
    'region': mgn_m.get('region'), 'pipeline': mgn_m.get('pipeline'),
    'host_age': np.nan, 'host_sex': np.nan, 'subject_id': np.nan})
meta16 = pd.concat([agp_m2, mgn_m2], ignore_index=True).drop_duplicates('sample_id')
meta16 = meta16[meta16['sample_id'].isin(g16_ra.index)]
meta16.to_csv(os.path.join(OUT, "corpus_16s_metadata.csv"), index=False)

# ================= UNIFIED CATALOG =================
cols = ['sample_uid','source','study','modality','body_site','region','pipeline',
        'host_age','host_sex','subject_id','country','sequencing_platform','disease','study_condition']
m16 = meta16.copy(); m16['sample_uid'] = m16['source'].astype(str) + ':' + m16['sample_id'].astype(str)
for c in ['country','sequencing_platform','disease','study_condition']:
    m16[c] = np.nan
catalog = pd.concat([shotgun_std[cols], m16[cols]], ignore_index=True)

# health_status: healthy / diseased / unlabeled (from disease + study_condition)
def _health(row):
    d = row['disease']
    if pd.isna(d):
        return 'healthy' if row.get('study_condition') == 'control' else 'unlabeled'
    d = str(d).strip().lower()
    return 'healthy' if d in ('healthy', 'control', '') else 'diseased'
catalog['health_status'] = catalog.apply(_health, axis=1)

catalog.to_csv(os.path.join(OUT, "corpus_metadata_catalog.csv"), index=False)
catalog.to_parquet(os.path.join(OUT, "corpus_metadata_catalog.parquet"), index=False)
print(f"[harmonize] unified catalog: {catalog.shape}")
print(catalog.groupby(['modality','source']).size().to_string())
print("[harmonize] done.")
