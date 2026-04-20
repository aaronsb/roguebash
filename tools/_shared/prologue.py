"""Shared prologue for exploration-tool Python snippets.

Invoked by `tools/_shared/common.sh::rb_run_py` as:

    RB_USER_PY=<path/to/logic.py> python3 prologue.py

We set up helpers and globals, then exec the user file in this module's
globals(). Keeping the scaffolding here (rather than in engine/) means
`engine.state` stays importable without side effects.

Globals the user file sees:
- RUN_DIR, RESOURCES (pathlib.Path)
- ARGS (dict, parsed from RB_ARGS_JSON env; {} if unset)
- Character, World, _ledger (engine.state.*)
- _load_world(), _save_world(w)
- _load_character(), _save_character(c)
- _load_graph()
- _ledger_path()
- _catalog(name), _catalog_lookup(name, ref)
- _fail(msg, code=1) — print to stderr and exit
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RUN_DIR = Path(os.environ["ROGUEBASH_RUN_DIR"])
RESOURCES = Path(os.environ.get("ROGUEBASH_RESOURCES", ""))

_raw_args = os.environ.get("RB_ARGS_JSON", "") or "{}"
try:
    ARGS = json.loads(_raw_args)
except json.JSONDecodeError as e:
    print(f"error: invalid JSON args: {e}", file=sys.stderr)
    sys.exit(2)

from engine.state.character import Character  # noqa: E402
from engine.state.world import World  # noqa: E402
from engine.state import ledger as _ledger  # noqa: E402
from engine.state.paths import (  # noqa: E402
    CHARACTER_FILE,
    WORLD_FILE,
    GRAPH_FILE,
    LEDGER_FILE,
)


def _fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def _load_graph():
    with (RUN_DIR / GRAPH_FILE).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_world():
    return World.load_from(RUN_DIR / WORLD_FILE)


def _save_world(w):
    w.save_to(RUN_DIR / WORLD_FILE)


def _load_character():
    return Character.load_from(RUN_DIR / CHARACTER_FILE)


def _save_character(c):
    c.save_to(RUN_DIR / CHARACTER_FILE)


def _ledger_path():
    return RUN_DIR / LEDGER_FILE


def _catalog(name):
    """Yield entries from resources/<name>.jsonl. Silent [] if absent."""
    p = RESOURCES / f"{name}.jsonl"
    if not p.is_file():
        return
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _catalog_lookup(name, ref):
    """Find the catalog entry whose id == ref; None if missing."""
    for entry in _catalog(name):
        if entry.get("id") == ref:
            return entry
    return None


_user_py = os.environ.get("RB_USER_PY", "")
if not _user_py:
    _fail("internal: RB_USER_PY is not set", code=2)

_path = Path(_user_py)
if not _path.is_file():
    _fail(f"internal: user py file not found: {_user_py}", code=2)

with _path.open("r", encoding="utf-8") as _fh:
    _src = _fh.read()
exec(compile(_src, str(_path), "exec"), globals())
