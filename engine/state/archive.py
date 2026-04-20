"""End-of-run archival.

Per `engine/state/README.md`, on death or victory the run directory is
renamed from `<state_root>/<run-id>/` to `<state_root>/_archive/<run-id>/`
so `delve list` can still surface it but `delve play` won't resume it.

We also append a final terminal event to the (now archived) ledger so the
classifier in `paths.py` can tell dead from won without reading save files.
The caller can pass an event type hint (`"death"` or `"victory"`); the
default is `"death"` since that's the overwhelmingly common path.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from . import ledger as _ledger
from .paths import archive_dir, run_dir, LEDGER_FILE


def archive_run(
    run_id: str,
    cause: str,
    *,
    kind: str = "death",
    actor: str = "player",
    turn: int | None = None,
) -> Path:
    """Move the run's directory under `_archive/` and append a terminal event.

    Parameters
    ----------
    run_id : the run to archive
    cause  : free-text cause ('hazard.leech_pool', 'boss.dread_wyrm', 'goal.sunken_library')
    kind   : 'death' or 'victory' — which canonical event to append
    actor  : who died / who won (default 'player')
    turn   : turn number to record; if None, we scan the existing ledger
             for the max `t` and use that (so the terminal event sits on
             the last active turn, matching the README example).

    Returns the new archived path.

    Raises FileNotFoundError if the run doesn't exist.
    Raises FileExistsError if an archive with the same id already exists
    (we refuse to clobber — the caller should have picked a new id).
    """
    src = run_dir(run_id)
    if not src.is_dir():
        raise FileNotFoundError(f"run not found: {run_id} ({src})")

    dst_parent = archive_dir()
    dst_parent.mkdir(parents=True, exist_ok=True)
    dst = dst_parent / run_id
    if dst.exists():
        raise FileExistsError(f"archive already exists: {dst}")

    # Infer the turn from the existing ledger if the caller didn't specify.
    if turn is None:
        turn = _infer_last_turn(src / LEDGER_FILE)

    # Move first, then append to the archived ledger. This ordering means
    # a crash mid-archive leaves the directory in exactly one of two
    # states: at the source (terminal event missing, but the run is still
    # resumable — we can recover), or at the destination (we'll re-append
    # idempotently-ish on retry; the double event is harmless since the
    # classifier walks back to the *first* terminal event it finds).
    shutil.move(os.fspath(src), os.fspath(dst))

    ledger_path = dst / LEDGER_FILE
    if kind == "death":
        _ledger.death(ledger_path, turn, actor=actor, cause=cause)
    elif kind == "victory":
        _ledger.victory(ledger_path, turn, player=actor, goal=cause)
    else:
        raise ValueError(f"unknown archive kind: {kind!r}")

    return dst


def _infer_last_turn(ledger_path: Path) -> int:
    """Return the max `t` across all parseable ledger entries, or 0.

    Used when `archive_run` isn't told a turn number. We could peek only
    at the last line, but runs with a crashed trailing write would then
    return an implausible turn; scanning the whole thing is negligible
    for roguebash's event volumes.
    """
    if not ledger_path.is_file():
        return 0
    best = 0
    for evt in _ledger.iter_events(ledger_path):
        t = evt.get("t")
        if isinstance(t, int) and t > best:
            best = t
    return best
