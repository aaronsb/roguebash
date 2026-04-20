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
   tag overlap, ensure BFS-reachable start→goal.
2. **Micro layer**: for each area, instantiate its internal subgraph
   with entrance/exit rooms pinned.
3. **Set-piece inserts**: place handcrafted special rooms where tags
   match.
4. **Spawn resolution**: roll spawn tables once at generation time so
   `graph.json` is fully populated (no runtime randomness per room).

Suggested entrypoint: `generate.py` (Python; graph algorithms are
cleaner here than bash), but any language is fine as long as its output
matches the graph schema.

Non-goals:
- The generator does not touch `world.json` (that starts empty and is
  filled by the `move` tool as rooms are revealed).
- The generator does not talk to the LLM.
