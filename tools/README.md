# tools/ — game tool contract

Tools follow the same MCP-shaped convention as the sibling
[agent-bash](https://github.com/aaronsb/agent-bash) project's `tools/`:

- Each tool lives in its own directory: `tools/<name>/`
- Inside, an executable named `<name>` is the entrypoint
- `<name> --schema` prints its OpenAI function-schema as JSON
- `<name>` (no args) reads a JSON argument blob from stdin, runs, prints
  its result to stdout. Non-zero exit means the tool failed.

The `agent` runner discovers every subdir of `tools/` at startup and
registers it automatically.

## Shared environment (set by `delve play` before invoking `agent`)

- `ROGUEBASH_RUN_DIR` — absolute path to the run's XDG directory
  (contains `character.json`, `world.json`, `graph.json`, `ledger.jsonl`)
- `ROGUEBASH_SCENARIOS` — absolute path to the `scenarios/` directory

Tools read those envs and mutate state files directly. They do not take
the run-id as an argument — the environment is authoritative.

## Tool categories

### Exploration (text-adventure verbs)
- `look` — describe current room (short_desc + visible exits + items)
- `move {direction}` — traverse an exit; writes new `current_room` to
  `world.json`, may fire room-enter hazards
- `examine {target}` — deeper description of a room, item, or feature
- `take {item_ref}` — move item from room to inventory
- `drop {item_ref}` — move item from inventory to room
- `use {item_ref} [target]` — invoke the item's `use.effect`
- `inventory` — list carried items

### Mechanics (5e dice & math)
- `skill_check {ability, dc}` — roll d20 + mod; emit structured result
- `save_throw {save_type, dc}` — saving-throw variant of the above
- `attack {target, weapon}` — full 5e attack flow (to-hit, damage, crit)
- `cast_spell {spell, target}` — apply spell effects, consume slots
- `character_sheet` — dump `character.json` (read-only for the model)

### Meta
- `save_game` — explicit snapshot (though state persists after every
  mutation automatically)

## Authoring checklist

1. Create `tools/<name>/<name>` with `#!/bin/bash` shebang
2. Implement the `--schema` path: print a valid function-schema JSON
3. Read stdin args, do work, print a short human-friendly result
4. Mutate state by writing to files under `$ROGUEBASH_RUN_DIR`
5. Append a structured event to `ledger.jsonl`
6. `chmod +x tools/<name>/<name>`
7. Run `agent --help` from the parent project to confirm registration

## Supporting files

Complex tools (e.g. `attack`, `cast_spell`) may keep helpers in their
directory: lookup tables, spell-effect JSON, Python math helpers. Only
`<name>/<name>` is called by the agent; everything else is implementation
detail.
