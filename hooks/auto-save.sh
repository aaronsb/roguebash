#!/bin/bash
# Auto-Save Confirmation — subtle indicator when session state is persisted

printf '\033[2;37m[Session state saved]\033[0m\n'

# Subtle save sound (macOS Submarine = soft ping)
command -v afplay &>/dev/null && afplay /System/Library/Sounds/Submarine.aiff &
