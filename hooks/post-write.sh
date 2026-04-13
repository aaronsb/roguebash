#!/bin/bash
# Post-Write Dispatcher — routes Write tool events to atmospheric handlers
# Called by Claude Code PostToolUse hook when the Write tool is used

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="${TOOL_INPUT:-}"

# Auto-save: session-state.md written
if echo "$INPUT" | grep -q 'session-state.md'; then
    bash "$SCRIPT_DIR/auto-save.sh" 2>/dev/null
    bash "$SCRIPT_DIR/location-change.sh" 2>/dev/null
fi

# Combat start: encounter.md written with initiative/round 1
if echo "$INPUT" | grep -q 'encounter.md'; then
    bash "$SCRIPT_DIR/combat-start.sh" 2>/dev/null
fi

# HP check: player character sheet written
if echo "$INPUT" | grep -qE 'players/.*\.md'; then
    bash "$SCRIPT_DIR/hp-warning.sh" 2>/dev/null
fi
