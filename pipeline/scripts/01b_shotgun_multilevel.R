#!/usr/bin/env Rscript
# ==========================================================================
# 01b_shotgun_multilevel.R  —  Multi-level taxonomic tables from cMD.
# Re-pulls relative_abundance with FULL MetaPhlAn lineage and writes one
# relative-abundance table per rank (phylum, class, order, family, genus,
# species) to $DATA_DIR/multilevel/shotgun/.
# ==========================================================================
suppressWarnings({ .libPaths(c(Sys.getenv("R_OVERLAY_LIB"), .libPaths())) })
suppressMessages({ library(curatedMetagenomicData); library(data.table)
                   library(SummarizedExperiment) })
DATA <- Sys.getenv("DATA_DIR"); SNAP <- Sys.getenv("CMD_SNAPSHOT", "2021-10-14")
OUTD <- file.path(DATA, "multilevel", "shotgun"); dir.create(OUTD, recursive=TRUE, showWarnings=FALSE)

sm <- as.data.frame(sampleMetadata); studies <- unique(sm$study_name)
snaps <- unique(c(SNAP, "2021-03-31","2021-04-02","2022-04-13","2022-10-19"))
markers <- c(phylum="p__", class="c__", order="o__", family="f__", genus="g__", species="s__")

# cMD relative_abundance stores ONLY species rows, but each rowname carries the
# full MetaPhlAn lineage (k__..|p__..|..|s__..). We aggregate to each rank by
# truncating every species lineage to that rank marker and summing shared labels.
trunc_to_rank <- function(rn, marker) {
  # keep lineage segments up to and including the one starting with `marker`
  segs <- strsplit(rn, "\\|", fixed=FALSE)[[1]]
  hit <- which(startsWith(segs, marker))
  if (length(hit) == 0) return(NA_character_)
  paste(segs[seq_len(hit[1])], collapse="|")
}

collect_rank <- setNames(vector("list", length(markers)), names(markers))
for (st in studies) {
  se <- NULL
  for (s in snaps) {
    se <- tryCatch(curatedMetagenomicData(paste0(s,".",st,".relative_abundance"),
                     dryrun=FALSE, rownames="long")[[1]], error=function(e) NULL)
    if (!is.null(se)) break
  }
  if (is.null(se)) next
  m <- as.matrix(assay(se)); rn <- rownames(m)          # species x samples
  for (rk in names(markers)) {
    lab <- vapply(rn, trunc_to_rank, "", marker=markers[[rk]])
    ok <- !is.na(lab)
    if (!any(ok)) next
    agg <- rowsum(m[ok, , drop=FALSE], group=lab[ok])   # rank x samples
    # short label = last |-segment
    rownames(agg) <- sub(".*\\|", "", rownames(agg))
    dt <- as.data.table(t(agg), keep.rownames="sample_id")
    dt[, sample_uid := paste0(st, ":", sample_id)][, sample_id := NULL]
    collect_rank[[rk]][[st]] <- dt
  }
}
for (rk in names(markers)) {
  lst <- collect_rank[[rk]]
  if (is.null(lst) || length(lst) == 0) { cat(sprintf("shotgun %-8s: EMPTY, skipped\n", rk)); next }
  tab <- rbindlist(lst, use.names=TRUE, fill=TRUE)
  if (!("sample_uid" %in% names(tab)) || nrow(tab) == 0) {
    cat(sprintf("shotgun %-8s: no sample_uid/rows, skipped\n", rk)); next }
  for (j in names(tab)) if (j!="sample_uid") set(tab, which(is.na(tab[[j]])), j, 0)
  setcolorder(tab, "sample_uid")
  fwrite(tab, file.path(OUTD, paste0("cmd_", rk, "_relab.csv.gz")))
  cat(sprintf("shotgun %-8s: %d x %d\n", rk, nrow(tab), ncol(tab)-1))
}
cat("[shotgun multilevel] done.\n")
