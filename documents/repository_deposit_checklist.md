# Repository Deposit Checklist (Scientific Data)

## Recommended deposition
- **Feature tables + metadata + inventory** → **Zenodo** (or Figshare): single versioned DOI for the whole corpus.
  Files: corpus_metadata_catalog.{csv,parquet}, corpus_shotgun_species_relab.parquet,
  corpus_shotgun_pathway_relab.parquet, corpus_shotgun_metadata.csv,
  corpus_16s_genus_relab.parquet, corpus_16s_genus_counts.parquet, corpus_16s_metadata.csv,
  data_records_inventory.json, provenance_qc_report.md, validation_*.{csv,json},
  fig_technical_validation.png, mgnify_human_bodysite_studies.csv
- **Raw sequences:** NOT re-deposited — already in public archives; cite the original accessions:
  - cMD → per-study ENA/SRA (in cMD metadata: NCBI_accession / PMID)
  - AGP → ENA PRJEB11419 (ERP012803), Qiita 10317
  - MGnify → 12 MGYS accessions (see data_records_inventory.json > provenance.16S_mgnify)

## Scientific Data submission requirements
- [ ] ISA-Tab / data-records table linking each file to a repository DOI
- [ ] Data Descriptor manuscript (Background, Methods, Data Records, Technical Validation, Usage Notes)
- [ ] Machine-readable metadata (data_records_inventory.json) — DONE
- [ ] License: CC-BY 4.0 for derived tables; note upstream licenses (cMD, AGP public-domain, MGnify)
- [ ] Code availability: harmonization scripts (this project's lineage) on GitHub + archived to Zenodo
- [ ] Confirm no controlled-access data included (AD Knowledge Portal EXCLUDED — DUA-gated)

## External add-on (not in this deposit)
- AD: AGMP/MARS via AD Knowledge Portal (Sage Bionetworks DUA) — describe, do not redistribute.
- PD: public shotgun cohorts (Wallen 2022 etc.) — fine-tuning eval, separate release.
