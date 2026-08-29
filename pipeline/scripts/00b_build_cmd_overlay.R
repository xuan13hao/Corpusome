#!/usr/bin/env Rscript
# Build the overlay library: rbiom 1.0.3 (source) + curatedMetagenomicData.
# rbiom >= 2.0 dropped the `unifrac` export that Bioconductor `mia` imports,
# so cMD fails to load against the conda rbiom. We pin rbiom 1.0.3 here.
overlay <- Sys.getenv("R_OVERLAY_LIB")
if (overlay == "") stop("R_OVERLAY_LIB not set (source _config.sh)")
dir.create(overlay, showWarnings = FALSE, recursive = TRUE)
.libPaths(c(overlay, .libPaths()))

have <- function(p) requireNamespace(p, quietly = TRUE)

# Point R at the conda compilers (needed to build rbiom's C++).
cc  <- Sys.glob(file.path(Sys.getenv("CONDA_PREFIX"), "bin", "*-linux-gnu-gcc"))
cxx <- Sys.glob(file.path(Sys.getenv("CONDA_PREFIX"), "bin", "*-linux-gnu-g++"))
if (length(cc) && length(cxx)) {
  dir.create("~/.R", showWarnings = FALSE)
  writeLines(sprintf("CC=%s\nCXX=%s\nCXX11=%s\nCXX14=%s\nCXX17=%s",
                     cc[1], cxx[1], cxx[1], cxx[1], cxx[1]), "~/.R/Makevars")
}

if (!have("rbiom") || packageVersion("rbiom") >= "2.0") {
  message("[overlay] building rbiom 1.0.3 from CRAN archive")
  install.packages(
    "https://cran.r-project.org/src/contrib/Archive/rbiom/rbiom_1.0.3.tar.gz",
    repos = NULL, type = "source", lib = overlay)
}
stopifnot("unifrac" %in% getNamespaceExports(loadNamespace("rbiom", lib.loc = overlay)))

if (!have("curatedMetagenomicData")) {
  message("[overlay] installing curatedMetagenomicData 3.18.0")
  url <- "https://bioconductor.org/packages/3.22/data/experiment/src/contrib/curatedMetagenomicData_3.18.0.tar.gz"
  install.packages(url, repos = NULL, type = "source", lib = overlay)
}
suppressMessages(library(curatedMetagenomicData))
cat("[overlay] OK — sampleMetadata:", nrow(sampleMetadata), "x", ncol(sampleMetadata), "\n")
