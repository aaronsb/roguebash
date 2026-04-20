"""Catalog lookups by ref.

`resources/*.jsonl` are loaded lazily on first call and cached for the
life of the Python process (each tool invocation is its own process,
so caching is scoped correctly).

Public surface:
    lookup(ref)        -> dict | None    # any ref, auto-routed by prefix
    lookup_item(id)    -> dict | None
    lookup_monster(id) -> dict | None
    lookup_npc(id)     -> dict | None
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

from . import runtime as _rt


def _load_jsonl(path: Path) -> dict[str, dict]:
    """Load a JSONL catalog keyed on each entry's `id` field."""
    out: dict[str, dict] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"[_shared.catalogs] {path.name}:{lineno} "
                    f"malformed JSON — skipped ({e})",
                    file=sys.stderr,
                )
                continue
            _id = obj.get("id")
            if isinstance(_id, str):
                out[_id] = obj
    return out


@lru_cache(maxsize=1)
def _items() -> dict[str, dict]:
    return _load_jsonl(_rt.resources_dir() / "items.jsonl")


@lru_cache(maxsize=1)
def _monsters() -> dict[str, dict]:
    return _load_jsonl(_rt.resources_dir() / "monsters.jsonl")


@lru_cache(maxsize=1)
def _npcs() -> dict[str, dict]:
    return _load_jsonl(_rt.resources_dir() / "npcs.jsonl")


def lookup_item(ref: str) -> dict | None:
    """Return the catalog entry for an item ref (e.g. ``item.longbow``)."""
    return _items().get(ref)


def lookup_monster(ref: str) -> dict | None:
    """Return the catalog entry for a monster ref (e.g. ``monster.wolf``)."""
    return _monsters().get(ref)


def lookup_npc(ref: str) -> dict | None:
    """Return the catalog entry for an NPC ref (e.g. ``npc.bandit_archer``)."""
    return _npcs().get(ref)


def lookup(ref: str) -> dict | None:
    """Route by id-prefix, returning whichever catalog knows about ``ref``.

    The canonical prefixes are ``item.``, ``monster.``, ``npc.``; if the
    prefix isn't recognized we still try all three so edge refs still
    resolve.
    """
    if not isinstance(ref, str):
        return None
    if ref.startswith("item."):
        return lookup_item(ref)
    if ref.startswith("monster."):
        return lookup_monster(ref)
    if ref.startswith("npc."):
        return lookup_npc(ref)
    # Unknown prefix — try each.
    return lookup_item(ref) or lookup_monster(ref) or lookup_npc(ref)
