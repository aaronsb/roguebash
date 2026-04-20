"""examine — deeper look at a target (room / item / npc / monster).

Target resolution order:
1. Literal "room" / "here" / the current room's id -> long_desc + tags
2. Item in current room's spawns (not yet taken) -> item short_desc + tags
3. Item in inventory -> item short_desc + tags + qty
4. Dropped item in current room -> item short_desc + tags
5. NPC present in current room -> short_desc + species + role + disposition + dialog_hooks
6. Monster present in current room -> short_desc + visible HP status
7. Otherwise: friendly error with suggestions.

HP status for monsters is intentionally fuzzy: "unhurt / wounded /
bloodied / near death" rather than raw numbers, per the prose-bubbling
contract in engine/prompt/README.md (monster exact HP must never
surface to the model).
"""

target = ARGS.get("target")
if not target or not isinstance(target, str):
    _fail("error: missing required arg: target (a room id, item.<id>, npc.<id>, or monster.<id>)", code=2)

world = _load_world()
graph = _load_graph()
rooms = graph.get("rooms", {})
current_id = world.current_room
room = rooms.get(current_id)
if room is None:
    _fail(f"error: current room {current_id!r} not in graph")

# ---- helper: HP status bucket for monsters ----
def _hp_status_from_spec(hp_spec):
    """Map a monster HP spec (int or dice string) to a fuzzy bucket.

    Without per-encounter rolled HP tracking (lane-10 combat will own
    that), we can't compute a live fraction. For pre-combat examination
    we report 'unhurt' — the DM will replace this with a live reading
    during combat via the mechanics tools.
    """
    return "unhurt"


# ---- 1 & 2: room ----
room_aliases = {"room", "here", current_id}
if target in room_aliases:
    world.mark_inspected(current_id)
    _save_world(world)
    name = room.get("name") or current_id
    parts = [f"ROOM: {name} ({current_id})"]
    if room.get("long_desc"):
        parts.append(room["long_desc"])
    elif room.get("short_desc"):
        parts.append(room["short_desc"])
    tags = room.get("tags") or []
    if tags:
        parts.append("Tags: " + ", ".join(tags))
    flags = {k: v for k, v in (room.get("flags") or {}).items() if v}
    if flags:
        parts.append("Flags: " + ", ".join(sorted(flags.keys())))
    result = "\n".join(parts)
    _ledger.tool_call(_ledger_path(), world.turn, "examine", {"target": target}, "room")
    print(result)
    raise SystemExit(0)

rec = world.revealed.get(current_id, {})
taken = set(rec.get("items_taken", []))
dropped = list(rec.get("items_dropped", []))
spawns = room.get("spawns") or {}
room_item_refs = {
    s.get("ref") for s in (spawns.get("items") or []) if s.get("ref") and s.get("ref") not in taken
}
room_item_refs.update(dropped)
room_npc_refs = {s.get("ref") for s in (spawns.get("npcs") or []) if s.get("ref")}
room_monster_refs = {s.get("ref") for s in (spawns.get("monsters") or []) if s.get("ref")}

char = _load_character()
inv_entries = {e.get("ref"): e for e in char.inventory if e.get("ref")}

# ---- 3 & 4: item (room or inventory) ----
if target.startswith("item."):
    in_room = target in room_item_refs
    in_inv = target in inv_entries
    if not in_room and not in_inv:
        _fail(
            f"error: no item {target!r} visible here or in your inventory. "
            f"Try `look` to see what's around or `inventory` to see what you carry."
        )
    entry = _catalog_lookup("items", target) or {}
    name = entry.get("name") or target
    parts = [f"ITEM: {name} ({target})"]
    if in_inv:
        parts.append(f"Carried (qty {inv_entries[target].get('qty', 1)}).")
    elif in_room:
        parts.append("Lying here.")
    if entry.get("short_desc"):
        parts.append(entry["short_desc"])
    tags = entry.get("tags") or []
    if tags:
        parts.append("Tags: " + ", ".join(tags))
    use = entry.get("use")
    if use and isinstance(use, dict):
        eff = use.get("effect")
        if eff:
            parts.append(f"Use: {eff}")
    weight = entry.get("weight")
    if weight is not None:
        parts.append(f"Weight: {weight}")
    result = "\n".join(parts)
    _ledger.tool_call(_ledger_path(), world.turn, "examine", {"target": target}, "item")
    print(result)
    raise SystemExit(0)

# ---- 5: NPC ----
if target.startswith("npc."):
    if target not in room_npc_refs:
        _fail(f"error: no NPC {target!r} here. Try `look` to see who's around.")
    npc = _catalog_lookup("npcs", target) or {}
    # NPCs in npcs.jsonl rarely have a literal `name` field — they're
    # archetypes (species + role). Compose a friendly label.
    label = npc.get("name")
    if not label:
        sp = npc.get("species") or ""
        role = npc.get("role") or ""
        label = (f"{sp} {role}".strip()) or target
    parts = [f"NPC: {label} ({target})"]
    if npc.get("short_desc"):
        parts.append(npc["short_desc"])
    bits = []
    if npc.get("species"):
        bits.append(f"species={npc['species']}")
    if npc.get("role"):
        bits.append(f"role={npc['role']}")
    disposition = npc.get("disposition_default")
    if disposition:
        bits.append(f"disposition={disposition}")
    if npc.get("faction_default"):
        bits.append(f"faction={npc['faction_default']}")
    if bits:
        parts.append(" · ".join(bits))
    hooks = npc.get("dialog_hooks") or []
    if hooks:
        parts.append("Dialog hooks:")
        for h in hooks:
            parts.append(f"  - {h}")
    result = "\n".join(parts)
    _ledger.tool_call(_ledger_path(), world.turn, "examine", {"target": target}, "npc")
    print(result)
    raise SystemExit(0)

# ---- 6: monster ----
if target.startswith("monster."):
    if target not in room_monster_refs:
        _fail(f"error: no creature {target!r} here. Try `look` to see what's around.")
    mon = _catalog_lookup("monsters", target) or {}
    name = mon.get("name") or target
    parts = [f"CREATURE: {name} ({target})"]
    if mon.get("short_desc"):
        parts.append(mon["short_desc"])
    status = _hp_status_from_spec(mon.get("hp"))
    parts.append(f"Condition: {status}")
    tags = mon.get("tags") or []
    if tags:
        parts.append("Tags: " + ", ".join(tags))
    result = "\n".join(parts)
    _ledger.tool_call(_ledger_path(), world.turn, "examine", {"target": target}, "monster")
    print(result)
    raise SystemExit(0)

# ---- fall-through: give the model a helpful nudge ----
_fail(
    f"error: cannot examine {target!r}. "
    f"Targets are 'room'/'here', or an id like item.<x>, npc.<x>, monster.<x>. "
    f"Try `look` to see what's here."
)
