"""World state — what the player has revealed so far.

This is *not* the full world graph (that's `graph.json`, the answer key
the model never sees). This file tracks the player's fog-of-war view:
rooms they've entered, exits they know about, whether they've inspected
each room.

Per `engine/state/README.md` the canonical shape is:

    {
      "current_room": "<room_id>",
      "revealed": {
        "<room_id>": {
          "exits_known": [...],
          "inspected": false,
          "items_taken": []
        }
      },
      "turn": <int>
    }

We add a `mode` field for the exploration/combat overlay the prompt
composer cares about; the README shows mode switching on the prompt side
but this is the natural place to persist it between turns.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from . import io as _io
from .paths import WORLD_FILE, run_dir


# Allowed mode values. Callers can pass anything but we validate at the
# entry points to catch typos early.
_MODES = frozenset({"exploration", "combat"})


def _fresh_room_record() -> dict[str, Any]:
    return {"exits_known": [], "inspected": False, "items_taken": []}


@dataclass
class World:
    current_room: str
    revealed: dict[str, dict[str, Any]] = field(default_factory=dict)
    turn: int = 0
    mode: str = "exploration"

    # ---- serialization -------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Preserve README ordering.
        return {
            "current_room": d["current_room"],
            "revealed": d["revealed"],
            "mode": d["mode"],
            "turn": d["turn"],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "World":
        return cls(
            current_room=data["current_room"],
            revealed={
                k: dict(v) for k, v in data.get("revealed", {}).items()
            },
            turn=int(data.get("turn", 0)),
            mode=data.get("mode", "exploration"),
        )

    # ---- disk ----------------------------------------------------------

    @classmethod
    def load(cls, run_id: str) -> "World":
        return cls.from_dict(_io.load_json(run_dir(run_id) / WORLD_FILE))

    def save(self, run_id: str) -> None:
        _io.save_json(run_dir(run_id) / WORLD_FILE, self.to_dict())

    @classmethod
    def load_from(cls, path: Path | str) -> "World":
        return cls.from_dict(_io.load_json(path))

    def save_to(self, path: Path | str) -> None:
        _io.save_json(path, self.to_dict())

    # ---- mutations -----------------------------------------------------

    def _ensure(self, room_id: str) -> dict[str, Any]:
        """Return the record for `room_id`, creating a blank one if needed."""
        rec = self.revealed.get(room_id)
        if rec is None:
            rec = _fresh_room_record()
            self.revealed[room_id] = rec
        return rec

    def enter_room(self, room_id: str) -> None:
        """Move the player to `room_id` and reveal it.

        A room is "revealed" the moment it's entered: its record appears
        in `revealed` (creating a blank one if needed) and `current_room`
        updates.
        """
        self._ensure(room_id)
        self.current_room = room_id

    def reveal_exit(self, direction: str, room_id: str | None = None) -> None:
        """Mark `direction` as a known exit from `room_id` (default: current).

        Idempotent: calling twice does not duplicate the direction.
        """
        rec = self._ensure(room_id or self.current_room)
        exits = rec.setdefault("exits_known", [])
        if direction not in exits:
            exits.append(direction)

    def mark_inspected(self, room_id: str | None = None) -> None:
        """Flip `inspected=True` for `room_id` (default: current)."""
        rec = self._ensure(room_id or self.current_room)
        rec["inspected"] = True

    def mark_item_taken(self, item_ref: str, room_id: str | None = None) -> None:
        """Record that the player pulled `item_ref` out of `room_id`.

        This is what keeps re-entering a room from re-spawning loot the
        player already pocketed.
        """
        rec = self._ensure(room_id or self.current_room)
        taken = rec.setdefault("items_taken", [])
        if item_ref not in taken:
            taken.append(item_ref)

    def set_mode(self, mode: str) -> None:
        """Switch between exploration and combat overlays.

        Raises ValueError on unknown modes rather than silently accepting
        them — the prompt composer picks overlays off this field and a
        typo here would misroute the system prompt.
        """
        if mode not in _MODES:
            raise ValueError(f"unknown mode: {mode!r} (want one of {sorted(_MODES)})")
        self.mode = mode

    def tick_turn(self) -> int:
        """Advance the turn counter by 1 and return the new value."""
        self.turn += 1
        return self.turn
