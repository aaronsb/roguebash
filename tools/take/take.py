"""take — pocket an item that's visible in the current room.

An item is "visible in the current room" if it's listed in the room's
`spawns.items` (from graph.json) and not already in the room's
`items_taken` set, OR if it's in the room's `items_dropped` list (a
state-schema extension — see the tool-lane report).

On success:
- Character inventory gains +1 of the item (merged via Character.add_item).
- World: item_ref added to `items_taken` (or removed from `items_dropped`
  if it had been dropped here) so subsequent looks hide it.
- Ledger gets an `item_taken` event and a `tool_call` event.
"""

item_ref = ARGS.get("item_ref")
if not item_ref or not isinstance(item_ref, str):
    _fail("error: missing required arg: item_ref (e.g. 'item.lantern')", code=2)

world = _load_world()
graph = _load_graph()
rooms = graph.get("rooms", {})
current = world.current_room
room = rooms.get(current)
if room is None:
    _fail(f"error: current room {current!r} not in graph")

rec = world.revealed.setdefault(
    current,
    {"exits_known": [], "inspected": False, "items_taken": []},
)
taken = set(rec.get("items_taken", []))
dropped = list(rec.get("items_dropped", []))
spawns = room.get("spawns") or {}
spawn_refs = {s.get("ref") for s in (spawns.get("items") or []) if s.get("ref")}

in_spawns_and_available = item_ref in spawn_refs and item_ref not in taken
in_dropped = item_ref in dropped

if not in_spawns_and_available and not in_dropped:
    _fail(
        f"error: no item {item_ref!r} here to take. "
        f"Try `look` to see what's in the room."
    )

# Move it: into inventory, out of visible-in-room.
char = _load_character()
char.add_item(item_ref, qty=1)

if in_dropped:
    # Remove one occurrence from the dropped list.
    dropped.remove(item_ref)
    rec["items_dropped"] = dropped
else:
    world.mark_item_taken(item_ref, current)

_save_character(char)
_save_world(world)

entry = _catalog_lookup("items", item_ref) or {}
name = entry.get("name") or item_ref
result = f"You take the {name}."

_ledger.item_taken(_ledger_path(), world.turn, item_ref, current)
_ledger.tool_call(
    _ledger_path(),
    world.turn,
    "take",
    {"item_ref": item_ref},
    {"taken": item_ref, "from_room": current},
)
print(result)
