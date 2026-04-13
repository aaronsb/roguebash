#!/bin/bash
# HP Threshold Warning — alerts when character HP drops to dangerous levels
# Parses HP fraction (e.g., "15/45") from character sheet content

INPUT="${TOOL_INPUT:-}"

# Look for HP fraction pattern: digits/digits (e.g., "15/45", "0/38")
FRACTION=$(echo "$INPUT" | grep -oE '[0-9]+/[0-9]+' | head -1)

if [ -z "$FRACTION" ]; then
    exit 0
fi

CURRENT=$(echo "$FRACTION" | cut -d'/' -f1)
MAX=$(echo "$FRACTION" | cut -d'/' -f2)

# Validate numbers
if [ -z "$MAX" ] || [ "$MAX" -eq 0 ] 2>/dev/null; then
    exit 0
fi

PCT=$((CURRENT * 100 / MAX))

if [ "$CURRENT" -eq 0 ]; then
    printf '\n'
    printf '\033[1;31m ❤ ═══════════════════════════ ❤\033[0m\n'
    printf '\033[1;31m        CHARACTER DOWN!\033[0m\n'
    printf '\033[1;31m ❤ ═══════════════════════════ ❤\033[0m\n'
    printf '\n'
    command -v afplay &>/dev/null && afplay /System/Library/Sounds/Sosumi.aiff &
elif [ "$PCT" -le 25 ]; then
    printf '\033[1;31m[HP CRITICAL: %s (%d%%)]\033[0m\n' "$FRACTION" "$PCT"
    command -v afplay &>/dev/null && afplay /System/Library/Sounds/Basso.aiff &
elif [ "$PCT" -le 50 ]; then
    printf '\033[1;33m[HP LOW: %s (%d%%)]\033[0m\n' "$FRACTION" "$PCT"
fi
