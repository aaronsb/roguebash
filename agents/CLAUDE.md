# agents/ — NPC Agent System
7 template files + active/retired directories. Defines NPC archetypes that can be instantiated as Claude Code subagents.

## How It Works
1. When a campaign needs a significant NPC, create an agent from a template
2. Agent definitions go in `/.claude/agents/npc-{name}.md` (Claude Code native format)
3. The DM invokes `@npc-{name}` for extended NPC interactions
4. The agent reads game state files, plays the NPC in character, writes state changes back
5. Multiple agents can run in parallel for multi-NPC scenes

## Templates
| Template | Archetype | Use When... |
|----------|-----------|-------------|
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
4. Create the NPC's state file at `games/{campaign}/world/npcs/{name}.md`
5. Add to `agents/active/` for tracking

## Agent-DM Communication
- Agents READ: session-state.md, their own NPC file, npc-attitudes.md, relevant world files
- Agents WRITE: their own NPC file (status changes), npc-attitudes.md (disposition updates)
- Agents NEVER: modify session-state.md, other NPC files, player sheets, or rules files

## Active vs Retired
- `active/` — NPCs currently in the campaign
- `retired/` — NPCs who died, departed, or are no longer relevant
