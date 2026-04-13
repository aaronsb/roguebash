# hooks/ — Atmospheric Trigger Scripts

Shell scripts that fire automatically via Claude Code hooks to create atmospheric feedback during gameplay. Configured in `/.claude/settings.json`.

## Architecture

Three **dispatcher scripts** route `PostToolUse` events to specific handlers:

| Dispatcher | Triggers On | Routes To |
|------------|------------|-----------|
| `post-write.sh` | Write tool | auto-save, combat-start, hp-warning, location-change |
| `post-edit.sh` | Edit tool | auto-save, hp-warning, location-change |
| `post-bash.sh` | Bash tool | dice-fanfare |

## Handler Scripts

| Script | What It Does | Trigger Condition |
|--------|-------------|-------------------|
| `dice-fanfare.sh` | Banner + sound for natural 20s and 1s | Bash output contains "Natural 20" or "Natural 1" |
| `combat-start.sh` | "ROLL INITIATIVE" banner + sound | encounter.md written with Round 1 / Initiative |
| `auto-save.sh` | Save confirmation indicator | session-state.md written or edited |
| `hp-warning.sh` | HP threshold alerts (critical/low/down) | Player file written with HP fraction |
| `location-change.sh` | Terminal title update + location indicator | session-state.md written with location data |

## Audio

Scripts use **macOS system sounds** via `afplay` by default. Sounds are played in the background (`&`) so they don't block the agent.

To use custom audio, place files in `hooks/audio/` and update the scripts. Supported formats: `.aiff`, `.mp3`, `.wav`.

### Cross-Platform Notes
- **macOS**: `afplay` (built-in)
- **Linux**: `paplay` (PulseAudio) or `aplay` (ALSA)
- **Windows**: `powershell -c (New-Object Media.SoundPlayer 'file.wav').PlaySync()`

All audio commands are guarded with `command -v` checks — scripts work silently on platforms without audio support.

## Environment Variables

Hook scripts receive from Claude Code:
- `$TOOL_INPUT` — JSON string of the tool's input parameters
- `$TOOL_OUTPUT` — JSON string of the tool's output (PostToolUse only)

## Customization

To add new atmospheric triggers:
1. Create a handler script in this directory
2. Add routing logic to the appropriate dispatcher (`post-write.sh`, `post-edit.sh`, or `post-bash.sh`)
3. No changes to `settings.json` needed — dispatchers handle routing
