"""HP arithmetic.

The ``hp`` block in ``character.json`` is ``{"current": int, "max": int}``.
Functions here accept **either** the full dict or a ``(current, max)``
pair for monster HP tracking where the caller may not have a dict yet.

Returns always match the input shape — pass a dict, get a dict back; pass
a pair, get a pair back. These functions are pure (no mutation).
"""

from __future__ import annotations

from typing import Tuple, Union

HpLike = Union[dict, Tuple[int, int]]


def _unpack(hp: HpLike) -> tuple[int, int, bool]:
    """Return (current, max, was_dict). Normalizes both input shapes."""
    if isinstance(hp, dict):
        if "current" not in hp or "max" not in hp:
            raise ValueError(f"hp dict must have 'current' and 'max': {hp!r}")
        cur = int(hp["current"])
        mx = int(hp["max"])
        return cur, mx, True
    if isinstance(hp, tuple) and len(hp) == 2:
        return int(hp[0]), int(hp[1]), False
    raise TypeError(f"hp must be dict or (current, max) tuple, got {type(hp).__name__}")


def _pack(cur: int, mx: int, was_dict: bool) -> HpLike:
    if was_dict:
        return {"current": cur, "max": mx}
    return (cur, mx)


def apply_damage(hp: HpLike, amount: int) -> HpLike:
    """Subtract ``amount`` from current HP, clamped at 0.

    Does **not** mutate the input. Negative ``amount`` raises — use
    :func:`heal` for the positive direction so callers' intent is explicit.
    """
    if amount < 0:
        raise ValueError(f"apply_damage amount must be >= 0, got {amount}")
    cur, mx, was_dict = _unpack(hp)
    new = cur - amount
    if new < 0:
        new = 0
    return _pack(new, mx, was_dict)


def heal(hp: HpLike, amount: int) -> HpLike:
    """Add ``amount`` to current HP, clamped at max.

    Does **not** mutate the input. Negative ``amount`` raises — use
    :func:`apply_damage` to deal damage.
    """
    if amount < 0:
        raise ValueError(f"heal amount must be >= 0, got {amount}")
    cur, mx, was_dict = _unpack(hp)
    new = cur + amount
    if new > mx:
        new = mx
    return _pack(new, mx, was_dict)


def is_dead(hp: HpLike) -> bool:
    """True if current HP is at or below 0.

    5e has the death-save layer on top of this for PCs — that belongs in
    the tool / state layer, not here. This predicate is the floor.
    """
    cur, _mx, _ = _unpack(hp)
    return cur <= 0
