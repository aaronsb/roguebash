"""drop — move an item out of inventory and onto the current room's floor.

State-schema note: `world.json.revealed[room].items_taken` exists, but
there's no mirror `items_dropped` field in the documented schema. We add
a `items_dropped` list to the room record here (and `take`/`look` read
it) rather than mutating `graph.json` (the answer key; keep it clean).
This is flagged in the tool-lane report.
"""

item_ref = ARGS.get("item_ref")
if not item_ref or not isinstance(item_ref, str):
    _fail("error: missing required arg: item_ref (e.g. 'item.lantern')", code=2)

world = _load_world()
char = _load_character()

inv_entry = next(
    (e for e in char.inventory if e.get("ref") == item_ref),
    None,
)
if inv_entry is None:
    _fail(
        f"error: you are not carrying {item_ref!r}. "
        f"Use `inventory` to see what you have."
    )

# Remove one (Character.remove_item decrements; deletes at zero).
char.remove_item(item_ref, qty=1)

current = world.current_room
rec = world.revealed.setdefault(
    current,
    {"exits_known": [], "inspected": False, "items_taken": []},
)
dropped = rec.setdefault("items_dropped", [])
# Append even if already present — multiple dropped copies are legal.
dropped.append(item_ref)

_save_character(char)
_save_world(world)

entry = _catalog_lookup("items", item_ref) or {}
name = entry.get("name") or item_ref
result = f"You drop the {name}."

_ledger.item_dropped(_ledger_path(), world.turn, item_ref, current)
_ledger.tool_call(
    _ledger_path(),
    world.turn,
    "drop",
    {"item_ref": item_ref},
    {"dropped": item_ref, "to_room": current},
)
print(result)
