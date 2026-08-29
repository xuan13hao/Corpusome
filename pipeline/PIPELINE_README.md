# Harmonized two-tier cross-body-site human microbiome corpus — build pipeline

One-click, reproducible construction of a 30,680-sample microbiome corpus spanning
six body sites and two sequencing modalities, from three public sources
(curatedMetagenomicData, American Gut Project, EBI MGnify).

## Quick start

```bash
./run.sh                 # full pipeline (builds conda envs, then all stages)
./run.sh --skip-setup    # if the two conda envs already exist
./run.sh harmonize       # resume from a stage: setup|shotgun|agp|mgnify|harmonize|validate|inventory
```

Outputs land in `output/`; per-stage logs in `logs/`; raw + intermediate data in `data/`.

## Requirements

- `conda` (or `mamba`/`micromamba`) on `PATH`
- ~15 GB free disk (AGP tarball is ~2.4 GB; cMD ExperimentHub cache grows during the shotgun stage)
- Internet access to `bioconductor.org` / ExperimentHub, `ftp.microbio.me`, `www.ebi.ac.uk`

## Pipeline stages

| # | Script | Env | Produces |
|---|--------|-----|----------|
| 0 | `00_setup_env.sh` + `00b_build_cmd_overlay.R` | — | conda envs `microbiome`, `cmd-bioc` |
| 1 | `01_shotgun_cmd.R` | cmd-bioc | cMD species + pathway tables, shotgun metadata |
| 2 | `02_16s_agp.py` | microbiome | AGP genus table + metadata |
| 3 | `03_16s_mgnify.py` | microbiome | MGnify demonstrator genus table + metadata + manifest |
| 4 | `04_harmonize.py` | microbiome | **final corpus tables** (species/pathway/genus + unified catalog w/ `health_status`) |
| 4b | `04b_multilevel_16s.py` | microbiome | 16S rank tables: phylum, class, order, family |
| 4c | `01b_shotgun_multilevel.R` + `04c_multilevel_shotgun.py` | cmd-bioc, microbiome | shotgun rank tables: phylum..species |
| 5 | `05_validate.py` | microbiome | QC counts, PERMANOVA-style R², technical-validation figure |
| 6 | `06_inventory.py` | microbiome | machine-readable `data_records_inventory.json` |

### Taxonomic resolution & health status

- **Every rank is released**, not just the finest. Shotgun: phylum/class/order/family/genus/species;
  16S: phylum/class/order/family/genus. Each rank is a separate prevalence-filtered
  relative-abundance table under `output/multilevel/{shotgun,16s}/`, derived by summing the finest
  profiles within each parent lineage (ranks nest consistently). Pick the resolution your model needs.
- **`health_status`** column in `corpus_metadata_catalog.*`: `healthy` (14,566) / `diseased` (8,022,
  spanning 142 conditions — IBD, T2D, CRC, …) / `unlabeled` (8,092, the un-annotated 16S tier).
  The corpus is majority-healthy but deliberately includes perturbed states for pretraining.

## The two environments

- **`microbiome`** (Python 3.11): pandas, pyarrow, scipy, h5py, biom-format, scikit-bio, matplotlib.
- **`cmd-bioc`** (R 4.5, Bioconductor 3.22): curatedMetagenomicData 3.18.0.
  A dependency (`mia`) imports `rbiom::unifrac`, which `rbiom >= 2.0` removed, so the setup
  builds `rbiom 1.0.3` from source into an **overlay library** (`data/cmd_rlib`) and installs
  cMD there. Every R invocation prepends the overlay via `R_LIBS` (set in `scripts/_config.sh`).
  Frozen environment specs are in `envs/*.yml`.

## Design choices (see `provenance_qc_report.md`)

- **Two tiers, kept separate.** Shotgun (species + pathway) and 16S (genus) use different
  profilers/taxonomies; they are linked-but-separate feature spaces. `modality` is a metadata
  column, not a mixed axis. Do **not** merge the two into one matrix.
- **Relative abundance + prevalence filter.** All feature tables are per-sample L1-normalized;
  features present in `< max(10, 0.5% of samples)` are dropped. Raw-count union of the 16S
  vocabulary is also kept (`corpus_16s_genus_counts.parquet`) for reproducibility.
- **Controlled vocabularies.** Body sites are normalized to
  `stool / oral / skin / respiratory / urogenital / milk`.
- **Batch structure retained.** `study` (shotgun) and `source` (16S) are recorded per sample
  for downstream batch modeling.

## Scope & exclusions

- Disease cohorts (Alzheimer's AGMP/MARS; Parkinson's shotgun) are **not** part of this
  pretraining corpus — they are downstream fine-tuning/evaluation sets. The AD data are
  access-controlled (Data Use Agreement) and cannot be redistributed.
- The full MGnify human catalogue (774 studies, ~160k samples) is included as a documented
  expansion index (`data/mgnify_human_bodysite_studies.csv`), not fully downloaded; scale the
  16S tier by extending `03_16s_mgnify.py`'s study list.

## Determinism

`CORPUS_SEED=0` (in `_config.sh`) fixes the stratified subsampling used for the validation
ordinations. The corpus tables themselves are deterministic given the upstream source versions.
Note that live MGnify/cMD contents can change over time; pinned versions are recorded in
`output/data_records_inventory.json` and `data/cmd_feature_provenance.json`.
