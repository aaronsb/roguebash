# roguebash

A text-adventure-voiced, 5e-mechanics-backed, procedurally-generated
dungeon crawler where a local LLM plays the DM. State lives on disk as
files — permadeath, save-anywhere, resume-anywhere. Driven through a
pluggable adapter layer so any agent that can do tool calling and
multi-turn loops can run it (sibling project's `agent` by default).

Forked from [forayconsulting/crawledcode](https://github.com/forayconsulting/crawledcode)
and rebuilt top-to-bottom.

## Quick start

Prerequisites:
- Python 3.11+ (for `tomllib`)
- A working agent adapter. Default is `adapters/local/run`, which wraps
  the `agent` script from the sibling
  [**agent-bash**](https://github.com/aaronsb/agent-bash) project —
  a bash-first local LLM stack (ask/askd/agent + MCP-shaped tool
  plugins) built on `llama.cpp-vulkan`. Install it once and roguebash
  (and anything else you write) can reuse the same DM brain.

### Install the agent (one-time)

```sh
git clone git@github.com:aaronsb/agent-bash.git ~/Projects/agent-bash
cd ~/Projects/agent-bash
ln -s "$PWD/ask"   ~/.local/bin/ask
ln -s "$PWD/askd"  ~/.local/bin/askd
ln -s "$PWD/agent" ~/.local/bin/agent
askd download   # fetches the default GGUF (~21 GB)
askd start      # starts the llama-server in the background
```

See the agent-bash README for hardware notes and alternative models.

```sh
git clone git@github.com:aaronsb/roguebash.git
cd roguebash
# optional: symlink for convenience
ln -s "$PWD/bin/delve" ~/.local/bin/delve

# start a run
delve new --scenario barrow_swamp --name Ibri
# → prints a run-id like 4815162342-ibri-202604201813

delve list
delve show <run-id>

# play (requires the adapter to be reachable)
delve play
```

## Commands

```
delve new  [--scenario N] [--seed N] [--name N] [--class C] [--race R]
           [--macro-nodes N]
delve play [<run-id>]         # defaults to most recent alive
delve list                    # all runs, alive and archived
delve show [<run-id>]         # sheet + current room
delve abandon <run-id>        # delete (confirms)
delve help
```

Scenarios live under `scenarios/<name>/`. `--scenario random` picks one
deterministically from the seed.

## Layout

- `bin/delve` — the CLI
- `engine/generator/` — seeded graph procgen (macro + micro + biome-
  adjacency splining + transition rooms)
- `engine/state/` — XDG-backed save files (character, world, graph,
  ledger)
- `engine/rules/` — pure 5e math (d20, ability, checks, attack, HP)
- `engine/prompt/` — per-turn system-prompt composer
- `tools/` — MCP-shaped bash tools the DM agent calls (look, move,
  attack, cast_spell, ...)
- `adapters/` — pluggable agent frontends (local, goose stub)
- `scenarios/` — catalogs (rooms, areas, NPCs, factions, monsters,
  items, hazards)
- `prompts/` — DM voice + mode overlays

## Config

Optional `delve.toml` at the repo root or `$XDG_CONFIG_HOME/roguebash/delve.toml`:

```toml
[agent]
adapter   = "local"   # which adapters/<name>/ to use
max_turns = 12        # per-turn tool-call cap

[generator]
default_scenario    = "barrow_swamp"
default_macro_nodes = 10
```

CLI flags override config.

## Testing

```sh
# unit tests
python3 -m unittest engine.rules.tests engine.state.tests \
                    engine.generator.tests engine.prompt.tests

# end-to-end CLI smoke (no LLM required)
./tests/smoke.sh
```

## Architecture

See `design.md` for the full architecture. The short version:

- **Exploration layer** (text-adventure voice): `look`, `move`,
  `examine`, `take`, `drop`, `use`, `inventory`. Second-person terse
  prose, Scott Adams / Infocom lineage.
- **Mechanics layer** (5e rules): `skill_check`, `save_throw`, `attack`,
  `cast_spell`, `character_sheet`. Tools do the math; model narrates
  the result.
- **State layer** (files, not model memory): `character.json`,
  `world.json`, `graph.json`, `ledger.jsonl` under `$XDG_STATE_HOME/roguebash/<run-id>/`.

Every turn, the model sees: DM voice + mode overlay + rules excerpt +
character sheet + current room prose + faction context + last 5 ledger
events + your input. It never sees the full graph, unvisited rooms,
loot tables, exact monster HP, or internal faction population mixes.

## Design ethos (from the upstream fork)

- **Describe what you do, not what you want to happen.** Say "I press my
  ear to the door" instead of "I roll Perception." The DM calls for
  rolls when mechanics matter.
- **Combat is one option, not the default.** You can fight the monster.
  You can also talk to her. Some of the best sessions end with zero
  arrows fired.
- **Fail forward.** Bad rolls don't dead-end the story. A botched
  Investigation might mean you miss a journal but find something else.
- **Make choices that feel right for your character**, not choices that
  are mechanically optimal.
- **Permadeath.** One life per run. The save file deletes when the
  character dies or the objective is won.
