"""Top-level generator orchestrator + CLI.

Wires catalogs → macro → micro → faction population → spawn resolution
→ serialization. Everything is deterministic given a single int seed.

CLI usage:

    python3 -m engine.generator --seed 12345 --macro-nodes 10 --out graph.json
    python3 -m engine.generator --help
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

from .catalogs import load_catalogs
from .factions import populate_area
from .macro import bfs_path_exists, build_macro
from .micro import instantiate_area
from .spawns import apply_setpieces, resolve_room_spawns


# The default `--macro-nodes` target. Task says 8–15 is the range.
DEFAULT_MACRO_NODES = 10
DEFAULT_RESOURCES = Path("resources")


def _verbose(enabled: bool, msg: str) -> None:
    if enabled:
        print(f"[engine.generator] {msg}", file=sys.stderr)


def generate(
    seed: int,
    resources_dir: Path,
    macro_nodes: int = DEFAULT_MACRO_NODES,
    verbose: bool = False,
) -> dict[str, Any]:
    """Produce the full `graph.json` dict for a given seed.

    Returns a dict that can be serialized with `json.dumps(..., sort_keys=True)`
    for byte-identical output across runs.
    """
    rng = random.Random(seed)

    _verbose(verbose, f"loading catalogs from {resources_dir}")
    cat = load_catalogs(resources_dir)

    _verbose(
        verbose,
        f"catalog sizes: areas={len(cat.areas)}, rooms={len(cat.rooms)}, "
        f"factions={len(cat.factions)}, npcs={len(cat.npcs)}, "
        f"monsters={len(cat.monsters)}, items={len(cat.items)}, "
        f"hazards={len(cat.hazards)}",
    )

    if not cat.areas:
        raise RuntimeError("No areas loaded — cannot generate a world.")
    if not cat.rooms:
        raise RuntimeError("No rooms loaded — cannot generate a world.")

    # ------------------------------------------------------------------
    # Macro layer
    # ------------------------------------------------------------------
    _verbose(verbose, f"macro: picking {macro_nodes} area-nodes")
    selected_areas, adj, start_area, goal_area = build_macro(
        cat.areas, macro_nodes, rng
    )
    _verbose(
        verbose,
        f"macro: start={start_area} goal={goal_area} "
        f"selected={len(selected_areas)}",
    )

    # ------------------------------------------------------------------
    # Micro layer — per-area room subgraphs.
    # ------------------------------------------------------------------
    # Rooms are mutually exclusive across areas: the first area to claim
    # a room keeps it. Later areas pick from the remainder. If a later
    # area's pool is exhausted, it is dropped from the macro layer and
    # BFS(start, goal) is re-verified against the pruned adjacency.
    #
    # Processing order is load-bearing. We instantiate areas in this
    # priority sequence so the most-constrained areas get first pick:
    #   1. start_area  — must have a valid entrance for the run.
    #   2. goal_area   — must have its declared must_includes.
    #   3. areas with non-empty must_include  — handcrafted rooms are
    #      unique in the catalog and can't be substituted.
    #   4. the rest, in macro-selection order.
    # Within each priority band we preserve macro-selection order so
    # the traversal remains deterministic.
    _verbose(verbose, "micro: instantiating per-area room subgraphs")

    def _priority_key(a: dict[str, Any]) -> int:
        if a["id"] == start_area:
            return 0
        if a["id"] == goal_area:
            return 1
        if (a.get("rooms") or {}).get("must_include"):
            return 2
        return 3

    # Stable sort → ties keep macro-order.
    ordered_for_instantiation = sorted(
        enumerate(selected_areas),
        key=lambda pair: (_priority_key(pair[1]), pair[0]),
    )
    instantiation_order = [a for _, a in ordered_for_instantiation]

    layouts: dict[str, dict[str, Any]] = {}
    used_rooms: set[str] = set()
    dropped_area_ids: list[str] = []
    for a in instantiation_order:
        layout = instantiate_area(a, cat.rooms, rng, used_rooms=used_rooms)
        if not layout["room_ids"]:
            _verbose(verbose, f"  {a['id']}: pool exhausted, dropping from macro")
            dropped_area_ids.append(a["id"])
            continue
        layouts[a["id"]] = layout
        used_rooms.update(layout["room_ids"])
        _verbose(
            verbose,
            f"  {a['id']}: {len(layout['room_ids'])} rooms "
            f"(entrance={layout['entrance']}, exit={layout['exit']})",
        )

    if dropped_area_ids:
        # Before removing dropped areas, stitch each dropped node's
        # former neighbors to each other. The dropped area was just a
        # waypoint — without this repair, removing it can disconnect
        # the macro spine. No compat check: we're preserving
        # connectivity, not extending it.
        dropped_set = set(dropped_area_ids)
        for dropped in sorted(dropped_set):
            nbrs = sorted(n for n in adj.get(dropped, []) if n not in dropped_set)
            for i, a_id in enumerate(nbrs):
                for b_id in nbrs[i + 1:]:
                    if b_id not in adj.get(a_id, []):
                        adj[a_id].append(b_id)
                        adj[a_id].sort()
                    if a_id not in adj.get(b_id, []):
                        adj[b_id].append(a_id)
                        adj[b_id].sort()

        selected_areas = [a for a in selected_areas if a["id"] not in dropped_set]
        new_adj: dict[str, list[str]] = {}
        for aid, neigh in adj.items():
            if aid in dropped_set:
                continue
            new_adj[aid] = sorted(n for n in neigh if n not in dropped_set)
        adj = new_adj

        # If start or goal got dropped, fail loudly — this is a content
        # issue (their declared rooms all collided). In the real
        # catalog this shouldn't happen because the tier-0/1 starts and
        # tier-4/5 goals have distinct biomes.
        if start_area in dropped_area_ids or goal_area in dropped_area_ids:
            raise RuntimeError(
                f"Start ({start_area}) or goal ({goal_area}) area was "
                f"dropped due to exhausted pool; check catalog coverage."
            )

        if not bfs_path_exists(adj, start_area, goal_area):
            raise RuntimeError(
                "After pruning pool-exhausted areas, macro BFS(start, goal) "
                "no longer succeeds. Widen the room catalog or reduce "
                "--macro-nodes."
            )

    # ------------------------------------------------------------------
    # Stitch macro edges at the room level.
    # ------------------------------------------------------------------
    # Macro adjacency is area<->area; at the room level we wire one
    # area's `exit` to the neighbor area's `entrance` (or vice versa),
    # using whichever cardinal slot is free on each side. Without this
    # step the global room graph is a forest of disconnected per-area
    # subgraphs — BFS(start_room, goal_room) can't succeed.
    #
    # We iterate `selected_areas` in the order macro placed them
    # (start, ramp, goal) and process each edge once via a
    # (min_id, max_id) canonical key.
    _verbose(verbose, "stitch: connecting area boundaries at the room level")
    opposite = {"north": "south", "south": "north", "east": "west", "west": "east"}

    def _free_dir(room_exits: dict[str, str | None]) -> str | None:
        for d in ("north", "east", "south", "west"):
            if room_exits.get(d) is None:
                return d
        return None

    already_stitched: set[tuple[str, str]] = set()
    for a in selected_areas:
        aid = a["id"]
        # Iterate neighbors in id-order for determinism.
        for nid in sorted(adj.get(aid, [])):
            key = tuple(sorted((aid, nid)))
            if key in already_stitched:
                continue
            # Decide which end plays "exit side" vs "entrance side":
            # lower-id area is the exit side by convention — purely
            # deterministic and unambiguous.
            low, high = key
            low_exit = layouts[low]["exit"]
            high_entrance = layouts[high]["entrance"]

            low_exits = layouts[low]["exits"][low_exit]
            high_exits = layouts[high]["exits"][high_entrance]

            d_low = _free_dir(low_exits)
            if d_low is None:
                # Overwrite a cardinal that points within the same area —
                # degraded case for hyperconnected stubs. Safe because
                # the interior spine already guarantees BFS(entrance,exit)
                # per area.
                d_low = "north"
            d_high = opposite[d_low]
            if high_exits.get(d_high) is not None:
                # Use any free slot.
                alt = _free_dir(high_exits)
                d_high = alt if alt is not None else "south"
            low_exits[d_low] = high_entrance
            high_exits[d_high] = low_exit
            already_stitched.add(key)

    # ------------------------------------------------------------------
    # Macro metadata for graph.json's `macro` list.
    # ------------------------------------------------------------------
    macro_entries: list[dict[str, Any]] = []
    for a in selected_areas:
        aid = a["id"]
        macro_entries.append(
            {
                "id": aid,
                "neighbors": sorted(adj.get(aid, [])),
                "entrance_room": layouts[aid]["entrance"],
                "exit_room": layouts[aid]["exit"],
            }
        )

    # ------------------------------------------------------------------
    # Faction population per area
    # ------------------------------------------------------------------
    _verbose(verbose, "factions: populating areas")
    populations_by_room: dict[str, list[str]] = {}
    tension_by_area: dict[str, bool] = {}
    claiming_by_area: dict[str, list[str]] = {}
    for a in selected_areas:
        layout = layouts[a["id"]]
        pop, tension, claims = populate_area(
            a, layout, cat.factions, cat.npcs, rng
        )
        for rid, npcs_in in pop.items():
            populations_by_room[rid] = npcs_in
        tension_by_area[a["id"]] = tension
        claiming_by_area[a["id"]] = claims
        if tension:
            _verbose(
                verbose,
                f"  {a['id']}: factional_tension (claims: {', '.join(claims)})",
            )

    # ------------------------------------------------------------------
    # Spawn resolution + set-piece inserts, serialize rooms
    # ------------------------------------------------------------------
    _verbose(verbose, "spawns: rolling room tables")
    rooms_out: dict[str, dict[str, Any]] = {}
    all_room_ids: list[str] = []
    for a in selected_areas:
        layout = layouts[a["id"]]
        for rid in layout["room_ids"]:
            room = cat.rooms.get(rid)
            if room is None:
                # Defensive: instantiation only pulls from cat.rooms so
                # this shouldn't happen, but skip if it ever does.
                continue
            spawns_resolved = resolve_room_spawns(room, cat, rng)
            apply_setpieces(room, spawns_resolved, cat, rng)

            # Build the room's final exits block — always include all
            # four cardinals with null for missing sides (schema rule).
            exits_layout = layout["exits"].get(rid, {})
            exits_final = {
                d: exits_layout.get(d) for d in ("north", "east", "south", "west")
            }

            npcs_here = sorted(populations_by_room.get(rid, []))
            rooms_out[rid] = {
                "area": a["id"],
                "exits": exits_final,
                "spawns": spawns_resolved,
                "npcs": npcs_here,
                "flags": dict(room.get("flags") or {}),
                "factional_tension": tension_by_area.get(a["id"], False),
            }
            all_room_ids.append(rid)

    # ------------------------------------------------------------------
    # Final graph.json structure
    # ------------------------------------------------------------------
    graph = {
        "seed": seed,
        "start_area": start_area,
        "goal_area": goal_area,
        "start_room": layouts[start_area]["entrance"],
        "goal_room": layouts[goal_area]["exit"],
        "macro": sorted(macro_entries, key=lambda m: m["id"]),
        "rooms": rooms_out,
        "factions": {
            aid: {"claimed_by": claiming_by_area.get(aid, [])}
            for aid in sorted(claiming_by_area.keys())
        },
    }
    _verbose(
        verbose,
        f"done: {len(macro_entries)} macro nodes, {len(rooms_out)} rooms",
    )
    return graph


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m engine.generator",
        description=(
            "Procedurally generate a roguebash world (graph.json) from the "
            "resources/ JSONL catalogs. Fully deterministic given --seed."
        ),
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Integer seed. Defaults to a random value, echoed on stderr.",
    )
    p.add_argument(
        "--macro-nodes",
        type=int,
        default=DEFAULT_MACRO_NODES,
        help=f"Number of macro-level area nodes (default {DEFAULT_MACRO_NODES}, range 8–15).",
    )
    p.add_argument(
        "--out",
        type=str,
        default="-",
        help="Output path. Defaults to stdout ('-').",
    )
    p.add_argument(
        "--resources",
        type=str,
        default=str(DEFAULT_RESOURCES),
        help="Path to the resources/ directory containing the JSONL catalogs.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Log each pipeline stage to stderr.",
    )
    return p


def _choose_seed() -> int:
    """Pick a random seed when the user didn't supply one.

    Uses a fresh SystemRandom so the auto-chosen seed is not itself
    derived from anything we might later want deterministic.
    """
    return random.SystemRandom().randrange(2**31)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    seed = args.seed
    if seed is None:
        seed = _choose_seed()
        print(f"[engine.generator] chose seed: {seed}", file=sys.stderr)

    resources = Path(args.resources).expanduser().resolve()
    if not resources.is_dir():
        print(
            f"[engine.generator] error: --resources dir does not exist: {resources}",
            file=sys.stderr,
        )
        return 2

    t0 = time.monotonic()
    graph = generate(
        seed=seed,
        resources_dir=resources,
        macro_nodes=args.macro_nodes,
        verbose=args.verbose,
    )
    dt = time.monotonic() - t0
    _verbose(args.verbose, f"generated in {dt*1000:.1f} ms")

    # IMPORTANT: `sort_keys=True` is load-bearing for the determinism
    # test. Don't remove it.
    payload = json.dumps(graph, indent=2, sort_keys=True, ensure_ascii=False)

    if args.out == "-" or not args.out:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    else:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
        _verbose(args.verbose, f"wrote {out_path}")

    return 0
