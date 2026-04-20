"""use — invoke an item's use-effect from the items catalog.

Items carry a `use` block shaped like:
    {"effect": "<name>", "duration_turns": N?, "consumes": "<ref>|self"}

This tool handles the effects that are purely exploration-layer state:
- `grants_light`: adds the `has_light` status effect to the character.
- `refuel_lantern`: consumes self + requires `item.lantern` in inventory;
  re-applies `has_light`.
- Any other effect with `consumes: "self"`: consume the item and emit a
  best-effort narration; mark deferred effects with a clear TODO marker.

Combat-ish effects (damage, heal-in-combat, etc.) are deferred to the
mechanics lane. We still consume the item if `consumes` is set, so the
economy works; the DM is told what was deferred so narration is honest.
"""

item_ref = ARGS.get("item_ref")
target = ARGS.get("target")
if not item_ref or not isinstance(item_ref, str):
    _fail("error: missing required arg: item_ref", code=2)

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

entry = _catalog_lookup("items", item_ref) or {}
use = entry.get("use")
if not isinstance(use, dict) or not use.get("effect"):
    _fail(
        f"error: {item_ref!r} has no defined use-effect. "
        f"Try `examine {item_ref}` to see what it is."
    )

effect = use.get("effect")
duration = use.get("duration_turns")
consumes = use.get("consumes")

name = entry.get("name") or item_ref
consumed = []
deferred = False
messages = [f"You use the {name}."]

# ---- consumption ----
if consumes == "self":
    char.remove_item(item_ref, qty=1)
    consumed.append(item_ref)
elif isinstance(consumes, str) and consumes:
    # Require the resource in inventory to burn it.
    needed = next(
        (e for e in char.inventory if e.get("ref") == consumes),
        None,
    )
    if needed is None:
        _fail(
            f"error: using {item_ref} requires {consumes} in inventory, "
            f"and you have none."
        )
    char.remove_item(consumes, qty=1)
    consumed.append(consumes)

# ---- effect dispatch ----
if effect == "grants_light":
    char.set_status("has_light")
    dur_note = f" for about {duration} turns" if duration else ""
    messages.append(f"Light fills the space around you{dur_note}.")
elif effect == "refuel_lantern":
    # Consuming the oil flask itself is already done via consumes:self.
    # Ensure the lantern is carried.
    has_lantern = any(e.get("ref") == "item.lantern" for e in char.inventory)
    if not has_lantern:
        _fail("error: you have no lantern to refuel.")
    char.set_status("has_light")
    messages.append("You pour oil into the lantern; the flame steadies.")
elif effect in {"heal", "restore_hp"}:
    # Lane-10 combat math owns real healing — but exploration-layer
    # potions between fights are common enough to handle crudely.
    # TODO(lane-10): route healing through a proper heal() pipeline
    # that rolls dice / respects temporary HP / etc.
    amount = use.get("amount")
    if isinstance(amount, int) and amount > 0:
        new_hp = char.heal(amount)
        _ledger.heal(_ledger_path(), world.turn, "player", amount, source=item_ref)
        messages.append(f"You feel better. (HP now {new_hp}/{char.hp.get('max')})")
    else:
        deferred = True
        messages.append(f"[TODO: {effect} dice rolling deferred to the mechanics lane.]")
else:
    # TODO(later-lane): any effect we don't recognize (combat buffs,
    # spell-like effects, unique items) needs resolution in a lane
    # that owns the rules. We consume the item (if applicable) and
    # tell the DM the effect is pending mechanics.
    deferred = True
    messages.append(
        f"[TODO: effect {effect!r} not yet implemented in the exploration lane; "
        f"the DM should call the mechanics tools to resolve.]"
    )

_save_character(char)
_save_world(world)

result = "\n".join(messages)
_ledger.tool_call(
    _ledger_path(),
    world.turn,
    "use",
    {"item_ref": item_ref, "target": target} if target else {"item_ref": item_ref},
    {
        "effect": effect,
        "consumed": consumed,
        "deferred": deferred,
        "target": target,
    },
)
print(result)
