"""Parse the scenario.md opening hook.

Each scenario's ``scenario.md`` has a ``## Hook (opening narration seed)``
section containing a Markdown blockquote. We join the blockquote lines
and write the result to the ledger as the turn-0 narration.
"""

from __future__ import annotations

from pathlib import Path


def opening_hook(repo_root: Path, scenario: str) -> str:
    """Return the opening hook for ``scenario`` or a fallback string."""
    p = repo_root / "scenarios" / scenario / "scenario.md"
    if not p.is_file():
        return f"You begin your run in the {scenario} scenario."
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return ""

    collecting = False
    hook: list[str] = []
    for line in text.splitlines():
        if line.strip().lower().startswith("## hook"):
            collecting = True
            continue
        if not collecting:
            continue
        if line.strip().startswith("## "):
            break
        if line.lstrip().startswith(">"):
            hook.append(line.lstrip()[1:].strip())
        elif not line.strip() and hook:
            break

    joined = " ".join(h for h in hook if h)
    return joined or f"Your run begins in the {scenario} scenario."
