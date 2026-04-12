# crawledcode — D&D 5e Campaign Engine for Claude Code

A complete D&D 5th Edition campaign engine that turns Claude Code into an expert Dungeon Master. The entire game state lives on disk as a navigable directory tree — rules, characters, world state, NPCs, quests, combat, and narrative are all tracked in structured markdown files.

## How It Works

Claude Code reads `CLAUDE.md` files at every directory level for context, uses bash for dice rolling, spawns NPC subagents for rich character interactions, and persists all game state to disk so campaigns can be saved and resumed across sessions.

## Quick Start

```
/session new my-campaign
```

## Directory Structure

```
crawledcode/
├── CLAUDE.md                    Master DM instructions
├── .claude/
│   ├── settings.json            Hooks + agent teams config
│   ├── agents/                  NPC subagent definitions (created per campaign)
│   └── skills/                  6 custom slash commands
│       ├── roll.md              /roll — dice rolling engine
│       ├── combat.md            /combat — combat encounter management
│       ├── rest.md              /rest — short/long rest processing
│       ├── levelup.md           /levelup — guided character advancement
│       ├── shop.md              /shop — merchant interaction
│       └── session.md           /session — campaign lifecycle management
│
├── rules/                       D&D 5e SRD 5.1 reference (READ ONLY)
│   ├── 00-quick-reference.md    DM screen: DCs, conditions, actions
│   ├── core/                    7 files — ability scores, skills, combat, conditions, etc.
│   ├── classes/                 13 files — all 12 classes + multiclassing
│   ├── races/                   All 9 SRD races
│   ├── backgrounds/             Acolyte + background system
│   ├── feats/                   Grappler + feat system
│   ├── equipment/               5 files — weapons, armor, gear, mounts, economy
│   ├── spellcasting/            3 files + spells/ — casting rules + indices
│   │   └── spells/              10 files — all 361 SRD spells by level
│   ├── monsters/                8 files — 300+ stat blocks organized by CR
│   ├── treasure/                3 files — 250+ magic items, treasure tables
│   ├── running-the-game/        5 files — encounter building, XP, traps, etc.
│   └── feats/                   Grappler (only SRD feat)
│
├── games/                       Campaign data (one subdirectory per campaign)
│
└── agents/                      NPC agent system
    └── templates/               7 archetype templates (quest-giver, merchant,
                                 companion, villain, authority, sage, trickster)
```

## Available Skills

| Command | Description |
|---------|-------------|
| `/roll` | Roll dice — XdY+Z, advantage, disadvantage, checks, saves, attacks |
| `/combat` | Enter, manage, and end combat encounters with initiative and ASCII maps |
| `/rest` | Process short or long rests with hit dice, HP, and feature recharges |
| `/levelup` | Walk through leveling up a character step by step |
| `/shop` | Browse merchant inventory, buy, sell, and haggle |
| `/session` | Start, save, resume, or create campaigns |

## Rules Coverage

All content sourced from the **D&D 5e SRD 5.1** (Creative Commons Attribution 4.0 International by Wizards of the Coast):

- **88 reference files** totaling ~1 MB of game content
- **12 classes** with complete features levels 1-20 and SRD subclasses
- **9 races** with full racial traits
- **361 spells** with complete mechanical descriptions
- **300+ monsters** with full stat blocks (CR 0 through CR 30)
- **250+ magic items** across all rarity tiers
- **Complete equipment tables**, encounter building rules, treasure generation, and more

## NPC Agent System

Significant NPCs can be implemented as Claude Code subagents that run in the background, providing realistic multi-character worlds. Each NPC agent:

- Has a defined personality, knowledge boundaries, and goals
- Reads game state files to understand the current situation
- Stays in character during extended interactions
- Writes state changes back to the campaign files

Seven archetype templates are provided: quest-giver, merchant, companion, villain, authority figure, sage, and trickster.

## Campaign State Tracking

When a campaign is created, it generates a full directory tree tracking:

- Player character sheets (YAML frontmatter + markdown)
- World building (regions, locations, factions, NPCs, lore)
- Session logs with summaries and DM notes
- Active/completed/failed/hidden quests
- Combat encounters with initiative, HP, and ASCII maps
- Party inventory and shop inventories
- NPC relationships and faction reputation
- In-game calendar, weather, and time
- Narrative arcs, plot threads, and DM secrets

## Architecture Inspiration

Directory structure and CLAUDE.md navigation patterns inspired by [praecipio_intelligence_framework](https://github.com/forayconsulting/praecipio_intelligence_framework) and [dig](https://github.com/forayconsulting/dig) — hierarchical navigation hubs, numbered files for reading order, and cross-references between knowledge domains.

## License

Rules content from the D&D 5e SRD 5.1, published under [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/) by Wizards of the Coast.
