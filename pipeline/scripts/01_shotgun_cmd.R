#!/usr/bin/env Rscript
# ==========================================================================
# 01_shotgun_cmd.R  —  SHOTGUN TIER from curatedMetagenomicData 3.18.0
#
# Produces (in $DATA_DIR):
#   cmd_species_relab.csv.gz   samples x species  MetaPhlAn3 relative abundance
#   cmd_pathway_relab.csv.gz   samples x pathways HUMAnN3   relative abundance
#   cmd_shotgun_metadata.csv   full sampleMetadata + modality/source columns
#   cmd_feature_provenance.json
#
# Species = MetaPhlAn clades containing |s__ and NOT |t__ (strain).
# Pathways = unstratified community-level HUMAnN pathways (rownames w/o '|').
# Sample key = sample_uid = study_name:sample_id  (bare sample_id collides).
# ==========================================================================
suppressWarnings({
  overlay <- Sys.getenv("R_OVERLAY_LIB"); .libPaths(c(overlay, .libPaths()))
})
suppressMessages({
  library(curatedMetagenomicData); library(dplyr); library(data.table)
  library(jsonlite); library(SummarizedExperiment); library(TreeSummarizedExperiment)
})
DATA <- Sys.getenv("DATA_DIR"); SNAP <- Sys.getenv("CMD_SNAPSHOT", "2021-10-14")
stopifnot(DATA != "")

sm <- as.data.frame(sampleMetadata)
sm$sample_uid <- paste0(sm$study_name, ":", sm$sample_id)
studies <- unique(sm$study_name)
cat(sprintf("[shotgun] %d samples, %d studies\n", nrow(sm), length(studies)))

# ---- helper: fetch one assay for one study, return samples x features dt ----
fetch_assay <- function(study, assay) {
  # Try preferred snapshot, then fall back across known cMD snapshot dates.
  snaps <- unique(c(SNAP, "2021-03-31", "2021-04-02", "2022-04-13", "2022-10-19"))
  for (s in snaps) {
    res <- tryCatch(
      curatedMetagenomicData(paste0(s, ".", study, ".", assay),
                             dryrun = FALSE, rownames = "long"),
      error = function(e) NULL)
    if (!is.null(res) && length(res) >= 1) {
      se <- res[[1]]
      mat <- assay(se)                              # features x samples
      return(list(mat = mat, snap = s))
    }
  }
  NULL
}

split_species <- function(mat) mat[grepl("\\|s__", rownames(mat)) &
                                   !grepl("\\|t__", rownames(mat)), , drop = FALSE]
split_pathway <- function(mat) mat[!grepl("\\|", rownames(mat)), , drop = FALSE]

collect <- function(assay, splitter, label) {
  cols <- list(); snap_used <- c(); failed <- c()
  for (st in studies) {
    r <- fetch_assay(st, assay)
    if (is.null(r)) { failed <- c(failed, st); next }
    m <- splitter(r$mat); snap_used[st] <- r$snap
    if (ncol(m) == 0) next
    # rename to species/pathway short label (last |-field for species)
    if (label == "species") rownames(m) <- sub(".*\\|", "", rownames(m))
    df <- as.data.table(t(as.matrix(m)), keep.rownames = "sample_id")
    df[, sample_uid := paste0(st, ":", sample_id)][, sample_id := NULL]
    cols[[st]] <- df
  }
  tab <- rbindlist(cols, use.names = TRUE, fill = TRUE)
  for (j in names(tab)) if (j != "sample_uid") set(tab, which(is.na(tab[[j]])), j, 0)
  setcolorder(tab, "sample_uid")
  list(tab = tab, snap = snap_used, failed = failed)
}

cat("[shotgun] collecting species (relative_abundance) ...\n")
sp <- collect("relative_abundance", split_species, "species")
fwrite(sp$tab, file.path(DATA, "cmd_species_relab.csv.gz"))
cat(sprintf("  species table: %d x %d  (failed studies: %d)\n",
            nrow(sp$tab), ncol(sp$tab) - 1, length(sp$failed)))

cat("[shotgun] collecting pathways (pathway_abundance) ...\n")
pw <- collect("pathway_abundance", split_pathway, "pathway")
fwrite(pw$tab, file.path(DATA, "cmd_pathway_relab.csv.gz"))
cat(sprintf("  pathway table: %d x %d\n", nrow(pw$tab), ncol(pw$tab) - 1))

# ---- metadata ----
sm$modality <- "shotgun"; sm$source <- "curatedMetagenomicData"
fwrite(sm, file.path(DATA, "cmd_shotgun_metadata.csv"))

prov <- list(
  corpus_tier = "shotgun", source = "curatedMetagenomicData",
  package_version = as.character(packageVersion("curatedMetagenomicData")),
  snapshot_preferred = SNAP,
  profiler_taxonomic = "MetaPhlAn 3.0", profiler_functional = "HUMAnN 3.0",
  value_type = "relative_abundance (per-sample sum = 1 after renorm)",
  sample_key = "sample_uid = study_name:sample_id",
  n_studies = length(studies),
  n_samples_species = nrow(sp$tab), n_species = ncol(sp$tab) - 1,
  n_samples_pathway = nrow(pw$tab), n_pathways = ncol(pw$tab) - 1,
  failed_studies = sp$failed,
  build_date = as.character(Sys.Date()))
write_json(prov, file.path(DATA, "cmd_feature_provenance.json"),
           auto_unbox = TRUE, pretty = TRUE)
cat("[shotgun] done.\n")
