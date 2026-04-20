"""Macro generator — pick and connect area-nodes.

Pipeline:
1. Choose `start` from tier 0-1 areas and `goal` from tier 4-5 areas.
2. Sample additional areas to fill out the difficulty ramp between them.
3. Connect pairs whose `compatible_with` patterns match (see compat.py).
   Every non-start node gets at least one edge to a previously-placed
   node with lower-or-equal tier, so the graph is laid out as a ramp
   rather than a random blob. When an adjacency matrix is available,
   edge candidates are **weighted by biome-distance** (lower cost =
   higher probability) so the run's biome arc curves rather than jumps.
4. Splice synthetic **transition areas** into any remaining high-cost
   edges (biome distance > 1): the macro generator inserts a one-room
   area that bridges the two biomes via a `transition.*` room authored
   in `rooms.jsonl`. Keeps biome sequences reading as a gradient instead
   of an abrupt cut.
5. Verify BFS(start, goal) succeeds — retry with reshuffled picks if not.

Determinism: consumes a single seeded `random.Random` and never touches
the module-level `random`. Every iteration over dicts/sets sorts first.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from .adjacency import (
    BiomeAdjacency,
    find_transition_room,
    index_transition_rooms,
    synthesize_transition_area,
)
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
    adjacency: BiomeAdjacency | None = None,
) -> dict[str, list[str]]:
    """Wire the selected areas with compat-respecting edges, ramp-first.

    Strategy:
    - Iterate selected areas in the order we picked them (start, then
      middle ramp, then goal).
    - For each non-first area, connect it to one earlier compatible area,
      **biased toward low biome-adjacency cost**. With an adjacency matrix
      loaded, the weighted sampler pulls `forest → swamp` over `forest →
      desert` even when both are compatible; without one (empty matrix
      fallback), every candidate weighs 1.0 and behavior matches the old
      shuffle-and-first-pass.
    - Then add extra compat-passing edges. The bonus-edge probability is
      itself cost-scaled — low-cost pairs get roughly 2x the chance of a
      high-cost pair. Keeps the graph interesting without exploding.
    """
    adj: dict[str, list[str]] = {a["id"]: [] for a in selected}

    def add_edge(u: str, v: str) -> None:
        if u == v:
            return
        if v not in adj[u]:
            adj[u].append(v)
        if u not in adj[v]:
            adj[v].append(u)

    def biome_cost(a: dict[str, Any], b: dict[str, Any]) -> int:
        if adjacency is None:
            return 1
        return adjacency.cost(str(a.get("biome", "")), str(b.get("biome", "")))

    def _weighted_pick(
        current: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Pick one candidate with weights ~ 1/(1+cost). Returns None if none compatible.

        Only compatible candidates get positive weight. Iterating in
        input order + a pre-sorted candidate list keeps the draw
        deterministic under a fixed rng sequence.
        """
        compat_cands = [c for c in candidates if compatible(current, c)]
        if not compat_cands:
            return None
        weights = [1.0 / (1.0 + biome_cost(current, c)) for c in compat_cands]
        total = sum(weights)
        if total <= 0:
            return compat_cands[0]
        r = rng.random() * total
        acc = 0.0
        for cand, w in zip(compat_cands, weights):
            acc += w
            if r <= acc:
                return cand
        return compat_cands[-1]

    # Mandatory spine — every node gets a path back toward start.
    for i in range(1, len(selected)):
        cur = selected[i]
        # Sort earlier by id for deterministic input to the weighted pick.
        earlier = sorted(selected[:i], key=lambda a: a["id"])
        chosen = _weighted_pick(cur, earlier)
        if chosen is not None:
            add_edge(cur["id"], chosen["id"])
        else:
            # Fallback: force-link to previous node so BFS still works.
            add_edge(cur["id"], selected[i - 1]["id"])

    # Bonus edges — for each pair, roll a cost-scaled probability and
    # add if compatible. p = 0.5 / (1 + cost):
    #   cost 0 → 0.50, cost 1 → 0.25, cost 2 → 0.167, cost 3 → 0.125,
    #   cost 4 → 0.10.  Keeps the graph interesting but favors low-cost
    #   connections so biome arcs stay coherent.
    ids = [a["id"] for a in selected]
    for i in range(len(selected)):
        for j in range(i + 2, len(selected)):
            a, b = selected[i], selected[j]
            cost = biome_cost(a, b)
            p = 0.5 / (1.0 + cost)
            if rng.random() < p and compatible(a, b):
                add_edge(ids[i], ids[j])

    # Normalize neighbor lists to deterministic order.
    for k in adj:
        adj[k] = sorted(adj[k])
    return adj


