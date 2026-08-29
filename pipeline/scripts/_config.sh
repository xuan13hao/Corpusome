#!/usr/bin/env bash
# Shared configuration sourced by every pipeline script.
set -euo pipefail

# Root = parent of scripts/
export PIPE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DATA_DIR="$PIPE_ROOT/data"         # raw + intermediate downloads
export OUT_DIR="$PIPE_ROOT/output"        # final corpus tables + figures
export LOG_DIR="$PIPE_ROOT/logs"
mkdir -p "$DATA_DIR" "$OUT_DIR" "$LOG_DIR"

# R overlay library holding rbiom 1.0.3 + curatedMetagenomicData (see 00b_*.R).
# Every R invocation prepends this via R_LIBS so the pinned rbiom shadows the
# conda rbiom whose `unifrac` export mia depends on was removed upstream.
export R_OVERLAY_LIB="$DATA_DIR/cmd_rlib"
export R_LIBS="$R_OVERLAY_LIB"

# curatedMetagenomicData snapshot preference (falls back per-study).
export CMD_SNAPSHOT="2021-10-14"

# Prevalence filter: keep a feature present in >= max(MIN_N, PREV_FRAC * n_samples).
export PREV_FRAC="0.005"
export PREV_MIN_N="10"

# MGnify demonstrator: max samples pulled per study (politeness / bound).
export MGNIFY_MAX_PER_STUDY="200"

# Reproducibility
export CORPUS_SEED="0"
