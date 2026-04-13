#!/bin/bash
# Post-Edit Dispatcher — routes Edit tool events to atmospheric handlers
# Called by Claude Code PostToolUse hook when the Edit tool is used

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="${TOOL_INPUT:-}"

# Auto-save on session-state edit
if echo "$INPUT" | grep -q 'session-state.md'; then
    bash "$SCRIPT_DIR/auto-save.sh" 2>/dev/null
    bash "$SCRIPT_DIR/location-change.sh" 2>/dev/null
fi

# HP check on character sheet edit
if echo "$INPUT" | grep -qE 'players/.*\.md'; then
    bash "$SCRIPT_DIR/hp-warning.sh" 2>/dev/null
fi
