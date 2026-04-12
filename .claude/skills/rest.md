---
name: rest
description: "Process short or long rests for the party. Handles hit dice, HP recovery, feature recharges, and spell slot restoration."
---

# /rest — Rest Processing

## Commands
- `/rest short` — Process a short rest
- `/rest long` — Process a long rest

## Short Rest (1+ hours)

1. Read all PC sheets from the active campaign's `players/` directory
2. For each PC, show their current HP and available hit dice
3. Ask each player: "How many hit dice do you want to spend?"
4. For each hit die spent, roll recovery:
   ```bash
   # Hit die + CON modifier
   HD=$((RANDOM % DIE_SIZE + 1)); echo "Hit Die: $HD + CON_MOD = $((HD + CON_MOD)) HP recovered"
   ```
5. Update HP (cap at max HP)
6. Recharge short-rest features:
   - Fighter: Second Wind, Action Surge
   - Monk: All Ki points
   - Warlock: All Pact Magic spell slots
   - Bard (5th+): Bardic Inspiration
   - Cleric: Channel Divinity
   - Druid: Wild Shape uses
   - Any feature that says "recharges on a short or long rest"
7. If a Bard with Song of Rest is in the party: roll the extra die for allies who spent hit dice
8. Update all character sheets
9. Update `session-state.md`
10. Advance `calendar.md` by 1 hour

## Long Rest (8+ hours)

1. Read all PC sheets
2. Restore ALL hit points to maximum for each PC
3. Recover spent hit dice: each PC recovers half their total hit dice (rounded down, minimum 1)
4. Restore ALL spell slots for all casters
5. Restore ALL daily-use features:
   - All short-rest features (listed above)
   - Barbarian: Rage uses
   - Paladin: Lay on Hands pool, Divine Sense, Cleansing Touch
   - Sorcerer: Sorcery Points
   - Wizard: Arcane Recovery
   - All "recharges on a long rest" features
6. Remove 1 level of exhaustion (if the character had food and water during the rest)
7. Update all character sheets
8. Update `session-state.md` with restored resources
9. Advance `calendar.md` by 8 hours
10. If in the wilderness, consider rolling for random encounters (check `random-tables/`)

## Rules Reference
- Resting rules: `rules/core/06-resting.md`
- Class features that recharge: see individual class files in `rules/classes/`
