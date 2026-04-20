"""Macro generator — pick and connect area-nodes.

Pipeline:
1. Choose `start` from tier 0-1 areas and `goal` from tier 4-5 areas.
2. Sample additional areas to fill out the difficulty ramp between them.
3. Connect pairs whose `compatible_with` patterns match (see compat.py).
   Every non-start node gets at least one edge to a previously-placed
   node with lower-or-equal tier, so the graph is laid out as a ramp
   rather than a random blob.
4. Verify BFS(start, goal) succeeds — retry with reshuffled picks if not.

Determinism: consumes a single seeded `random.Random` and never touches
the module-level `random`. Every iteration over dicts/sets sorts first.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from .compat import compatible


# How many attempts before we accept a "degenerate" layout and warn.
# In practice the first attempt almost always succeeds because the
# catalogs were authored with lots of cross-biome overlap.
MAX_RETRIES = 32


def _areas_at_tier_range(
    areas: dict[str, dict[str, Any]],
    lo: int,
    hi: int,
) -> list[dict[str, Any]]:
    """All areas whose `tier` ∈ [lo, hi], sorted by id for determinism."""
    picks = [a for a in areas.values() if lo <= int(a.get("tier", 0)) <= hi]
    return sorted(picks, key=lambda a: a["id"])


def _sample_middle(
    areas: dict[str, dict[str, Any]],
    taken: set[str],
    n_more: int,
    rng: random.Random,
    seeded_biomes: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Sample `n_more` additional areas not already in `taken`.

    Two priorities:
    - tier spread (bucket round-robin across tiers 1..4) so the run
      ramps in difficulty rather than being flat.
    - biome diversity: on each pick, prefer an area whose biome hasn't
      been selected yet. The catalog is tight (40 rooms across 8 biomes)
      so picking two areas with identical biomes starves the second
      one of rooms at the micro layer. Biome bias reduces that.

    `seeded_biomes` is the biome set already in use (e.g. from the
    chosen start and goal). Pass it in so the middle picks avoid
    collisions with the fixed endpoints.
    """
    biomes_used: set[str] = set(seeded_biomes or ())

    # Bucket unclaimed areas by tier (clamped to the middle band).
    buckets: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: [], 4: []}
    for a in sorted(areas.values(), key=lambda x: x["id"]):
        if a["id"] in taken:
            continue
        t = int(a.get("tier", 0))
        # Map anything outside 1..4 to the nearest bucket.
        t = max(1, min(4, t))
        buckets[t].append(a)

    picks: list[dict[str, Any]] = []
    # Allocate slots roughly evenly across the four tiers (round-robin fill).
    order = [1, 2, 3, 4]
    # Rotate order deterministically by rng so runs with different seeds
    # don't always start their ramp in tier 1.
    shift = rng.randrange(4)
    order = order[shift:] + order[:shift]

    remaining = n_more
    while remaining > 0 and any(buckets[t] for t in order):
        for t in order:
            if remaining <= 0:
                break
            if not buckets[t]:
                continue
            # Split this bucket into "novel-biome" and "repeat-biome"
            # sub-pools. Pick from the novel pool first when non-empty.
            novel = [a for a in buckets[t] if a.get("biome") not in biomes_used]
            candidates = novel if novel else buckets[t]
            # Sorted in bucket already (we only append during scan); deterministic pick.
            idx = rng.randrange(len(candidates))
            chosen = candidates[idx]
            buckets[t].remove(chosen)
            picks.append(chosen)
            biomes_used.add(chosen.get("biome", ""))
            remaining -= 1
    return picks


def bfs_path_exists(adj: dict[str, list[str]], start: str, goal: str) -> bool:
    """Classic BFS reachability on an undirected adjacency map."""
    if start == goal:
        return True
    if start not in adj or goal not in adj:
        return False
    seen = {start}
    q: deque[str] = deque([start])
    while q:
        cur = q.popleft()
        for nxt in adj.get(cur, []):
            if nxt in seen:
                continue
            if nxt == goal:
                return True
            seen.add(nxt)
            q.append(nxt)
    return False


