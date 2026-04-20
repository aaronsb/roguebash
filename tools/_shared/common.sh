#!/bin/bash
# tools/_shared/common.sh — sourced by every exploration tool.
#
# Responsibilities:
#   - Verify ROGUEBASH_RUN_DIR / ROGUEBASH_RESOURCES are set
#   - Compute and export PYTHONPATH so tools can `from engine.state ...`
#   - Capture stdin into RB_ARGS_JSON
#   - Provide `rb_run_py <path>` which runs the named python file with
#     the prologue already executed (helpers like _load_world etc.
#     become importable module-level names).
#
# The `_` prefix keeps this directory out of the agent's tool discovery.

set -euo pipefail

# Locate the repo root from the sourced-file's path. `common.sh` lives at
# <repo>/tools/_shared/common.sh — go up three dirs for the repo root.
__RB_COMMON_SELF="${BASH_SOURCE[0]}"
__RB_COMMON_REAL="$(readlink -f "$__RB_COMMON_SELF" 2>/dev/null || realpath "$__RB_COMMON_SELF")"
ROGUEBASH_REPO_ROOT="$(cd "$(dirname "$__RB_COMMON_REAL")/../.." && pwd)"
export ROGUEBASH_REPO_ROOT
export __RB_COMMON_DIR="$(dirname "$__RB_COMMON_REAL")"

if [ -z "${ROGUEBASH_RUN_DIR:-}" ]; then
  echo "error: ROGUEBASH_RUN_DIR is not set" >&2
  exit 2
fi
if [ ! -d "$ROGUEBASH_RUN_DIR" ]; then
  echo "error: ROGUEBASH_RUN_DIR does not exist: $ROGUEBASH_RUN_DIR" >&2
  exit 2
fi

# ROGUEBASH_RESOURCES is optional for some tools (look, move) but we still
# set a best-effort default so `use`/`examine` can resolve catalogs.
if [ -z "${ROGUEBASH_RESOURCES:-}" ]; then
  ROGUEBASH_RESOURCES="$ROGUEBASH_REPO_ROOT/resources"
  export ROGUEBASH_RESOURCES
fi

# Put the repo root on sys.path so `from engine.state ...` works.
if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="$ROGUEBASH_REPO_ROOT:$PYTHONPATH"
else
  export PYTHONPATH="$ROGUEBASH_REPO_ROOT"
fi

# rb_read_args — capture stdin (if any) into RB_ARGS_JSON, defaulting to "{}".
rb_read_args() {
  local raw
  raw="$(cat 2>/dev/null || true)"
  if [ -z "$raw" ]; then
    raw="{}"
  fi
  export RB_ARGS_JSON="$raw"
}

# rb_run_py <path-to-user-code.py>
# Runs the prologue (which imports helpers and then execfile()'s the
# target script). This way each tool keeps its Python in a plain .py
# file — no bash-quoting hell, linters and syntax-highlighters work.
rb_run_py() {
  local user_py="$1"
  RB_USER_PY="$user_py" python3 "$__RB_COMMON_DIR/prologue.py"
}
