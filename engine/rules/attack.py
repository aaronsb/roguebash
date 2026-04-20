"""Attack resolution — full 5e flow.

Signature::

    attack(attacker, weapon, target_ac, *, advantage=False, disadvantage=False, rng=None)

Inputs:

``attacker``
    A character-or-monster dict. Supplies stats & level for player attacks
    when the weapon does not carry a pre-computed ``to_hit``.

``weapon``
    The attack spec. Two flavors are accepted, mirroring
    ``scenarios/schema.md`` and ``engine/state/README.md``:

    * **Statblock style** (monsters / NPCs): has ``to_hit`` as a signed
      string (``"+4"``) or int, and ``damage`` as a dice expression
      (``"1d6+2"``). This module uses those directly.
    * **Character style** (player weapons): has ``damage_dice`` (e.g.
      ``"1d8"``) and an ``ability`` (``"str"`` or ``"dex"`` — finesse
      weapons let the caller choose). To-hit modifier is computed as
      ``ability_mod + (proficiency_bonus if weapon.proficient else 0)``.
      The same ability modifier is added to damage.

``target_ac``
    The defender's armor class. ``int``.

Returns::

    {
      "to_hit_roll":  int,           # d20 face kept
      "to_hit_rolls": [int, ...],    # [a, b] on adv/dis, else [face]
      "to_hit_mod":   int,           # attacker's total +to-hit modifier
      "to_hit_total": int,           # roll + mod
      "hit":          bool,
      "crit":         bool,          # nat20
      "fumble":       bool,          # nat1 — auto-miss
      "damage":       int,           # 0 on miss
      "damage_type":  str | None,
      "damage_rolls": [int, ...]|[], # individual dice faces rolled for damage
    }

Crit rule (PHB): on a natural 20, roll **all damage dice twice** and add
modifiers once. We implement that by re-rolling the dice half of the
expression and summing both sets, while the flat modifier is applied
exactly once.
"""

from __future__ import annotations

import random as _random
from typing import Optional

from .ability import modifier, proficiency_bonus
from .dice import _eval_dice_term, d20  # _eval_dice_term is internal but stable
from .parser import parse_dice_expr, parse_signed_int

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")


def _resolve_to_hit_mod(attacker: dict, weapon: dict) -> int:
    """Derive the +to-hit modifier for this attack.

    Prefers an explicit ``to_hit`` on the weapon (statblock style). Falls
    back to ``ability_mod + proficiency_bonus (if proficient)`` from the
    attacker for character-style weapons.
    """
    if "to_hit" in weapon and weapon["to_hit"] is not None:
        return parse_signed_int(weapon["to_hit"])

    ability = (weapon.get("ability") or "str").lower()
    if ability not in ABILITIES:
        raise ValueError(f"weapon.ability invalid: {ability!r}")
    stats = (attacker or {}).get("stats") or {}
    if ability not in stats:
        raise ValueError(f"attacker.stats missing {ability!r} for weapon ability")
    mod = modifier(int(stats[ability]))
    if weapon.get("proficient"):
        level = (attacker or {}).get("level", 1)
        mod += proficiency_bonus(int(level))
    return mod


def _split_damage_expr(expr: str) -> tuple[list[tuple[int, dict]], int]:
    """Split a parsed damage expression into (dice_terms, flat_modifier).

    Each dice term is ``(sign, parsed_term_dict)``; the modifier is the
    signed sum of all flat int terms.
    """
    parsed = parse_dice_expr(expr)
    dice_terms: list[tuple[int, dict]] = []
    flat = 0
    for sign, term in parsed:
        if isinstance(term, int):
            flat += sign * term
        else:
            dice_terms.append((sign, term))
    return dice_terms, flat


def _roll_damage(
    weapon: dict,
    attacker: dict,
    *,
    crit: bool,
    rng: _random.Random | None = None,
) -> dict:
    """Roll damage for this attack.

    Statblock weapons: ``damage`` is the full dice expression (already
    includes any attacker bonus — NPCs/monsters bake this in at authoring).

    Character weapons: ``damage_dice`` is the weapon's base dice (e.g.
    ``"1d8"``); we add the attacker's ability modifier on top, matching
    the 5e rule "damage roll: weapon damage die + ability modifier".

    On crit: dice are rolled twice, the flat modifier is added once.
    """
    rng = rng or _random.Random()
    damage_type = weapon.get("damage_type")

    if "damage" in weapon and weapon["damage"] is not None:
        dice_terms, flat = _split_damage_expr(weapon["damage"])
    elif "damage_dice" in weapon and weapon["damage_dice"] is not None:
        dice_terms, flat = _split_damage_expr(weapon["damage_dice"])
        # Add attacker ability modifier into the flat part.
        ability = (weapon.get("ability") or "str").lower()
        stats = (attacker or {}).get("stats") or {}
        if ability in stats:
            flat += modifier(int(stats[ability]))
    else:
        raise ValueError("weapon must carry 'damage' or 'damage_dice'")

    all_faces: list[int] = []
    dice_total = 0
    # First pass over the dice.
    for sign, term in dice_terms:
        ev = _eval_dice_term(term, rng)
        all_faces.extend(ev["rolls"])
        dice_total += sign * ev["total"]

    # On crit, roll every dice term a second time and add (PHB 5e).
    if crit:
        for sign, term in dice_terms:
            ev = _eval_dice_term(term, rng)
            all_faces.extend(ev["rolls"])
            dice_total += sign * ev["total"]

    damage = dice_total + flat
    # 5e damage can be reduced but never below 0 at the roll stage
    # (resistance/immunity are applied later, outside this helper).
    if damage < 0:
        damage = 0
    return {
        "damage": damage,
        "damage_type": damage_type,
        "damage_rolls": all_faces,
        "flat_mod": flat,
    }


def attack(
    attacker: dict,
    weapon: dict,
    target_ac: int,
    *,
    advantage: bool = False,
    disadvantage: bool = False,
    rng: Optional[_random.Random] = None,
) -> dict:
    """Resolve a single 5e attack roll + damage (see module docstring)."""
    to_hit_mod = _resolve_to_hit_mod(attacker, weapon)
    d = d20(adv=advantage, dis=disadvantage, mod=to_hit_mod, rng=rng)

    # 5e attack roll specials:
    #   nat 20 = crit & auto-hit
    #   nat  1 = auto-miss (no crit fail flag beyond 'fumble=True')
    crit = d["nat20"]
    fumble = d["nat1"]
    if crit:
        hit = True
    elif fumble:
        hit = False
    else:
        hit = d["total"] >= target_ac

    if hit:
        dmg = _roll_damage(weapon, attacker, crit=crit, rng=rng)
        damage = dmg["damage"]
        damage_type = dmg["damage_type"]
        damage_rolls = dmg["damage_rolls"]
    else:
        damage = 0
        damage_type = weapon.get("damage_type")
        damage_rolls = []

    return {
        "to_hit_roll": d["roll"],
        "to_hit_rolls": d["rolls"],
        "to_hit_mod": to_hit_mod,
        "to_hit_total": d["total"],
        "hit": hit,
        "crit": crit,
        "fumble": fumble,
        "damage": damage,
        "damage_type": damage_type,
        "damage_rolls": damage_rolls,
    }
