#!/bin/bash
# Location Change — updates terminal title with current location
# Parses location from session-state.md content

INPUT="${TOOL_INPUT:-}"

# Try to extract location from session-state content
# Common patterns: "Location: {place}", "**Location**: {place}", "## Current Location"
LOCATION=$(echo "$INPUT" | grep -iE '^\*?\*?(Current )?Location' | head -1 | sed 's/.*[Ll]ocation[:#*]* *//' | sed 's/\*//g' | cut -c1-50)

if [ -n "$LOCATION" ]; then
    # Update terminal title
    printf '\033]0;%s\007' "$LOCATION"
fi
