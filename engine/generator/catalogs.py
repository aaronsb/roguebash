"""Load the scenario JSONL catalogs into plain Python dicts.

Catalogs live under `scenarios/`:

    scenarios/_common/            — scenario-agnostic catalogs
        monsters.jsonl            — bestiary, biome-tagged
        items.jsonl               — loot and usables
        hazards.jsonl             — traps and environmental perils
    scenarios/<name>/             — one scenario's world content
        rooms.jsonl               — terminal-node catalog
        areas.jsonl               — container-node catalog
        factions.jsonl            — who owns what
        npcs.jsonl                — sentient denizens
        overrides.jsonl           — optional: scenario-specific monster/item/
                                    hazard replacements, merged by id with
                                    the common catalogs (scenario wins)

JSONL: one JSON object per line. Blank lines and lines prefixed with `#`
are ignored. Malformed lines emit a warning on stderr but do NOT abort
the load — the schema is append-only and a single bad row shouldn't
brick a run.

The loader returns a `Catalogs` bundle keyed by canonical file name.
Everything downstream reads from this bundle; nothing else opens the
JSONL files directly.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable


# Catalogs that live under `_common/` and are reusable across scenarios.
COMMON_FILES: dict[str, str] = {
    "monsters": "monsters.jsonl",
    "items": "items.jsonl",
    "hazards": "hazards.jsonl",
}

# Catalogs that live inside a specific `scenarios/<name>/` directory.
SCENARIO_FILES: dict[str, str] = {
    "areas": "areas.jsonl",
    "rooms": "rooms.jsonl",
    "factions": "factions.jsonl",
    "npcs": "npcs.jsonl",
}

# Optional scenario-local overrides — entries here are merged on top of
# the common catalogs, keyed by `id`. The loader routes each override
# into the right bucket based on its id prefix (`monster.`, `item.`,
# `hazard.`).
OVERRIDES_FILE = "overrides.jsonl"


class Catalogs:
    """Parsed catalog bundle. Each attribute is a `dict[id -> entry]`.

    Storing by id (rather than as a list) makes ref resolution O(1) and
    keeps the downstream code readable.
    """

    def __init__(
        self,
        areas: dict[str, dict[str, Any]],
        rooms: dict[str, dict[str, Any]],
        factions: dict[str, dict[str, Any]],
        npcs: dict[str, dict[str, Any]],
        monsters: dict[str, dict[str, Any]],
        items: dict[str, dict[str, Any]],
        hazards: dict[str, dict[str, Any]],
    ) -> None:
        self.areas = areas
        self.rooms = rooms
        self.factions = factions
        self.npcs = npcs
        self.monsters = monsters
        self.items = items
        self.hazards = hazards

    # Ref-resolution helpers. Return None on miss so callers can skip
    # gracefully (logged via warn(), never raised).
    def resolve(self, ref: str) -> dict[str, Any] | None:
        if not isinstance(ref, str):
            return None
        if ref.startswith("item."):
            return self.items.get(ref)
        if ref.startswith("monster."):
            return self.monsters.get(ref)
        if ref.startswith("hazard."):
            return self.hazards.get(ref)
        if ref.startswith("npc."):
            return self.npcs.get(ref)
        if ref.startswith("faction."):
            return self.factions.get(ref)
        if ref.startswith("area."):
            return self.areas.get(ref)
        # Rooms: ids are dotted like `swamp.boardwalk_gate`, no `room.` prefix.
        return self.rooms.get(ref)

    def iter_npcs_by_role(self, role: str) -> list[dict[str, Any]]:
        """All NPC entries with the given role, sorted by id for determinism."""
        out = [n for n in self.npcs.values() if n.get("role") == role]
        return sorted(out, key=lambda n: n.get("id", ""))


def _warn(msg: str) -> None:
    print(f"[engine.generator] warning: {msg}", file=sys.stderr)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file tolerantly. Skip malformed / non-object lines with a warn."""
    out: list[dict[str, Any]] = []
    if not path.is_file():
        _warn(f"catalog missing: {path} — returning empty")
        return out
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                _warn(f"{path.name}:{lineno}: {exc.msg} — skipped")
                continue
            if not isinstance(obj, dict):
                _warn(f"{path.name}:{lineno}: not a JSON object — skipped")
                continue
            if "id" not in obj or not isinstance(obj["id"], str):
                _warn(f"{path.name}:{lineno}: missing string 'id' — skipped")
                continue
            out.append(obj)
    return out


