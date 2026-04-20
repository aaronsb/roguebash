"""Append-only event log — one JSON object per line.

The model sees only the **last 5** events in the ledger per turn (via
`tail`), so the prompt stays bounded regardless of run length. Tools and
the runner emit events via the canonical helpers below.

Every emission helper writes a dict shaped like:

    {"t": <turn>, "type": "<canonical_type>", ...fields...}

This matches `engine/state/README.md`. The helpers exist (rather than a
single generic `emit(type, **kwargs)`) so callers can't silently drift
the field names — the README table is the contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from . import io as _io
from .paths import LEDGER_FILE, run_dir


# ---- helpers ---------------------------------------------------------


def _ledger_path(run_id_or_path: str | Path) -> Path:
    """Accept either a run_id (str) or a direct path to `ledger.jsonl`.

    Tools typically hand us a run_id; tests hand us a tempfile path. Both
    work.
    """
    p = Path(run_id_or_path)
    if p.suffix == ".jsonl" or p.name == LEDGER_FILE:
        return p
    if p.is_absolute() or "/" in str(run_id_or_path):
        # Caller handed us a directory path.
        return p / LEDGER_FILE
    # Treat as a run_id.
    return run_dir(str(run_id_or_path)) / LEDGER_FILE


def _emit(where: str | Path, turn: int, **fields: Any) -> dict[str, Any]:
    """Assemble and append a single event; return the dict for callers
    that want to log or echo it."""
    evt = {"t": int(turn), **fields}
    _io.append_jsonl(_ledger_path(where), evt)
    return evt


# ---- canonical emitters (one per README event type) ------------------


def narration(where: str | Path, turn: int, text: str) -> dict[str, Any]:
    """Prose from the DM. Written after every model response."""
    return _emit(where, turn, type="narration", text=text)


def tool_call(
    where: str | Path,
    turn: int,
    name: str,
    args: dict[str, Any],
    result: Any,
) -> dict[str, Any]:
    """A tool the model invoked this turn, with its arguments and result."""
    return _emit(where, turn, type="tool_call", name=name, args=args, result=result)


def skill_check(
    where: str | Path,
    turn: int,
    ability: str,
    dc: int,
    roll: int,
    modifier: int,
    total: int,
    pass_: bool,
) -> dict[str, Any]:
    """An ability-check resolution. `pass_` is the dataclass-safe spelling
    of the `pass` key in the JSON — we serialize it as `pass`."""
    return _emit(
        where,
        turn,
        type="skill_check",
        ability=ability,
        dc=int(dc),
        roll=int(roll),
        modifier=int(modifier),
        total=int(total),
        **{"pass": bool(pass_)},
    )


def save_throw(
    where: str | Path,
    turn: int,
    save_type: str,
    dc: int,
    roll: int,
    modifier: int,
    total: int,
    pass_: bool,
) -> dict[str, Any]:
    """A saving-throw resolution."""
    return _emit(
        where,
        turn,
        type="save_throw",
        save_type=save_type,
        dc=int(dc),
        roll=int(roll),
        modifier=int(modifier),
        total=int(total),
        **{"pass": bool(pass_)},
    )


def attack(
    where: str | Path,
    turn: int,
    attacker: str,
    target: str,
    weapon: str,
    to_hit_roll: int,
    to_hit_total: int,
    ac: int,
    hit: bool,
    damage: int,
) -> dict[str, Any]:
    """An attack resolution (to-hit + damage). On a miss, `damage` is 0."""
    return _emit(
        where,
        turn,
        type="attack",
        attacker=attacker,
        target=target,
        weapon=weapon,
        to_hit_roll=int(to_hit_roll),
        to_hit_total=int(to_hit_total),
        ac=int(ac),
        hit=bool(hit),
        damage=int(damage),
    )


def damage(
    where: str | Path,
    turn: int,
    target: str,
    amount: int,
    type_: str,
    source: str,
) -> dict[str, Any]:
    """Damage applied outside a normal attack (hazards, spells, falls).

    `type_` is the damage type (piercing, fire, ...). The README shape
    uses `"type"` as BOTH the event discriminator and the damage type;
    we preserve that — the outer `"type": "damage"` collides with the
    damage-type key, but the README example resolves the conflict by
    making the damage event carry only `target/amount/type/source` where
    `type` is the damage type. We match that here: the canonical event
    type 'damage' is preserved; the damage-type goes under `type` too,
    but the outer discriminator wins at JSON-serialization time.

    Rather than rely on dict collision behavior, we assemble the event
    by hand so the shape is unambiguous.
    """
    evt = {
        "t": int(turn),
        "type": "damage",
        "target": target,
        "amount": int(amount),
        "damage_type": type_,
        "source": source,
    }
    _io.append_jsonl(_ledger_path(where), evt)
    return evt


def heal(
    where: str | Path,
    turn: int,
    target: str,
    amount: int,
    source: str,
) -> dict[str, Any]:
    """Healing applied (potion, cleric spell, long rest, ...)."""
    return _emit(
        where,
        turn,
        type="heal",
        target=target,
        amount=int(amount),
        source=source,
    )


def item_taken(
    where: str | Path,
    turn: int,
    item_ref: str,
    from_room: str,
) -> dict[str, Any]:
    """Player took an item out of a room."""
    return _emit(
        where,
        turn,
        type="item_taken",
        item_ref=item_ref,
        from_room=from_room,
    )


def item_dropped(
    where: str | Path,
    turn: int,
    item_ref: str,
    to_room: str,
) -> dict[str, Any]:
    """Player dropped an item into a room."""
    return _emit(
        where,
        turn,
        type="item_dropped",
        item_ref=item_ref,
        to_room=to_room,
    )


def level_up(
    where: str | Path,
    turn: int,
    new_level: int,
    choices: dict[str, Any],
) -> dict[str, Any]:
    """Player leveled up. `choices` is an open dict of what they picked
    (ASI, subclass, spells, ...)."""
    return _emit(
        where,
        turn,
        type="level_up",
        new_level=int(new_level),
        choices=choices,
    )


def death(where: str | Path, turn: int, actor: str, cause: str) -> dict[str, Any]:
    """Someone died. For the player this also triggers archiving."""
    return _emit(where, turn, type="death", actor=actor, cause=cause)


def victory(where: str | Path, turn: int, player: str, goal: str) -> dict[str, Any]:
    """Run ended in victory. Triggers archiving."""
    return _emit(where, turn, type="victory", player=player, goal=goal)


# ---- read side -------------------------------------------------------


def tail(path: str | Path, n: int = 5) -> list[dict[str, Any]]:
    """Return the last `n` events from `path`, oldest-first.

    Skips blank lines and unparseable partials (from e.g. a crashed mid-
    write). If the file doesn't exist yet, returns `[]`.
    """
    p = _ledger_path(path)
    if not p.exists():
        return []
    # For the event volumes roguebash produces (tens to low thousands per
    # run), reading the whole file is cheap enough and simpler than a
    # reverse-seek parser. Revisit if that ever changes.
    out: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # Tolerate a partial trailing line from a crashed writer.
                continue
    if n <= 0:
        return []
    return out[-n:]


def iter_events(path: str | Path) -> Iterable[dict[str, Any]]:
    """Yield every parseable event from `path`, oldest-first.

    Convenience for tools that need the full history (e.g. `delve show`).
    """
    p = _ledger_path(path)
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
