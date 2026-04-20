"""System-prompt composer.

Implements the prose-bubbling contract documented in
``engine/prompt/README.md``. Called by the delve turn loop to produce
one assembled system prompt per turn.

The composer is the *only* component that pulls prose out of the
scenario catalogs and graph.json into the model's prompt. It is also
the gatekeeper for what does *not* bubble up: the full graph, rooms
the player has not entered, NPC loot tables, exact monster HP, and
internal faction population mixes.

Pure and stdlib-only. No LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.generator.catalogs import load_catalogs
from engine.state import ledger as _ledger
from engine.state.paths import (
    CHARACTER_FILE,
    GRAPH_FILE,
    LEDGER_FILE,
    WORLD_FILE,
)


_MAX_LEDGER_EVENTS = 5


def build_system_prompt(run_dir: str | Path, repo_root: str | Path) -> str:
    """Assemble the per-turn system prompt for `run_dir`.

    Returns a single string, sections separated by ``\\n\\n---\\n\\n``.
    Sections that come up empty are elided so the prompt stays tight.
    """
    run_dir = Path(run_dir)
    repo_root = Path(repo_root)

    character = _read_json(run_dir / CHARACTER_FILE)
    world = _read_json(run_dir / WORLD_FILE)
    graph = _read_json(run_dir / GRAPH_FILE)
    scenario = graph.get("scenario", "barrow_swamp")

    # Load the merged catalog view (scenarios/_common + scenarios/<scenario>).
    catalogs = load_catalogs(repo_root / "scenarios", scenario)

    mode = world.get("mode", "exploration")

    parts: list[str] = []

    _append(parts, _read_text(repo_root / "prompts" / "dm_voice.md"))
    _append(parts, _read_text(repo_root / "prompts" / f"{mode}_mode.md"))
    _append(parts, _rules_excerpt(mode, world, graph, catalogs))
    _append(parts, _render_character(character))
    _append(parts, _render_current_room(world, graph, catalogs))
    _append(parts, _render_room_contents(world, graph, catalogs))
    _append(parts, _render_active_factions(world, graph, catalogs))
    _append(parts, _render_ledger_tail(run_dir))

    return "\n\n---\n\n".join(parts)


# =====================================================================
# Section renderers
# =====================================================================


def _render_character(character: dict) -> str:
    """Dump the character sheet as pretty JSON under a CHARACTER header."""
    return "CHARACTER:\n" + json.dumps(character, indent=2)


def _render_current_room(world: dict, graph: dict, catalogs) -> str:
    """Describe the current room.

    First entry (the revealed record is pristine) → use ``long_desc``.
    Subsequent visits → use ``short_desc``. Always include ambient_desc
    from the containing area, plus the list of known exits.
    """
    current_id = world.get("current_room")
    if not current_id:
        return ""
    graph_rooms: dict = graph.get("rooms", {})
    room = graph_rooms.get(current_id)
    if not room:
        return ""

    # graph.json rooms carry only structural data (exits, spawns, area_id).
    # Prose lives in the catalog entry by id.
    catalog_room = catalogs.rooms.get(current_id, {}) if hasattr(catalogs, "rooms") else {}

    revealed: dict = world.get("revealed", {}).get(current_id, {})
    is_first_entry = not (
        revealed.get("exits_known")
        or revealed.get("inspected")
        or revealed.get("items_taken")
        or revealed.get("items_dropped")
    )

    desc_field = "long_desc" if is_first_entry else "short_desc"
    desc = catalog_room.get(desc_field) or catalog_room.get("short_desc") or ""

    name = catalog_room.get("name") or current_id
    lines: list[str] = [f"ROOM: {name}"]
    if desc:
        lines.append(desc)

    # Ambient from the containing area.
    area_id = room.get("area") or room.get("area_id")
    if area_id:
        area = catalogs.areas.get(area_id, {}) if hasattr(catalogs, "areas") else {}
        ambient = area.get("ambient_desc")
        if ambient:
            lines.append(f"(ambient) {ambient}")

    # Known exits come from world.json — the player has only seen
    # directions they explicitly tried or that were revealed by look.
    known = revealed.get("exits_known") or []
    if known:
        exits = ", ".join(sorted(known))
        lines.append(f"Exits you know: {exits}")
    else:
        # On pristine entry, tell the model which directions *have* an
        # exit at all (without revealing where they lead) so it can
        # describe them. This only shows the cardinal direction keys
        # from graph, never the target room id.
        all_dirs = [d for d, t in (room.get("exits") or {}).items() if t]
        if all_dirs:
            lines.append(f"Exits visible from the room: {', '.join(sorted(all_dirs))}")

    return "\n".join(lines)


def _render_room_contents(world: dict, graph: dict, catalogs) -> str:
    """Items / monsters / NPCs / triggered hazards in the current room."""
    current_id = world.get("current_room")
    if not current_id:
        return ""
    graph_rooms: dict = graph.get("rooms", {})
    room = graph_rooms.get(current_id) or {}
    revealed = world.get("revealed", {}).get(current_id, {})

    items_taken = set(revealed.get("items_taken") or [])
    items_dropped = list(revealed.get("items_dropped") or [])

    lines: list[str] = []

    # Items — visible items from original spawns minus what's been taken,
    # plus anything that's been dropped in the room.
    visible_item_refs = [
        e.get("ref") for e in (room.get("spawns", {}).get("items") or []) if e.get("ref")
    ]
    visible_item_refs = [r for r in visible_item_refs if r not in items_taken] + items_dropped
    for ref in visible_item_refs:
        entry = catalogs.items.get(ref) if hasattr(catalogs, "items") else None
        if not entry:
            continue
        sd = entry.get("short_desc") or entry.get("name") or ref
        lines.append(f"Item: {sd}")

    # Monsters — surface short_desc + name + qualitative HP.
    for spawn in room.get("spawns", {}).get("monsters") or []:
        ref = spawn.get("ref")
        if not ref:
            continue
        entry = catalogs.monsters.get(ref) if hasattr(catalogs, "monsters") else None
        if not entry:
            continue
        name = entry.get("name") or ref
        sd = entry.get("short_desc") or ""
        hp_status = _qualitative_hp(spawn, entry)
        lines.append(f"Monster: {name} — {sd} [{hp_status}]")

    # NPCs — short_desc + name + species + role + disposition + dialog_hooks.
    for spawn in room.get("spawns", {}).get("npcs") or []:
        ref = spawn.get("ref")
        if not ref:
            continue
        entry = catalogs.npcs.get(ref) if hasattr(catalogs, "npcs") else None
        if not entry:
            continue
        name = entry.get("name") or ref
        species = entry.get("species", "?")
        role = entry.get("role", "?")
        disp = entry.get("disposition_default", "neutral")
        sd = entry.get("short_desc") or ""
        hooks = entry.get("dialog_hooks") or []
        block = [f"NPC: {name} ({species} {role}, {disp}) — {sd}"]
        if hooks:
            block.append("  dialog hooks:")
            for h in hooks:
                block.append(f"    - {h}")
        lines.append("\n".join(block))

    # Hazards — surface only if the world has flagged them triggered.
    triggered = set(revealed.get("triggered_hazards") or [])
    for spawn in room.get("spawns", {}).get("hazards") or []:
        ref = spawn.get("ref")
        if not ref or ref not in triggered:
            continue
        entry = catalogs.hazards.get(ref) if hasattr(catalogs, "hazards") else None
        if not entry:
            continue
        sd = entry.get("short_desc") or entry.get("name") or ref
        lines.append(f"Hazard (triggered): {sd}")

    if not lines:
        return ""
    return "ROOM CONTENTS:\n" + "\n".join(lines)


def _render_active_factions(world: dict, graph: dict, catalogs) -> str:
    """Faction context for the area containing the current room."""
    current_id = world.get("current_room")
    if not current_id:
        return ""
    room = (graph.get("rooms") or {}).get(current_id) or {}
    area_id = room.get("area") or room.get("area_id")
    if not area_id:
        return ""

    lines: list[str] = []
    for fid, fac in (catalogs.factions.items() if hasattr(catalogs, "factions") else []):
        home = fac.get("home_areas") or []
        territories = fac.get("territories") or []
        if area_id not in home and area_id not in territories:
            continue
        name = fac.get("name") or fid
        desc = (fac.get("description") or "").strip()
        # Truncate to first sentence of the description — only the essence surfaces.
        essence = desc.split(". ")[0] if desc else ""
        if essence and not essence.endswith("."):
            essence += "."
        disp = (fac.get("relations") or {}).get("player_default") or "neutral"
        alignment = fac.get("alignment")
        tone = f" [{alignment}]" if alignment else ""
        block = [f"Faction: {name}{tone} — player disposition: {disp}"]
        if essence:
            block.append(f"  {essence}")
        lines.append("\n".join(block))

    if not lines:
        return ""
    return "ACTIVE FACTIONS:\n" + "\n".join(lines)


def _render_ledger_tail(run_dir: Path) -> str:
    """Last N ledger events, newest last."""
    path = run_dir / LEDGER_FILE
    try:
        events = _ledger.tail(path, n=_MAX_LEDGER_EVENTS)
    except Exception:
        return ""
    if not events:
        return ""
    lines: list[str] = ["RECENT EVENTS:"]
    for e in events:
        t = e.get("t", "?")
        kind = e.get("type", "?")
        if kind == "narration":
            text = (e.get("text") or "").strip()
            lines.append(f"  [t{t}] narration: {text}")
        elif kind == "tool_call":
            name = e.get("name", "?")
            lines.append(f"  [t{t}] tool:{name}")
        else:
            lines.append(f"  [t{t}] {kind}")
    return "\n".join(lines)


def _rules_excerpt(mode: str, world: dict, graph: dict, catalogs) -> str:
    """Small rules excerpt picked for the current situation.

    For MVP: empty in exploration mode, a short core-resolution nudge
    in combat mode plus the stat blocks of any monsters in the current
    room. The prompt composer should never be the place this grows;
    larger rules windows mean smaller remaining context for play.
    """
    if mode != "combat":
        return ""
    lines: list[str] = [
        "RULES EXCERPT (combat mode):",
        "- Attack: d20 + to_hit vs target AC; nat 20 crits (double damage dice);",
        "  nat 1 auto-misses.",
        "- Damage reduces target HP toward 0; 0 HP = defeated.",
    ]
    # Append stat blocks for monsters in the current room.
    current_id = world.get("current_room")
    if current_id:
        room = (graph.get("rooms") or {}).get(current_id) or {}
        for spawn in room.get("spawns", {}).get("monsters") or []:
            ref = spawn.get("ref")
            entry = (
                catalogs.monsters.get(ref) if hasattr(catalogs, "monsters") else None
            )
            if not entry:
                continue
            attacks = []
            for atk in entry.get("attacks") or []:
                attacks.append(
                    f"{atk.get('name','?')} (to-hit {atk.get('to_hit','?')}, "
                    f"damage {atk.get('damage','?')})"
                )
            lines.append(
                f"- {entry.get('name', ref)}: AC {entry.get('ac','?')}, "
                f"attacks = {', '.join(attacks) if attacks else 'none'}"
            )
    return "\n".join(lines)


# =====================================================================
# Helpers
# =====================================================================


def _append(parts: list[str], section: str) -> None:
    if section and section.strip():
        parts.append(section.rstrip())


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _qualitative_hp(spawn: dict, monster: dict) -> str:
    """Translate a monster's HP into a qualitative bucket for the DM.

    Exact HP must never bubble up (per `engine/prompt/README.md`). We
    return: ``unhurt`` / ``bloodied`` / ``near death`` / ``down``.
    """
    cur = spawn.get("hp_current")
    mx = spawn.get("hp_max")
    if cur is None or mx is None:
        # Fresh encounter — no damage taken yet.
        return "unhurt"
    if cur <= 0:
        return "down"
    if mx <= 0:
        return "unhurt"
    ratio = cur / mx
    if ratio <= 0.25:
        return "near death"
    if ratio <= 0.5:
        return "bloodied"
    return "unhurt"
