---
title: "A harmonized two-tier cross-body-site human microbiome corpus for microbial representation learning"
article_type: "Data Descriptor"
target_journal: "Scientific Data"
---

# A harmonized two-tier cross-body-site human microbiome corpus for microbial representation learning

**Authors:** [Author One]^1^, [Author Two]^1^, [Corresponding Author]^1,\*^

^1^[Affiliation]
\*Correspondence: [email]

---

## Abstract

Machine-learning models of the human microbiome are overwhelmingly trained on stool samples from single cohorts, which limits their capacity to represent the host–microbiome ecosystem across body sites and to generalize across studies. Progress on cross-niche, cross-study modelling is constrained less by algorithms than by the absence of a single harmonized multi-body-site corpus carrying the technical metadata needed to model — rather than ignore — batch structure. Here we assemble and release such a resource: a harmonized corpus of **187,546 human microbiome samples** integrating standardized profiles from three complementary public resources — curatedMetagenomicData, the American Gut Project, and the EBI MGnify platform. The corpus follows a deliberate **two-tier** design that preserves both functional depth and cross-body-site breadth: a **shotgun tier** (22,588 samples, 93 studies) with species-level taxonomic and pathway-level functional profiles, and a **16S tier** (164,958 samples) providing genus-level profiles that extend coverage into oral, skin, respiratory, and urogenital sites where shotgun data are sparse. The 16S tier is built from a full pull of the human body-site catalogue of MGnify (708 studies), assembled from study-level SSU rRNA taxonomy tables. In total the corpus spans **six body sites** and **two sequencing modalities**, with harmonized per-sample metadata (body site, modality, study/source, host covariates). Technical validation confirms that biological body-site signal is the dominant axis of variation and exceeds technical/source variance in the 16S tier by ≈2.4×. All harmonization and validation code is released as a one-command reproducible pipeline. The corpus is intended as a pretraining resource for microbial representation learning and as a benchmark for body-site and cross-study generalization.

---

## Background & Summary

The human microbiome varies profoundly across body sites: the communities of the gut, mouth, skin, airways, and urogenital tract differ in composition, diversity, and function. Yet the datasets used to train computational models of the microbiome are dominated by a single niche (stool) drawn from individual studies, and are typically confined to one sequencing modality. Models trained this way learn features that are entangled with cohort-specific technical artefacts and that do not transfer to other body sites or studies. Self-supervised "foundation model" approaches to microbial data have made this limitation explicit, identifying multi-body-site integration and cross-study generalization as the principal open problems.

Addressing those problems requires training data with three properties that no single public resource provides at once: (i) breadth across body sites, (ii) depth of functional characterization, and (iii) rich, harmonized technical metadata that lets biological and batch effects be separated during modelling. curatedMetagenomicData (cMD)^1^ offers depth — uniformly reprocessed shotgun taxonomic and functional profiles for tens of thousands of samples — but is dominated by stool. The American Gut Project (AGP)^2^ contributes a large, fully public citizen-science cohort with genuine within-subject multi-site sampling, but only as 16S amplicon data. The EBI MGnify platform^3^ hosts standardized profiles for hundreds of thousands of samples across every human body site, in both modalities, but serves them per-sample through a rate-limited API rather than as ready analysis matrices.

Here we integrate these three resources into a single harmonized corpus. Rather than force incompatible data types into one matrix — which would confound biological signal with primer-region and profiler differences — we adopt a **two-tier** design that keeps shotgun and 16S profiles as linked-but-separate feature spaces, with modality recorded as an explicit metadata field. The result is a corpus of 187,546 samples spanning six body sites and two modalities (Figure 1a), with per-sample body site, study/source, sequencing platform, and host covariates retained for batch-aware modelling. We provide feature tables (species, pathways, genera), a unified sample metadata catalogue, a machine-readable data-records inventory, and a one-command pipeline that reconstructs the corpus from primary sources. The corpus is designed as a pretraining and benchmarking resource; disease-labelled cohorts for downstream fine-tuning are described as external add-ons and are not part of this release.

---

## Methods

### Shotgun tier — curatedMetagenomicData

Standardized shotgun profiles were obtained from curatedMetagenomicData v3.18.0 (Bioconductor)^1^. Taxonomic profiles are MetaPhlAn 3.0 clade relative abundances; functional profiles are HUMAnN 3.0 pathway abundances. Because cMD ExperimentHub snapshots are keyed by study-addition date rather than being cumulative, complete coverage of all 93 studies required combining snapshots, with the 2021-10-14 snapshot preferred and older snapshots used as per-study fallbacks.

