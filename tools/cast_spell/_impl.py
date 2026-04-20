"""cast_spell — apply a spell's mechanical effect.

MVP SCOPE — read carefully.

The full 5e spell list is tens of thousands of words. Authoring a
``spells.jsonl`` catalog is a downstream task (see the TODO in
tools/cast_spell/README.md). For now this tool carries a *small inline
spell table* covering the five most-cast level-0/1 spells, enough to
prove the cast → apply-effect → ledger-write flow end-to-end.

The five MVP spells:

  - ``cure_wounds``   (heal): 1d8 + caster's wis/cha mod. Self or ally.
  - ``magic_missile`` (force damage): 3 darts, 1d4+1 each, auto-hit.
  - ``shield``        (status): self only, +5 AC for one turn (status effect
                      ``shield_up``; the DM or monster-ai prompt is
                      responsible for honoring it — we just record it).
  - ``bless``         (status): target gains ``blessed`` status.
  - ``guidance``      (status): target gains ``guidance`` status.

Slot tracking is best-effort: if ``character.spell_slots`` exists, we
decrement the smallest available slot. If it doesn't, we log the cast
without slot bookkeeping — the character schema doesn't yet define
spell slots, and blocking on a missing field would wedge the tool.

REPLACE WITH spells.jsonl CATALOG WHEN AUTHORED.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from tools._shared import combat as _combat
from tools._shared import runtime as rt
from engine.rules import ability as rules_ability
from engine.rules import dice as rules_dice
from engine.state import ledger


# ---- inline MVP spell table (REPLACE WITH spells.jsonl CATALOG) ------


_SPELLS: dict[str, dict] = {
    # Level 1. Touch. Heals 1d8 + spellcasting-ability mod.
    "cure_wounds": {
        "level": 1,
        "kind": "heal",
        "dice": "1d8",
        "add_mod": True,      # add the caster's spellcasting mod
        "target_scope": "self_or_ally",
    },
    # Level 1. 3 darts, each 1d4+1 force. Auto-hit.
    "magic_missile": {
        "level": 1,
        "kind": "damage",
        "dice": "3d4+3",      # 3 darts of 1d4+1 collapsed to 3d4+3
        "damage_type": "force",
        "auto_hit": True,
        "target_scope": "enemy",
    },
    # Level 1. Self only. +5 AC until end of next turn.
    "shield": {
        "level": 1,
        "kind": "status",
        "status": "shield_up",
        "duration": 1,
        "target_scope": "self",
    },
    # Level 1. Target gains +1d4 to attacks/saves for one minute.
    "bless": {
        "level": 1,
        "kind": "status",
        "status": "blessed",
        "duration": 10,
        "target_scope": "ally",
    },
    # Cantrip. Target gains +1d4 to next ability check.
    "guidance": {
        "level": 0,
        "kind": "status",
        "status": "guidance",
        "duration": 1,
        "target_scope": "ally",
    },
}


_CASTER_ABILITY_BY_CLASS = {
    "wizard": "int",
    "cleric": "wis",
    "druid": "wis",
    "ranger": "wis",
    "paladin": "cha",
    "bard": "cha",
    "sorcerer": "cha",
    "warlock": "cha",
}


def _caster_mod(character: dict) -> int:
    """Pick the spellcasting ability mod based on the PC's class."""
    ability = _CASTER_ABILITY_BY_CLASS.get(
        (character.get("class") or "").lower(),
        "wis",  # reasonable default for an unclassed PC
    )
    score = (character.get("stats") or {}).get(ability, 10)
    return rules_ability.modifier(int(score))


def _consume_slot(character: dict, level: int) -> bool:
    """Decrement the smallest slot of at least ``level``. Best-effort.

    character.json does not currently declare ``spell_slots``; if it
    isn't there we silently succeed (the feature will light up once
    the sheet carries slots).
    """
    slots = character.get("spell_slots")
    if not isinstance(slots, dict):
        return False
    # slots shape assumed: {"1": 2, "2": 0, ...}
    # Find the smallest slot ≥ `level` with > 0 remaining.
    for lvl_key in sorted(slots.keys(), key=lambda s: int(s)):
        if int(lvl_key) < level:
            continue
        if int(slots[lvl_key]) > 0:
            slots[lvl_key] = int(slots[lvl_key]) - 1
            return True
    return False


def _set_status(character: dict, effect: str) -> None:
    effects = character.setdefault("status_effects", [])
    if effect not in effects:
        effects.append(effect)


