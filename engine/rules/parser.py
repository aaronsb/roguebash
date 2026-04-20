"""Small parsers shared by dice / attack / hp helpers.

Everything here is string-in, number-or-tuple-out. No RNG, no state.
"""

from __future__ import annotations

import re
from typing import Tuple

# ---------------------------------------------------------------------------
# signed integer strings — the schema writes "+4", "-1", "0", sometimes "4"
# ---------------------------------------------------------------------------

_SIGNED_INT_RE = re.compile(r"^\s*([+-]?\d+)\s*$")


def parse_signed_int(text: str | int) -> int:
    """Parse ``"+4"`` / ``"-1"`` / ``"4"`` / ``4`` → ``int``.

    Used for the `to_hit` and fixed-modifier fields in ``monsters.jsonl``
    and ``npcs.jsonl``. Accepts a raw int untouched for caller convenience.
    """
    if isinstance(text, int):
        return text
    if not isinstance(text, str):
        raise TypeError(f"parse_signed_int expects str|int, got {type(text).__name__}")
    m = _SIGNED_INT_RE.match(text)
    if not m:
        raise ValueError(f"not a signed integer: {text!r}")
    return int(m.group(1))


# ---------------------------------------------------------------------------
# dice expressions
# ---------------------------------------------------------------------------
#
# Grammar (informal):
#
#   expr       := term (('+' | '-') term)*
#   term       := dice_term | int_literal
#   dice_term  := [N]d M [ (kh|kl) K ]
#
# N defaults to 1. M is the die size. "kh K" / "kl K" keep the highest /
# lowest K dice out of N (5e advantage = 2d20kh1, disadvantage = 2d20kl1).
#
# The parser returns a structured form; `dice.roll` does the actual RNG.

_DICE_RE = re.compile(
    r"""
    ^\s*
    (?P<count>\d+)?       # optional N
    [dD]                  # d
    (?P<sides>\d+)        # M
    (?:
      \s*(?P<keep>kh|kl|KH|KL)\s*
      (?P<keep_n>\d+)
    )?
    \s*$
    """,
    re.VERBOSE,
)

_INT_RE = re.compile(r"^\s*([+-]?\d+)\s*$")


def parse_dice_term(term: str) -> dict:
    """Parse a single dice token like ``"2d6"`` or ``"2d20kh1"``.

    Returns ``{"count": int, "sides": int, "keep": "kh"|"kl"|None, "keep_n": int|None}``.
    Raises ``ValueError`` if the token is not a dice term.
    """
    m = _DICE_RE.match(term)
    if not m:
        raise ValueError(f"not a dice term: {term!r}")
    count = int(m.group("count")) if m.group("count") else 1
    sides = int(m.group("sides"))
    if count < 1:
        raise ValueError(f"dice count must be >= 1: {term!r}")
    if sides < 1:
        raise ValueError(f"die size must be >= 1: {term!r}")
    keep = m.group("keep")
    keep_n = m.group("keep_n")
    if keep:
        keep = keep.lower()
        keep_n = int(keep_n)
        if keep_n < 1 or keep_n > count:
            raise ValueError(f"keep count out of range: {term!r}")
    else:
        keep = None
        keep_n = None
    return {"count": count, "sides": sides, "keep": keep, "keep_n": keep_n}


def parse_dice_expr(expr: str) -> list[Tuple[int, dict | int]]:
    """Parse an additive dice expression.

    Returns a list of ``(sign, term)`` pairs where ``sign`` is ``+1`` or
    ``-1`` and ``term`` is either a parsed dice-term dict or a plain int
    (flat modifier). Whitespace is tolerated.

    Examples::

        parse_dice_expr("2d6+3")      -> [(+1, {...d6...}), (+1, 3)]
        parse_dice_expr("1d20-1")     -> [(+1, {...d20...}), (-1, 1)]
        parse_dice_expr("2d20kh1+4")  -> [(+1, {...d20 kh 1...}), (+1, 4)]
    """
    if not isinstance(expr, str):
        raise TypeError(f"parse_dice_expr expects str, got {type(expr).__name__}")

    # Split on + / - while keeping the sign. Leading sign is optional.
    s = expr.strip()
    if not s:
        raise ValueError("empty dice expression")

    # Tokenize: we walk the string, carving out signed segments.
    tokens: list[Tuple[int, str]] = []
    sign = +1
    buf = ""
    # Allow an explicit leading sign.
    i = 0
    if s[0] in "+-":
        sign = +1 if s[0] == "+" else -1
        i = 1
    while i < len(s):
        ch = s[i]
        if ch in "+-":
            if not buf.strip():
                raise ValueError(f"stray {ch!r} in: {expr!r}")
            tokens.append((sign, buf.strip()))
            sign = +1 if ch == "+" else -1
            buf = ""
        else:
            buf += ch
        i += 1
    if not buf.strip():
        raise ValueError(f"trailing operator in: {expr!r}")
    tokens.append((sign, buf.strip()))

    out: list[Tuple[int, dict | int]] = []
    for sgn, tok in tokens:
        # Try dice first, then int literal.
        try:
            out.append((sgn, parse_dice_term(tok)))
            continue
        except ValueError:
            pass
        m = _INT_RE.match(tok)
        if not m:
            raise ValueError(f"unrecognized term {tok!r} in: {expr!r}")
        # A bare negative literal ("-3") inside an additive chain is rare
        # but legal; fold its sign into the outer sign.
        lit = int(m.group(1))
        if lit < 0:
            out.append((-sgn, -lit))
        else:
            out.append((sgn, lit))
    return out


# ---------------------------------------------------------------------------
# HP strings — schema allows "2d6+2" or "11 (2d8+2)" or a bare integer.
# ---------------------------------------------------------------------------

_HP_WITH_AVG_RE = re.compile(r"^\s*(\d+)\s*\(\s*(.+?)\s*\)\s*$")


def parse_hp_expression(value: str | int) -> str:
    """Normalize an HP field to a pure dice expression.

    Accepts:
      - ``12``           → ``"12"``
      - ``"12"``         → ``"12"``
      - ``"2d6+2"``      → ``"2d6+2"``
      - ``"11 (2d8+2)"`` → ``"2d8+2"``  (schema-idiomatic "avg (dice)" form)

    The returned string is guaranteed parseable by :func:`parse_dice_expr`.
    """
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, str):
        raise TypeError(f"parse_hp_expression expects str|int, got {type(value).__name__}")
    m = _HP_WITH_AVG_RE.match(value)
    if m:
        inner = m.group(2)
        # Validate.
        parse_dice_expr(inner)
        return inner
    # Plain dice expression or bare integer — validate.
    parse_dice_expr(value)
    return value.strip()
