# tools/_shared — cross-tool helpers

Shared Python modules imported by the individual tool `_impl.py` files.
Neither the agent runner nor any external caller invokes anything here
directly — this directory has no entrypoint (note the underscore
prefix, which also makes the runner's tool-discovery loop skip it).

## Modules

- **`runtime.py`** — ROGUEBASH env vars (`ROGUEBASH_RUN_DIR`,
  `ROGUEBASH_RESOURCES`), stdin JSON reader, state-file loaders and
  atomic savers. Every tool starts with a call or two here.
- **`catalogs.py`** — lazy loaders and `lookup(ref)` against
  `resources/*.jsonl`. Used by combat (monster/NPC stats), by
  `character_sheet` (rendering item names), and by exploration tools
  in lane 9 (for item descriptions).
- **`combat.py`** — weapon reshape (PC items → `engine.rules.attack`
  character-style spec), target resolution against the current room's
  spawns, lazy monster-HP instantiation.

## Why a helper dir instead of inline heredocs

The bash entrypoints stay under 40 lines (schema + delegation). The
Python bodies live beside each entrypoint as `_impl.py`, and anything
that two tools need goes here. This makes the tools unit-testable in
isolation and keeps the bash/python split crisp.
