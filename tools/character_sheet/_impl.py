"""character_sheet — render character.json as human-readable prose.

This is the "what do I have" tool the DM reaches for when the player
asks about themselves. It's deliberately read-only and emits no ledger
event — peeking at your sheet is a free action.

The rendering is plain text, formatted for a terminal. It deliberately
does not summarize: everything on the sheet is shown, because the
player might be asking specifically about the thing you'd otherwise
omit.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from tools._shared import catalogs as _cat
from tools._shared import runtime as rt
from engine.rules import ability as rules_ability


def _fmt_mod(score: int) -> str:
    m = rules_ability.modifier(int(score))
    return f"{score:>2} ({m:+d})"


def _render_inventory(inv: list) -> list[str]:
    if not inv:
        return ["  (empty)"]
    lines: list[str] = []
    for entry in inv:
        ref = entry.get("ref", "?")
        qty = entry.get("qty", 1)
        cat = _cat.lookup_item(ref) or {}
        name = cat.get("name", ref)
        line = f"  - {name} x{qty}" if qty != 1 else f"  - {name}"
        if "damage" in cat:
            line += f"  [{cat['damage']} {cat.get('damage_type', '')}]".rstrip()
        lines.append(line)
    return lines


def main() -> int:
    # No args. Read quietly.
    _ = rt.read_args()

    character = rt.load_character()

    name = character.get("name", "?")
    race = character.get("race", "?")
    klass = character.get("class", "?")
    level = character.get("level", 1)
    xp = character.get("xp", 0)
    hp = character.get("hp", {"current": 0, "max": 0})
    ac = character.get("ac", 10)
    speed = character.get("speed", 30)
    gold = character.get("gold", 0)
    stats = character.get("stats", {})
    profs = character.get("proficiencies", [])
    statuses = character.get("status_effects", [])
    inv = character.get("inventory", [])

    out: list[str] = []
    out.append(f"== {name} ==")
    out.append(f"Level {level} {race} {klass}  (XP {xp})")
    out.append(f"HP {hp.get('current', 0)}/{hp.get('max', 0)}   AC {ac}   Speed {speed}   Gold {gold}")
    out.append("")
    out.append("Stats:")
    for ab in ("str", "dex", "con", "int", "wis", "cha"):
        if ab in stats:
            out.append(f"  {ab.upper()}  {_fmt_mod(stats[ab])}")
    out.append("")
    out.append("Proficiencies:")
    out.append("  " + (", ".join(profs) if profs else "(none)"))
    out.append("")
    if statuses:
        out.append("Status effects:")
        for s in statuses:
            out.append(f"  - {s}")
        out.append("")
    out.append("Inventory:")
    out.extend(_render_inventory(inv))

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
