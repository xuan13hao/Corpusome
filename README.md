# Corpusome, Harmonized cross-body-site human microbiome corpus — v1.1 (expanded)

A reusable pretraining resource for microbial representation learning:
**187,546 human microbiome samples** across **six body sites** and **two sequencing
modalities**, integrated from curatedMetagenomicData, the American Gut Project, and a
**full pull of the EBI MGnify human body-site catalogue** (708 studies).

**What changed from v1.0 (30,680 samples):** the 16S pretraining tier was scaled from
8,092 to **164,958 samples** by pulling the full MGnify human body-site catalogue via
study-level SSU taxonomy tables. Every non-stool body site grew by 1–2 orders of
magnitude (respiratory 335→40,833; oral 1,695→24,463; skin 1,246→14,635; urogenital
483→12,223). The shotgun tier (22,588) is unchanged.

---

## Folder layout

```
microbiome_corpus_v1.1_release/
├── README.md · MANIFEST.csv
├── data/
│   ├── metadata/
│   │   ├── corpus_metadata_catalog_expanded.{parquet,csv}   187,546 × 15 (incl. health_status)
│   │   └── mgnify_human_bodysite_studies.csv                774-study catalogue index
│   ├── shotgun/                shotgun tier (curatedMetagenomicData, unchanged)
│   │   ├── corpus_shotgun_species_relab.parquet   22,583 × 713   MetaPhlAn3 species
│   │   ├── corpus_shotgun_pathway_relab.parquet   22,512 × 510   HUMAnN3 pathways
│   │   └── corpus_shotgun_metadata.csv            22,588 × 14
│   ├── 16s/                     merged 16S tier (all sources, harmonized terminal-genus)
│   │   ├── corpus_16s_genus_relab_expanded.parquet   164,958 × 977
│   │   └── corpus_16s_metadata_expanded.csv          164,958 × 10
│   ├── 16s_mgnify_full/         MGnify full pull, per-rank (SILVA lineages)
│   │   ├── corpus_mgnify_{phylum,class,order,family,genus}_relab.parquet
│   │   │       157,905 × {61, 100, 197, 340, 808}
│   │   ├── mgnify_full_metadata.csv               156,866 × 6
│   │   └── mgnify_full_download_manifest.csv       per-study download log (resume/provenance)
│   └── multilevel/shotgun/      shotgun per-rank tables phylum…genus
├── documents/
│   ├── microbiome_corpus_manuscript.{pdf,md,html}  Scientific Data descriptor (updated)
│   ├── data_records_inventory.json                 machine-readable records (v1.1)
│   ├── fig_technical_validation.png                Figure 1 (ordination validation)
│   ├── fig_expanded_composition.png                Figure 2 (corpus growth)
│   ├── validation_qc_counts.csv · validation_summary.json
│   ├── provenance_qc_report.md · repository_deposit_checklist.md
└── pipeline/                    reproducible build (run.sh + numbered scripts + envs)
```

---

## Corpus at a glance

**Two tiers, kept separate** (different profilers/taxonomies — do not merge naively; `modality`
is a metadata column). Both tiers are released at every taxonomic rank from phylum down.

| Body site | 16S | Shotgun | Total |
|-----------|-----|---------|-------|
| Stool | 74,354 | 21,030 | 95,384 |
| Respiratory | 40,740 | 93 | 40,833 |
| Oral | 23,606 | 857 | 24,463 |
| Skin | 14,131 | 504 | 14,635 |
| Urogenital | 12,127 | 96 | 12,223 |
| Milk | — | 8 | 8 |
| **Total** | **164,958** | **22,588** | **187,546** |

**Health status** (`health_status` in the catalogue): healthy 14,566 / diseased 8,022 (141
conditions, shotgun tier only) / unlabeled 164,958 (the 16S tier). This is a pretraining
corpus — disease-labelled and neurodegenerative cohorts are out of scope.

**Taxonomic vocabulary note:** the MGnify full pull uses SILVA lineages; AGP uses Greengenes.
The merged 16S genus table (`corpus_16s_genus_relab_expanded.parquet`) harmonizes both on the
terminal genus token (e.g. `g__Bacteroides`). The per-rank MGnify tables under
`data/16s_mgnify_full/` keep the native SILVA labels.

## How to use

```python
import pandas as pd
X    = pd.read_parquet("data/16s/corpus_16s_genus_relab_expanded.parquet").set_index("sample_id")
meta = pd.read_parquet("data/metadata/corpus_metadata_catalog_expanded.parquet").set_index("sample_uid")
```
All feature tables are `samples × features`, relative abundance summing to 1. Pick the
taxonomic rank your model needs.

## Reproduce / extend

`cd pipeline && ./run.sh`. The MGnify pull (`scripts/03b_mgnify_full_download.py`) is
**resumable and memory-bounded** (<4 GB, one study at a time); its manifest lets an
interrupted run continue where it stopped, and re-running picks up any newly-added studies.

Version 1.1. Full provenance and per-file checksums in `MANIFEST.csv` and
`documents/data_records_inventory.json`.
