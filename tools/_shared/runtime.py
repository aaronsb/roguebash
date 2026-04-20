"""Thin wrappers over ROGUEBASH_RUN_DIR / ROGUEBASH_SCENARIOS.

Every mechanics / exploration tool opens with the same few lines:
read the run-dir and scenarios paths from env, load character.json,
world.json, graph.json, and (on demand) a catalog file. Centralizing
that keeps each tool's entrypoint short and the error messages uniform.

Mutation helpers (`save_character`, `save_graph`) write via
`engine.state.io.save_json`, which is atomic (tmp + os.replace).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Make sure the project root is importable when a tool invokes us via
# `python3 -m tools._shared.x`. Each tool bash wrapper sets PYTHONPATH
# to the project root already; this import works either way.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parent.parent.parent  # tools/_shared -> tools -> root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def project_root() -> Path:
    """Absolute path to the roguebash project root (repo checkout)."""
    return _PROJECT_ROOT


def run_dir() -> Path:
    """The current run's state directory (character/world/graph/ledger live here)."""
    v = os.environ.get("ROGUEBASH_RUN_DIR")
    if not v:
        raise RuntimeError("ROGUEBASH_RUN_DIR is not set")
    p = Path(v)
    if not p.is_dir():
        raise RuntimeError(f"ROGUEBASH_RUN_DIR does not exist: {p}")
    return p


def scenarios_dir() -> Path:
    """Path to the repo's scenarios/ directory (contains _common/ + scenario dirs)."""
    v = os.environ.get("ROGUEBASH_SCENARIOS")
    if v:
        p = Path(v)
    else:
        p = project_root() / "scenarios"
    if not p.is_dir():
        raise RuntimeError(f"scenarios dir does not exist: {p}")
    return p


def active_scenario() -> str:
    """Active scenario: graph.json's top-level 'scenario' > $ROGUEBASH_SCENARIO > 'barrow_swamp'."""
    try:
        g = load_graph()
        name = g.get("scenario")
        if name:
            return str(name)
    except Exception:
        pass
    return os.environ.get("ROGUEBASH_SCENARIO") or "barrow_swamp"


# Backward-compat shim: the previous name resources_dir() is kept so any
# late-merging branch doesn't break. It now returns _common, which is the
# closest analogue.
def resources_dir() -> Path:
    return scenarios_dir() / "_common"


def read_args() -> dict:
    """Read the tool's JSON argument blob from stdin.

    Empty stdin is tolerated and yields ``{}``. Non-object JSON (a bare
    list or scalar) raises — every roguebash tool takes an object.
    """
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"tool args are not valid JSON: {e}") from None
    if not isinstance(obj, dict):
        raise RuntimeError(f"tool args must be a JSON object, got {type(obj).__name__}")
    return obj


def load_json(path: Path) -> dict:
    """Read a JSON file. Tiny convenience around ``engine.state.io``."""
    from engine.state import io as _io
    return _io.load_json(path)


def save_json(path: Path, data: Any) -> None:
    """Atomic JSON save. Tiny convenience around ``engine.state.io``."""
    from engine.state import io as _io
    _io.save_json(path, data)


def load_character() -> dict:
    """Load the current run's character sheet as a raw dict."""
    return load_json(run_dir() / "character.json")


def save_character(data: dict) -> None:
    """Atomically write character.json back."""
    save_json(run_dir() / "character.json", data)


def load_world() -> dict:
    """Load the current run's world.json."""
    return load_json(run_dir() / "world.json")


def load_graph() -> dict:
    """Load the current run's graph.json (the answer key)."""
    return load_json(run_dir() / "graph.json")


def save_graph(data: dict) -> None:
    """Atomically write graph.json back (e.g. to persist monster HP)."""
    save_json(run_dir() / "graph.json", data)


def current_turn() -> int:
    """Return world.turn (0 if world.json is missing a turn field)."""
    try:
        return int(load_world().get("turn", 0))
    except (FileNotFoundError, RuntimeError):
        return 0
