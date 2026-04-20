"""Low-level disk I/O helpers.

All JSON writes go through `save_json`, which writes to `<path>.tmp` first
and then `os.replace`s it over the destination. On POSIX, `rename(2)` is
atomic within a single filesystem, so a reader either sees the full prior
version or the full new version — never a half-written file.

`append_jsonl` is *not* crash-safe in the strict sense: if the process dies
mid-write the ledger could end with a partial line. Callers that `tail()`
should tolerate (skip) unparseable trailing lines. We flush + fsync after
each append so that a completed line is durable on disk before we return.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_json(path: os.PathLike | str) -> dict:
    """Read a JSON file and return the decoded object.

    Raises FileNotFoundError if the path does not exist, and
    json.JSONDecodeError if the contents are not valid JSON.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: os.PathLike | str, data: Any) -> None:
    """Atomically write `data` as JSON to `path`.

    Strategy: write to `path.tmp`, fsync, then `os.replace` it over `path`.
    `os.replace` is atomic on POSIX when source and destination are on the
    same filesystem (which they always are here, since `.tmp` sits alongside
    the target).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            # fsync can fail on some exotic filesystems / test harnesses;
            # the rename is still the primary atomicity guarantee.
            pass
    os.replace(tmp, p)


def append_jsonl(path: os.PathLike | str, obj: Any) -> None:
    """Append a single JSON object as one line to `path`.

    Opens in append mode so concurrent appenders on POSIX each get their
    bytes atomically if the line is shorter than PIPE_BUF (4096 on Linux) —
    our events are well under that.

    Crash-safety: if a prior writer died before writing its trailing `\\n`,
    the file will end in a partial line. We detect that (last byte isn't a
    newline) and inject one before our own write, so the corrupt partial
    stays confined to its own line and `tail()` can skip it cleanly.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    with p.open("ab") as fh:
        # Heal a missing trailing newline from a crashed previous writer.
        try:
            size = fh.tell()
        except OSError:
            size = 0
        if size > 0:
            # Read the final byte without disturbing append position.
            with p.open("rb") as rh:
                rh.seek(-1, os.SEEK_END)
                last = rh.read(1)
            if last != b"\n":
                fh.write(b"\n")
        fh.write(line.encode("utf-8"))
        fh.write(b"\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
