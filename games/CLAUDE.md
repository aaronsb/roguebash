# games/ — Campaign Data

Empty until a campaign is created. Use `/session new {name}` to create a new campaign.

Each campaign lives in its own subdirectory with full state tracking: player characters, world building, session logs, quests, combat, economy, relationships, and narrative arcs.

## Key Files Per Campaign

| File | Purpose |
|------|---------|
| `session-state.md` | Current party location, status, immediate situation |
| `calendar.md` | In-game date, time, and weather |
| `world-tick-log.md` | Append-only log of background world simulation events |
| `campaign.md` | Campaign tone, theme, and overview |

### World Tick Log

`world-tick-log.md` is created and appended by the `world-tick` background agent. Each entry records:
- Time window simulated
- NPC and faction events (with dice rolls)
- State changes made to world files
- DM hooks for narrating results to the player

The DM reviews this log before narrating off-screen events. See `/world-tick` skill and the root `CLAUDE.md` World Tick Protocol for details.

See the root `CLAUDE.md` for the full campaign directory structure template.
