"""save_game — explicit snapshot / UX reassurance.

State is written atomically after every mutation via
`engine.state.io.save_json`, so nothing here is strictly necessary.
But players expect a "save" verb to exist, and the DM voice should be
able to surface a reassuring "saved at turn N" line when asked.

What this tool does:
  1. Re-reads character.json, world.json, graph.json, and writes each
     one back through the atomic-save path — a no-op if they're already
     current, a healer if a prior crash left a stale `.tmp` lying around.
  2. Reports the run-id (directory name) and current turn.

What it does NOT do:
  - Fork the save to a new run-id. Roguebash is permadeath; there are
    no branch-points. Save-scumming is out of scope by design.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from tools._shared import runtime as rt
from engine.state import ledger


def main() -> int:
    _ = rt.read_args()  # no args

    run = rt.run_dir()
    run_id = run.name

    # Round-trip each file so any half-written state is healed.
    try:
        character = rt.load_character()
        rt.save_character(character)
    except FileNotFoundError:
        print("save_game: no character.json in run dir", file=sys.stderr)
        return 2
    try:
        world = rt.load_world()
        rt.save_json(run / "world.json", world)
    except FileNotFoundError:
        print("save_game: no world.json in run dir", file=sys.stderr)
        return 2
    try:
        graph = rt.load_graph()
        rt.save_graph(graph)
    except FileNotFoundError:
        # graph.json being absent is unusual but not fatal for a save.
        graph = None

    turn = int((world or {}).get("turn", 0))

    # Emit a tool_call event so the DM can narrate the save.
    ledger.tool_call(
        run,
        turn,
        name="save_game",
        args={},
        result={"run_id": run_id, "turn": turn, "ok": True},
    )

    print(f"Saved. run_id={run_id}  turn={turn}")
    print(json.dumps({"ok": True, "run_id": run_id, "turn": turn}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
