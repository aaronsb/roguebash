#!/bin/bash
# Smoke-test: examine the current room, then the lantern in the room.
set -euo pipefail
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
ROGUEBASH_RUN_DIR="$("$HERE/../_shared/make_fixture.sh")"
export ROGUEBASH_RUN_DIR
export ROGUEBASH_SCENARIOS="$HERE/../../resources"
echo '{"target":"room"}' | "$HERE/examine"
echo "---"
echo '{"target":"item.lantern"}' | "$HERE/examine"
