"""XDG-aware path resolution and run-id helpers.

Everything durable lives under `$XDG_STATE_HOME/roguebash/`, defaulting to
`~/.local/state/roguebash/` per the XDG Base Directory spec.

A run-id is `<seed>-<name-slug>-<yyyymmddHHMM>`. The name-slug is a lowered,
ASCII-only, hyphenated version of the player's chosen name — so two runs
started in the same minute with different names still produce distinct ids,
and the id remains safe as a directory name on any filesystem we care about.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import unicodedata
from pathlib import Path


_APP_NAME = "roguebash"
_ARCHIVE_SUBDIR = "_archive"

# Canonical state-file names — imported by siblings rather than hardcoded.
CHARACTER_FILE = "character.json"
WORLD_FILE = "world.json"
GRAPH_FILE = "graph.json"
LEDGER_FILE = "ledger.jsonl"


def state_root() -> Path:
    """Return the roguebash XDG state root.

    Honors `$XDG_STATE_HOME` if set (and non-empty), else
    `~/.local/state`. The directory is *not* created here; callers
    that write create it via `save_json` / `append_jsonl`.
    """
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".local" / "state"
    return base / _APP_NAME


def run_dir(run_id: str) -> Path:
    """Path to a specific run's directory (not guaranteed to exist)."""
    return state_root() / run_id


def archive_dir() -> Path:
    """Path to the archive directory where ended runs are moved."""
    return state_root() / _ARCHIVE_SUBDIR


def _slugify(name: str) -> str:
    """Collapse a player name to an id-safe slug.

    Strips accents via NFKD so `Ëlf` → `Elf` rather than dropping the
    character entirely. Then lowercases, replaces any run of non-
    alphanumerics with a single hyphen, strips leading/trailing hyphens,
    and falls back to `"player"` if the input reduces to empty. ASCII-
    only so the resulting directory name is portable.
    """
    if not name:
        return "player"
    # Decompose unicode (é → e + combining-accent) then drop non-ASCII.
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return slug or "player"


def make_run_id(
    seed: int,
    player_name: str,
    now: _dt.datetime | None = None,
) -> str:
    """Build a run id: `<seed>-<name-slug>-<yyyymmddHHMM>`.

    `now` is injectable for determinism in tests.
    """
    stamp = (now or _dt.datetime.now()).strftime("%Y%m%d%H%M")
    return f"{seed}-{_slugify(player_name)}-{stamp}"


def _classify(run_id: str, root: Path, archive: Path) -> str:
    """Infer a run's status from on-disk signals.

    `alive`  — directory exists under state_root, not in archive
    `dead`   — directory is under `_archive/` AND ledger ends in a `death`
    `won`    — directory is under `_archive/` AND ledger ends in a `victory`
    `ended`  — archived but no classifiable terminal event

    This is a best-effort classifier: an archived run whose ledger we can't
    read returns `ended`. We scan the ledger tail rather than the head so
    the classification is O(small) even on long runs.
    """
    direct = root / run_id
    if direct.is_dir():
        return "alive"
    arch = archive / run_id
    if not arch.is_dir():
        return "unknown"

    ledger = arch / LEDGER_FILE
    if not ledger.is_file():
        return "ended"
    # Walk backwards for the most recent terminal event.
    try:
        with ledger.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return "ended"
    import json as _json

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            evt = _json.loads(line)
        except _json.JSONDecodeError:
            continue
        t = evt.get("type")
        if t == "death":
            return "dead"
        if t == "victory":
            return "won"
    return "ended"


def list_runs() -> list[tuple[str, str]]:
    """Return `[(run_id, status), ...]` for every known run.

    Includes both live runs (direct children of state_root) and archived
    runs (children of `_archive/`). Order: most recently modified first.
    Status values: `alive`, `dead`, `won`, `ended`.
    """
    root = state_root()
    arch = archive_dir()
    entries: list[tuple[Path, str]] = []

    if root.is_dir():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if child.name == _ARCHIVE_SUBDIR:
                continue
            entries.append((child, child.name))

    if arch.is_dir():
        for child in arch.iterdir():
            if not child.is_dir():
                continue
            entries.append((child, child.name))

    # Sort by mtime descending (most recent first).
    entries.sort(key=lambda pair: pair[0].stat().st_mtime, reverse=True)
    return [(run_id, _classify(run_id, root, arch)) for _, run_id in entries]


def latest_run() -> str | None:
    """Most recently modified run_id, or None if there are no runs."""
    runs = list_runs()
    return runs[0][0] if runs else None
