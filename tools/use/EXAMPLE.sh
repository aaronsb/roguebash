#!/bin/bash
# Smoke-test: take the lantern, then use it (grants_light; consumes oil_flask).
set -euo pipefail
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
ROGUEBASH_RUN_DIR="$("$HERE/../_shared/make_fixture.sh")"
export ROGUEBASH_RUN_DIR
export ROGUEBASH_SCENARIOS="$HERE/../../resources"
echo '{"item_ref":"item.lantern"}' | "$HERE/../take/take"
echo "---"
echo '{"item_ref":"item.lantern"}' | "$HERE/use"
