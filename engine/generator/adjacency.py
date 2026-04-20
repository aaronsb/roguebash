"""Biome adjacency matrix — cost-of-transition between canonical biomes.

Loaded from `scenarios/_common/biome_adjacency.json` (see that file for the
cost rationale). Lower cost = more thematically adjacent. Self-cost is 0;
1 = natural neighbor (forest↔swamp); 4 = opposite extremes (swamp↔desert).

Used by the macro generator to:
- bias edge selection toward low-cost biome pairs, so a run's biome arc
  feels like a curve rather than a random walk
- decide when to splice a one-room transition area into a high-cost edge
  (cost > 1 → insert)

Transition rooms themselves (biome `"transition"`) are out-of-band and not
part of this matrix; they are indexed separately by their `bridges` field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Cost used when either biome is unknown to the matrix. We pick a value
# large enough that the weighted sampler deprioritizes the edge, but not
# so large that graph generation fails when a scenario uses an
# off-canonical biome. 3 matches the "distant but plausible" band.
UNKNOWN_COST = 3

# The path (relative to `scenarios_dir`) where the matrix lives.
ADJACENCY_FILE = Path("_common") / "biome_adjacency.json"


class BiomeAdjacency:
    """Lookup wrapper around the JSON matrix.

    Exposes `cost(a, b)` returning an int, defaulting to UNKNOWN_COST when
    either biome is missing. Self-cost is always 0 regardless of the file.
    """

    def __init__(self, matrix: dict[str, dict[str, int]]) -> None:
        # Store a copy in normalized form so callers can't mutate it.
        self._matrix: dict[str, dict[str, int]] = {
            str(a): {str(b): int(c) for b, c in row.items()}
            for a, row in matrix.items()
        }

    def cost(self, a: str, b: str) -> int:
        """Return the integer cost of stepping from biome `a` to `b`.

        - Empty or None biomes → UNKNOWN_COST.
        - Self-cost is always 0.
        - Asymmetric matrices are tolerated: if only one direction is
          present we use that; the shipped matrix is symmetric.
        """
        if not a or not b:
            return UNKNOWN_COST
        if a == b:
            return 0
        row_a = self._matrix.get(a)
        row_b = self._matrix.get(b)
        if row_a is not None and b in row_a:
            return int(row_a[b])
        if row_b is not None and a in row_b:
            return int(row_b[a])
        return UNKNOWN_COST

    @property
    def biomes(self) -> list[str]:
        return sorted(self._matrix.keys())

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {a: dict(row) for a, row in self._matrix.items()}


def load_adjacency(scenarios_dir: Path) -> BiomeAdjacency:
    """Load `_common/biome_adjacency.json`, or return an empty matrix.

    Missing file is tolerated — callers get UNKNOWN_COST for every pair,
    which falls back to the old "all biome transitions are equally likely"
    behavior. That keeps the generator working on scenarios that haven't
    been annotated with an adjacency matrix.
    """
    path = scenarios_dir / ADJACENCY_FILE
    if not path.is_file():
        return BiomeAdjacency({})
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return BiomeAdjacency({})
    matrix = data.get("matrix") or {}
    if not isinstance(matrix, dict):
        return BiomeAdjacency({})
    return BiomeAdjacency(matrix)


def index_transition_rooms(
    rooms: dict[str, dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Build an index of transition rooms keyed by their (bio_a, bio_b) pair.

    The key is a frozen 2-tuple with the biomes in alphabetical order, so
    callers can look up either direction with the same key. Multiple
    transition rooms per pair are supported (returned as a sorted list by
    id) for future expansion.
    """
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rid in sorted(rooms.keys()):
        room = rooms[rid]
        if room.get("biome") != "transition":
            continue
        bridges = room.get("bridges") or []
        if not isinstance(bridges, list) or len(bridges) != 2:
            continue
        a, b = str(bridges[0]), str(bridges[1])
        key = tuple(sorted((a, b)))
        out.setdefault(key, []).append(room)
    # Ensure deterministic order within each bucket.
    for key in out:
        out[key].sort(key=lambda r: r["id"])
    return out


def find_transition_room(
    transition_index: dict[tuple[str, str], list[dict[str, Any]]],
    biome_a: str,
    biome_b: str,
) -> dict[str, Any] | None:
    """Return the first transition room bridging `(biome_a, biome_b)` or None."""
    if not biome_a or not biome_b or biome_a == biome_b:
        return None
    key = tuple(sorted((biome_a, biome_b)))
    hits = transition_index.get(key)
    if not hits:
        return None
    return hits[0]


def synthesize_transition_area(
    area_a: dict[str, Any],
    area_b: dict[str, Any],
    transition_room: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    """Build a one-room "transition area" dict that wraps `transition_room`.

    The returned area is shaped like any authored entry in `areas.jsonl`
    so the rest of the pipeline (micro, stitching, faction population)
    can process it without special-casing. Key choices:

    - `id`: `_transition.<bio_a>_<bio_b>.<seq>` — the leading underscore
      is deliberate so it never collides with an authored `area.*` id,
      and so it sorts predictably.
    - `rooms.pool` and `rooms.must_include` explicitly name the transition
      room by id (not by a glob); `_expand_pool` uses biome-head matching
      that wouldn't find a `biome: "transition"` room otherwise.
    - `min == max == 1`: we only want the one bridging room.
    - `entrance_rooms == exit_rooms`: the single room serves as both.
    - `compatible_with`: globs for both bridged biomes, so existing compat
      checks continue to pass.
    - `tier`: average of the two neighbors, so macro-layer difficulty
      sorting stays sensible.
    """
    bio_a = str(area_a.get("biome", ""))
    bio_b = str(area_b.get("biome", ""))
    lo_bio, hi_bio = sorted((bio_a, bio_b))
    tier_a = int(area_a.get("tier", 0) or 0)
    tier_b = int(area_b.get("tier", 0) or 0)
    tier = (tier_a + tier_b) // 2
    room_id = transition_room["id"]

    return {
        "id": f"_transition.{lo_bio}_{hi_bio}.{sequence:02d}",
        "type": "area",
        "name": str(transition_room.get("name", "Transition")),
        "biome": "transition",
        "tier": tier,
        "tags": ["liminal", "boundary", "transition"],
        "compatible_with": [f"{lo_bio}.*", f"{hi_bio}.*"],
        "rooms": {
            "min": 1,
            "max": 1,
            "pool": [room_id],
            "must_include": [room_id],
        },
        "entrance_rooms": [room_id],
        "exit_rooms": [room_id],
        "ambient_desc": str(transition_room.get("short_desc", "")),
        # Metadata used by tests / verbose logs — not consumed downstream.
        "_synthesized": True,
        "_bridges": [lo_bio, hi_bio],
    }
