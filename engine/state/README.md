# engine/state — save files, XDG paths, ledger

## Locations

Everything durable lives under:

    $XDG_STATE_HOME/roguebash/<run-id>/
    (default: ~/.local/state/roguebash/<run-id>/)

The run-id is a short slug: `<seed>-<player-name>-<yyyymmddHHMM>`.

## Files per run

### character.json
The player's live sheet. Tools mutate this.

```json
{
  "name": "Ibri Copperfoot",
  "race": "halfling",
  "class": "ranger",
  "level": 1,
  "xp": 0,
  "stats": { "str": 10, "dex": 16, "con": 12, "int": 10, "wis": 14, "cha": 8 },
  "hp": { "current": 12, "max": 12 },
  "ac": 14,
  "speed": 25,
  "proficiencies": ["longbow", "shortsword", "stealth", "survival"],
  "inventory": [
    { "ref": "item.longbow", "qty": 1 },
    { "ref": "item.arrows",  "qty": 20 }
  ],
  "status_effects": [],
  "gold": 0
}
```

### world.json
What the player has revealed. The *model reads this every turn.*

```json
{
  "current_room": "swamp.boardwalk_gate",
  "revealed": {
    "swamp.boardwalk_gate": {
      "exits_known": ["north"],
      "inspected": false,
      "items_taken": []
    }
  },
  "turn": 7
}
```

### graph.json
Full shuffled world — the answer key. **Never shown to the model.**

```json
{
  "seed": 4815162342,
  "macro": [
    { "id": "area.barrow_swamp", "neighbors": ["area.old_highway", "area.ziggurat_steps"] }
  ],
  "rooms": {
    "swamp.boardwalk_gate": {
      "area": "area.barrow_swamp",
      "exits": { "north": "swamp.sunken_grove", "south": null, "east": null, "west": null },
      "spawns": {
        "items":    [{ "ref": "item.lantern" }],
        "monsters": [],
        "hazards":  []
      },
      "flags": { "dark": false }
    }
  }
}
```

### ledger.jsonl
Append-only event log. One JSON line per event.

```jsonl
{"t":1,"type":"narration","text":"You stand at a boardwalk gate. To the north, the marsh gapes open."}
{"t":1,"type":"tool_call","name":"look","args":{},"result":"..."}
{"t":2,"type":"tool_call","name":"move","args":{"direction":"north"},"result":"ok"}
{"t":2,"type":"skill_check","ability":"dex","dc":11,"roll":14,"modifier":3,"total":17,"pass":true}
{"t":2,"type":"damage","target":"player","amount":3,"source":"hazard.leech_pool"}
{"t":3,"type":"death","actor":"player","cause":"hazard.leech_pool"}
```

The model sees **only the last 5** events in the ledger each turn — not the
full history. This bounds prompt size regardless of run length.

## Event types (canonical set)

| type | fields |
|---|---|
| `narration` | `text` |
| `tool_call` | `name`, `args`, `result` |
| `skill_check` | `ability`, `dc`, `roll`, `modifier`, `total`, `pass` |
| `save_throw` | `save_type`, `dc`, `roll`, `modifier`, `total`, `pass` |
| `attack` | `attacker`, `target`, `weapon`, `to_hit_roll`, `to_hit_total`, `ac`, `hit`, `damage` |
| `damage` | `target`, `amount`, `damage_type`, `source` (the inner field is named `damage_type` to avoid collision with the outer event-type discriminator `"type":"damage"`) |
| `heal` | `target`, `amount`, `source` |
| `item_taken` | `item_ref`, `from_room` |
| `item_dropped` | `item_ref`, `to_room` |
| `level_up` | `new_level`, `choices` |
| `death` | `actor`, `cause` |
| `victory` | `player`, `goal` |

## End-of-run

On `death` or `victory`, the run directory is renamed:

    ~/.local/state/roguebash/<run-id>/  →  ~/.local/state/roguebash/_archive/<run-id>/

so `delve list` can surface it but `delve play` will not resume it.
