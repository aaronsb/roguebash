# resources/schema.md — JSONL catalog schemas

Every catalog file under `resources/` is a JSONL (one JSON object per line,
no outer array). Objects are free to carry additional fields beyond the
schema, but these are the required / well-known ones.

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