def _to_map(entries: Iterable[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    """Index entries by id. Warn on duplicates; first wins."""
    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        eid = e["id"]
        if eid in out:
            _warn(f"{label}: duplicate id {eid!r} — keeping first")
            continue
        out[eid] = e
    return out


def list_scenarios(scenarios_dir: Path) -> list[str]:
    """Return a sorted list of scenario directory names under `scenarios_dir`.

    Excludes `_common` and any hidden/underscore-prefixed entries. Sorted
    alphabetically so callers relying on deterministic selection (e.g.
    seed-based `--scenario random`) get a stable ordering.
    """
    if not scenarios_dir.is_dir():
        return []
    out: list[str] = []
    for entry in scenarios_dir.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("_") or name.startswith("."):
            continue
        out.append(name)
    out.sort()
    return out


def pick_random_scenario(scenarios_dir: Path, rng: random.Random) -> str:
    """Pick a scenario name deterministically from `rng`.

    Raises RuntimeError if no scenarios are present. Using the caller's
    seeded RNG keeps `--scenario random --seed N` reproducible.
    """
    names = list_scenarios(scenarios_dir)
    if not names:
        raise RuntimeError(f"No scenarios found under {scenarios_dir}")
    return rng.choice(names)


def load_catalogs(scenarios_dir: Path, scenario: str) -> Catalogs:
    """Parse the common + scenario catalogs and return a Catalogs bundle.

    Load order per content type:
      1. Read `_common/<file>.jsonl` for monsters/items/hazards.
      2. Read `<scenario>/<file>.jsonl` for areas/rooms/factions/npcs.
      3. Read optional `<scenario>/overrides.jsonl`; its entries replace
         the common entry with the same `id` (scenario wins). Overrides
         are routed by id prefix (`monster.` / `item.` / `hazard.`).
    """
    common_dir = scenarios_dir / "_common"
    scen_dir = scenarios_dir / scenario

    if not scen_dir.is_dir():
        raise RuntimeError(
            f"scenario directory not found: {scen_dir} "
            f"(available: {', '.join(list_scenarios(scenarios_dir)) or '—'})"
        )

    # Common catalogs.
    monsters_map = _to_map(
        _load_jsonl(common_dir / COMMON_FILES["monsters"]), "monsters.jsonl"
    )
    items_map = _to_map(
        _load_jsonl(common_dir / COMMON_FILES["items"]), "items.jsonl"
    )
    hazards_map = _to_map(
        _load_jsonl(common_dir / COMMON_FILES["hazards"]), "hazards.jsonl"
    )

    # Scenario catalogs.
    areas_map = _to_map(
        _load_jsonl(scen_dir / SCENARIO_FILES["areas"]), "areas.jsonl"
    )
    rooms_map = _to_map(
        _load_jsonl(scen_dir / SCENARIO_FILES["rooms"]), "rooms.jsonl"
    )
    factions_map = _to_map(
        _load_jsonl(scen_dir / SCENARIO_FILES["factions"]), "factions.jsonl"
    )
    npcs_map = _to_map(
        _load_jsonl(scen_dir / SCENARIO_FILES["npcs"]), "npcs.jsonl"
    )

    # Optional overrides — scenario-specific replacements for
    # monster/item/hazard entries. Keyed by id prefix. Missing file is fine.
    overrides_path = scen_dir / OVERRIDES_FILE
    if overrides_path.is_file():
        for entry in _load_jsonl(overrides_path):
            eid = entry["id"]
            if eid.startswith("monster."):
                monsters_map[eid] = entry
            elif eid.startswith("item."):
                items_map[eid] = entry
            elif eid.startswith("hazard."):
                hazards_map[eid] = entry
            else:
                _warn(
                    f"overrides.jsonl: entry {eid!r} has unrecognized prefix "
                    "(expected monster./item./hazard.) — skipped"
                )

    return Catalogs(
        areas=areas_map,
        rooms=rooms_map,
        factions=factions_map,
        npcs=npcs_map,
        monsters=monsters_map,
        items=items_map,
        hazards=hazards_map,
    )
