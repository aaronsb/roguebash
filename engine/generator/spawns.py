"""Resolve each room's `spawns` tables at generation time.

The schema stores weighted spawn entries as `{"ref": ..., "chance": float}`.
The generated `graph.json` strips the `chance` field because the roll
has already been made — so a spawn list in graph.json is a flat list
of `{"ref": ...}` objects. This matches the example in
`engine/state/README.md` (see the `spawns` field of the `rooms` subtree).

Missing refs are warned + skipped (task rule).
"""

from __future__ import annotations

import random
import sys
from typing import Any


def _warn(msg: str) -> None:
    print(f"[engine.generator] warning: {msg}", file=sys.stderr)


def _roll_table(
    entries: list[dict[str, Any]],
    rng: random.Random,
    resolver,
    label: str,
) -> list[dict[str, str]]:
    """Return [{"ref": ...}, ...] after rolling each entry's `chance`.

    Entries without a `chance` field are treated as guaranteed (chance=1).
    Entries with unresolvable `ref` are skipped with a warning.
    """
    out: list[dict[str, str]] = []
    for e in entries or []:
        ref = e.get("ref")
        if not isinstance(ref, str):
            _warn(f"{label}: spawn entry missing string 'ref' — skipped")
            continue
        chance = e.get("chance", 1.0)
        try:
            chance_f = float(chance)
        except (TypeError, ValueError):
            chance_f = 1.0
        if resolver(ref) is None:
            _warn(f"{label}: unresolvable ref {ref!r} — skipped")
            continue
        # Always consume an rng roll — even for chance=1 — so downstream
        # determinism isn't perturbed by editing a chance value.
        if rng.random() <= chance_f:
            out.append({"ref": ref})
    return out


def resolve_room_spawns(
    room: dict[str, Any],
    catalogs,
    rng: random.Random,
) -> dict[str, list[dict[str, str]]]:
    """Return the resolved `spawns` block for one room."""
    spawns = room.get("spawns") or {}
    rid = room.get("id", "<unknown>")
    return {
        "items": _roll_table(spawns.get("items"), rng, catalogs.resolve, f"{rid}.items"),
        "monsters": _roll_table(spawns.get("monsters"), rng, catalogs.resolve, f"{rid}.monsters"),
        "hazards": _roll_table(spawns.get("hazards"), rng, catalogs.resolve, f"{rid}.hazards"),
    }


# ----------------------------------------------------------------------
# Set-piece inserts
# ----------------------------------------------------------------------

def apply_setpieces(
    room: dict[str, Any],
    resolved_spawns: dict[str, list[dict[str, str]]],
    catalogs,
    rng: random.Random,
) -> None:
    """Mutate `resolved_spawns` in place to honor any set-piece tags.

    Set-pieces are rooms with the `set_piece` tag. For every such room
    we scan their declared `spawns` tables and force all entries to
    appear (whether or not the chance roll succeeded) — the rationale
    being that handcrafted rooms are meant to feel populated in a
    specific way. This is a cheap, deterministic implementation of
    the "set-piece inserts" step in the task spec; we deliberately
    avoid randomness here so set-pieces feel stable across seeds.

    Missing refs are logged + skipped.
    """
    tags = room.get("tags") or []
    if "set_piece" not in tags:
        return

    spawns = room.get("spawns") or {}
    rid = room.get("id", "<unknown>")
    for bucket in ("items", "monsters", "hazards"):
        seen_refs = {e["ref"] for e in resolved_spawns.get(bucket, [])}
        for e in spawns.get(bucket) or []:
            ref = e.get("ref")
            if not isinstance(ref, str) or ref in seen_refs:
                continue
            if catalogs.resolve(ref) is None:
                print(
                    f"[engine.generator] warning: {rid} set-piece {bucket}: "
                    f"unresolvable ref {ref!r} — skipped",
                    file=sys.stderr,
                )
                continue
            resolved_spawns[bucket].append({"ref": ref})
            seen_refs.add(ref)
