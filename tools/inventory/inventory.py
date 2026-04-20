"""inventory — snapshot of what the character carries.

Each inventory entry has `ref` + `qty`; we resolve the short_desc from
the items catalog so the DM narrates the flavor, not the ref id. Status
effects and gold round out the picture.

No equipped-slot model is documented in engine/state/README.md for
character.json, so we don't invent one here; if the schema later grows
slots, this tool should surface them.
"""

world = _load_world()
char = _load_character()

lines = [f"INVENTORY ({char.name})"]
if not char.inventory:
    lines.append("  (empty)")
else:
    for entry in char.inventory:
        ref = entry.get("ref", "?")
        qty = entry.get("qty", 1)
        item = _catalog_lookup("items", ref) or {}
        name = item.get("name") or ref
        desc = item.get("short_desc") or ""
        qty_part = f" x{qty}" if qty != 1 else ""
        if desc:
            lines.append(f"  - {name}{qty_part} ({ref}): {desc}")
        else:
            lines.append(f"  - {name}{qty_part} ({ref})")

lines.append(f"Gold: {char.gold}")
if char.status_effects:
    lines.append("Status: " + ", ".join(char.status_effects))

result = "\n".join(lines)
_ledger.tool_call(_ledger_path(), world.turn, "inventory", {}, "ok")
print(result)
