"""Ability-score arithmetic.

5e rules:

- Ability modifier = ``(score - 10) // 2`` (floor division handles negatives
  correctly, e.g. score 3 → -4 rather than -3).
- Proficiency bonus is a flat per-tier value keyed on character level.
"""

from __future__ import annotations


# 5e canonical tiers (PHB / SRD):
#   levels  1- 4 → +2
#   levels  5- 8 → +3
#   levels  9-12 → +4
#   levels 13-16 → +5
#   levels 17-20 → +6
_PROFICIENCY_BY_LEVEL = {
    **{lvl: 2 for lvl in range(1, 5)},
    **{lvl: 3 for lvl in range(5, 9)},
    **{lvl: 4 for lvl in range(9, 13)},
    **{lvl: 5 for lvl in range(13, 17)},
    **{lvl: 6 for lvl in range(17, 21)},
}


def modifier(score: int) -> int:
    """Return the 5e ability modifier for a raw ability score.

    ``(score - 10) // 2``. Python's floor division makes this agree with
    the 5e table at the negatives as well (e.g. score 3 → -4).
    """
    if not isinstance(score, int) or isinstance(score, bool):
        raise TypeError(f"modifier expects int, got {type(score).__name__}")
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    """Return the 5e proficiency bonus for ``level`` (1..20)."""
    if not isinstance(level, int) or isinstance(level, bool):
        raise TypeError(f"proficiency_bonus expects int, got {type(level).__name__}")
    if level not in _PROFICIENCY_BY_LEVEL:
        raise ValueError(f"level out of range 1..20: {level}")
    return _PROFICIENCY_BY_LEVEL[level]
