# templates/ — NPC Agent Archetypes

7 template files. Starting points for creating campaign-specific NPC agents. Each template defines the structure and prompt patterns for a common NPC archetype.

## File Index

| File | Archetype | Use When Creating... |
|------|-----------|---------------------|
| `01-quest-giver.md` | Quest Giver | NPCs who assign quests and missions |
| `02-merchant.md` | Merchant | Shopkeepers, traders, vendors |
| `03-companion.md` | Companion | NPCs who travel with the party |
| `04-villain.md` | Villain | Antagonists, bosses, recurring enemies |
| `05-authority-figure.md` | Authority Figure | Rulers, officials, faction leaders |
| `06-sage.md` | Sage | Scholars, wizards, lore-keepers |
| `07-trickster.md` | Trickster | Rogues, fey, con artists, chaotic NPCs |

## How to Use

1. Choose the closest archetype template
2. Copy to `/.claude/agents/npc-{name}.md`
3. Fill in: identity, personality, knowledge, goals, voice
4. Create the NPC's state file at `games/{campaign}/world/npcs/{name}.md`
5. Register in `agents/active/`

## Relationships

- **Parent**: `../` (agents system overview)
- **Destination**: `/.claude/agents/` (where instantiated agents live)
- **State files**: `games/{campaign}/world/npcs/` (NPC persistent state)
