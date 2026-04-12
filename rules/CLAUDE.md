# rules/ — D&D 5e SRD 5.1 Reference

READ-ONLY reference library. All content from the Systems Reference Document 5.1, published under Creative Commons Attribution 4.0 International License by Wizards of the Coast. **Never modify these files during gameplay.**

## Quick Lookup Guide

| Need to know... | Read this file |
|-----------------|---------------|
| DC for a check, condition effects, action types | `00-quick-reference.md` (DM screen) |
| How ability scores and modifiers work | `core/01-ability-scores.md` |
| Which skill uses which ability | `core/02-skills.md` |
| How attacks, damage, and death work | `core/03-combat.md` |
| What a condition does mechanically | `core/04-conditions.md` |
| Movement, jumping, climbing, swimming | `core/05-movement-and-positioning.md` |
| Short rest vs long rest recovery | `core/06-resting.md` |
| Travel pace, food, water, light, hazards | `core/07-adventuring.md` |
| A specific class's features | `classes/{NN}-{class}.md` |
| Multiclassing rules and spell slots | `classes/13-multiclassing.md` |
| Racial traits and abilities | `races/01-races.md` |
| Background features | `backgrounds/01-backgrounds.md` |
| Weapon damage and properties | `equipment/01-weapons.md` |
| Armor AC and requirements | `equipment/02-armor.md` |
| Gear prices and descriptions | `equipment/03-adventuring-gear.md` |
| Spellcasting rules (slots, concentration, etc.) | `spellcasting/01-spellcasting-rules.md` |
| Which class gets which spells | `spellcasting/02-spell-index-by-class.md` |
| A specific spell's mechanics | `spellcasting/spells/{NN}-level-{N}.md` |
| A monster's stat block | `monsters/` (grep index, then read CR file) |
| How to balance an encounter | `running-the-game/01-encounter-building.md` |
| XP by CR and leveling table | `running-the-game/02-experience-points.md` |
| Magic item properties | `treasure/01-magic-items.md` |
| Random treasure generation | `treasure/02-treasure-tables.md` |

## Rule Lookup Protocol

1. **Check `00-quick-reference.md` first** — covers 80% of mid-play lookups
2. If not found, **grep the rules directory** for the relevant term: `grep -ri "term" rules/`
3. **Read the specific file** for the full rule text
4. Apply the rule, citing the source
5. If a rule is ambiguous, **make a ruling, note it, and move on** — don't pause play

## Directory Structure

```
rules/
├── 00-quick-reference.md           DM screen: DCs, conditions, actions
├── core/                           7 files — fundamental mechanics
├── classes/                        13 files — all 12 classes + multiclassing
├── races/                          1 file — all 9 SRD races
├── backgrounds/                    1 file — Acolyte + background system
├── feats/                          1 file — Grappler + feat system
├── equipment/                      5 files — weapons, armor, gear, mounts, economy
├── spellcasting/                   3 files + spells/ — casting rules + indices
│   └── spells/                     10 files — all 361 SRD spells by level
├── monsters/                       8 files — rules, index, stat blocks by CR
├── treasure/                       3 files — magic items, treasure tables, gems
├── running-the-game/               5 files — encounters, XP, traps, diseases, downtime
└── feats/                          1 file — Grappler (only SRD feat)
```

## Source Integrity

All content is sourced exclusively from the **SRD 5.1** (Creative Commons Attribution 4.0 International). No content from sourcebooks beyond the SRD is included. When players reference non-SRD content (additional subclasses, feats, spells, etc.), note that it is outside the SRD and adjudicate based on the player's description or ask them to provide the rules text.
