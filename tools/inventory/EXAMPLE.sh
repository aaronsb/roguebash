#!/bin/bash
# Smoke-test: list inventory.
set -euo pipefail
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
ROGUEBASH_RUN_DIR="$("$HERE/../_shared/make_fixture.sh")"
export ROGUEBASH_RUN_DIR
export ROGUEBASH_SCENARIOS="$HERE/../../resources"
echo '{}' | "$HERE/inventory"
