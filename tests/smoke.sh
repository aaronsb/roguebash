#!/bin/bash
# Smoke test: drives the delve CLI through new → list → show → abandon
# without invoking any adapter or LLM. Exits 0 if the lifecycle works.

set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
export XDG_STATE_HOME="$(mktemp -d)"
trap 'rm -rf "$XDG_STATE_HOME"' EXIT

echo "=== delve new ==="
RUN_ID="$("$ROOT/bin/delve" new --seed 42 --name Smoke --scenario barrow_swamp | tail -1)"
echo "run: $RUN_ID"

echo
echo "=== delve list ==="
"$ROOT/bin/delve" list

echo
echo "=== delve show ==="
"$ROOT/bin/delve" show "$RUN_ID" | head -20

echo
echo "=== delve abandon ==="
echo y | "$ROOT/bin/delve" abandon "$RUN_ID"

echo
echo "=== delve list (post-abandon) ==="
"$ROOT/bin/delve" list

echo
echo "smoke: ok"
