"""Dice rolling.

``roll(expr)`` evaluates an arbitrary additive dice expression (e.g.
``"2d6+3"``, ``"1d20"``, ``"2d20kh1"``) and returns the total plus the
per-term breakdown. ``d20(...)`` is the hot path for checks / attacks and
encodes 5e advantage/disadvantage natively.

All randomness goes through a caller-supplied ``random.Random`` or the
module's default instance. Tests inject a seeded RNG for determinism.
"""

from __future__ import annotations

import random as _random
from typing import Optional

from .parser import parse_dice_expr

# Module-level default RNG. Tests can pass their own via the `rng` kwarg;
# we do not reseed this one.
_DEFAULT_RNG = _random.Random()


def _roll_die(sides: int, rng: _random.Random) -> int:
    """Roll one die with `sides` faces."""
    if sides < 1:
        raise ValueError(f"die size must be >= 1, got {sides}")
    return rng.randint(1, sides)


def _eval_dice_term(term: dict, rng: _random.Random) -> dict:
    """Roll a dice-term dict produced by :func:`parser.parse_dice_term`.

    Returns::

        {
          "count": N,
          "sides": M,
          "rolls": [int, ...],     # every die that was physically rolled
          "kept":  [int, ...],     # subset retained after kh/kl (or all)
          "total": int,            # sum(kept)
        }
    """
    count = term["count"]
    sides = term["sides"]
    keep = term["keep"]
    keep_n = term["keep_n"]

    rolls = [_roll_die(sides, rng) for _ in range(count)]
    if keep == "kh":
        kept = sorted(rolls, reverse=True)[:keep_n]
    elif keep == "kl":
        kept = sorted(rolls)[:keep_n]
    else:
        kept = list(rolls)
    return {
        "count": count,
        "sides": sides,
        "rolls": rolls,
        "kept": kept,
        "total": sum(kept),
    }


def roll(expr: str, *, rng: Optional[_random.Random] = None) -> dict:
    """Evaluate an additive dice expression.

    Returns::

        {
          "expr":  original string,
          "total": int,                    # signed sum of all terms
          "terms": [                       # per-term breakdown in order
            {"sign": +1|-1, "kind": "dice", ...dice fields...},
            {"sign": +1|-1, "kind": "mod",  "value": int},
            ...
          ],
        }

    Examples::

        roll("2d6+3")  -> {"total": 9,  "terms": [dice 2d6 rolled 2+4, mod +3]}
        roll("1d20")   -> {"total": 14, "terms": [dice 1d20 rolled 14]}
        roll("2d20kh1") -> advantage roll
    """
    rng = rng or _DEFAULT_RNG
    parsed = parse_dice_expr(expr)
    total = 0
    terms: list[dict] = []
    for sign, term in parsed:
        if isinstance(term, int):
            total += sign * term
            terms.append({"sign": sign, "kind": "mod", "value": term})
        else:
            evaluated = _eval_dice_term(term, rng)
            total += sign * evaluated["total"]
            terms.append({"sign": sign, "kind": "dice", **evaluated})
    return {"expr": expr, "total": total, "terms": terms}


def d20(
    *,
    adv: bool = False,
    dis: bool = False,
    mod: int = 0,
    rng: Optional[_random.Random] = None,
) -> dict:
    """Roll a d20 with 5e advantage/disadvantage semantics.

    Advantage and disadvantage **cancel** (per PHB): if both are ``True``,
    a single straight d20 is rolled.

    Returns::

        {
          "rolls": [int, int] | [int],   # both dice on adv/dis, else one
          "roll":  int,                  # the die that was kept
          "mod":   int,                  # modifier added
          "total": roll + mod,
          "nat1":  bool,                 # kept die == 1
          "nat20": bool,                 # kept die == 20
        }
    """
    rng = rng or _DEFAULT_RNG
    # Cancel when both set.
    if adv and dis:
        adv = dis = False

    if adv:
        a, b = _roll_die(20, rng), _roll_die(20, rng)
        kept = max(a, b)
        rolls = [a, b]
    elif dis:
        a, b = _roll_die(20, rng), _roll_die(20, rng)
        kept = min(a, b)
        rolls = [a, b]
    else:
        kept = _roll_die(20, rng)
        rolls = [kept]

    return {
        "rolls": rolls,
        "roll": kept,
        "mod": mod,
        "total": kept + mod,
        "nat1": kept == 1,
        "nat20": kept == 20,
    }
