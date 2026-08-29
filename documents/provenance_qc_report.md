# Per-Source Provenance & QC Report
**Corpus:** Harmonized two-tier cross-body-site human microbiome corpus v1.0
**Build date:** 2026-08-22 · **Total samples:** 30,680

## 1. Sources & access

| Source | Modality | Access | Samples | Body sites |
|---|---|---|---|---|
| curatedMetagenomicData 3.18.0 | Shotgun | Bioconductor (open) | 22,588 | stool, oral, skin, urogenital, respiratory, milk |
| American Gut Project (Qiita 10317) | 16S V4 | Qiita FTP / ENA PRJEB11419 (open) | 6,716 | stool, oral, skin, urogenital |
| MGnify demonstrator (12 studies) | 16S | EBI MGnify REST API (open) | 1,376 | skin, oral, respiratory, urogenital |

## 2. Shotgun tier (curatedMetagenomicData)
- **Profilers:** MetaPhlAn 3.0 (species), HUMAnN 3.0 (pathways).
- **Snapshot policy:** Per study, preferred 2021-10-14 snapshot; fell back to 2021-03-31, then 2021-04-02/2022-04-13/2022-10-19 for studies absent from 2021-10-14. cMD snapshots are keyed by study-addition date, not cumulative, so full 93-study coverage requires multiple dates.
- **Snapshot distribution:** {'2021-03-31': 55, '2021-04-02': 2, '2021-10-14': 29, '2022-04-13': 4, '2022-10-19': 3}
- **Sample key:** sample_uid = study_name:sample_id (sample_id alone collides across 177 shared IDs / 354 samples in 2 studies each)
- **Feature tables:** species 22,583 × 713; pathways 22,512 × 510 (after prevalence filter).
- **Value type:** relative abundance (per-sample sum = 1).
- **Download failures:** 0 / 93 studies.

## 3. 16S tier
### 3a. American Gut Project
- Precomputed rounds 1–21 (2.38 GB); `split/notrim/raw/` closed-reference OTU BIOM (Greengenes 13_8), V4 515F/806R.
- OTU taxonomy collapsed to **genus**; 6,716 human samples × 1,620 genera (raw).
- Within-subject multi-site: **363 subjects** sampled at >1 body site.

### 3b. MGnify demonstrator
- 12 amplicon studies chosen to add non-stool breadth (3 each: skin, oral, respiratory, urogenital); ≤200 samples/study.
- SSU OTU tables → genus collapse; 1,376 samples × 3,092 genera (raw).

### 3c. Harmonized 16S tier
- Genus vocabularies unioned (4,302 genera; 410 shared AGP∩MGnify), relative-abundance normalized, prevalence-filtered to **1,468 genera** (present in ≥40 samples).

## 4. Quality control
- **Duplicate sample IDs:** 0 across all 30,680 samples.
- **Body-site labeling:** 100%. **Metadata completeness:** age 80.9%, sex 87.1%, subject 95.5%, country 73.6%, disease 73.6%.

## 5. Technical validation (Bray–Curtis PCoA + PERMANOVA-style R²)
- **Shotgun:** body-site R² = 0.277, study R² = 0.3078 (n=1391). Body-site and study effects are comparable and confounded (studies differ by body site).
- **16S:** body-site R² = 0.3173 **>>** source R² = 0.1305 (n=1829). Biological (body-site) signal dominates the technical/source effect ≈2.4×.

## 6. Known limitations
- 16S and shotgun are kept as SEPARATE feature spaces (two tiers); do not merge naively.
- AGP (16S) is stool-dominated; MGnify demo supplies non-stool 16S breadth -> source confounded with body site in 16S tier (R2_source=0.13 vs R2_body_site=0.32).
- cMD study effect (R2=0.31) is comparable to body-site effect (R2=0.28) and confounded with it; condition on study for batch modeling.
- AD (AGMP/MARS) and PD disease cohorts are NOT included: AD is DUA-gated (AD Knowledge Portal); both are fine-tuning eval sets outside this pretraining-corpus descriptor.
- MGnify full catalog (774 studies) is provided as an index, not fully downloaded (per-sample API, rate-limited).
