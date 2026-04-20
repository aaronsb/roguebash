# scenarios/schema.md — JSONL catalog schemas

Every catalog file under `scenarios/` is a JSONL (one JSON object per line,
no outer array). Objects are free to carry additional fields beyond the
schema, but these are the required / well-known ones.

Content is split across two tiers:

- `scenarios/_common/` holds scenario-agnostic catalogs (monsters, items,
  hazards — biome-tagged and reusable).
- `scenarios/<name>/` holds one scenario's world content (rooms, areas,
  factions, npcs, plus an optional `overrides.jsonl` that replaces
  common entries by id).

See `scenarios/_common/biomes.md` for the canonical biome set and
`scenarios/<name>/scenario.md` for that scenario's pitch, tone, and
victory condition.

Seeds are deterministic: the generator re-reads these files at `delve new`
time, shuffles with the run seed, and writes `graph.json` into the run's
XDG state directory.

---

## rooms.jsonl — terminal nodes

```json
{
  "id": "swamp.sunken_grove",
  "type": "room",
  "name": "Sunken Grove",
  "biome": "swamp",
  "tier": 2,
  "tags": ["outdoor", "wet", "eerie"],
  "compatible_with": ["swamp.*", "path", "overgrown"],
  "short_desc": "A ring of rotten willows, knee-deep in black water.",
  "long_desc": "Moss drips from every branch. The water ripples once, then settles. Something down there is watching the reflection of the sky.",
  "exits": { "north": null, "east": null, "south": null, "west": null },
  "spawns": {
    "items":    [{ "ref": "item.lantern", "chance": 0.4 }],
    "monsters": [{ "ref": "monster.giant_frog", "chance": 0.3 }],
    "hazards":  [{ "ref": "hazard.leech_pool", "chance": 0.2 }]
  },
  "flags": { "dark": false, "submerged_partial": true }
}
```

### Field contract

| field | type | notes |
|---|---|---|
| `id` | string | globally unique, dotted namespace by biome/area |
| `type` | `"room"` | literal |
| `name` | string | short title shown in UI |
| `biome` | string | `cavern`, `swamp`, `desert`, `mountain`, `urban`, `tomb`, `forest`, `river`, `ruin`, ... |
| `tier` | integer | 0 (tutorial) → 5 (endgame) |
| `tags` | string[] | small, predicate-style; used for compatibility and set-piece matching |
| `compatible_with` | string[] | glob-ish ids or tag patterns; the generator places neighbors whose tags or ids intersect |
| `short_desc` | string | one-line used in `look` |
| `long_desc` | string | shown on first entry or `examine room` |
| `exits` | object | cardinal exits; generator fills in connections |
| `spawns` | object | weighted spawn tables (refs into other catalogs) |
| `flags` | object | room-level state toggles (`dark`, `locked`, `submerged_partial`, ...) |

---

## Transition rooms — the spline between biomes

Transition rooms are a special first-class subtype of `room` whose job is to
smooth abrupt biome cuts in the macro-generated path. Instead of stitching
`swamp → desert` directly (a "randomly-generated" tell), the generator
inserts a transition room like `desert.windcut_dunes → transition.desert_ruin_wash → ruin.overgrown_plaza` whenever the biome-adjacency cost between two
macro neighbors is > 1.

A transition room lives in `rooms.jsonl` alongside ordinary rooms, but uses
`biome: "transition"` (not one of the canonical eight) and adds a `bridges`
field naming the two biomes it connects:

```json
{
  "id": "transition.forest_swamp_edge",
  "type": "room",
  "name": "Forest Swamp Edge",
  "biome": "transition",
  "bridges": ["forest", "swamp"],
  "tier": 1,
  "tags": ["outdoor", "liminal", "boundary"],
  "compatible_with": ["forest.*", "swamp.*"],
  "short_desc": "The last of the trees give way to standing water.",
  "long_desc": "…",
  "exits": { "north": null, "east": null, "south": null, "west": null },
  "spawns": { "items": [], "monsters": [], "hazards": [] },
  "flags": {}
}
```

### Conventions

| field | notes |
|---|---|
| `id` | `transition.<bio_a>_<bio_b>_<descriptor>` (order `bio_a, bio_b` alphabetical where practical — just be consistent) |
| `biome` | literally `"transition"` — keeps them out of normal biome pools in `rooms.pool: ["forest.*"]` etc. |
| `bridges` | exactly two biome strings; order insignificant |
| `compatible_with` | should include globs for both bridged biomes so generic compat checks still pass |
| `tier` | pick a tier near the average of what you expect on either side; generators match by biome cost, not tier |
| `tags` | always include `liminal` and `boundary`; room-feel tags (`wet`, `dark`, `collapsed`) as normal |

### How they're placed

Transition rooms are **not** picked up by normal `rooms.pool` entries —
their `biome` is `"transition"`, not (e.g.) `"forest"`, so `_expand_pool`'s
biome-head match skips them. The macro generator synthesizes a single-room
"transition area" on the fly when it inserts a transition between two
high-cost neighbors. That synthetic area explicitly names the transition
room in its `rooms.pool` / `must_include`, so the micro layer instantiates
it just like any other area.

