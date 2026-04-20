"""move — walk one step in a cardinal (or vertical) direction.

Contract:
- Direction must be a real exit in graph.json for the current room.
- Reveal the exit we came through so the back-path is discoverable.
- Reveal the new room's visible exits (the player can see doorways on arrival).
- If the new room has an `on_enter` hazard, surface its short_desc in the
  result and record it in the tool_call ledger event. Full hazard
  resolution (skill_check + damage application) is deferred — see the
  TODO below; that plumbing needs the mechanics tools lane-10 owns.
"""

direction = ARGS.get("direction")
if not direction:
    _fail("error: missing required arg: direction", code=2)

world = _load_world()
graph = _load_graph()
rooms = graph.get("rooms", {})
current = world.current_room
room = rooms.get(current)
if room is None:
    _fail(f"error: current room {current!r} not in graph")

exits_map = room.get("exits") or {}
target = exits_map.get(direction)
if not target:
    valid = [d for d, dest in exits_map.items() if dest]
    pretty = ", ".join(valid) if valid else "(none)"
    _fail(f"error: no exit {direction!r} from {current}. Available: {pretty}")
if target not in rooms:
    _fail(f"error: target room {target!r} not in graph")

# Confirm the current-room exit (now that we've used it) and move.
world.reveal_exit(direction, current)
world.enter_room(target)

target_room = rooms[target]
# Reveal the back-exit in the new room.
for back_dir, back_dest in (target_room.get("exits") or {}).items():
    if back_dest == current:
        world.reveal_exit(back_dir, target)
        break

# Reveal all visible exits on arrival. A text-adventure entrance shows
# you the doorways; this isn't a stealth problem.
all_target_exits = [
    d for d, dest in (target_room.get("exits") or {}).items() if dest
]
for d in all_target_exits:
    world.reveal_exit(d, target)

name = target_room.get("name") or target
lines = [f"You move {direction} to {name} ({target})."]
if target_room.get("short_desc"):
    lines.append(target_room["short_desc"])
exits_known = world.revealed[target].get("exits_known", [])
lines.append(
    "Exits: " + (", ".join(exits_known) if exits_known else "(none visible)")
)

# Hazard detection on entry. TODO(later-lane): actual resolution needs
# the mechanics tools (skill_check to avoid; damage on fail). For now
# we surface the prose and log the trigger — the DM can narrate the
# warning and prompt the player or invoke mechanics tools directly.
spawns = target_room.get("spawns") or {}
hazards_in_room = [h for h in (spawns.get("hazards") or []) if h.get("ref")]
hazard_events = []
for h in hazards_in_room:
    ref = h.get("ref")
    haz = _catalog_lookup("hazards", ref) or {}
    if haz.get("trigger") == "on_enter":
        desc = haz.get("short_desc") or ref
        lines.append(f"HAZARD ({ref}): {desc}")
        hazard_events.append({
            "ref": ref,
            "trigger": "on_enter",
            "check": haz.get("check"),
        })

result = "\n".join(lines)
_save_world(world)
_ledger.tool_call(
    _ledger_path(),
    world.turn,
    "move",
    {"direction": direction},
    {"to": target, "hazards_triggered": hazard_events},
)
print(result)
