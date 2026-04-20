"""engine/state — save files, XDG paths, ledger.

This package owns the on-disk representation of a roguebash run:

    $XDG_STATE_HOME/roguebash/<run-id>/
        character.json   — player sheet (mutated by tools)
        world.json       — what the player has revealed
        graph.json       — full shuffled world (answer key; never shown to LLM)
        ledger.jsonl     — append-only event log

Zero LLM calls. Stdlib only. See `engine/state/README.md` for the full spec.
"""

from . import paths, io, character, world, ledger, archive
from .character import Character
from .world import World

__all__ = [
    "paths",
    "io",
    "character",
    "world",
    "ledger",
    "archive",
    "Character",
    "World",
]
