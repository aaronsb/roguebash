#!/bin/bash
# Smoke-test: build a fixture run dir and run `look`.
set -euo pipefail
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
ROGUEBASH_RUN_DIR="$("$HERE/../_shared/make_fixture.sh")"
export ROGUEBASH_RUN_DIR
export ROGUEBASH_RESOURCES="$HERE/../../resources"
echo '{}' | "$HERE/look"
