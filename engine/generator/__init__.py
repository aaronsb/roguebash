"""engine.generator — deterministic world procgen for roguebash.

Loads `scenarios/_common/*.jsonl` + `scenarios/<name>/*.jsonl` catalogs,
assembles a macro graph of area nodes connected by `compatible_with`
matches, instantiates each area's internal room subgraph, resolves
faction-aware NPC populations and spawn tables, and serializes the
result to `graph.json`.

Stdlib only. No LLM calls. Fully deterministic given `--seed`.

Entrypoints:
    python3 -m engine.generator --seed 12345 --out graph.json
    from engine.generator.generate import generate, main
"""

from __future__ import annotations

from .generate import generate, main  # noqa: F401
