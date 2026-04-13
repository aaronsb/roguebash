#!/bin/bash
# Combat Start Atmosphere — banner + sound when a new encounter begins
# Only fires for NEW encounters (checks for Round 1 / Initiative in content)

INPUT="${TOOL_INPUT:-}"

# Only show banner if this looks like a NEW encounter, not a mid-combat update
if echo "$INPUT" | grep -qiE '(Round.*1|Initiative Order|initiative order)'; then
    printf '\n'
    printf '\033[1;31m ⚔ ═══════════════════════════════════ ⚔\033[0m\n'
    printf '\033[1;31m            ROLL INITIATIVE!\033[0m\n'
    printf '\033[1;31m ⚔ ═══════════════════════════════════ ⚔\033[0m\n'
    printf '\n'

    # Update terminal title to show combat mode
    printf '\033]0;⚔ COMBAT ⚔\007'

    # macOS system sound (Hero = dramatic flourish)
    command -v afplay &>/dev/null && afplay /System/Library/Sounds/Hero.aiff &
    # Linux fallback
    command -v paplay &>/dev/null && paplay /usr/share/sounds/freedesktop/stereo/service-login.oga 2>/dev/null &
fi
