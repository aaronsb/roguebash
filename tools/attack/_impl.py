"""attack — the PC attacks a target in the current room.

Flow:
  1. Load character.json, world.json, graph.json.
  2. Resolve ``target`` against the current room's spawns (monsters/NPCs)
     or against ``self`` (a PC striking themselves is a niche case we
     still permit for completeness).
  3. Resolve ``weapon`` against the character's inventory (or any item
     in the catalog as a fallback) and reshape to the character-style
     attack spec (so ``engine.rules.attack`` applies ability + prof).
  4. Roll the attack via ``engine.rules.attack.attack``. Emit the
     canonical ``attack`` ledger event.
  5. On hit, apply damage (persist to graph.json for spawns; to
     character.json for the PC — the schema doesn't carry "dummies" yet,
     so PC-vs-PC would only fire in self-target edge cases). Emit a
     ``damage`` event. If HP drops to 0, emit a ``death`` event.

What we *don't* do yet (explicitly deferred):
  - Resistance/vulnerability/immunity application. Monster catalogs
    carry ``resistances`` blocks but we pass damage through raw.
  - NPC attacks-of-opportunity or monster reactions.
  - PC death-save machinery (5e uses three saves at 0 HP). We emit
    ``death`` at HP 0 directly; the archival layer picks it up.
  - Multi-instance target disambiguation (two wolves in one room).
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
from engine.rules import attack as rules_attack
from engine.state import ledger


def main() -> int:
    args = rt.read_args()
    target = str(args.get("target", "")).strip()
    weapon = str(args.get("weapon", "")).strip()
    if not target or not weapon:
        print("attack: 'target' and 'weapon' are required", file=sys.stderr)
        return 2
    advantage = bool(args.get("advantage", False))
    disadvantage = bool(args.get("disadvantage", False))

    character = rt.load_character()
    world = rt.load_world()
    graph = rt.load_graph()

    # Seeded from the OS; passed through to every RNG consumer so the
    # engine.rules helpers don't fall back on their own module-level RNG
    # (and so we can inject deterministic RNGs in tests later).
    rng = random.Random()

    try:
        tgt = _combat.resolve_target(
            target,
            character=character,
            world=world,
            graph=graph,
            rng=rng,
        )
    except LookupError as e:
        print(f"attack: {e}", file=sys.stderr)
        return 2

    try:
        weapon_spec, weapon_name = _combat.resolve_weapon(
            weapon,
            attacker_kind="player",
            attacker_catalog=None,
            character=character,
        )
    except LookupError as e:
        print(f"attack: {e}", file=sys.stderr)
        return 2

    result = rules_attack.attack(
        character,
        weapon_spec,
        target_ac=tgt.ac,
        advantage=advantage,
        disadvantage=disadvantage,
        rng=rng,
    )

    run = rt.run_dir()
    turn = rt.current_turn()
    attacker_label = character.get("name", "player")

    ledger.attack(
        run,
        turn,
        attacker=attacker_label,
        target=tgt.id,
        weapon=weapon_name,
        to_hit_roll=result["to_hit_roll"],
        to_hit_total=result["to_hit_total"],
        ac=tgt.ac,
        hit=result["hit"],
        damage=result["damage"],
    )

    # Narration line.
    lines: list[str] = []
    verdict = "HIT" if result["hit"] else "MISS"
    crit = " (CRIT!)" if result["crit"] else ""
    fumble = " (fumble)" if result["fumble"] else ""
    lines.append(
        f"{attacker_label} attacks {tgt.name} with {weapon_name}: "
        f"to-hit {result['to_hit_roll']}+{result['to_hit_mod']}"
        f"={result['to_hit_total']} vs AC {tgt.ac} → {verdict}{crit}{fumble}."
    )

    if result["hit"] and result["damage"] > 0:
        new_hp = tgt.apply_damage(result["damage"])
        dtype = result["damage_type"] or "damage"
        lines.append(
            f"{tgt.name} takes {result['damage']} {dtype} "
            f"(HP {new_hp}/{tgt.hp.get('max', '?')})."
        )
        ledger.damage(
            run,
            turn,
            target=tgt.id,
            amount=result["damage"],
            type_=result["damage_type"] or "untyped",
            source=f"weapon:{weapon_name}",
        )
        if tgt.is_dead():
            lines.append(f"{tgt.name} falls.")
            ledger.death(
                run,
                turn,
                actor=tgt.id,
                cause=f"weapon:{weapon_name}",
            )
            # Player death triggers archival (the runner / meta layer
            # is the canonical place to archive, but we emit the event
            # here; `engine.state.archive` is available if the caller
            # wants to act on it immediately).

    # Always persist graph/character after an attack — even on a miss
    # against a monster we need to save the freshly-rolled HP so the
    # next attack doesn't re-roll it.
    if tgt.kind == "player":
        rt.save_character(character)
    else:
        rt.save_graph(graph)

    print("\n".join(lines))
    print(json.dumps({**result, "target": tgt.id, "target_hp": tgt.hp}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
