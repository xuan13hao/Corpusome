#!/usr/bin/env bash
# ==========================================================================
# 00_setup_env.sh  —  Build the two conda environments the pipeline needs.
#
#   env "cmd-bioc"   : R 4.5 + curatedMetagenomicData 3.18  (shotgun tier)
#   env "microbiome" : Python 3.11 + biom-format, h5py, pandas, pyarrow,
#                      scipy, scikit-bio (16S tier + harmonization + validation)
#
# Idempotent: skips creation if the env already exists.
# Requires: conda (miniconda/mambaforge) on PATH.
# ==========================================================================
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$here/_config.sh"

command -v conda >/dev/null 2>&1 || { echo "ERROR: conda not on PATH"; exit 1; }
# Prefer mamba if available (faster solves)
SOLVER=conda; command -v mamba >/dev/null 2>&1 && SOLVER=mamba

# ---------------------------------------------------------------- microbiome
if ! conda env list | grep -qE "^\s*microbiome\s"; then
  echo "[setup] creating env 'microbiome'"
  $SOLVER create -y -n microbiome -c conda-forge python=3.11 \
      "pandas>=2" "pyarrow" "numpy" "scipy" "h5py" "biom-format" \
      "scikit-bio" "matplotlib" "seaborn" "requests" "python-wget"
else
  echo "[setup] env 'microbiome' already exists — skipping"
fi

# ------------------------------------------------------------------ cmd-bioc
# curatedMetagenomicData is a Bioconductor DATA package. The leaf package does
# not resolve cleanly through conda, and a dependency (mia) imports
# rbiom::unifrac which recent rbiom (>=2.0) removed. We therefore:
#   1. create the R env with cMD's dependencies,
#   2. build rbiom 1.0.3 from source (still exports unifrac) into an OVERLAY lib,
#   3. install the cMD source tarball into that overlay lib.
# Every R script prepends the overlay lib via .libPaths() (see _config.sh R_LIBS).
if ! conda env list | grep -qE "^\s*cmd-bioc\s"; then
  echo "[setup] creating env 'cmd-bioc' (R 4.5 + Bioconductor 3.22)"
  $SOLVER create -y -n cmd-bioc -c bioconda -c conda-forge \
      "bioconductor-experimenthub" "bioconductor-annotationhub" \
      "bioconductor-mia" "bioconductor-summarizedexperiment" \
      "bioconductor-treesummarizedexperiment" "bioconductor-multiassayexperiment" \
      "r-base>=4.5,<4.6" "r-biocmanager" "r-dplyr" "r-tidyr" "r-jsonlite" "r-data.table" \
      "r-rcppparallel" "r-rjson" "r-r.utils" "r-openxlsx" "r-zip" \
      "gxx_linux-64" "gcc_linux-64" "make"
else
  echo "[setup] env 'cmd-bioc' already exists — skipping"
fi

# Build the overlay lib (rbiom 1.0.3 + curatedMetagenomicData) if missing.
mkdir -p "$R_OVERLAY_LIB"
conda run -n cmd-bioc Rscript "$here/00b_build_cmd_overlay.R"

echo "[setup] done."
