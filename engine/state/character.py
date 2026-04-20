"""Character sheet — the player's live state.

The shape matches `engine/state/README.md`. Tools mutate this via the
mutation methods (`take_damage`, `heal`, ...); the dataclass provides
type-checked accessors around the underlying dict-y JSON.

Inventory items are dicts of shape `{"ref": "item.<id>", "qty": N}` per
`scenarios/schema.md`. `add_item` merges on `ref` (so picking up two
torches yields one entry with `qty: 2`), and `remove_item` decrements
(and deletes the entry at 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from . import io as _io
from .paths import CHARACTER_FILE, run_dir


@dataclass
class Character:
    name: str
    race: str
    class_: str  # `class` is reserved
    level: int = 1
    xp: int = 0
    stats: dict[str, int] = field(default_factory=dict)
    hp: dict[str, int] = field(default_factory=lambda: {"current": 1, "max": 1})
    ac: int = 10
    speed: int = 30
    proficiencies: list[str] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    status_effects: list[str] = field(default_factory=list)
    gold: int = 0

    # ---- serialization -------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Render as the JSON shape documented in the README.

        The dataclass attribute `class_` is serialized back to `"class"`.
        """
        d = asdict(self)
        d["class"] = d.pop("class_")
        # Preserve README field ordering for diff-friendly saves.
        ordered = {
            "name": d["name"],
            "race": d["race"],
            "class": d["class"],
            "level": d["level"],
            "xp": d["xp"],
            "stats": d["stats"],
            "hp": d["hp"],
            "ac": d["ac"],
            "speed": d["speed"],
            "proficiencies": d["proficiencies"],
            "inventory": d["inventory"],
            "status_effects": d["status_effects"],
            "gold": d["gold"],
        }
        return ordered

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        """Inverse of `to_dict` — accepts the README shape."""
        data = dict(data)  # don't mutate caller
        if "class" in data and "class_" not in data:
            data["class_"] = data.pop("class")
        # Fill in sane defaults for any missing optional fields.
        return cls(
            name=data["name"],
            race=data["race"],
            class_=data["class_"],
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            stats=data.get("stats", {}),
            hp=data.get("hp", {"current": 1, "max": 1}),
            ac=data.get("ac", 10),
            speed=data.get("speed", 30),
            proficiencies=list(data.get("proficiencies", [])),
            inventory=[dict(e) for e in data.get("inventory", [])],
            status_effects=list(data.get("status_effects", [])),
            gold=data.get("gold", 0),
        )

    # ---- disk ----------------------------------------------------------

    @classmethod
    def load(cls, run_id: str) -> "Character":
        """Load `character.json` for a given run."""
        return cls.from_dict(_io.load_json(run_dir(run_id) / CHARACTER_FILE))

    def save(self, run_id: str) -> None:
        """Atomically save `character.json` for a given run."""
        _io.save_json(run_dir(run_id) / CHARACTER_FILE, self.to_dict())

    @classmethod
    def load_from(cls, path: Path | str) -> "Character":
        """Load from an arbitrary path (useful for tests / tools)."""
        return cls.from_dict(_io.load_json(path))

    def save_to(self, path: Path | str) -> None:
        """Save to an arbitrary path."""
        _io.save_json(path, self.to_dict())

    # ---- mutations -----------------------------------------------------

    def take_damage(self, amount: int) -> int:
        """Subtract `amount` from current HP, clamping at 0.

        Returns the new current HP. Negative `amount` is treated as zero
        (to heal, use `heal`).
        """
        if amount < 0:
            amount = 0
        cur = int(self.hp.get("current", 0))
        cur = max(0, cur - int(amount))
        self.hp["current"] = cur
        return cur

    def heal(self, amount: int) -> int:
        """Add `amount` to current HP, clamping at max.

        Returns the new current HP. Negative `amount` is treated as zero.
        """
        if amount < 0:
            amount = 0
        cur = int(self.hp.get("current", 0))
        mx = int(self.hp.get("max", cur))
        cur = min(mx, cur + int(amount))
        self.hp["current"] = cur
        return cur

    def add_item(self, ref: str, qty: int = 1) -> None:
        """Add `qty` of `ref` to inventory, merging with any existing entry.

        No-op if `qty <= 0`.
        """
        if qty <= 0:
            return
        for entry in self.inventory:
            if entry.get("ref") == ref:
                entry["qty"] = int(entry.get("qty", 0)) + int(qty)
                return
        self.inventory.append({"ref": ref, "qty": int(qty)})

    def remove_item(self, ref: str, qty: int = 1) -> bool:
        """Remove up to `qty` of `ref` from inventory.

        Returns True if any were removed. Drops the entry when qty hits 0.
        If the current qty is less than `qty`, removes what's there and
        returns True (partial remove).
        """
        if qty <= 0:
            return False
        for i, entry in enumerate(self.inventory):
            if entry.get("ref") == ref:
                have = int(entry.get("qty", 0))
                new = have - int(qty)
                if new <= 0:
                    del self.inventory[i]
                else:
                    entry["qty"] = new
                return True
        return False

    def set_status(self, effect: str) -> None:
        """Idempotently add a status effect (e.g. 'poisoned', 'prone')."""
        if effect not in self.status_effects:
            self.status_effects.append(effect)

    def clear_status(self, effect: str) -> bool:
        """Remove a status effect if present. Returns True if removed."""
        try:
            self.status_effects.remove(effect)
            return True
        except ValueError:
            return False