From the taxonomic tables we retained species-level clades — labels containing the `|s__` field and excluding the strain tag `|t__` — and assembled them into a samples × species matrix. From the functional tables we retained unstratified, community-level HUMAnN pathways (dropping per-species stratified rows) and kept the `UNMAPPED` and `UNINTEGRATED` bins. Samples were keyed as `sample_uid = study_name:sample_id`, because bare sample identifiers collide across studies. All 93 studies were retrieved without download failure.

### 16S tier — American Gut Project

The AGP precomputed release (rounds 1–21) was downloaded from the Qiita FTP mirror (open access; ENA study PRJEB11419 / ERP012803)^2^. We used the per-body-habitat closed-reference OTU BIOM tables from the `split/notrim/raw/` directory (Greengenes 13_8 reference; V4 region, 515F/806R primers). OTU taxonomy was collapsed to genus by summing counts within each full lineage; genera unresolved at the genus rank were labelled by their deepest assigned rank. AGP provides genuine within-subject multi-site coverage: 363 participants were sampled at more than one body site.

### 16S tier — MGnify demonstrator

To extend 16S coverage across all human body sites at scale, we performed a full pull of the MGnify human body-site catalogue^3^ (774 catalogued studies). Rather than the rate-limited per-sample API, we retrieved each study's **combined study-level SSU rRNA taxonomy table** (one file per study covering all its samples, carrying the full taxonomic lineage), which reduced acquisition from ≈12 s per sample to ≈1 s per study and made a whole-catalogue pull feasible. Of 774 catalogued studies, 770 were attempted in the download (the four studies present in the catalogue index but absent from the manifest — MGYS00006247, MGYS00005980, MGYS00006421, MGYS00005408 — were added to MGnify after the download was complete and are not included in this release); 708 provided a usable combined SSU table (yielding 157,915 samples); the remaining 62 had no usable SSU table (56 fungal ITS-only or shotgun-only studies, 6 download failures) and are logged in the download manifest. Lineage rows were aggregated to each taxonomic rank (phylum through genus). The downloader is resumable and memory-bounded: it processes one study at a time, writes each study's table to its own file, and records progress in an append-only manifest so an interrupted run continues where it stopped. An earlier 12-study demonstrator subset (three each for skin, oral, respiratory, urogenital; ≤200 samples per study) is retained within the 16S tier. The full catalogue index is also released as `mgnify_human_bodysite_studies.csv`.

### Harmonization

Body-site labels from all sources were mapped to a controlled vocabulary: stool, oral, skin, respiratory, urogenital, milk. Because the MGnify full pull uses SILVA-based lineages while AGP uses Greengenes, the 16S genus tables were harmonized on the terminal genus token (e.g. `g__Bacteroides`); of the 683 terminal genera in the earlier 16S tier, 514 are shared with the MGnify vocabulary. Each feature table was converted to per-sample relative abundance (L1 normalization) and prevalence-filtered, retaining features present in at least `max(10, 0.5% of samples)`. The expanded 16S genus table spans 164,958 samples × 977 genera; the shotgun tier retains 713 species and 510 pathways. Rank-specific 16S tables (phylum through genus) are released for the MGnify full pull, and shotgun tables span phylum through species. Sample-level metadata from all sources were merged into a single catalogue under a common schema (`sample_uid, source, study, modality, body_site, region, pipeline, host_age, host_sex, subject_id, country, sequencing_platform, disease, study_condition`).

### Reproducible pipeline

The full build is packaged as a one-command pipeline (`run.sh`) driving six numbered stages across two conda environments (Python 3.11 for acquisition/harmonization/validation; R 4.5 + Bioconductor 3.22 for cMD). Environment specifications are frozen as YAML files. Stochastic steps (the stratified subsampling used for validation ordinations) are seeded. Notably, the Bioconductor dependency `mia` imports `rbiom::unifrac`, an export removed in `rbiom ≥ 2.0`; the setup builds `rbiom 1.0.3` into an overlay library to restore a loadable cMD, a step documented in the pipeline README.

---

## Data Records

The corpus is deposited as a single versioned archive (see **Usage Notes**). Table 1 lists the released records; the complete schema, per-file checksums, and provenance are in `data_records_inventory.json`.

**Table 1. Released data records.**

