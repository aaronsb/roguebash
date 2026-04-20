#!/bin/bash
# Smoke-test: build a fixture and move north into the Sunken Grove
# (which has a hazard and a monster — exercises the hazard-on-enter
# detection path).
set -euo pipefail
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
ROGUEBASH_RUN_DIR="$("$HERE/../_shared/make_fixture.sh")"
export ROGUEBASH_RUN_DIR
export ROGUEBASH_RESOURCES="$HERE/../../resources"
echo '{"direction":"north"}' | "$HERE/move"