def _insert_transitions(
    selected: list[dict[str, Any]],
    adj: dict[str, list[str]],
    adjacency: BiomeAdjacency,
    transition_index: dict[tuple[str, str], list[dict[str, Any]]],
    rng: random.Random,
    verbose_log: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    """Splice synthetic transition areas into high-cost macro edges.

    For each edge `(a, b)` with `adjacency.cost(a.biome, b.biome) > 1`:
    - if a transition room exists in `transition_index[(a.biome, b.biome)]`,
      synthesize a one-room area wrapping it, drop the direct edge, and
      wire `a — transition — b`.
    - if no transition room is authored for that biome pair, leave the
      direct edge alone (graceful degradation; pairs we haven't written
      content for still produce a playable, if jarring, run).

    Returns `(new_selected, new_adj, inserted_areas)`. `inserted_areas`
    is the list of synthesized area dicts in insertion order; callers
    may log them or expose them to tests.

    Edges are processed in canonical `(min_id, max_id)` order for
    determinism.
    """
    inserted: list[dict[str, Any]] = []
    # Freeze the edge list up-front; we're about to mutate `adj`.
    edges: set[tuple[str, str]] = set()
    for aid, neigh in adj.items():
        for nid in neigh:
            edges.add(tuple(sorted((aid, nid))))

    # Index selected by id for lookups.
    by_id: dict[str, dict[str, Any]] = {a["id"]: a for a in selected}

    # Sort edges deterministically by the id pair.
    sequence = 0
    new_selected = list(selected)
    for u, v in sorted(edges):
        area_u = by_id.get(u)
        area_v = by_id.get(v)
        if area_u is None or area_v is None:
            continue
        bio_u = str(area_u.get("biome", ""))
        bio_v = str(area_v.get("biome", ""))
        # Skip self-biome or unknown-biome (no meaningful bridge to build).
        if not bio_u or not bio_v or bio_u == bio_v:
            continue
        cost = adjacency.cost(bio_u, bio_v)
        if cost <= 1:
            continue
        t_room = find_transition_room(transition_index, bio_u, bio_v)
        if t_room is None:
            # No authored bridge for this pair; leave the direct edge.
            continue
        sequence += 1
        synth = synthesize_transition_area(area_u, area_v, t_room, sequence)
        sid = synth["id"]
        # Splice: drop direct edge u-v, add u-synth and synth-v.
        if v in adj.get(u, []):
            adj[u].remove(v)
        if u in adj.get(v, []):
            adj[v].remove(u)
        adj.setdefault(sid, [])
        if sid not in adj[u]:
            adj[u].append(sid)
        if u not in adj[sid]:
            adj[sid].append(u)
        if sid not in adj[v]:
            adj[v].append(sid)
        if v not in adj[sid]:
            adj[sid].append(v)
        new_selected.append(synth)
        by_id[sid] = synth
        inserted.append(synth)
        if verbose_log is not None:
            verbose_log.append(
                f"transition: {u}({bio_u}) ↔ {sid} ↔ {v}({bio_v}) "
                f"via {t_room['id']} (cost {cost})"
            )

    # Normalize neighbor lists.
    for k in adj:
        adj[k] = sorted(adj[k])
    return new_selected, adj, inserted


def build_macro(
    areas: dict[str, dict[str, Any]],
    n_nodes: int,
    rng: random.Random,
    adjacency: BiomeAdjacency | None = None,
    rooms: dict[str, dict[str, Any]] | None = None,
    verbose_log: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], str, str]:
    """Return (selected_areas, adjacency, start_id, goal_id).

    Retries up to MAX_RETRIES times if BFS(start, goal) fails under the
    current selection. On each retry we reshuffle picks using the same
    rng (so the result still depends only on the original seed).

    With `adjacency` supplied, edge selection is biome-cost-weighted and
    high-cost edges (> 1) are spliced with transition areas sourced from
    the `rooms` catalog (via `biome: "transition"` entries).

    `verbose_log` (optional) accumulates human-readable strings for
    transitions and fallbacks — the caller can emit them on stderr.
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

    # Build the transition-room index once per call (cheap).
    transition_index = index_transition_rooms(rooms or {})

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
        adj = _build_adjacency(selected, rng, adjacency=adjacency)
        # Splice transitions — only if we have a usable adjacency matrix
        # and at least one transition room in the catalog. Otherwise
        # behavior is identical to the pre-adjacency generator.
        if adjacency is not None and transition_index:
            selected, adj, _inserted = _insert_transitions(
                selected, adj, adjacency, transition_index, rng,
                verbose_log=verbose_log,
            )
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
