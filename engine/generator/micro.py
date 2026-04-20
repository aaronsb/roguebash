"""Micro generator — populate each area with rooms and internal edges.

For every area selected by the macro layer we:

1. Gather candidate rooms from the area's `rooms.pool` (glob-expanded
   against `rooms.jsonl`).
2. Honor `rooms.must_include` (forced members).
3. Clamp the final count to `[rooms.min, rooms.max]`, further clamped
   by the pool size.
4. Designate entrance/exit rooms: prefer the area's declared ones, else
   synthesize from the chosen pool.
5. Wire an undirected internal subgraph by laying out the rooms in a
   spine and then sprinkling a few extra compatibility-respecting
   edges, ensuring BFS(entrance → exit) holds.
6. Return per-area and global dicts the serializer can consume.
"""

from __future__ import annotations

import fnmatch
import random
from collections import deque
from typing import Any

from .compat import compatible


CARDINAL = ("north", "east", "south", "west")


def _expand_pool(
    pool: list[str],
    rooms: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve a pool list (globs + exact ids) to room entries.

    Glob patterns match against a room's id or biome. Exact ids match
    the room's id only. Dedup by id, preserve deterministic order
    (sorted by id).
    """
    seen: dict[str, dict[str, Any]] = {}
    for pat in pool or []:
        pat_s = str(pat)
        if "*" in pat_s or "?" in pat_s or "[" in pat_s:
            head = pat_s.split(".", 1)[0]
            for room in rooms.values():
                rid = room["id"]
                if rid in seen:
                    continue
                biome = str(room.get("biome", ""))
                if fnmatch.fnmatchcase(rid, pat_s):
                    seen[rid] = room
                    continue
                if head and biome == head:
                    seen[rid] = room
                    continue
                # Also accept `rid` whose first segment equals the head.
                if head and rid.startswith(head + "."):
                    seen[rid] = room
        else:
            room = rooms.get(pat_s)
            if room and pat_s not in seen:
                seen[pat_s] = room
    return [seen[k] for k in sorted(seen.keys())]


def _wire_rooms(
    chosen: list[dict[str, Any]],
    entrance: str,
    exit_: str,
    rng: random.Random,
) -> dict[str, dict[str, str | None]]:
    """Return `{room_id: {direction: neighbor_id_or_None, ...}}` for `chosen`.

    Builds a spine (entrance → ... → exit) so BFS reachability is
    guaranteed, then adds up to a handful of bonus edges between
    compatibility-passing rooms. Directions are picked per edge from
    the four cardinals, skipping any already-used direction on either
    endpoint.
    """
    exits: dict[str, dict[str, str | None]] = {
        r["id"]: {d: None for d in CARDINAL} for r in chosen
    }

    ids = [r["id"] for r in chosen]
    # Put entrance first, exit last, shuffle the middle deterministically.
    middle = [rid for rid in ids if rid not in (entrance, exit_)]
    rng.shuffle(middle)
    spine = [entrance] + middle + ([exit_] if exit_ != entrance else [])
    # Drop consecutive duplicates (happens if entrance == exit).
    dedup: list[str] = []
    for rid in spine:
        if not dedup or dedup[-1] != rid:
            dedup.append(rid)
    spine = dedup

    by_id = {r["id"]: r for r in chosen}

    def free_dir(rid: str) -> str | None:
        for d in CARDINAL:
            if exits[rid][d] is None:
                return d
        return None

    def connect(a: str, b: str) -> bool:
        """Attach a<->b in opposite cardinal directions if both have slots."""
        if a == b:
            return False
        # Already connected?
        if any(exits[a][d] == b for d in CARDINAL):
            return True
        d_a = free_dir(a)
        d_b = free_dir(b)
        if d_a is None or d_b is None:
            return False
        # Try to use opposite cardinals for the return direction.
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east"}
        if exits[b][opposites[d_a]] is None:
            d_b = opposites[d_a]
        exits[a][d_a] = b
        exits[b][d_b] = a
        return True

    # Spine connections (mandatory).
    for i in range(len(spine) - 1):
        connect(spine[i], spine[i + 1])

    # Bonus edges — a light sprinkle between compatible rooms.
    extras = max(0, len(chosen) // 3)
    for _ in range(extras):
        a = rng.choice(ids)
        b = rng.choice(ids)
        if a == b:
            continue
        if compatible(by_id[a], by_id[b]):
            connect(a, b)

    return exits


def _bfs_ok(
    exits: dict[str, dict[str, str | None]],
    start: str,
    goal: str,
) -> bool:
    if start == goal:
        return True
    if start not in exits or goal not in exits:
        return False
    seen = {start}
    q: deque[str] = deque([start])
    while q:
        cur = q.popleft()
        for nxt in exits[cur].values():
            if nxt is None or nxt in seen:
                continue
            if nxt == goal:
                return True
            seen.add(nxt)
            q.append(nxt)
    return False


def _clamp_count(min_n: int, max_n: int, pool_size: int) -> int:
    """Clamp a desired [min, max] count to what the pool can supply."""
    if pool_size <= 0:
        return 0
    lo = max(1, min(min_n, pool_size))
    hi = max(lo, min(max_n, pool_size))
    return hi  # prefer fuller areas; still deterministic


def instantiate_area(
    area: dict[str, Any],
    all_rooms: dict[str, dict[str, Any]],
    rng: random.Random,
    used_rooms: set[str] | None = None,
) -> dict[str, Any]:
    """Return per-area layout:
        {
          "area_id": str,
          "room_ids": [str, ...],
          "entrance": str,
          "exit": str,
          "exits": {room_id: {dir: neighbor_or_None, ...}},
        }

    `used_rooms` (if supplied) is a set of room ids already claimed by
    previously-instantiated areas. Picks from this area exclude those
    rooms so every room belongs to exactly one area. The caller is
    responsible for updating `used_rooms` with the returned `room_ids`.

    When a must-include room has already been claimed, the later area
    gives it up (first-assigned wins). When the pool is exhausted after
    exclusion, the area's min/max clamp is re-computed against what's
    actually available — if that's zero, this function returns a layout
    with `room_ids == []` and the caller should drop the area.
    """
    used = used_rooms if used_rooms is not None else set()

    rooms_spec = area.get("rooms") or {}
    pool = _expand_pool(rooms_spec.get("pool") or [], all_rooms)
    must_include_ids = [
        rid
        for rid in (rooms_spec.get("must_include") or [])
        if rid in all_rooms and rid not in used
    ]
    must_include = [all_rooms[rid] for rid in must_include_ids]

    # Union pool + must-include, dedup, deterministic order, exclude used.
    combined: dict[str, dict[str, Any]] = {
        r["id"]: r for r in pool if r["id"] not in used
    }
    for r in must_include:
        combined.setdefault(r["id"], r)
    available = sorted(combined.values(), key=lambda r: r["id"])

    desired_min = int(rooms_spec.get("min", 3))
    desired_max = int(rooms_spec.get("max", 5))
    target = _clamp_count(desired_min, desired_max, len(available))
    if target == 0:
        # Pool exhausted — return an empty layout; caller drops this area.
        return {
            "area_id": area["id"],
            "room_ids": [],
            "entrance": "",
            "exit": "",
            "exits": {},
        }

    # Must-include is pinned; pick the rest from `available - must_include`.
    pinned = [all_rooms[rid] for rid in sorted(set(must_include_ids))]
    remaining = [r for r in available if r["id"] not in {p["id"] for p in pinned}]
    rng.shuffle(remaining)
    need = max(0, target - len(pinned))
    picked = pinned + remaining[:need]

    # Re-sort for determinism of the final layout order. (Entrance/exit
    # selection below uses explicit fields; the spine shuffle uses rng.)
    picked_ids = sorted(r["id"] for r in picked)
    picked = [next(r for r in picked if r["id"] == rid) for rid in picked_ids]

    # Entrance/exit designation. Any declared room already claimed by
    # an earlier area is not available here (first-assigned wins).
    picked_set = {r["id"] for r in picked}
    declared_entrances = [
        rid
        for rid in (area.get("entrance_rooms") or [])
        if rid in picked_set and rid not in used
    ]
    declared_exits = [
        rid
        for rid in (area.get("exit_rooms") or [])
        if rid in picked_set and rid not in used
    ]
    # Also try adding declared rooms that are available in the catalog
    # but weren't picked — *only if* unclaimed and resolvable. This is
    # the "stub area synthesized entrance" case inverted: an area with
    # a declared entrance whose min clamped it out of the pool.
    for rid in (area.get("entrance_rooms") or []):
        if (
            rid not in picked_set
            and rid not in used
            and rid in all_rooms
        ):
            picked.append(all_rooms[rid])
            picked_set.add(rid)
            declared_entrances.append(rid)
    for rid in (area.get("exit_rooms") or []):
        if (
            rid not in picked_set
            and rid not in used
            and rid in all_rooms
        ):
            picked.append(all_rooms[rid])
            picked_set.add(rid)
            declared_exits.append(rid)

    if declared_entrances:
        entrance = declared_entrances[0]
    elif picked:
        entrance = picked[0]["id"]
    else:
        # Should be unreachable because target>0 guarded earlier.
        return {
            "area_id": area["id"],
            "room_ids": [],
            "entrance": "",
            "exit": "",
            "exits": {},
        }

    if declared_exits:
        non_entrance = [rid for rid in declared_exits if rid != entrance]
        exit_ = non_entrance[0] if non_entrance else declared_exits[0]
    else:
        alt = [r["id"] for r in picked if r["id"] != entrance]
        exit_ = alt[-1] if alt else entrance

    picked_ids_final = sorted(r["id"] for r in picked)

    exits = _wire_rooms(picked, entrance, exit_, rng)

    # BFS sanity — if this area's spine somehow broke (it shouldn't),
    # patch a direct entrance↔exit edge.
    if not _bfs_ok(exits, entrance, exit_):
        # Force a direct edge.
        for d in CARDINAL:
            if exits[entrance][d] is None:
                exits[entrance][d] = exit_
                # Find a slot on the other end too.
                opp = {"north": "south", "south": "north", "east": "west", "west": "east"}[d]
                if exits[exit_][opp] is None:
                    exits[exit_][opp] = entrance
                else:
                    for d2 in CARDINAL:
                        if exits[exit_][d2] is None:
                            exits[exit_][d2] = entrance
                            break
                break

    return {
        "area_id": area["id"],
        "room_ids": picked_ids_final,
        "entrance": entrance,
        "exit": exit_,
        "exits": exits,
    }
