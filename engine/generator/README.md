# engine/generator — world procgen

Inputs:
- `scenarios/_common/*.jsonl` (monsters, items, hazards)
- `scenarios/<name>/*.jsonl` (rooms, areas, factions, npcs; optional overrides)
- `--scenario <name>` (default `barrow_swamp`; `random` picks deterministically from the seed)
- `--seed N` (integer)
- target size: number of macro nodes

Output:
- A `graph.json` file conforming to `engine/state/README.md`

Responsibilities:
1. **Macro layer**: sample area-nodes, connect by `compatible_with`
   tag overlap *weighted by biome-distance* (see Biome adjacency below),
   splice transition areas into any remaining high-cost edges, ensure
   BFS-reachable start→goal.
2. **Micro layer**: for each area, instantiate its internal subgraph
   with entrance/exit rooms pinned.
3. **Set-piece inserts**: place handcrafted special rooms where tags
   match.
4. **Spawn resolution**: roll spawn tables once at generation time so
   `graph.json` is fully populated (no runtime randomness per room).

## Biome adjacency + transition rooms

`scenarios/_common/biome_adjacency.json` is an 8×8 integer cost matrix
over the canonical biomes. Lower cost = more thematically adjacent (0
= self, 1 = natural neighbor like forest↔swamp, 4 = opposite extremes
like swamp↔desert).

The macro generator uses it in two places:

- **Weighted edge selection.** When deciding which earlier area a new
  node should connect to, candidates are weighted by `1 / (1 + cost)`
  so the run's biome arc curves rather than jumps. Bonus-edge
  probability is likewise cost-scaled.
- **Transition splicing.** After edges are placed, any edge with
  cost > 1 that has a matching `transition.*` room (see
  `scenarios/schema.md` → *Transition rooms*) gets split: the direct
  edge is replaced with `A ↔ transition ↔ B`, where the transition is
  a synthesized one-room "area" wrapping the authored transition room.

Transition rooms live in `scenarios/<name>/rooms.jsonl` with
`biome: "transition"` and a `bridges: [bio_a, bio_b]` field. They are
skipped by regular pool-by-biome expansion, so they only enter the
world through the macro generator's synthetic transition areas.

Falling back gracefully: a missing adjacency file or a biome pair with
no authored transition room leaves edges alone. Scenarios that haven't
been annotated still generate (just without the smoothing).

Suggested entrypoint: `generate.py` (Python; graph algorithms are
cleaner here than bash), but any language is fine as long as its output
matches the graph schema.

Non-goals:
- The generator does not touch `world.json` (that starts empty and is
  filled by the `move` tool as rooms are revealed).
- The generator does not talk to the LLM.