| File | Content | Rows × Cols |
|------|---------|-------------|
| `corpus_metadata_catalog_expanded.csv` / `.parquet` | Unified sample metadata, all sources | 187,546 × 15 |
| `corpus_shotgun_{phylum,class,order,family,genus,species}_relab.parquet` | MetaPhlAn3 taxa, relative abundance, one table per rank | 22,584 × {14, 28, 48, 89, 206, 713} |
| `corpus_shotgun_pathway_relab.parquet` | HUMAnN3 pathway relative abundance | 22,512 × 510 |
| `corpus_shotgun_metadata.csv` | Shotgun sample metadata (harmonized schema) | 22,588 × 14 |
| `corpus_16s_genus_relab_expanded.parquet` | 16S genus relative abundance, all sources (harmonized terminal-genus) | 164,958 × 977 |
| `corpus_mgnify_phylum_relab.parquet` | MGnify full-pull 16S taxa, phylum | 157,905 × 61 |
| `corpus_mgnify_class_relab.parquet` | MGnify full-pull 16S taxa, class | 157,905 × 100 |
| `corpus_mgnify_order_relab.parquet` | MGnify full-pull 16S taxa, order | 157,865 × 197 |
| `corpus_mgnify_family_relab.parquet` | MGnify full-pull 16S taxa, family | 157,865 × 340 |
| `corpus_mgnify_genus_relab.parquet` | MGnify full-pull 16S taxa, genus | 156,866 × 808 |
| `corpus_16s_metadata_expanded.csv` | 16S sample metadata (all sources) | 164,958 × 10 |
| `mgnify_full_metadata.csv` | Per-sample metadata for the MGnify full pull | 156,866 × 6 |
| `mgnify_full_download_manifest.csv` | Per-study download log (resume/provenance) | 770 studies |
| `mgnify_human_bodysite_studies.csv` | MGnify catalogue index | 774 studies |
| `fig_technical_validation.png` | Technical-validation figure | — |

**Table 2. Corpus composition by body site and modality (sample counts).**

| Body site | 16S | Shotgun | Total |
|-----------|-----|---------|-------|
| Stool | 74,354 | 21,030 | 95,384 |
| Respiratory | 40,740 | 93 | 40,833 |
| Oral | 23,606 | 857 | 24,463 |
| Skin | 14,131 | 504 | 14,635 |
| Urogenital | 12,127 | 96 | 12,223 |
| Milk | — | 8 | 8 |
| **Total** | **164,958** | **22,588** | **187,546** |

**Taxonomic resolution.** To support modelling at multiple taxonomic scales, each tier is released at every rank from phylum to its finest available resolution — species for the shotgun tier (MetaPhlAn3), genus for the 16S tier (Greengenes lineages), plus phylum/class/order/family for both. Each rank is a separate per-sample relative-abundance table, prevalence-filtered under the same rule, and derived by summing the finest-rank profiles within each parent lineage (rank tables therefore nest consistently: a phylum abundance equals the sum of its constituent genera/species). Users select the resolution appropriate to their model; coarser ranks are denser and less study-specific, finer ranks carry more biological detail.

![**Figure 2. Corpus expansion via the MGnify full pull.** (**a**) Sample counts by body site before (v1.0, 30,680 samples) and after (v1.1, 187,546 samples) the full MGnify human body-site pull; every non-stool site grows by one to two orders of magnitude. (**b**) Composition of the expanded 16S tier by source (log scale).]({{artifact:b79d3f69-07e5-45a2-af77-f09a1407258b}})

**Health status.** Each sample carries a `health_status` field (healthy / diseased / unlabeled) in the metadata catalogue. The corpus is predominantly but not exclusively healthy: within the shotgun tier, 14,566 samples (64.5%) are from healthy/control participants and 8,022 (35.5%) carry a disease label spanning 141 conditions (most frequently inflammatory bowel disease, type 2 diabetes, and colorectal cancer). The 16S tier (American Gut Project, MGnify) is not disease-annotated and is marked `unlabeled` (164,958 samples). This healthy-plus-perturbed mixture is deliberate for a pretraining corpus: it exposes a model to both baseline and altered community states. It is distinct from the dedicated disease cohorts used for downstream fine-tuning, which are out of scope here (see Usage Notes).

All feature tables are keyed to the metadata catalogue by `sample_uid` (shotgun) or `sample_id` (16S). Feature-table values are per-sample relative abundances summing to 1.

---

## Technical Validation