def main() -> int:
    args = rt.read_args()
    spell = str(args.get("spell", "")).strip().lower().replace(" ", "_")
    target = str(args.get("target", "self")).strip() or "self"

    if spell not in _SPELLS:
        print(
            f"cast_spell: unknown spell {spell!r} (MVP table: "
            f"{sorted(_SPELLS)}). A full spells.jsonl catalog is pending.",
            file=sys.stderr,
        )
        return 2

    spec = _SPELLS[spell]

    character = rt.load_character()
    world = rt.load_world()
    graph = rt.load_graph()

    rng = random.Random()

    # Resolve target — may be self, an ally (not implemented), or an enemy.
    try:
        tgt = _combat.resolve_target(
            target,
            character=character,
            world=world,
            graph=graph,
            rng=rng,
        )
    except LookupError as e:
        print(f"cast_spell: {e}", file=sys.stderr)
        return 2

    run = rt.run_dir()
    turn = rt.current_turn()
    caster = character.get("name", "player")

    slot_consumed = False
    if spec.get("level", 0) >= 1:
        slot_consumed = _consume_slot(character, spec["level"])

    # Outcome summary — populated by the branch that actually runs,
    # then attached to the `tool_call` ledger event once the effect
    # has resolved (so the ledger carries the real amount, not a
    # 'pending' placeholder).
    outcome: dict = {
        "spell": spell,
        "target": tgt.id,
        "kind": spec["kind"],
        "slot_consumed": slot_consumed,
    }

    lines: list[str] = [f"{caster} casts {spell.replace('_', ' ')} on {tgt.name}."]

    kind = spec["kind"]

    if kind == "damage":
        rolled = rules_dice.roll(spec["dice"], rng=rng)
        amount = max(0, int(rolled["total"]))
        dtype = spec.get("damage_type", "force")
        killed = False
        if amount > 0:
            new_hp = tgt.apply_damage(amount)
            lines.append(
                f"{tgt.name} takes {amount} {dtype} "
                f"(HP {new_hp}/{tgt.hp.get('max', '?')})."
            )
            ledger.damage(
                run,
                turn,
                target=tgt.id,
                amount=amount,
                type_=dtype,
                source=f"spell:{spell}",
            )
            if tgt.is_dead():
                killed = True
                lines.append(f"{tgt.name} is destroyed.")
                ledger.death(run, turn, actor=tgt.id, cause=f"spell:{spell}")
        # Persist even on zero-damage / first-touch (HP may have been rolled).
        if tgt.kind == "player":
            rt.save_character(character)
        else:
            rt.save_graph(graph)
        outcome["damage"] = amount
        outcome["damage_type"] = dtype
        outcome["killed"] = killed

    elif kind == "heal":
        rolled = rules_dice.roll(spec["dice"], rng=rng)
        amount = int(rolled["total"])
        if spec.get("add_mod"):
            amount += _caster_mod(character)
        amount = max(0, amount)
        if amount > 0:
            new_hp = tgt.apply_heal(amount)
            lines.append(
                f"{tgt.name} regains {amount} HP "
                f"(HP {new_hp}/{tgt.hp.get('max', '?')})."
            )
            ledger.heal(
                run,
                turn,
                target=tgt.id,
                amount=amount,
                source=f"spell:{spell}",
            )
        if tgt.kind == "player":
            rt.save_character(character)
        else:
            rt.save_graph(graph)
        outcome["healed"] = amount

    elif kind == "status":
        effect = spec["status"]
        # For MVP we only carry status effects on the PC. Monsters/NPCs
        # don't yet have a status_effects list in the runtime shape, so
        # we log but don't persist on them.
        applied = False
        if tgt.kind == "player":
            _set_status(character, effect)
            rt.save_character(character)
            applied = True
        lines.append(f"{tgt.name} is now {effect} (duration {spec.get('duration', 1)}).")
        outcome["status"] = effect
        outcome["applied"] = applied

    else:
        print(f"cast_spell: internal error — unknown spell kind {kind!r}", file=sys.stderr)
        return 2

    # tool_call event carries the realized outcome, not a 'pending' placeholder.
    ledger.tool_call(
        run,
        turn,
        name="cast_spell",
        args={"spell": spell, "target": target},
        result=outcome,
    )

    if slot_consumed:
        rt.save_character(character)
        lines.append("(spell slot consumed)")
    elif spec.get("level", 0) >= 1:
        lines.append("(no slot tracking yet; MVP)")

    print("\n".join(lines))
    print(json.dumps({**outcome, "target_hp": tgt.hp}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
