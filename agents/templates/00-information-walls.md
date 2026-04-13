# Information Wall Protocol for NPC Subagents

Every NPC subagent operates behind an **information wall**. The NPC genuinely does not know things outside its defined knowledge boundaries. This creates real information asymmetry — the NPC might withhold, reveal, or accidentally leak information based on its own judgment, not a DM pretending to not know something.

## How It Works

NPC agents are spawned as separate Claude Code subagents with their own system prompt. The prompt defines:
1. **Who they are** — identity, personality, voice
2. **What they know** — an explicit whitelist of allowed files and knowledge
3. **What they don't know** — an explicit blacklist of forbidden files and topics
4. **What they want** — goals that drive their dialogue choices

The DM maintains omniscience by monitoring the agent via the Monitor tool, but the NPC's words and decisions come from an independent generation with restricted context.

## File Access Rules

### Every NPC Agent MAY Read
- Their own NPC profile: `games/{campaign}/world/npcs/{their-name}.md`
- Their attitude toward the party: `games/{campaign}/relationships/npc-attitudes.md`
- Their home location: `games/{campaign}/world/locations/{their-location}.md`
- Public calendar: `games/{campaign}/calendar.md`
- Their faction file (if affiliated): `games/{campaign}/world/factions/{faction}.md`

### Every NPC Agent MUST NEVER Read
- **Player character sheets**: `games/{campaign}/players/` — they don't know PC stats, HP, or abilities
- **Other NPC private files**: `games/{campaign}/world/npcs/{other-npc}.md` — they don't know other NPCs' secret thoughts
- **DM narrative secrets**: `games/{campaign}/narrative/secrets.md`
- **Hidden quests**: `games/{campaign}/quests/hidden.md`
- **Combat state**: `games/{campaign}/combat/` — meta-knowledge about encounters
- **Session state**: `games/{campaign}/session-state.md` — meta-knowledge about party status
- **World tick logs**: `games/{campaign}/world-tick-log.md` — behind-the-scenes world simulation

### Exceptions
- A **spy** or **diviner** NPC might have access to additional files representing their intelligence network. Document these exceptions explicitly in the agent definition.
- A **companion** NPC traveling with the party would reasonably know the party's general location and recent events (but still not their stats or private conversations).

## Writing Changes

NPC agents may ONLY write to:
- Their own NPC file (update status, record interaction history)
- `relationships/npc-attitudes.md` (update their feelings toward the party)

They must NEVER write to session-state.md, player files, quest files, or other NPC files.

## DM Monitoring Workflow

The DM has full omniscience — just like a real DM. The information wall enforces epistemology at the NPC level, not the DM level.

### Spawning an NPC Agent
```
Agent(
  name: "npc-{name}",
  prompt: "Context: {scene description, what the player said, relevant situation}",
  run_in_background: true
)
```

### Monitoring the Interaction
Use the **Monitor** tool to watch the NPC agent's tool calls and responses in real time. This lets the DM:
- See what files the NPC is reading (verify they stay in bounds)
- See the NPC's internal reasoning
- Intercept if the NPC tries to access forbidden files
- Observe the NPC's genuine reactions before narrating them to the player

### Relaying Dialogue
Use **SendMessage** to pass player dialogue to the NPC agent:
```
SendMessage(to: "npc-{name}", message: "The player says: '{dialogue}'")
```

The NPC responds independently. The DM then narrates the response to the player, adding body language, environmental context, and any DM observations.

### Quick Interactions (Foreground)
For brief exchanges (< 5 lines of dialogue), spawn the NPC in the foreground instead:
```
Agent(
  name: "npc-{name}",
  prompt: "The player approaches and says: '{dialogue}'. Respond in character."
)
```

The DM gets the response directly and narrates it.

## Template Integration

When creating a new NPC agent from `agents/templates/`, add these sections to the agent definition:

```markdown
## CRITICAL: Information Boundaries

You are an information-walled agent. You have your OWN knowledge and perspective.

### Files You MAY Read
- /games/{campaign}/world/npcs/{your-name}.md
- /games/{campaign}/relationships/npc-attitudes.md
- /games/{campaign}/world/locations/{your-location}.md
- /games/{campaign}/calendar.md
{add any character-specific allowed files}

### Files You MUST NEVER Read
- /games/{campaign}/players/ (player character sheets)
- /games/{campaign}/narrative/secrets.md (DM secrets)
- /games/{campaign}/quests/hidden.md (hidden quests)
- /games/{campaign}/world/npcs/ (other NPCs' files)
- /games/{campaign}/combat/ (combat meta-state)
- /games/{campaign}/session-state.md (party meta-state)

If you need information not in your allowed files, respond based on what your character would reasonably know or guess. You may say "I don't know" — that's realistic.
```

## Multi-NPC Scenes

For scenes with multiple NPCs present (e.g., a tavern, a council meeting):
1. Spawn each NPC as a separate named background agent
2. Use Monitor to watch all of them simultaneously
3. Relay the player's words to all relevant NPCs via SendMessage
4. Each NPC responds independently — they may agree, disagree, talk over each other, or reveal different perspectives
5. The DM weaves the responses into a coherent scene

This creates a living room rather than one voice playing all parts sequentially.