See `scenarios/_common/biome_adjacency.json` for the cost matrix that
drives the insertion decision, and `engine/generator/macro.py` for the
synthesis logic.

---

## areas.jsonl — container nodes with internal subgraphs

```json
{
  "id": "area.barrow_swamp",
  "type": "area",
  "name": "Barrow Swamp",
  "biome": "swamp",
  "tier": 2,
  "tags": ["outdoor", "wetlands", "haunted"],
  "compatible_with": ["river.*", "forest.*", "ruin.*"],
  "rooms": {
    "min": 4,
    "max": 7,
    "pool": ["swamp.*"],
    "must_include": ["swamp.witch_hut"]
  },
  "entrance_rooms": ["swamp.boardwalk_gate"],
  "exit_rooms":     ["swamp.old_causeway"],
  "ambient_desc": "Fat flies bumble through air that smells of wet rope."
}
```

### Notes
- `rooms.pool` entries accept glob patterns (`swamp.*`) or exact ids.
- `entrance_rooms`/`exit_rooms` must be in the final subgraph; they are the
  only nodes the macro generator may connect through.

---

## Beasts vs NPCs (the load-bearing distinction)

- A **beast** (`monsters.jsonl`) is something you *fight or loot*. No
  dialog surface. Giant frogs, oozes, wights, swarms, wild dogs, feral
  wraiths. Encounter = combat or evasion.
- An **NPC** (`npcs.jsonl`) is something that can *hinder, help, or
  simply exist alongside you* — a human bandit, a dwarven blacksmith, a
  hermit, a frightened farmer. NPCs have a disposition, a role, a
  species, and optionally a faction allegiance. Encounter surfaces
  include conversation, trade, quest hooks, and (if it comes to it)
  combat.

The same *species* can legally live on either side: a goblin swarm
bursting out of a sewer grate is a beast; the goblin tribe with a camp,
a grievance, and a chief is an NPC roster. Authoring choice, per entry.

---

## monsters.jsonl — bestiary-lite

```json
{
  "id": "monster.giant_frog",
  "name": "giant frog",
  "tier": 1,
  "tags": ["beast", "amphibious", "swamp"],
  "ac": 11,
  "hp": "2d6+2",
  "speed": { "walk": 20, "swim": 30 },
  "stats": { "str": 12, "dex": 13, "con": 11, "int": 2, "wis": 10, "cha": 3 },
  "attacks": [
    { "name": "bite", "to_hit": "+3", "damage": "1d6+1", "damage_type": "piercing" },
    { "name": "swallow", "condition": "on crit", "effect": "grappled + restrained" }
  ],
  "xp": 50,
  "short_desc": "A toad the size of a small dog, mottled green and grey."
}
```

HP can be an integer (fixed) or a dice expression; rolled at spawn.

---

## npcs.jsonl — sentient denizens with social surface

```json
{
  "id": "npc.bandit_archer",
  "species": "human",
  "role": "bandit",
  "tier": 1,
  "disposition_default": "hostile",
  "faction_default": "faction.red_hollow",
  "alignment": "CE",
  "ac": 12,
  "hp": "11 (2d8+2)",
  "stats": { "str": 11, "dex": 14, "con": 12, "int": 10, "wis": 10, "cha": 10 },
  "attacks": [
    { "name": "shortbow", "to_hit": "+4", "damage": "1d6+2", "damage_type": "piercing", "range": 80 },
    { "name": "scimitar", "to_hit": "+3", "damage": "1d6+1", "damage_type": "slashing" }
  ],
  "dialog_hooks": [
    "demands gold, crossbow aimed",
    "boasts about what the Red Hollow will do to the next caravan",
    "threatens but will run if outmatched"
  ],
  "loot_table": ["item.copper_pouch", "item.arrows", "item.stolen_ring"],
  "xp": 25,
  "short_desc": "A hollow-eyed human in mismatched leather, bow drawn."
}
```

### Field contract (deltas from monsters.jsonl)

| field | notes |
|---|---|
| `species` | `human`, `dwarf`, `elf`, `halfling`, `goblin`, `orc`, ... |
| `role` | `bandit`, `blacksmith`, `farmer`, `guard`, `merchant`, `hermit`, `cultist`, `scout`, `innkeeper`, `priest`, ... |
| `disposition_default` | `hostile`, `wary`, `neutral`, `friendly` — can be overridden by the encounter context (e.g. a normally-friendly farmer is hostile if you just burned his barn) |
| `faction_default` | `faction.*` id, or `null` for unaligned wanderers |
| `alignment` | Optional two-letter 5e shorthand (`LG`/`NG`/`CG`/`LN`/`TN`/`CN`/`LE`/`NE`/`CE`). **Flavor hint, not script.** See below. |
| `dialog_hooks` | 2–5 one-line prompts the DM can use to drive the NPC's voice. Not literal dialog — hooks for improvisation. |
| `loot_table` | item refs dropped on death (looted only; no gamey "corpses contain 5gp" — make it flavored) |

