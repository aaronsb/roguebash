"""Skill checks and saving throws.

Both follow the same shape in 5e:

    d20 + ability modifier + (proficiency bonus if proficient) vs DC.

These helpers do **not** decide whether a character is proficient — the
caller (tool layer) consults ``character.json["proficiencies"]`` and
passes ``proficient=True`` accordingly. Keeps this layer free of
character-sheet semantics.
"""

from __future__ import annotations

import random as _random
from typing import Optional

from .ability import modifier, proficiency_bonus
from .dice import d20

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")


def _character_modifier(character: dict, ability: str, *, proficient: bool) -> int:
    """Compute the signed modifier for a check/save.

    = ability modifier  (+ proficiency bonus if `proficient`)

    The character dict is expected to carry ``stats`` (dict of ability -> score)
    and ``level`` (int), as described in ``engine/state/README.md``.
    """
    ability = ability.lower()
    if ability not in ABILITIES:
        raise ValueError(f"unknown ability: {ability!r} (expected one of {ABILITIES})")
    stats = character.get("stats") or {}
    if ability not in stats:
        raise ValueError(f"character.stats missing {ability!r}: {stats!r}")
    level = character.get("level", 1)
    mod = modifier(int(stats[ability]))
    if proficient:
        mod += proficiency_bonus(int(level))
    return mod


def _resolve(
    character: dict,
    ability: str,
    dc: int,
    *,
    proficient: bool,
    advantage: bool,
    disadvantage: bool,
    rng: Optional[_random.Random],
) -> dict:
    mod = _character_modifier(character, ability, proficient=proficient)
    d = d20(adv=advantage, dis=disadvantage, mod=mod, rng=rng)
    return {
        "ability": ability.lower(),
        "mod": mod,
        "roll": d["roll"],       # the kept d20 face
        "rolls": d["rolls"],     # both dice on adv/dis, else [roll]
        "total": d["total"],
        "dc": dc,
        "pass": d["total"] >= dc,
        "nat1": d["nat1"],
        "nat20": d["nat20"],
    }


def skill_check(
    character: dict,
    ability: str,
    dc: int,
    *,
    proficient: bool = False,
    advantage: bool = False,
    disadvantage: bool = False,
    rng: Optional[_random.Random] = None,
) -> dict:
    """Resolve a skill check.

    Returns ``{ability, mod, roll, rolls, total, dc, pass, nat1, nat20}``.

    Ability checks do *not* auto-succeed on nat20 or auto-fail on nat1 in
    5e RAW — only attack rolls and death saves do. We surface the nat1/
    nat20 flags so callers can narrate them; the ``pass`` field is based
    on ``total >= dc`` alone.
    """
    return _resolve(
        character, ability, dc,
        proficient=proficient,
        advantage=advantage,
        disadvantage=disadvantage,
        rng=rng,
    )


def save_throw(
    character: dict,
    ability: str,
    dc: int,
    *,
    proficient: bool = False,
    advantage: bool = False,
    disadvantage: bool = False,
    rng: Optional[_random.Random] = None,
) -> dict:
    """Resolve a saving throw.

    Mechanically identical to :func:`skill_check` at this layer — the
    difference lives in what the caller labels the event and which
    proficiency list it consults. Kept as a separate function so callers
    read naturally.
    """
    return _resolve(
        character, ability, dc,
        proficient=proficient,
        advantage=advantage,
        disadvantage=disadvantage,
        rng=rng,
    )
