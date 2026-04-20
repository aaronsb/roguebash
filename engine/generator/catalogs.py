"""Load the resources/*.jsonl catalogs into plain Python dicts.

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
import sys
from pathlib import Path
from typing import Any, Iterable


# Canonical catalog filenames. Order matters only for the stderr banner
# in --verbose mode; the dict below is insertion-ordered.
CATALOG_FILES: dict[str, str] = {
    "areas": "areas.jsonl",
    "rooms": "rooms.jsonl",
    "factions": "factions.jsonl",
    "npcs": "npcs.jsonl",
    "monsters": "monsters.jsonl",
    "items": "items.jsonl",
    "hazards": "hazards.jsonl",
}


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


def load_catalogs(resources_dir: Path) -> Catalogs:
    """Parse every catalog under `resources_dir` and return a Catalogs bundle."""
    raw = {k: _load_jsonl(resources_dir / fname) for k, fname in CATALOG_FILES.items()}
    return Catalogs(
        areas=_to_map(raw["areas"], "areas.jsonl"),
        rooms=_to_map(raw["rooms"], "rooms.jsonl"),
        factions=_to_map(raw["factions"], "factions.jsonl"),
        npcs=_to_map(raw["npcs"], "npcs.jsonl"),
        monsters=_to_map(raw["monsters"], "monsters.jsonl"),
        items=_to_map(raw["items"], "items.jsonl"),
        hazards=_to_map(raw["hazards"], "hazards.jsonl"),
    )
