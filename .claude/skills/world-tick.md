---
name: world-tick
description: "Advance the world state in the background while the party is busy. Simulates NPC agendas, faction movements, and environmental changes bound to in-game time."
---

# /world-tick — Background World Simulation

## Usage
- `/world-tick {duration}` — Simulate world events for the specified in-game time
- `/world-tick {duration} {context}` — Simulate with context about what the party is doing

## Examples
- `/world-tick 2 hours` — Party spends 2 hours investigating
- `/world-tick 1 day` — A full day of travel
- `/world-tick 8 hours while the party long rests at the inn`
- `/world-tick 30 minutes during the tavern conversation`

## How It Works

1. Parse the duration from the command
2. Read `games/{campaign}/calendar.md` for the current in-game time
3. Calculate the time window: current time + duration
4. Spawn the `world-tick` agent in the background:

```
Agent(
  name: "world-tick",
  run_in_background: true,
  prompt: "
    Campaign: games/{campaign}/
    Time window: {current_time} to {end_time} ({duration})
    Party activity: {what the party is doing}
    
    Read the campaign state files and simulate world events within this time window.
    Write results to games/{campaign}/world-tick-log.md.
  "
)
```

5. Continue play — the world tick runs concurrently
6. When the tick completes, review `world-tick-log.md` before narrating results

## DM Protocol After a Tick Completes

1. Read `games/{campaign}/world-tick-log.md` for the latest tick entry
2. Review the "DM Hooks" section for narration guidance
3. **Do NOT dump the log on the player** — weave results into discovery:
   - Describe changed environments the party notices
   - Have NPCs mention events or behave differently
   - Let the player find evidence through observation and interaction
4. If a tick result seems too dramatic or contradicts the narrative, the DM may override it — you have omniscience via the Monitor tool

## Automatic Triggers

World ticks should fire automatically during these events:

| Event | Tick Duration | Trigger |
|-------|--------------|---------|
| `/rest short` | 1 hour | After short rest processing |
| `/rest long` | 8 hours | After long rest processing |
| Scene transition with travel | Travel time | When narrating travel |
| Investigation/exploration | Scene duration | When party spends time in one place |
| Downtime | Days/weeks | When player declares downtime activities |

When using `/rest`, automatically trigger a world tick for the rest duration after processing the rest mechanics.

## Reviewing Tick History

The world tick log at `games/{campaign}/world-tick-log.md` is append-only. Each entry is timestamped and separated by `---`. The DM can review the full history to maintain narrative consistency.

## Guardrails

The world-tick agent has strict rules it cannot break:
- Events cannot surpass the in-game time window
- Player characters cannot be killed, injured, or directly affected
- Active quests cannot be resolved without player involvement
- Quest-critical items and locations cannot be destroyed
- All changes must leave discoverable evidence
