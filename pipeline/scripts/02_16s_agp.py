#!/usr/bin/env python3
# ==========================================================================
# 02_16s_agp.py  —  16S TIER, PART A: American Gut Project (Qiita 10317)
#
# Downloads the precomputed rounds 1-21 release from the Qiita FTP mirror
# (open access; ENA study PRJEB11419 / ERP012803), extracts the per-body-
# habitat closed-reference OTU BIOM tables from split/notrim/raw/ (Greengenes
# 13_8; V4 515F/806R), collapses OTU taxonomy to GENUS, and writes:
#   $DATA_DIR/agp_genus_table.parquet   samples x genus (int counts)
#   $DATA_DIR/agp_16s_metadata.csv      per-sample body_site + host covariates
# ==========================================================================
import os, sys, subprocess, tarfile
from collections import OrderedDict
import numpy as np, pandas as pd, scipy.sparse as sp
import biom

DATA = os.environ["DATA_DIR"]
TARBALL = os.path.join(DATA, "ag-precomputed.tar.gz")
URL = "https://ftp.microbio.me/AmericanGut/ag-precomputed-rounds-1-21.tar.gz"
EXTRACT = os.path.join(DATA, "agp_extract")
RAW = "ag-precomputed-rounds-1-21/split/notrim/raw"

# ---- 1. download (skip if present) ----
if not os.path.exists(TARBALL) or os.path.getsize(TARBALL) < 2_000_000_000:
    print(f"[agp] downloading {URL} (~2.4 GB)")
    subprocess.run(["curl", "-sL", "-o", TARBALL, URL], check=True)
print(f"[agp] tarball: {os.path.getsize(TARBALL)/1e9:.2f} GB")

# ---- 2. extract only the raw per-habitat biom + metadata ----
os.makedirs(EXTRACT, exist_ok=True)
with tarfile.open(TARBALL, "r:gz") as tf:
    members = [m for m in tf.getmembers()
               if m.name.startswith(RAW) and (m.name.endswith(".biom") or m.name.endswith(".txt"))]
    tf.extractall(EXTRACT, members=members)
rawdir = os.path.join(EXTRACT, RAW)
print(f"[agp] extracted {len(os.listdir(rawdir))} files to {rawdir}")

# ---- 3. genus collapse (verbatim logic used to build the corpus) ----
def genus_key(tax):
    levels = [x.strip() for x in (tax[:6] if len(tax) >= 6 else tax)]
    g = levels[5] if len(levels) >= 6 else 'g__'
    if g in ('g__', 'g__unclassified', '', None) or g.endswith('__'):
        resolved = [l for l in levels if l and not l.endswith('__')]
        deepest = resolved[-1] if resolved else 'Unassigned'
        return f"Unassigned_{deepest}"
    return ';'.join(levels)

def collapse_biom_to_genus(path):
    t = biom.load_table(path)
    obs_ids = t.ids('observation'); samp_ids = t.ids('sample')
    md = t.metadata(axis='observation')
    keys = [genus_key(o.get('taxonomy')) if (o and o.get('taxonomy')) else 'Unassigned' for o in md]
    uniq = list(OrderedDict.fromkeys(keys)); kidx = {k: i for i, k in enumerate(uniq)}
    rows = [kidx[k] for k in keys]
    M = sp.csr_matrix((np.ones(len(keys)), (rows, list(range(len(keys))))),
                      shape=(len(uniq), len(obs_ids)))
    genus_by_samp = M.dot(t.matrix_data)
    return pd.DataFrame.sparse.from_spmatrix(genus_by_samp.T, index=samp_ids, columns=uniq)

# habitat -> harmonized body_site (controlled vocabulary)
site_map = {'feces': 'stool', 'oral cavity': 'oral', 'skin': 'skin',
            'nose': 'skin', 'hair': 'skin', 'vagina': 'urogenital'}
habitats = ['feces', 'oral cavity', 'skin', 'nose', 'hair', 'vagina']

frames, sample_site = {}, {}
for hab in habitats:
    fn = os.path.join(rawdir, f"otu_table__BODY_HABITAT_UBERON:{hab}__.biom")
    if not os.path.exists(fn):
        print(f"[agp]   WARN missing {hab}"); continue
    df = collapse_biom_to_genus(fn); frames[hab] = df
    for sid in df.index:
        sample_site[sid] = (hab, site_map[hab])
    print(f"[agp]   {hab:12s} -> {df.shape[0]} samples, {df.shape[1]} genera")

all_genera = sorted(set().union(*[set(f.columns) for f in frames.values()]))
parts = []
for hab, df in frames.items():
    d = df.sparse.to_dense() if hasattr(df, 'sparse') else df
    parts.append(d.reindex(columns=all_genera, fill_value=0))
agp = pd.concat(parts, axis=0).reindex(columns=all_genera, fill_value=0).fillna(0).astype('int32')
agp.index.name = 'sample_id'
agp.to_parquet(os.path.join(DATA, "agp_genus_table.parquet"))
print(f"[agp] genus table: {agp.shape}")

# ---- 4. metadata (body_site + host covariates from mapping files) ----
def read_meta(hab):
    fn = os.path.join(rawdir, f"metadata__BODY_HABITAT_UBERON:{hab}__.txt")
    if not os.path.exists(fn): return None
    m = pd.read_csv(fn, sep='\t', dtype=str, low_memory=False)
    idc = m.columns[0]; m = m.rename(columns={idc: 'sample_id'})
    keep = {'sample_id': m['sample_id']}
    for src, dst in [('AGE_YEARS', 'host_age'), ('age', 'host_age'),
                     ('SEX', 'host_sex'), ('sex', 'host_sex'),
                     ('HOST_SUBJECT_ID', 'host_subject_id'), ('host_subject_id', 'host_subject_id')]:
        if src in m.columns and dst not in keep:
            keep[dst] = m[src]
    return pd.DataFrame(keep)

metas = [read_meta(h) for h in habitats]
meta = pd.concat([x for x in metas if x is not None], ignore_index=True).drop_duplicates('sample_id')
meta = meta[meta['sample_id'].isin(agp.index)].copy()
meta['body_site'] = meta['sample_id'].map(lambda s: sample_site.get(s, (None, None))[1])
meta['body_habitat_raw'] = meta['sample_id'].map(lambda s: sample_site.get(s, (None, None))[0])
meta['modality'] = '16S'; meta['source'] = 'AGP'; meta['study'] = 'Qiita_10317'
meta['region'] = 'V4 (515F/806R)'; meta['pipeline'] = 'Greengenes 13_8 closed-ref'
meta.to_csv(os.path.join(DATA, "agp_16s_metadata.csv"), index=False)
print(f"[agp] metadata: {meta.shape}; multi-site subjects: "
      f"{(meta.dropna(subset=['host_subject_id']).groupby('host_subject_id')['body_site'].nunique() > 1).sum()}")
print("[agp] done.")
