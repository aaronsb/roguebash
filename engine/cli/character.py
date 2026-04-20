"""Tier-0 character creation — placeholder, not a full 5e pipeline.

Full character creation (starting equipment by class, fighting style,
spellbook, racial sub-traits, etc.) is out of scope for the CLI lane;
this produces a playable sheet that matches `engine/state/README.md`
and is enough to drop into the world.
"""

from __future__ import annotations


_CLASS_DEFAULTS = {
    "ranger":   {"hit_die": 10, "proficiencies": ["longbow", "shortsword", "stealth", "survival"]},
    "fighter":  {"hit_die": 10, "proficiencies": ["longsword", "heavy armor", "athletics"]},
    "rogue":    {"hit_die": 8,  "proficiencies": ["shortsword", "stealth", "sleight of hand"]},
    "wizard":   {"hit_die": 6,  "proficiencies": ["arcana", "investigation"]},
    "cleric":   {"hit_die": 8,  "proficiencies": ["mace", "medium armor", "religion"]},
}
_RACE_DEFAULTS = {
    "halfling":  {"speed": 25},
    "human":     {"speed": 30},
    "dwarf":     {"speed": 25},
    "elf":       {"speed": 30},
    "half-orc":  {"speed": 30},
    "gnome":     {"speed": 25},
}
_STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]


def _stats_order_for(cls: str) -> list[str]:
    if cls in ("ranger", "rogue"):
        return ["dex", "wis", "con", "str", "int", "cha"]
    if cls == "wizard":
        return ["int", "wis", "con", "dex", "cha", "str"]
    if cls == "cleric":
        return ["wis", "cha", "con", "str", "dex", "int"]
    return ["str", "con", "dex", "wis", "int", "cha"]  # fighter + fallback


def make_character(name: str, race: str, cls: str) -> dict:
    """Assemble a level-1 character sheet in the README shape."""
    race = race.lower()
    cls = cls.lower()
    cd = _CLASS_DEFAULTS.get(cls, _CLASS_DEFAULTS["ranger"])
    rd = _RACE_DEFAULTS.get(race, _RACE_DEFAULTS["human"])
    stats = dict(zip(_stats_order_for(cls), _STANDARD_ARRAY))
    con_mod = (stats["con"] - 10) // 2
    hp_max = cd["hit_die"] + con_mod
    return {
        "name": name,
        "race": race,
        "class": cls,
        "level": 1,
        "xp": 0,
        "stats": stats,
        "hp": {"current": hp_max, "max": hp_max},
        "ac": 10 + max((stats["dex"] - 10) // 2, 0),
        "speed": rd["speed"],
        "proficiencies": cd["proficiencies"],
        "inventory": [],
        "status_effects": [],
        "gold": 0,
    }