**On alignment:** it's a shorthand for tendency and tone — a single anchor
the DM prompt can lean on when improvising. Tools never read it; the
generator reads it only as a weak preference signal (a CE faction slightly
prefers CE/NE/LE members, nothing hard). **If disposition, role, or the
situation conflicts with alignment, the situation wins.** A "lawful-good"
guard captain will still shake down travelers if his faction is corrupt and
his family is hungry; a "chaotic-evil" bandit will still spare the child
who reminds him of his sister. Alignment steers, it does not dictate.

---

## factions.jsonl — who owns what, who hates whom

Factions let the generator populate areas *coherently*: an area controlled
by the Red Hollow will draw bandit NPCs; a farming village under their
"protection" will draw fearful farmers and the occasional bandit toll
collector. The same dwarf template can appear as a blacksmith in a peaceful
dwarf-run town *or* as an angry exile in the wilds — faction and
disposition do the routing.

```json
{
  "id": "faction.red_hollow",
  "name": "Red Hollow Bandits",
  "tier": 2,
  "alignment": "CE",
  "description": "Former coachmen turned brigands after the western trade road collapsed. They extort the swampland villages and ambush what little traffic still uses the old highway.",
  "home_areas": ["area.red_hollow_camp"],
  "territories": ["area.barrow_swamp", "area.old_highway"],
  "roles": ["bandit", "bandit_captain", "scout", "fence"],
  "relations": {
    "player_default": "hostile",
    "faction.oak_mill": "dominating",
    "faction.crown_patrol": "hostile",
    "faction.iron_vein_clan": "neutral"
  },
  "population_mix": {
    "bandit": 0.7,
    "scout": 0.2,
    "bandit_captain": 0.1
  }
}
```

### Field contract

| field | notes |
|---|---|
| `home_areas` | areas *the faction lives in* — populated entirely from its role pool |
| `territories` | areas the faction *influences but doesn't wholly inhabit* — e.g. a village under protection, a highway they patrol — populated with a mix of local NPCs + faction agents |
| `roles` | which `role` values in `npcs.jsonl` this faction recruits from |
| `relations.player_default` | `hostile` / `wary` / `neutral` / `friendly` — starting disposition on first contact |
| `relations.<other_faction>` | `hostile` / `rival` / `neutral` / `allied` / `dominating` / `fearful` — two-way relationships; the generator uses this to decide secondary tensions in shared areas |
| `alignment` | Optional 5e two-letter shorthand for the faction's prevailing tone. Same "flavor hint, not script" rule as for NPCs — a CE faction can still have principled outliers; they're the narrative interesting ones. |
| `population_mix` | weights for role selection when generating home-area inhabitants |

### Cross-reference conventions

To keep parallel authoring sane:

- Area ids: `area.<biome>_<descriptor>`, e.g. `area.barrow_swamp`
- Room ids: `<biome>.<descriptor>`, e.g. `swamp.boardwalk_gate`
- NPC ids: `npc.<role>_<descriptor>`, e.g. `npc.bandit_archer`,
  `npc.dwarf_blacksmith`
- Monster ids: `monster.<descriptor>`, e.g. `monster.giant_frog`
- Item ids: `item.<descriptor>`
- Hazard ids: `hazard.<descriptor>`
- Faction ids: `faction.<short_name>`

Authors in parallel lanes should follow these conventions so cross-refs
(rooms referencing items, factions referencing areas, areas referencing
faction control) just work when assembled.

---

## items.jsonl — loot & usable items

```json
{
  "id": "item.lantern",
  "name": "brass lantern",
  "tags": ["light", "consumable"],
  "tier": 0,
  "use": {
    "effect": "grants_light",
    "duration_turns": 100,
    "consumes": "item.oil_flask"
  },
  "weight": 2,
  "short_desc": "A tarnished brass lantern. Shake it and you can hear oil inside."
}
```

### Armor AC fields (convention)

Armor entries carry an `armor_type` discriminator and use different AC
fields depending on it:

- `armor_type: "body"` → `ac_base` (integer), the AC *replacement* value
  (e.g. leather = 11, chain shirt = 13, plate = 18). Dex modifier
  application depends on the armor's mobility; record `dex_cap: N` or
  `dex_cap: "none"` if relevant.
- `armor_type: "shield"` → `ac_bonus` (integer), an *additive* bonus
  stacked on whatever body armor is worn (shield = +2).
- Optional `stealth_disadvantage: true` for plate/chain etc.

This split keeps the math unambiguous: consumers check `armor_type` and
read the appropriate field.

---

## hazards.jsonl — traps, environmental dangers, room-level perils

```json
{
  "id": "hazard.leech_pool",
  "name": "leech pool",
  "tier": 1,
  "tags": ["water", "biological"],
  "trigger": "on_enter",
  "check": { "ability": "dex", "dc": 11, "on_fail": "apply_leeches" },
  "effect": {
    "apply_leeches": {
      "damage_per_turn": "1d4",
      "damage_type": "piercing",
      "ends": "skill_check:athletics:12"
    }
  },
  "short_desc": "The water boils softly. Leeches rise toward warmth."
}
```
