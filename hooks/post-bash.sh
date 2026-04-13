#!/bin/bash
# Post-Bash Dispatcher — routes Bash tool output to atmospheric handlers
# Called by Claude Code PostToolUse hook when the Bash tool is used

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${TOOL_OUTPUT:-}"

# Dice roll fanfare: check for natural 20 or natural 1
if echo "$OUTPUT" | grep -qi 'Natural 20'; then
    bash "$SCRIPT_DIR/dice-fanfare.sh" nat20 2>/dev/null
elif echo "$OUTPUT" | grep -qi 'Natural 1[^0-9]'; then
    bash "$SCRIPT_DIR/dice-fanfare.sh" nat1 2>/dev/null
fi