![**Figure 1. Composition and technical validation of the corpus.** (**a**) Sample counts by body site and modality (log scale). (**b**) Principal-coordinates analysis (PCoA) of shotgun species profiles (Bray–Curtis dissimilarity), coloured by body site. (**c**) PCoA of 16S genus profiles, coloured by body site. (**d**) The same 16S ordination coloured by data source (AGP vs MGnify), showing that source structure aligns with the body-site axes rather than forming an independent batch. Ordinations use a body-site-stratified subsample (≤400 samples per site); percentages are variance explained by each principal coordinate.]({{artifact:3433d3d9-ca14-48e7-9dfb-fee2a650766c}})

**Body site is the dominant axis of variation.** Principal-coordinates analysis on Bray–Curtis dissimilarities separates samples by body site in both tiers (Figure 1b,c). We quantified this with a PERMANOVA-style variance partition (the ratio of between-group to total sum of squares) on body-site-stratified subsamples. In the 16S tier, body site explains R² = 0.32 of community variation versus R² = 0.13 for data source — biological signal exceeds the technical/source effect by ≈2.4× (Figure 1d). In the shotgun tier, body site (R² = 0.28) and study (R² = 0.31) explain comparable variance; because cMD studies differ systematically by body site, these two effects are partially confounded and should be modelled jointly rather than interpreted as independent.

**Integrity and completeness.** No duplicate sample identifiers occur across the 187,546 samples. Body site is labelled for 100% of samples; host age, sex, and subject identifiers are present for 80.9%, 87.1%, and 95.5% of samples, respectively. The American Gut Project's within-subject design is preserved: 363 participants are sampled at more than one body site, supporting paired cross-site analyses.

**Reproducibility.** The released pipeline reconstructs every corpus table from primary sources; running the harmonization and validation stages on the acquired inputs reproduces the reported dimensions and validation statistics exactly. Per-file SHA-256 checksums are provided.

---

## Usage Notes

- **Keep the tiers separate.** The shotgun (species/pathway) and 16S (genus) tiers use different profilers and reference taxonomies and are provided as linked-but-separate feature spaces. Modality is an explicit metadata column and should be used as a conditioning or batch variable, not marginalized away by naïvely concatenating the tiers.
- **Model batch structure.** Study (shotgun) and source (16S) are recorded per sample. Given the confounding between study and body site in the shotgun tier, we recommend conditioning on study identity (or applying reference-based normalization) and reporting results with and without batch correction.
- **Account for body-site imbalance.** Stool dominates both tiers; non-stool sites are comparatively better represented in the 16S tier. For balanced pretraining, consider body-site-stratified sampling, as used for the validation ordinations.
- **Extending the corpus.** The 16S tier already incorporates the full MGnify human body-site pull (708 studies). The resumable downloader (`03b_mgnify_full_download.py`) records per-study status in a manifest, so re-running it picks up any studies that failed or were newly added to MGnify; the shotgun tier can likewise be grown from newer curatedMetagenomicData snapshots.
- **Disease cohorts.** For downstream disease fine-tuning, Alzheimer's (AGMP/MARS, AD Knowledge Portal) and Parkinson's public shotgun cohorts are described in the deposit checklist. The Alzheimer's data are access-controlled and must be obtained under the relevant Data Use Agreement; they are not redistributed here.

---

## Data Availability

Derived feature tables, the metadata catalogue, the machine-readable inventory, and validation outputs are deposited under a single versioned DOI (to be minted at Zenodo/Figshare on acceptance; see `repository_deposit_checklist.md`). Raw sequence data remain in their original public archives and are cited rather than re-deposited: per-study ENA/SRA accessions for the shotgun tier (recorded in the cMD metadata), ENA PRJEB11419 / Qiita study 10317 for the American Gut Project, and the MGnify study accessions listed in the download manifest (`mgnify_full_download_manifest.csv`).

## Code Availability

The complete build pipeline — a one-command `run.sh`, six numbered stage scripts, frozen conda environment specifications, and documentation — is released as `microbiome_corpus_pipeline.tar.gz` and will be archived to Zenodo with a citable DOI at submission.

---

## References

1. Pasolli, E. et al. Accessible, curated metagenomic data through ExperimentHub. *Nat. Methods* **14**, 1023–1024 (2017).
2. McDonald, D. et al. American Gut: an open platform for citizen science microbiome research. *mSystems* **3**, e00031-18 (2018).
3. Richardson, L. et al. MGnify: the microbiome sequence data analysis resource in 2023. *Nucleic Acids Res.* **51**, D753–D759 (2023).
4. Beghini, F. et al. Integrating taxonomic, functional, and strain-level profiling of diverse microbial communities with bioBakery 3. *eLife* **10**, e65088 (2021).

---

*Author contributions, competing interests, and acknowledgements to be completed at submission.*
