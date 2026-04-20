"""look — emit a narration-friendly snapshot of the current room.

The DM calls this to orient the player. We read the current room from
`world.json`, resolve its content via `graph.json` (the answer key — tools
read it; the prompt composer does not), and filter out items the player
has already taken so loot doesn't "respawn" on re-entry.

Fog-of-war: the room's `exits_known` is authoritative for what directions
the player has observed. On the *first* look in a fresh room, though, we
fall back to the full exit set and then persist those directions as known
— a text-adventure `look` is the canonical "what can I see from here"
verb, not a stealth check.
"""

world = _load_world()
graph = _load_graph()
rooms = graph.get("rooms", {})
current = world.current_room
room = rooms.get(current)
if room is None:
    _fail(f"error: current room {current!r} not in graph")

rec = world.revealed.get(current, {})
known = list(rec.get("exits_known", []))
all_exits = [d for d, dest in (room.get("exits") or {}).items() if dest]
exits = known if known else all_exits
for d in exits:
    world.reveal_exit(d, current)

# Fog-of-war on loot: items already pocketed stay out of the description.
taken = set(rec.get("items_taken", []))
spawns = room.get("spawns") or {}
items = [s for s in (spawns.get("items") or []) if s.get("ref") not in taken]
monsters = list(spawns.get("monsters") or [])
npcs = list(spawns.get("npcs") or [])

# Items the player dropped back into this room. This is a state-schema
# extension (not documented in engine/state/README.md) — flagged in the
# tool implementation report.
dropped = list(rec.get("items_dropped", []))


def _short(catalog, ref):
    e = _catalog_lookup(catalog, ref)
    return (e or {}).get("short_desc") or ref


out = []
room_name = room.get("name") or current
out.append(f"ROOM: {room_name} ({current})")
if room.get("short_desc"):
    out.append(room["short_desc"])
out.append("Exits: " + (", ".join(exits) if exits else "(none visible)"))

visible_items = []
for s in items:
    visible_items.append(_short("items", s.get("ref")))
for ref in dropped:
    visible_items.append(_short("items", ref))
if visible_items:
    out.append("Items:")
    for line in visible_items:
        out.append(f"  - {line}")

if npcs:
    out.append("People:")
    for s in npcs:
        npc = _catalog_lookup("npcs", s.get("ref")) or {}
        label = npc.get("name")
        if not label:
            sp = npc.get("species") or ""
            role = npc.get("role") or ""
            label = (f"{sp} {role}".strip()) or s.get("ref")
        desc = npc.get("short_desc") or ""
        line = f"  - {label}: {desc}" if desc else f"  - {label}"
        out.append(line)

if monsters:
    out.append("Creatures:")
    for s in monsters:
        mon = _catalog_lookup("monsters", s.get("ref")) or {}
        name = mon.get("name") or s.get("ref")
        desc = mon.get("short_desc") or ""
        line = f"  - {name}: {desc}" if desc else f"  - {name}"
        out.append(line)

result = "\n".join(out)
_save_world(world)
_ledger.tool_call(_ledger_path(), world.turn, "look", {}, "ok")
print(result)
