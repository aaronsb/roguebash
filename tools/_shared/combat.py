"""Combat-adjacent helpers shared across attack / cast_spell / etc.

Three concerns live here:

1. **Weapon reshape** — `items.jsonl` stores PC weapons as
   ``{damage: "1d8", damage_type: "piercing", properties: [...]}``.
   `engine.rules.attack.attack` interprets ``damage`` as statblock-style
   (already-baked with attacker mod). PCs need the *character-style*
   shape: ``{damage_dice, ability, proficient}``. We translate here.

2. **Target resolution** — given a target id in the current room,
   locate it in graph.json (monster / NPC spawn) or on the character.
   Also returns enough context to mutate its HP back to disk.

3. **Monster HP instantiation** — catalog monsters declare HP as a dice
   expression (``"2d6"`` / ``"11 (2d8+2)"``). graph.json spawns don't
   carry an ``hp`` field until first contact; we roll on demand and
   persist an ``{"current": N, "max": N}`` block onto the spawn entry.
"""

from __future__ import annotations

import random as _random
from typing import Any

from . import catalogs as _cat
from . import runtime as _rt


# ---------------------------------------------------------------------------
# weapon reshape
# ---------------------------------------------------------------------------


_FINESSE_PROPS = {"finesse"}
_RANGED_TAGS = {"ranged"}


def _weapon_ability(item: dict) -> str:
    """Choose the 5e ability that governs this weapon.

    Ranged weapons use dex. Finesse weapons use dex unless the
    character's str mod would be higher — the tool doesn't need to be
    that clever, so we default finesse to dex. Everything else is str.
    """
    tags = set(item.get("tags") or [])
    props = set(item.get("properties") or [])
    if tags & _RANGED_TAGS:
        return "dex"
    if _FINESSE_PROPS & props:
        return "dex"
    return "str"


def _is_proficient_with(character: dict, item: dict) -> bool:
    """Match on weapon name or item ref in ``character.proficiencies``.

    Proficiency strings in character.json can be written as bare names
    (``"longbow"``) or full refs (``"item.longbow"``) — accept both.
    """
    profs = {p.lower() for p in (character.get("proficiencies") or [])}
    name = (item.get("name") or "").lower()
    item_id = (item.get("id") or "").lower()
    short_id = item_id.removeprefix("item.")
    return bool({name, item_id, short_id} & profs)


def pc_weapon_from_item(character: dict, item: dict) -> dict:
    """Reshape an items.jsonl weapon into the character-style attack spec.

    Output shape matches what `engine.rules.attack.attack` expects for
    character weapons: ``{damage_dice, damage_type, ability, proficient,
    name}``. No ``to_hit`` or ``damage`` keys, so the rules module will
    compute to-hit from ability + proficiency and add the ability mod
    to damage itself.
    """
    return {
        "name": item.get("name", item.get("id", "weapon")),
        "damage_dice": item["damage"],
        "damage_type": item.get("damage_type"),
        "ability": _weapon_ability(item),
        "proficient": _is_proficient_with(character, item),
    }


# ---------------------------------------------------------------------------
# target resolution
# ---------------------------------------------------------------------------


class TargetRef:
    """Where a target lives and how to mutate its HP in place.

    Attributes
    ----------
    kind : "player" | "monster" | "npc"
    id   : the catalog ref for monsters/NPCs, "player" for the PC
    ac   : defender AC (pulled from character/catalog)
    name : human-friendly display name
    hp   : {"current": int, "max": int} — may be freshly rolled here
    _spawn_entry : the live dict inside graph.json that we mutate
                   (None for the PC, whose HP lives in character.json)
    """

    def __init__(
        self,
        kind: str,
        id: str,
        ac: int,
        name: str,
        hp: dict,
        spawn_entry: dict | None,
    ):
        self.kind = kind
        self.id = id
        self.ac = int(ac)
        self.name = name
        self.hp = hp
        self._spawn_entry = spawn_entry

    def apply_damage(self, amount: int) -> int:
        """Subtract ``amount`` from current HP (clamped at 0). Return new HP.

        Caller is responsible for persisting the enclosing character/graph
        dict back to disk — we only update the in-memory HP block.
        """
        cur = int(self.hp.get("current", 0))
        cur = max(0, cur - int(amount))
        self.hp["current"] = cur
        if self._spawn_entry is not None:
            self._spawn_entry["hp"] = self.hp
        return cur

    def apply_heal(self, amount: int) -> int:
        """Add ``amount`` to current HP (clamped at max). Return new HP."""
        cur = int(self.hp.get("current", 0))
        mx = int(self.hp.get("max", cur))
        cur = min(mx, cur + int(amount))
        self.hp["current"] = cur
        if self._spawn_entry is not None:
            self._spawn_entry["hp"] = self.hp
        return cur

    def is_dead(self) -> bool:
        return int(self.hp.get("current", 0)) <= 0


def _roll_monster_hp(catalog: dict, rng: _random.Random | None = None) -> dict:
    """Roll a fresh ``{"current": N, "max": N}`` from ``catalog.hp``.

    Accepts both ``"2d6"`` and ``"11 (2d8+2)"`` forms.
    """
    from engine.rules import dice, parser

    raw = catalog.get("hp", 1)
    try:
        expr = parser.parse_hp_expression(raw)
    except Exception:
        expr = "1"
    try:
        val = int(expr)
    except ValueError:
        val = dice.roll(expr, rng=rng)["total"]
    if val < 1:
        val = 1
    return {"current": val, "max": val}


