"""save_throw — 5e saving-throw variant of skill_check.

Mechanically identical at the math layer (d20 + mod + prof vs DC) — the
difference is the ledger event name and the ``save_type`` label the DM
hands us. We accept either a bare ability (``"wis"``) or a phrase like
``"wisdom save vs fear"`` and extract the ability prefix.

Save proficiency in 5e is per-ability (each class gets proficiency in
two abilities' saves). We trust the caller's ``proficient`` flag rather
than reading a separate field off character.json — the character sheet
today lumps proficiencies as a flat list; the DM decides.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from tools._shared import runtime as rt
from engine.rules import checks
from engine.state import ledger


_ABILITY_WORDS = {
    "str": "str", "strength": "str",
    "dex": "dex", "dexterity": "dex",
    "con": "con", "constitution": "con",
    "int": "int", "intelligence": "int",
    "wis": "wis", "wisdom": "wis",
    "cha": "cha", "charisma": "cha",
}


def _extract_ability(save_type: str) -> str | None:
    """Pull the ability key out of a save-type phrase.

    ``"wisdom save vs fear"`` → ``"wis"``, ``"dex"`` → ``"dex"``.
    Returns None if no ability word is recognized.
    """
    for token in re.split(r"[\s\-_]+", save_type.lower()):
        if token in _ABILITY_WORDS:
            return _ABILITY_WORDS[token]
    return None


def main() -> int:
    args = rt.read_args()

    save_type = str(args.get("save_type") or args.get("ability") or "").strip()
    if not save_type:
        print("save_throw: 'save_type' is required", file=sys.stderr)
        return 2
    ability = _extract_ability(save_type)
    if ability is None:
        print(
            f"save_throw: could not extract ability from {save_type!r} "
            f"(expected e.g. 'wis' or 'wisdom save vs fear')",
            file=sys.stderr,
        )
        return 2

    try:
        dc = int(args.get("dc", 10))
    except (TypeError, ValueError):
        print("save_throw: 'dc' must be an integer", file=sys.stderr)
        return 2
    proficient = bool(args.get("proficient", False))
    advantage = bool(args.get("advantage", False))
    disadvantage = bool(args.get("disadvantage", False))

    character = rt.load_character()
    try:
        result = checks.save_throw(
            character,
            ability,
            dc,
            proficient=proficient,
            advantage=advantage,
            disadvantage=disadvantage,
        )
    except (KeyError, ValueError) as e:
        print(f"save_throw: {e}", file=sys.stderr)
        return 2

    turn = rt.current_turn()
    ledger.save_throw(
        rt.run_dir(),
        turn,
        save_type=save_type,
        dc=result["dc"],
        roll=result["roll"],
        modifier=result["mod"],
        total=result["total"],
        pass_=result["pass"],
    )

    verdict = "succeeds" if result["pass"] else "fails"
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
        f"{save_type} (DC {dc}): rolled {result['roll']}{adv_note} + "
        f"{result['mod']} = {result['total']}, {verdict}{nat}."
    )
    print(json.dumps({**result, "save_type": save_type}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