def _build_adjacency(
    selected: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, list[str]]:
    """Wire the selected areas with compat-respecting edges, ramp-first.

    Strategy:
    - Iterate selected areas in the order we picked them (start, then
      middle ramp, then goal).
    - For each non-first area, connect it to at least one earlier area
      that passes `compatible(...)`. If no earlier area is compatible,
      force a connection to the most-recent previous area (keeps the
      graph connected; documented as a fallback).
    - Then add a handful of extra compat-passing edges to make the graph
      less linear. Extras capped to keep things simple.
    """
    adj: dict[str, list[str]] = {a["id"]: [] for a in selected}

    def add_edge(u: str, v: str) -> None:
        if u == v:
            return
        if v not in adj[u]:
            adj[u].append(v)
        if u not in adj[v]:
            adj[v].append(u)

    # Mandatory spine — every node gets a path back toward start.
    for i in range(1, len(selected)):
        cur = selected[i]
        # Shuffle the earlier candidates deterministically and pick the
        # first compatible one.
        earlier = list(selected[:i])
        rng.shuffle(earlier)
        linked = False
        for prev in earlier:
            if compatible(cur, prev):
                add_edge(cur["id"], prev["id"])
                linked = True
                break
        if not linked:
            # Fallback: force-link to previous node so BFS still works.
            add_edge(cur["id"], selected[i - 1]["id"])

    # Bonus edges — for each pair, roll against a modest probability
    # and add if compatible. Keeps the graph interesting without
    # blowing up to a clique.
    ids = [a["id"] for a in selected]
    for i in range(len(selected)):
        for j in range(i + 2, len(selected)):
            if rng.random() < 0.25 and compatible(selected[i], selected[j]):
                add_edge(ids[i], ids[j])

    # Normalize neighbor lists to deterministic order.
    for k in adj:
        adj[k] = sorted(adj[k])
    return adj


def build_macro(
    areas: dict[str, dict[str, Any]],
    n_nodes: int,
    rng: random.Random,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], str, str]:
    """Return (selected_areas, adjacency, start_id, goal_id).

    Retries up to MAX_RETRIES times if BFS(start, goal) fails under the
    current selection. On each retry we reshuffle picks using the same
    rng (so the result still depends only on the original seed).
    """
    starts = _areas_at_tier_range(areas, 0, 1)
    goals = _areas_at_tier_range(areas, 4, 5)

    if not starts:
        raise RuntimeError("No tier 0–1 areas available to use as start.")
    if not goals:
        raise RuntimeError("No tier 4–5 areas available to use as goal.")

    # Clamp n_nodes to what the catalog can support.
    max_nodes = min(n_nodes, len(areas))
    if max_nodes < 2:
        raise RuntimeError("Catalog has fewer than 2 areas — cannot generate.")

    for attempt in range(MAX_RETRIES):
        start = rng.choice(starts)
        goal = rng.choice(goals)
        if start["id"] == goal["id"]:
            continue
        taken = {start["id"], goal["id"]}
        seeded_biomes = {start.get("biome", ""), goal.get("biome", "")}
        middle = _sample_middle(
            areas, taken, max_nodes - 2, rng, seeded_biomes=seeded_biomes
        )
        selected = [start] + middle + [goal]
        adj = _build_adjacency(selected, rng)
        if bfs_path_exists(adj, start["id"], goal["id"]):
            return selected, adj, start["id"], goal["id"]

    # Fallback: on the (extremely unlikely) case every attempt failed,
    # build the last attempt and force a chain start→middle→goal so BFS
    # succeeds. Better to produce a playable run than crash.
    start = starts[0]
    goal = goals[-1]
    taken = {start["id"], goal["id"]}
    middle = _sample_middle(areas, taken, max_nodes - 2, rng)
    selected = [start] + middle + [goal]
    adj = {a["id"]: [] for a in selected}
    for i in range(len(selected) - 1):
        u, v = selected[i]["id"], selected[i + 1]["id"]
        adj[u].append(v)
        adj[v].append(u)
    for k in adj:
        adj[k] = sorted(adj[k])
    return selected, adj, start["id"], goal["id"]