def _match_spawn(spawns: list, target: str) -> tuple[int, dict] | None:
    """Find the first still-alive spawn entry matching ``target``.

    ``target`` may be the catalog ref (``"monster.wolf"``), the bare id
    (``"wolf"``), or the creature's display name (``"wolf"``). If two
    instances share a room, we pick the first with HP>0; the second
    remains unreachable until the first dies (MVP limitation — see
    tools/attack/README.md).
    """
    if not spawns:
        return None
    tgt = target.lower()
    for i, entry in enumerate(spawns):
        ref = entry.get("ref", "")
        if not ref:
            continue
        matches = (
            tgt == ref.lower()
            or tgt == ref.lower().split(".", 1)[-1]
        )
        if not matches:
            cat = _cat.lookup(ref) or {}
            if tgt == (cat.get("name") or "").lower():
                matches = True
        if not matches:
            continue
        hp = entry.get("hp")
        if hp and int(hp.get("current", 0)) <= 0:
            continue  # already dead
        return i, entry
    return None


def resolve_target(
    target: str,
    *,
    character: dict,
    world: dict,
    graph: dict,
    rng: _random.Random | None = None,
) -> TargetRef:
    """Resolve ``target`` to a mutable HP handle.

    The target may be:
      - ``"self"`` / ``"player"`` / the PC's name → the character sheet
      - a monster/NPC ref or short name present in the current room's
        spawn list → mutates that spawn entry in graph.json

    Raises ``LookupError`` if no match is found.
    """
    tgt_raw = (target or "").strip()
    tgt = tgt_raw.lower()
    if not tgt:
        raise LookupError("empty target")

    # ---- player --------------------------------------------------
    pc_name = (character.get("name") or "").lower()
    if tgt in ("self", "player", "me", "pc") or tgt == pc_name:
        hp = character.setdefault("hp", {"current": 1, "max": 1})
        return TargetRef(
            kind="player",
            id="player",
            ac=int(character.get("ac", 10)),
            name=character.get("name", "player"),
            hp=hp,
            spawn_entry=None,
        )

    # ---- current room spawns ------------------------------------
    room_id = world.get("current_room")
    room = (graph.get("rooms") or {}).get(room_id, {}) if room_id else {}
    spawns_block = room.get("spawns") or {}

    for kind, key in (("monster", "monsters"), ("npc", "npcs")):
        entries = spawns_block.get(key) or []
        hit = _match_spawn(entries, tgt_raw)
        if hit is None:
            continue
        _, entry = hit
        ref = entry["ref"]
        cat = _cat.lookup(ref) or {}
        # Instantiate HP on first contact.
        if "hp" not in entry or entry["hp"] is None:
            entry["hp"] = _roll_monster_hp(cat, rng=rng)
        ac = int(cat.get("ac", 10))
        name = cat.get("name", ref)
        return TargetRef(
            kind=kind,
            id=ref,
            ac=ac,
            name=name,
            hp=entry["hp"],
            spawn_entry=entry,
        )

    raise LookupError(f"no target {target!r} in current room")


# ---------------------------------------------------------------------------
# weapon dispatch (name -> statblock or PC shape)
# ---------------------------------------------------------------------------


def resolve_weapon(
    weapon: str,
    *,
    attacker_kind: str,
    attacker_catalog: dict | None,
    character: dict,
) -> tuple[dict, str]:
    """Turn ``weapon`` into an attack spec + a human label.

    - For PC attackers (``attacker_kind == "player"``): try to find the
      weapon in the character's inventory by ref or short name, look up
      the item catalog, and reshape to the character-style spec.
    - For monsters/NPCs: look up the attack on the attacker's stat block
      by name and return it unmodified (it already has to_hit + damage).

    Returns ``(weapon_spec_dict, display_name)``.
    Raises ``LookupError`` on no match.
    """
    w_raw = (weapon or "").strip()
    w = w_raw.lower()
    if not w:
        raise LookupError("no weapon specified")

    if attacker_kind == "player":
        # Scan inventory. Accept ref, short ref, or weapon name.
        inv_refs = [entry.get("ref", "") for entry in character.get("inventory") or []]
        candidates: list[str] = []
        for ref in inv_refs:
            short = ref.removeprefix("item.")
            cat = _cat.lookup_item(ref) or {}
            if w in (ref.lower(), short.lower(), (cat.get("name") or "").lower()):
                candidates.append(ref)
        # If not in inventory, still allow lookup by ref/name from the catalog
        # (DM may narrate an improvised strike with a wielded weapon).
        if not candidates:
            maybe = _cat.lookup_item(w_raw) or _cat.lookup_item(f"item.{w}")
            if maybe:
                candidates.append(maybe["id"])
        if not candidates:
            raise LookupError(f"no weapon {weapon!r} in inventory or items catalog")
        item = _cat.lookup_item(candidates[0]) or {}
        if "damage" not in item:
            raise LookupError(f"item {candidates[0]!r} is not a weapon (no damage)")
        spec = pc_weapon_from_item(character, item)
        return spec, item.get("name", candidates[0])

    # Monster / NPC attack — look up on the stat block.
    atks = (attacker_catalog or {}).get("attacks") or []
    for atk in atks:
        if w == (atk.get("name") or "").lower():
            return dict(atk), atk.get("name", "attack")
    raise LookupError(f"no attack named {weapon!r} on {attacker_kind}")
