---
name: levelup
description: "Guide a player through leveling up their character. Handles HP, features, spells, ASI/feats."
---

# /levelup — Guided Character Advancement

## Usage
- `/levelup` — Start the level-up process
- `/levelup {character_name}` — Level up a specific character

## Process

1. Ask which character is leveling up (or use the name provided)
2. Read their character sheet from `games/{campaign}/players/{name}.md`
3. Read the class file from `rules/classes/{class}.md`
4. Determine the new level (current level + 1)

## Step-by-Step

### 1. Hit Points
Ask: "Roll or take average?"
- **Roll**: Roll the class hit die + CON modifier
  ```bash
  HD=$((RANDOM % DIE_SIZE + 1))
  echo "HP increase: $HD + CON_MOD = $((HD + CON_MOD))"
  ```
- **Average**: Use (die_size / 2 + 1) + CON modifier
  - d6: 4 + CON | d8: 5 + CON | d10: 6 + CON | d12: 7 + CON

### 2. Proficiency Bonus
Check if proficiency bonus increases (levels 5, 9, 13, 17): +2/+3/+4/+5/+6

### 3. Class Features
List ALL new features gained at this level from the class file. For each feature, explain what it does and present any choices needed.

### 4. Subclass Selection
If this is the subclass level (varies: Cleric/Sorcerer/Warlock 1st, Druid/Monk/Ranger/Wizard 2nd, others 3rd):
- Present the SRD subclass and its features

### 5. ASI or Feat
If this level grants an Ability Score Improvement:
- **Option A**: Increase one ability score by 2 (max 20)
- **Option B**: Increase two ability scores by 1 each (max 20)
- **Option C**: Take a feat instead (reference `rules/feats/01-feats.md`)

### 6. Spellcasting Updates (if applicable)
- New cantrips known? (check class progression)
- New spell slots? (show updated slot table)
- New spells known or increased preparation limit?
- For spells-known classes (Bard, Ranger, Sorcerer, Warlock): choose new spell(s)
- For preparing classes (Cleric, Druid, Paladin, Wizard): note new preparation limit

### 7. Multiclassing (if requested)
If the player wants a level in a different class:
- Check prerequisites in `rules/classes/13-multiclassing.md`
- Determine proficiencies gained
- Calculate new multiclass spell slots if applicable

### 8. Update Character Sheet
Write all changes to the character's `.md` file:
- New level, new max HP, new proficiency bonus (if changed)
- New features listed, new spell slots/spells
- Updated XP threshold for next level

### 9. Summary
Present a clean summary of all changes to the player.

## Rules Reference
- Class features: `rules/classes/{class}.md`
- Multiclassing: `rules/classes/13-multiclassing.md`
- Feats: `rules/feats/01-feats.md`
- XP to level: `rules/running-the-game/02-experience-points.md`
