# Corpusome — Harmonized cross-body-site human microbiome corpus (v1.0)

A reusable pretraining resource for microbial representation learning:
**189,052 human microbiome samples** across **7 body sites** and **two sequencing
modalities** (16S amplicon + shotgun), integrated from curatedMetagenomicData, the
American Gut Project, a full pull of the EBI MGnify human body-site catalogue, and
six disease-specific cohorts (Alzheimer's, lung cancer, type-2 diabetes).

> **Every number in this repository and on the website is computed from the release
> files, not hand-written.** Run `scripts/build_site_stats.py` to regenerate the
> canonical statistics (`docs/data/stats.json`) and `scripts/build_manifest.py` to
> regenerate the checksums (`MANIFEST.csv`). If a number here ever disagrees with the
> output of those scripts, the scripts (i.e. the data) are authoritative.

---

## Corpus at a glance

Two tiers, **kept separate** (different profilers/taxonomies — do not merge naively;
`modality` is a metadata column).

| Body site   |      16S | Shotgun |     Total |
|-------------|---------:|--------:|----------:|
| Stool       |   74,354 |  21,472 |    95,826 |
| Respiratory |   40,740 |   1,069 |    41,809 |
| Oral        |   23,606 |     857 |    24,463 |
| Skin        |   14,131 |     504 |    14,635 |
| Urogenital  |   12,127 |      96 |    12,223 |
| Brain       |       88 |       — |        88 |
| Milk        |        — |       8 |         8 |
| **Total**   | **165,046** | **24,006** | **189,052** |

**Studies:** 781 total (MGnify full pull 681; curatedMetagenomicData 93; earlier
selective MGnify pull 12; plus the disease cohorts). The MGnify human body-site
catalogue index (`mgnify_human_bodysite_studies.csv`) lists 774 catalogued studies.

**Health status** (`health_status` in the catalogue): healthy 14,835 / diseased 9,245
(145 distinct conditions, shotgun tier only) / unlabeled 164,972 (the 16S tier).

**Taxonomic vocabulary note:** the MGnify full pull uses SILVA lineages; AGP uses
Greengenes. The merged 16S genus table (`corpus_16s_genus_relab_expanded.parquet`)
harmonizes both on the terminal genus token (e.g. `g__Bacteroides`). The per-rank
MGnify tables under `data/16s_mgnify_full/` keep the native SILVA labels.

---

## Folder layout

```
Corpusome/
├── README.md · MANIFEST.csv          (MANIFEST = path, size_bytes, sha256 for every file)
├── data/
│   ├── metadata/
│   │   ├── corpus_metadata_catalog_expanded.{parquet,csv}   189,052 × 15 (master catalogue)
│   │   └── mgnify_human_bodysite_studies.csv                774-study catalogue index
│   ├── shotgun/                       shotgun tier
│   │   ├── corpus_shotgun_species_relab.parquet   22,747 × 766   MetaPhlAn3 species
│   │   ├── corpus_shotgun_pathway_relab.parquet   22,512 × 511   HUMAnN3 pathways
│   │   └── corpus_shotgun_metadata.csv            24,006 rows
│   ├── 16s/                           merged 16S tier (harmonized terminal-genus)
│   │   └── corpus_16s_genus_relab_expanded.parquet   165,325 × 1,492
│   ├── 16s_mgnify_full/               MGnify full pull, per-rank (SILVA lineages)
│   │   ├── corpus_mgnify_phylum_relab.parquet     157,905 × 62
│   │   ├── corpus_mgnify_genus_relab.parquet      156,866 × 809
│   │   ├── mgnify_full_metadata.csv               156,866 rows
│   │   └── mgnify_full_download_manifest.csv       per-study download log
│   └── multilevel/shotgun/            shotgun per-rank tables phylum…genus
├── docs/                             project website (GitHub Pages)
│   └── data/stats.json              ← canonical statistics, generated from the data
├── documents/                        manuscript + provenance/validation reports
├── pipeline/                         data build (run.sh + numbered scripts + envs)
└── scripts/
    ├── build_site_stats.py          data → docs/data/stats.json + docs/js/site_data.js
    └── build_manifest.py            data → MANIFEST.csv (sizes + SHA-256)
```

> Note on row counts across MGnify ranks: the per-rank MGnify tables form a strict
> nested subset from phylum (157,905) down to genus (156,866). Samples drop at finer
> ranks when they fail to resolve there (40 lack an order-level assignment; a further
> 999 retain no genus feature after prevalence filtering). This is taxonomic-resolution
> dropout, not duplicate removal.

---

## How to use

```python
import pandas as pd
X    = pd.read_parquet("data/16s/corpus_16s_genus_relab_expanded.parquet").set_index("sample_id")
meta = pd.read_parquet("data/metadata/corpus_metadata_catalog_expanded.parquet").set_index("sample_uid")

# Always split by modality before downstream analysis:
meta_16s = meta[meta.modality == "16S"]
meta_shg = meta[meta.modality == "shotgun"]
```
All feature tables are `samples × features`, relative abundance summing to 1. Pick the
taxonomic rank your model needs.

## Reproduce

```bash
# 1. (Re)build the raw tables
cd pipeline && ./run.sh && cd ..

# 2. Regenerate the website statistics and the file manifest from the data
python3 scripts/build_site_stats.py     # -> docs/data/stats.json, docs/js/site_data.js
python3 scripts/build_manifest.py        # -> MANIFEST.csv (sizes + SHA-256)
```

The MGnify pull (`pipeline/scripts/03b_mgnify_full_download.py`) is resumable and
memory-bounded (<4 GB, one study at a time); its manifest lets an interrupted run
continue where it stopped.

## Cite

See [`docs/cite.html`](docs/cite.html). Dataset DOI: `10.5281/zenodo.22150633`
(CC BY 4.0). Preprint DOI: `10.64898/2026.08.28.747922`.
