#!/bin/bash
# make_fixture.sh — create a throwaway run dir under $1 (default $TMPDIR/rb-fixture)
# with a tiny hand-crafted graph, character, and empty world/ledger.
#
# Sourced or invoked by each tool's EXAMPLE.sh so smoke-tests don't need
# a real delve run.
set -euo pipefail

FIXTURE_DIR="${1:-${TMPDIR:-/tmp}/rb-fixture}"
mkdir -p "$FIXTURE_DIR"

cat > "$FIXTURE_DIR/character.json" <<'EOF'
{
  "name": "Ibri",
  "race": "halfling",
  "class": "ranger",
  "level": 1,
  "xp": 0,
  "stats": {"str":10,"dex":16,"con":12,"int":10,"wis":14,"cha":8},
  "hp": {"current": 12, "max": 12},
  "ac": 14,
  "speed": 25,
  "proficiencies": ["longbow","stealth"],
  "inventory": [
    {"ref": "item.longbow", "qty": 1},
    {"ref": "item.oil_flask", "qty": 1}
  ],
  "status_effects": [],
  "gold": 0
}
EOF

cat > "$FIXTURE_DIR/world.json" <<'EOF'
{
  "current_room": "swamp.boardwalk_gate",
  "revealed": {
    "swamp.boardwalk_gate": {"exits_known": [], "inspected": false, "items_taken": []}
  },
  "mode": "exploration",
  "turn": 1
}
EOF

cat > "$FIXTURE_DIR/graph.json" <<'EOF'
{
  "seed": 1,
  "macro": [],
  "rooms": {
    "swamp.boardwalk_gate": {
      "area": "area.barrow_swamp",
      "name": "Boardwalk Gate",
      "tags": ["outdoor","wet"],
      "short_desc": "A warped boardwalk arcs over the marsh.",
      "long_desc": "The planks creak under every step; an iron gate leans half-open, its hinges weeping rust.",
      "exits": {"north": "swamp.sunken_grove", "south": null, "east": null, "west": null},
      "spawns": {
        "items": [{"ref": "item.lantern"}],
        "monsters": [],
        "npcs": [],
        "hazards": []
      },
      "flags": {"dark": false}
    },
    "swamp.sunken_grove": {
      "area": "area.barrow_swamp",
      "name": "Sunken Grove",
      "tags": ["outdoor","wet","eerie"],
      "short_desc": "A ring of rotten willows, knee-deep in black water.",
      "long_desc": "Moss drips from every branch. The water ripples once, then settles.",
      "exits": {"south": "swamp.boardwalk_gate", "north": null, "east": null, "west": null},
      "spawns": {
        "items": [],
        "monsters": [{"ref": "monster.giant_frog"}],
        "npcs": [{"ref": "npc.dwarf_blacksmith"}],
        "hazards": [{"ref": "hazard.leech_pool"}]
      },
      "flags": {"dark": false, "submerged_partial": true}
    }
  }
}
EOF

: > "$FIXTURE_DIR/ledger.jsonl"

echo "$FIXTURE_DIR"
