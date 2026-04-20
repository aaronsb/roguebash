"""engine.rules — pure 5e math.

Functions in this package take numbers/dicts in and return numbers/dicts
out. They do not touch the filesystem, mutate caller state, or call out
to an LLM. State mutation is the tool layer's job; these helpers are the
arithmetic the tools wrap.

Public surface:

    from engine.rules import dice, ability, checks, attack, hp, parser
"""

from . import ability, attack, checks, dice, hp, parser

__all__ = ["ability", "attack", "checks", "dice", "hp", "parser"]
