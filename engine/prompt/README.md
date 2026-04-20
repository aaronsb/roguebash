# engine/prompt — system-prompt composer

Builds the system prompt for each turn. Called by `delve play` between
every model invocation.

Inputs (all from the run directory unless noted):
- `prompts/dm_voice.md` (repo-level, fixed persona)
- Mode overlay: either `prompts/exploration_mode.md` or
  `prompts/combat_mode.md`, chosen by `world.json.mode`
- A small rules excerpt — 1–2 KB, picked dynamically (e.g. current
  monster stat block if in combat)
- `character.json`
- Current room block from `world.json[current_room]`
- Last 5 entries from `ledger.jsonl`

Output: one assembled string the runner passes as the `system` message.

Pseudocode:

```python
def build_prompt(run_dir):
    parts = [
        read(REPO / "prompts/dm_voice.md"),
        read(REPO / f"prompts/{mode}_mode.md"),
        rules_excerpt(context),
        "CHARACTER:\n" + read(run_dir / "character.json"),
        "ROOM:\n" + render_room(current_room),
        "RECENT EVENTS:\n" + tail_ledger(5),
    ]
    return "\n\n---\n\n".join(parts)
```

Keep the assembled prompt under ~4 KB — that leaves plenty of context
window for tool calls and the model's response.
