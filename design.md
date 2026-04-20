# roguebash — design

A text-adventure–presented, 5e-mechanics–backed, procedurally-generated
dungeon crawler where an LLM plays the DM. Forked from
[forayconsulting/crawledcode](https://github.com/forayconsulting/crawledcode)
and stripped down to run against a local llama.cpp instance via the sibling
project's `agent` tool-calling runner.

## Design ethos (preserved from the fork's README)

- **Text adventure voice**: terse second person, "you are in a dusty
  antechamber," Scott Adams / Infocom lineage.
- **Describe what you do, not what you want to happen.** Players type
  natural language; the LLM translates to tool calls.
- **Combat is one option, not the default.** Puzzles, social, exploration
  all resolve through the same surface.
- **Fail forward.** Bad rolls do not dead-end the story.
- **Permadeath.** One life per run; state is a file on disk that deletes
  when the character dies or the objective is won.

## Three-layer split

### 1. Exploration (text-adventure voice)
Verbs: `look`, `move(dir)`, `examine(target)`, `take`, `drop`, `use`,
`inventory`. No dice unless a skill check fires. Rooms describe themselves.

### 2. Mechanics (5e rules)
Verbs: `skill_check(ability, dc)`, `save(type, dc)`, `attack(target,
weapon)`, `cast_spell(spell, target)`, `damage(target, n)`, `heal(target,
n)`, `xp(n)`, `level_up()`. Tools do the math — roll, modify, compare — and
return structured results. The model narrates; it does not invent numbers.

### 3. State (files, not model memory)
Everything durable lives under `$XDG_STATE_HOME/roguebash/<run-id>/`
(default `~/.local/state/roguebash/<run-id>/`):

- `character.json` — sheet (class, race, stats, HP, AC, inventory, spells)
- `world.json` — what the player has revealed (visited rooms, known exits)
- `graph.json` — full shuffled world (the answer key)
- `ledger.jsonl` — append-only event log, one JSON line per event

The model never sees `graph.json`. Each turn it gets: current room from
`world.json`, character sheet, last ~5 ledger events, the player's input.

## World generation (graph procgen)

Hierarchical WaveFunctionCollapse-on-graphs pipeline, seeded by a single
integer for full determinism:

1. **Load catalogs from `resources/*.jsonl`.** Each entry is either a
   `room` (terminal node) or an `area` (container with a declared set of
   entrance/exit rooms and its own internal subgraph).
2. **Macro generator.** Choose `start` and `goal` area-nodes that sit at
   the low and high ends of the difficulty ramp. Sample N area-nodes from
   the catalog. Connect where `compatible_with` tags overlap. BFS(start,
   goal); retry on failure.
3. **Micro generator.** For each area node that is a container, instantiate
   its internal subgraph with the same compatibility logic; pin the
   declared entrance/exit rooms so they line up with macro-level neighbors.
4. **Set-piece inserts.** Handcrafted special rooms (the witch's hut, the
   sunken library) get placed into compatible slots based on tag match.
5. **Serialize** to `graph.json`.

Target run size: **8–15 macro nodes × 3–8 rooms each ≈ 50 rooms**. One
sitting, meaningful permadeath.

## System prompt composition (each turn)

The runner builds a fresh system prompt every turn from:

1. `prompts/dm_voice.md` — narrator persona & tone
2. Mode overlay — `prompts/exploration_mode.md` OR `prompts/combat_mode.md`
3. Small rules excerpt — 1–2 KB of just the currently-relevant rules
   (e.g. in combat: core resolution + current monster stat block)
4. `character.json` (as JSON)
5. Current room block — `world.json[current_room]` rendered as prose
6. Last ~5 `ledger.jsonl` events, most recent last
7. The player's turn text

The model's response is: tool calls (mechanics) + prose (narration). Tools
mutate state; prose is written to `ledger.jsonl` as a `narration` event.

## Command surface

`delve` is the user-facing CLI:

- `delve new [--seed N]` — new run, new graph, fresh XDG dir
- `delve play [<run-id>]` — resume (defaults to most recent)
- `delve list` — list runs with their state (alive, dead, won)
- `delve show [<run-id>]` — dump character sheet + current room
- `delve abandon <run-id>` — delete a run

`delve play` internally invokes our `agent` runner (from the sibling
qwen/ project) with the composed system prompt and the roguebash tool
directory.

## Directory layout

```
roguebash/
├── design.md                    # this file
├── README.md                    # preserved philosophy; to be rewritten
├── bin/
│   └── delve                    # user CLI (new / play / list / etc.)
├── engine/
│   ├── generator/               # graph procgen (macro + micro + BFS)
│   ├── state/                   # XDG paths, save/load, ledger append
│   ├── prompt/                  # system-prompt composer
│   └── rules/                   # skill-check, combat, damage math
├── resources/
│   ├── schema.md                # JSONL schemas (read this first)
│   ├── rooms.jsonl              # terminal-node catalog
│   ├── areas.jsonl              # container catalog (with subgraphs)
│   ├── monsters.jsonl           # BEASTS — fight / loot / evade
│   ├── npcs.jsonl               # NPCs — hinder / neutral / help
│   ├── factions.jsonl           # faction disposition matrix, territories
│   ├── items.jsonl              # loot catalog
│   └── hazards.jsonl            # traps & environmental dangers
├── tools/
│   ├── README.md                # tool contract (MCP-shaped)
│   ├── look/                    # exploration verbs
│   ├── move/
│   ├── examine/
│   ├── take/
│   ├── drop/
│   ├── use/
│   ├── inventory/
│   ├── skill_check/             # mechanics
│   ├── save_throw/
│   ├── attack/
│   ├── cast_spell/
│   ├── character_sheet/
│   └── save_game/               # meta
├── prompts/
│   ├── dm_voice.md              # narrator persona
│   ├── exploration_mode.md      # overlay: free movement, no initiative
│   ├── combat_mode.md           # overlay: turn order, attack economy
│   └── legacy_dm_prompt.md      # the fork's original 18 KB prompt (ref)
├── rules/                       # inherited 5e SRD content (to be pared)
└── images/                      # inherited
```

## Contracts (canonical references)

- JSONL schemas for rooms/areas/monsters/items/hazards:
  `resources/schema.md`
- Tool contract (entrypoint, `--schema`, stdin-JSON invocation):
  `tools/README.md`
- State file schemas (character, world, ledger events):
  `engine/state/README.md`

## Explicit non-goals

- Not a chat wrapper around 5e. The mechanics are strong enough to be
  played with dice on a table, even without the model.
- Not a narrative writing partner. The model narrates within the bounds
  the mechanics set; it does not decide outcomes.
- Not PvP, not multiplayer, not networked. One person, one terminal.
