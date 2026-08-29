#!/usr/bin/env bash
# ==========================================================================
# run.sh  —  One-click build of the harmonized two-tier cross-body-site
#            human microbiome corpus.
#
# Usage:
#   ./run.sh              # full pipeline: setup env -> acquire -> harmonize -> validate
#   ./run.sh --skip-setup # assume envs already built
#   ./run.sh harmonize    # run from a single stage onward (setup|shotgun|agp|mgnify|harmonize|validate|inventory)
#
# Requirements: conda (or mamba) on PATH; ~15 GB disk; internet access to
#   Bioconductor/ExperimentHub, ftp.microbio.me, and www.ebi.ac.uk.
# Runtime: dominated by the AGP download (~2.4 GB) and cMD ExperimentHub pulls.
#
# All outputs land in output/ ; logs in logs/ ; raw+intermediate in data/.
# ==========================================================================
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
source scripts/_config.sh

SKIP_SETUP=0
START="all"
for a in "$@"; do
  case "$a" in
    --skip-setup) SKIP_SETUP=1 ;;
    setup|shotgun|agp|mgnify|harmonize|validate|inventory) START="$a" ;;
    *) echo "unknown arg: $a"; exit 1 ;;
  esac
done

run() { echo -e "\n=== [$(date +%H:%M:%S)] $1 ==="; }
crun() { conda run --no-capture-output -n "$1" "${@:2}"; }  # run in env $1

order=(setup shotgun agp mgnify harmonize validate inventory)
active=0; [ "$START" = "all" ] && active=1
declare -A on
for s in "${order[@]}"; do [ "$s" = "$START" ] && active=1; on[$s]=$active; done

# ---- 0. environments ----
if [ "${on[setup]}" = "1" ] && [ "$SKIP_SETUP" = "0" ]; then
  run "0/6  setup conda environments"
  bash scripts/00_setup_env.sh 2>&1 | tee "$LOG_DIR/00_setup.log"
fi

# ---- 1. shotgun tier (R / cmd-bioc) ----
if [ "${on[shotgun]}" = "1" ]; then
  run "1/6  shotgun tier — curatedMetagenomicData"
  crun cmd-bioc Rscript scripts/01_shotgun_cmd.R 2>&1 | tee "$LOG_DIR/01_shotgun.log"
fi

# ---- 2. AGP 16S (python / microbiome) ----
if [ "${on[agp]}" = "1" ]; then
  run "2/6  16S tier — American Gut Project"
  crun microbiome python scripts/02_16s_agp.py 2>&1 | tee "$LOG_DIR/02_agp.log"
fi

# ---- 3. MGnify demonstrator (python / microbiome) ----
if [ "${on[mgnify]}" = "1" ]; then
  run "3/6  16S tier — MGnify demonstrator"
  crun microbiome python scripts/03_16s_mgnify.py 2>&1 | tee "$LOG_DIR/03_mgnify.log"
fi

# ---- 4. harmonize ----
if [ "${on[harmonize]}" = "1" ]; then
  run "4/6  harmonize both tiers -> corpus tables"
  crun microbiome python scripts/04_harmonize.py 2>&1 | tee "$LOG_DIR/04_harmonize.log"
fi

# ---- 4b/4c. multi-level taxonomic tables (phylum..species) ----
if [ "${on[harmonize]}" = "1" ]; then
  run "4b   16S multi-level tables (phylum..family)"
  crun microbiome python scripts/04b_multilevel_16s.py 2>&1 | tee "$LOG_DIR/04b_multilevel_16s.log"
  run "4c   shotgun multi-level tables (phylum..species)"
  # requires the raw rank tables from 01b (re-pull cMD with full lineage)
  crun cmd-bioc Rscript scripts/01b_shotgun_multilevel.R 2>&1 | tee "$LOG_DIR/01b_multilevel.log"
  crun microbiome python scripts/04c_multilevel_shotgun.py 2>&1 | tee "$LOG_DIR/04c_multilevel_shotgun.log"
fi

# ---- 5. technical validation ----
if [ "${on[validate]}" = "1" ]; then
  run "5/6  technical validation (QC, PCoA, PERMANOVA, figure)"
  crun microbiome python scripts/05_validate.py 2>&1 | tee "$LOG_DIR/05_validate.log"
fi

# ---- 6. inventory + reports ----
if [ "${on[inventory]}" = "1" ]; then
  run "6/6  data-records inventory + reports"
  crun microbiome python scripts/06_inventory.py 2>&1 | tee "$LOG_DIR/06_inventory.log"
fi

run "DONE — corpus tables in $OUT_DIR"
ls -la "$OUT_DIR"
