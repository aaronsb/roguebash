# templates/ — NPC Agent Archetypes

8 files: 1 protocol reference + 7 archetype templates. Starting points for creating campaign-specific NPC agents with **information walls** that enforce real epistemological boundaries.

## File Index

| File | Archetype | Use When Creating... |
|------|-----------|---------------------|
| `00-information-walls.md` | Protocol Reference | Understanding the info wall system (read first) |
| `01-quest-giver.md` | Quest Giver | NPCs who assign quests and missions |
| `02-merchant.md` | Merchant | Shopkeepers, traders, vendors |
| `03-companion.md` | Companion | NPCs who travel with the party |
| `04-villain.md` | Villain | Antagonists, bosses, recurring enemies |
| `05-authority-figure.md` | Authority Figure | Rulers, officials, faction leaders |
| `06-sage.md` | Sage | Scholars, wizards, lore-keepers |
| `07-trickster.md` | Trickster | Rogues, fey, con artists, chaotic NPCs |

## How to Use

1. Read `00-information-walls.md` to understand the information wall protocol
2. Choose the closest archetype template
3. Copy to `/.claude/agents/npc-{name}.md`
4. Fill in: identity, personality, knowledge, goals, voice
5. **Verify the information wall sections**: whitelist of allowed files, blacklist of forbidden files
6. Create the NPC's state file at `games/{campaign}/world/npcs/{name}.md`
7. Register in `agents/active/`

## Information Wall Customization

Each template has pre-configured file access lists appropriate for its archetype:
- **Companion** has broader access (travels with the party, knows current situation)
- **Villain/Sage/Trickster** have special access to `narrative/secrets.md` (filtered through what they'd actually know)
- **Merchant** can see party inventory (they observe what's brought to trade)
- **Quest Giver/Authority Figure** have standard access to their domain

## Relationships

- **Parent**: `../` (agents system overview)
- **Destination**: `/.claude/agents/` (where instantiated agents live)
- **State files**: `games/{campaign}/world/npcs/` (NPC persistent state)
