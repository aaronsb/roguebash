# agents/ — NPC Agent System
7 template files + active/retired directories. Defines NPC archetypes that can be instantiated as Claude Code subagents with **information walls** that enforce real epistemological boundaries.

## How It Works
1. When a campaign needs a significant NPC, create an agent from a template
2. Agent definitions go in `/.claude/agents/npc-{name}.md` (Claude Code native format)
3. Each agent has an **information wall** — it can only read files relevant to that character's knowledge
4. The DM invokes the agent for NPC interactions, monitoring via the Monitor tool
5. Multiple agents can run in parallel for multi-NPC scenes

## Information Wall Protocol

NPC subagents enforce real information asymmetry. The NPC genuinely does not know things outside its defined knowledge boundaries. See `templates/00-information-walls.md` for the full protocol.

**Key principle**: The DM maintains omniscience via the Monitor tool. The information wall enforces epistemology at the NPC level, not the DM level — just like a real D&D game.

### Quick Reference: File Access Rules

| NPC MAY Read | NPC MUST NEVER Read |
|-------------|-------------------|
| Their own NPC file | Player character sheets (`players/`) |
| Their attitude file | Other NPCs' private files |
| Their home location | DM narrative secrets |
| Public calendar | Hidden quests |
| Their faction file | Combat meta-state |
| | Session state / world tick logs |

## Templates
| Template | Archetype | Use When... |
|----------|-----------|-------------|
| 00-information-walls.md | Reference | Understanding the information wall protocol |
| 01-quest-giver.md | NPC who assigns quests | Creating quest-assigning NPCs |
| 02-merchant.md | Shopkeepers and traders | Creating merchant NPCs |
| 03-companion.md | Party allies and hirelings | Creating NPCs who travel with the party |
| 04-villain.md | Antagonists and bosses | Creating recurring villains |
| 05-authority-figure.md | Rulers, officials, leaders | Creating political/authority NPCs |
| 06-sage.md | Scholars, wizards, lore-keepers | Creating knowledge-dispensing NPCs |
| 07-trickster.md | Rogues, fey, con artists | Creating deceptive/chaotic NPCs |

## Creating a New NPC Agent
1. Choose the closest template from `templates/`
2. Copy to `/.claude/agents/npc-{name}.md`
3. Customize: identity, knowledge, goals, personality, voice
4. **Add the information wall sections** from `00-information-walls.md`:
   - Files the NPC MAY read (whitelist)
   - Files the NPC MUST NEVER read (blacklist)
5. Create the NPC's state file at `games/{campaign}/world/npcs/{name}.md`
6. Add to `agents/active/` for tracking

## DM Monitoring Workflow

### Spawning an NPC for Extended Interaction
```
Agent(
  name: "npc-{name}",
  prompt: "Context: {scene, what the player said, situation}",
  run_in_background: true
)
```

### Monitoring (DM Omniscience)
Use the **Monitor** tool to watch the NPC agent in real time:
- See what files the NPC reads (verify information wall compliance)
- Observe the NPC's internal reasoning and genuine reactions
- Intercept if the NPC attempts to access forbidden files

### Relaying Player Dialogue
```
SendMessage(to: "npc-{name}", message: "The player says: '{dialogue}'")
```

### Quick Interactions (Foreground)
For brief exchanges (< 5 lines), spawn in the foreground:
```
Agent(
  name: "npc-{name}",
  prompt: "The player approaches and says: '{dialogue}'. Respond in character."
)
```

### Multi-NPC Scenes
1. Spawn each NPC as a separate named background agent
2. Monitor all simultaneously
3. Relay player words to all relevant NPCs via SendMessage
4. Each responds independently — they may agree, disagree, or contradict
5. Weave the responses into a coherent scene

## Agent-DM Communication
- Agents READ: their own NPC file, npc-attitudes.md, their location, calendar, their faction
- Agents WRITE: their own NPC file (status changes), npc-attitudes.md (disposition updates)
- Agents NEVER: modify session-state.md, other NPC files, player sheets, quest files, or rules files

## Active vs Retired
- `active/` — NPCs currently in the campaign
- `retired/` — NPCs who died, departed, or are no longer relevant
