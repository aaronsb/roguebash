"""Faction-aware NPC population.

Three regimes, per `resources/schema.md` and the generator task spec:

- `home_areas`: every inhabitant drawn from the faction's `population_mix`.
- `territories`: mixed — faction agents plus "local" NPCs. We model
  "local" as: NPCs whose `faction_default` is None (unaligned) or whose
  `faction_default` is another faction that also claims the territory.
- Overlapping territories (e.g. `area.barrow_swamp` is in both
  `faction.red_hollow.territories` and `faction.ashen_vigil.territories`):
  blend the two factions' population_mixes with equal weight and flag
  `factional_tension=True` on that area's rooms.

Per-room population count: deterministic — we assign roughly
`ceil(room_count / 2)` NPCs per area, distributed across the area's
rooms in id-order. A room may carry zero NPCs; this is intentional so
not every room feels crowded.

Everything here is seeded from the supplied rng; no module-level random.
"""

from __future__ import annotations

import random
from typing import Any


# When no faction claim is found, areas still get a small seed of
# "ambient" NPCs whose faction_default is None (if any exist).
AMBIENT_NPCS_PER_AREA = 1


def _index_factions_by_area(
    factions: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Return (home_index, territory_index) mapping area_id -> [faction_id]."""
    home: dict[str, list[str]] = {}
    terr: dict[str, list[str]] = {}
    for fid in sorted(factions.keys()):
        fac = factions[fid]
        for aid in fac.get("home_areas") or []:
            home.setdefault(aid, []).append(fid)
        for aid in fac.get("territories") or []:
            terr.setdefault(aid, []).append(fid)
    return home, terr


def _weighted_role_pick(
    mix: dict[str, float],
    rng: random.Random,
) -> str | None:
    """Pick a role id from the weighted mix. Sorted first for determinism."""
    if not mix:
        return None
    items = sorted(mix.items())
    total = sum(max(0.0, float(w)) for _, w in items)
    if total <= 0:
        return items[0][0]
    r = rng.random() * total
    acc = 0.0
    for role, w in items:
        acc += max(0.0, float(w))
        if r <= acc:
            return role
    return items[-1][0]


def _blend_mix(mixes: list[dict[str, float]]) -> dict[str, float]:
    """Average two (or more) population_mixes. Keys are the union."""
    if not mixes:
        return {}
    if len(mixes) == 1:
        return dict(mixes[0])
    keys = sorted({k for m in mixes for k in m.keys()})
    out: dict[str, float] = {}
    for k in keys:
        out[k] = sum(float(m.get(k, 0.0)) for m in mixes) / len(mixes)
    return out


def _npcs_for_role(
    role: str,
    npcs: dict[str, dict[str, Any]],
    faction_id: str | None,
) -> list[dict[str, Any]]:
    """All NPC entries matching `role`. If `faction_id` given, prefer
    NPCs whose `faction_default` matches; if none match, fall back to
    any role match. Always sorted by id for determinism.
    """
    by_role = [n for n in npcs.values() if n.get("role") == role]
    if faction_id:
        preferred = [n for n in by_role if n.get("faction_default") == faction_id]
        if preferred:
            return sorted(preferred, key=lambda n: n["id"])
    return sorted(by_role, key=lambda n: n["id"])


def _unaligned_npcs(npcs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """NPCs with `faction_default: null` — the 'local color' pool."""
    out = [n for n in npcs.values() if n.get("faction_default") is None]
    return sorted(out, key=lambda n: n["id"])


def populate_area(
    area: dict[str, Any],
    layout: dict[str, Any],
    factions: dict[str, dict[str, Any]],
    npcs: dict[str, dict[str, Any]],
    rng: random.Random,
) -> tuple[dict[str, list[str]], bool, list[str]]:
    """Return ({room_id: [npc_id, ...]}, factional_tension_flag, claiming_factions).

    `layout` is the per-area dict from `micro.instantiate_area()`.
    """
    home, terr = _index_factions_by_area(factions)
    aid = area["id"]

    home_claims = home.get(aid, [])
    terr_claims = terr.get(aid, [])

    claiming = sorted(set(home_claims + terr_claims))
    factional_tension = len(terr_claims) >= 2 or (
        len(home_claims) >= 1 and len(terr_claims) >= 1 and
        any(f not in home_claims for f in terr_claims)
    )

    # Decide the role-weight mix.
    if home_claims:
        mixes = [factions[fid].get("population_mix") or {} for fid in sorted(home_claims)]
        mix = _blend_mix(mixes)
        # home regime: drawn entirely from faction roles
        faction_pool = sorted(home_claims)
        allow_locals = False
    elif terr_claims:
        mixes = [factions[fid].get("population_mix") or {} for fid in sorted(terr_claims)]
        mix = _blend_mix(mixes)
        faction_pool = sorted(terr_claims)
        allow_locals = True
    else:
        mix = {}
        faction_pool = []
        allow_locals = True

    room_ids = list(layout["room_ids"])
    # NPC headcount: about half the rooms, at least 1 if we have a mix.
    target = max(1 if (mix or allow_locals) else 0, len(room_ids) // 2)

    populations: dict[str, list[str]] = {rid: [] for rid in room_ids}
    if not room_ids:
        return populations, factional_tension, claiming

    # Assign per-room NPCs. Deterministic — we iterate a known order and
    # roll only via `rng`.
    locals_pool = _unaligned_npcs(npcs) if allow_locals else []

    # Decide, per slot, whether to draw a faction agent or a local.
    # In home regime always faction. In territory regime 60/40 faction/local
    # (so territories read as "mostly locals with faction agents around").
    for slot in range(target):
        pick_faction = True
        if allow_locals and faction_pool:
            pick_faction = rng.random() < 0.5
        elif allow_locals and not faction_pool:
            pick_faction = False

        npc_id: str | None = None
        if pick_faction and mix:
            # Choose a faction (if multiple) deterministically, then role.
            fac_id = faction_pool[rng.randrange(len(faction_pool))] if faction_pool else None
            role = _weighted_role_pick(mix, rng)
            if role:
                candidates = _npcs_for_role(role, npcs, fac_id)
                if candidates:
                    npc_id = candidates[rng.randrange(len(candidates))]["id"]
        elif locals_pool:
            npc_id = locals_pool[rng.randrange(len(locals_pool))]["id"]

        if not npc_id:
            continue

        # Place in the room with the fewest NPCs so far (deterministic tie-break by id).
        room_order = sorted(
            room_ids,
            key=lambda rid: (len(populations[rid]), rid),
        )
        populations[room_order[0]].append(npc_id)

    return populations, factional_tension, claiming
