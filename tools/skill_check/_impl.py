"""skill_check — roll d20 + ability modifier (+ prof) against a DC.

Thin tool around ``engine.rules.checks.skill_check``. The tool reads
``character.json`` from the current run, resolves the roll, appends a
``skill_check`` ledger event, and prints a one-line human summary.

Ability checks in 5e RAW do not auto-pass on nat 20 or auto-fail on
nat 1 — we surface those flags in the ledger and the prose output but
they do not flip the ``pass`` field.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make imports work when invoked as `python3 _impl.py`.
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from tools._shared import runtime as rt
from engine.rules import checks
from engine.state import ledger


_VALID_ABILITIES = ("str", "dex", "con", "int", "wis", "cha")


def main() -> int:
    args = rt.read_args()
    ability = str(args.get("ability", "")).lower().strip()
    if ability not in _VALID_ABILITIES:
        print(
            f"skill_check: 'ability' must be one of {_VALID_ABILITIES}; got {ability!r}",
            file=sys.stderr,
        )
        return 2
    try:
        dc = int(args.get("dc", 10))
    except (TypeError, ValueError):
        print("skill_check: 'dc' must be an integer", file=sys.stderr)
        return 2
    proficient = bool(args.get("proficient", False))
    advantage = bool(args.get("advantage", False))
    disadvantage = bool(args.get("disadvantage", False))

    character = rt.load_character()
    try:
        result = checks.skill_check(
            character,
            ability,
            dc,
            proficient=proficient,
            advantage=advantage,
            disadvantage=disadvantage,
        )
    except (KeyError, ValueError) as e:
        print(f"skill_check: {e}", file=sys.stderr)
        return 2

    turn = rt.current_turn()
    ledger.skill_check(
        rt.run_dir(),
        turn,
        ability=result["ability"],
        dc=result["dc"],
        roll=result["roll"],
        modifier=result["mod"],
        total=result["total"],
        pass_=result["pass"],
    )

    # Human prose. Kept terse; DM voice does its own narration on top.
    verdict = "succeeds" if result["pass"] else "fails"
    prof_note = " (proficient)" if proficient else ""
    adv_note = ""
    if advantage and not disadvantage:
        adv_note = f" [adv, rolls {result['rolls']}]"
    elif disadvantage and not advantage:
        adv_note = f" [dis, rolls {result['rolls']}]"
    nat = ""
    if result["nat20"]:
        nat = " (natural 20)"
    elif result["nat1"]:
        nat = " (natural 1)"
    print(
        f"{ability.upper()} check DC {dc}: rolled {result['roll']}{adv_note} "
        f"+ {result['mod']}{prof_note} = {result['total']}, {verdict}{nat}."
    )
    # Also emit the structured result on the next line so the harness
    # can consume it programmatically if needed.
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
