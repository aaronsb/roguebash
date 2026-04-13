#!/bin/bash
# Dice Roll Fanfare — visual + audio feedback for critical rolls
# Usage: bash dice-fanfare.sh [nat20|nat1]

EVENT="${1:-}"

if [ "$EVENT" = "nat20" ]; then
    printf '\n'
    printf '\033[1;33m ✦ ══════════════════════════════ ✦\033[0m\n'
    printf '\033[1;33m          NATURAL 20!\033[0m\n'
    printf '\033[1;33m ✦ ══════════════════════════════ ✦\033[0m\n'
    printf '\n'
    # macOS system sound (Glass = bright chime)
    command -v afplay &>/dev/null && afplay /System/Library/Sounds/Glass.aiff &
    # Linux fallback
    command -v paplay &>/dev/null && paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null &

elif [ "$EVENT" = "nat1" ]; then
    printf '\n'
    printf '\033[1;31m ☠ ══════════════════════════════ ☠\033[0m\n'
    printf '\033[1;31m          NATURAL 1...\033[0m\n'
    printf '\033[1;31m ☠ ══════════════════════════════ ☠\033[0m\n'
    printf '\n'
    # macOS system sound (Basso = low thud)
    command -v afplay &>/dev/null && afplay /System/Library/Sounds/Basso.aiff &
    # Linux fallback
    command -v paplay &>/dev/null && paplay /usr/share/sounds/freedesktop/stereo/dialog-warning.oga 2>/dev/null &
fi
