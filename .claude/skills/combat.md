---
name: combat
description: "Enter, manage, and end D&D 5e combat encounters. Tracks initiative, HP, conditions, and positioning."
---

# /combat — Combat Management System

## Commands
- `/combat` or `/combat start` — Begin a new encounter
- `/combat next` — Advance to next turn in initiative order
- `/combat end` — End the encounter, log results, award XP
- `/combat status` — Show current encounter state
- `/combat map` — Redraw the battlefield map

## Starting Combat

1. Ask: "Who is in this fight?" (get list of PCs + enemies)
2. Look up monster stat blocks from `rules/monsters/` using grep
3. Read PC stats from the active campaign's `players/` directory
4. Roll initiative for ALL combatants using bash:
   ```bash
   echo "Initiative: $((RANDOM % 20 + 1 + DEX_MOD))"
   ```
5. Sort by initiative (highest first, DEX breaks ties)
6. Create `games/{campaign}/combat/encounter.md` with:
   - Round counter (starts at 1)
   - Initiative order table: Init | Name | HP | AC | Conditions | Notes
   - ASCII battlefield map (5ft grid)
   - Active effects section
7. Announce initiative order and describe the scene
8. Ask the first combatant for their action

## Running Each Turn

For each combatant's turn:
1. Announce whose turn it is and their current status
2. **If PC**: Describe the situation and ask "What do you do?"
3. **If NPC/Monster**: Decide action based on stat block, tactics, and situation
4. Resolve the action:
   - Roll attacks using `/roll` patterns
   - Roll damage, apply resistances/vulnerabilities
   - Process saving throws
   - Apply conditions
5. Check for **concentration saves** if the creature is concentrating and took damage (DC = max of 10 or half damage taken)
6. Check for **death saving throws** if a creature is at 0 HP
7. Update `encounter.md` with all changes
8. Move to next combatant in initiative order

## Tracking Damage and Healing

When applying damage or healing:
- Update the creature's current HP in the encounter table
- Note temporary HP separately
- Apply resistance (half damage), vulnerability (double damage), immunity (no damage) as applicable
- If HP drops to 0: creature falls unconscious and starts death saves (PCs) or dies (most monsters)
- If healing brings a creature above 0 HP: they regain consciousness

## Combat Map

Draw ASCII grid maps:
```
     1    2    3    4    5
  +----+----+----+----+----+
A |    |    | G1 |    |    |
  +----+----+----+----+----+
B |    | Th |    | G2 |    |
  +----+----+----+----+----+
C | Ly |    |    |    | Wh |
  +----+----+----+----+----+
```
- Each cell = 5 ft
- Use 2-letter abbreviations for combatants
- Mark terrain: `#` wall, `~` water, `^` difficult terrain, `D` door

## Ending Combat

1. Narrate the conclusion
2. Calculate XP: sum all monster XP values, divide equally among party members
3. Log the encounter to `combat/encounter-log.md` (append)
4. Handle loot — roll on treasure tables if appropriate
5. Update `session-state.md` with party HP and resource changes
6. Update character sheets (HP, spell slots, feature uses)
7. Clear `encounter.md`

## Rules References
- Combat mechanics: `rules/core/03-combat.md`
- Conditions: `rules/core/04-conditions.md`
- Monster stat blocks: `rules/monsters/`
- Spells used in combat: `rules/spellcasting/spells/`
