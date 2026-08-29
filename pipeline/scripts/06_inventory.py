#!/usr/bin/env python3
# ==========================================================================
# 06_inventory.py  —  Build the machine-readable data-records inventory and
# the provenance/QC report from the produced corpus (no hardcoded counts).
# ==========================================================================
import os, json, hashlib
import pandas as pd

OUT = os.environ["OUT_DIR"]; DATA = os.environ["DATA_DIR"]

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def dims(fn):
    p = os.path.join(OUT, fn)
    if not os.path.exists(p): return None
    base = {"sha256": sha256(p), "size_bytes": os.path.getsize(p)}
    if fn.endswith(".parquet"):
        df = pd.read_parquet(p)
    elif fn.endswith(".csv"):
        df = pd.read_csv(p, low_memory=False)
    else:  # json / png / other — record hash + size only
        return base
    return {"rows": int(df.shape[0]), "cols": int(df.shape[1]), **base}

cat = pd.read_parquet(os.path.join(OUT, "corpus_metadata_catalog.parquet"))
perm = json.load(open(os.path.join(OUT, "validation_permanova.json")))
cmd_prov = {}
pth = os.path.join(DATA, "cmd_feature_provenance.json")
if os.path.exists(pth): cmd_prov = json.load(open(pth))

files = ["corpus_metadata_catalog.csv","corpus_metadata_catalog.parquet",
         "corpus_shotgun_pathway_relab.parquet","corpus_shotgun_metadata.csv",
         "corpus_16s_genus_relab.parquet","corpus_16s_genus_counts.parquet","corpus_16s_metadata.csv",
         "validation_qc_counts.csv","validation_permanova.json","fig_technical_validation.png"]
# multi-level rank tables (relative paths under output/)
for rk in ["phylum","class","order","family","genus","species"]:
    files.append(f"multilevel/shotgun/corpus_shotgun_{rk}_relab.parquet")
for rk in ["phylum","class","order","family"]:
    files.append(f"multilevel/16s/corpus_16s_{rk}_relab.parquet")

inventory = {
    "dataset_title": "A harmonized two-tier cross-body-site human microbiome corpus for microbial representation learning",
    "version": "1.0", "build_date": pd.Timestamp.now("UTC").strftime("%Y-%m-%d"),
    "n_samples_total": int(cat.shape[0]),
    "composition": cat.groupby(['modality','source']).size().to_dict().__repr__(),
    "body_site_by_modality": cat.pivot_table(index='body_site', columns='modality',
                              values='sample_uid', aggfunc='count', fill_value=0).to_dict(),
    "controlled_vocabularies": {"body_site": ["stool","oral","skin","respiratory","urogenital","milk"],
                                "modality": ["shotgun","16S"]},
    "data_records": [{"file": f, **(dims(f) or {"note": "not found"})} for f in files],
    "provenance_shotgun": cmd_prov,
    "technical_validation": perm,
    "known_limitations": [
        "16S and shotgun kept as SEPARATE feature spaces; do not merge naively.",
        "AGP (16S) is stool-dominated; MGnify demo supplies non-stool breadth -> source confounded with body site in 16S tier.",
        "cMD study effect comparable to and confounded with body-site effect; condition on study for batch modeling.",
        "AD (AGMP/MARS) and PD disease cohorts are external eval sets, not in this pretraining corpus; AD is DUA-gated.",
        "MGnify full catalogue (774 studies) provided as an index, not fully downloaded (per-sample API, rate-limited)."],
}
json.dump(inventory, open(os.path.join(OUT, "data_records_inventory.json"), "w"), indent=1, default=str)
print(f"[inventory] {len(inventory['data_records'])} records; total {inventory['n_samples_total']} samples")
