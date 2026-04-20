# adapters/ — pluggable agent frontends

Roguebash drives the game loop; an **agent** does the thinking. Rather
than hardcoding which agent, `delve play` reads a config pointing at
one adapter and invokes it per turn.

## The capability contract

Any compatible agent adapter must provide:

| requirement | why |
|---|---|
| **Tool calling** | The mechanics layer is tools, not prose. No tool calls → no dice, no combat, no state mutations. |
| **Multi-turn** | The agent must run its own tool-call loop: call a tool, see the result, possibly call another, then return prose. |
| **System prompt** | The composed system prompt (DM voice + mode + rules excerpt + character sheet + room + ledger tail) must be accepted per turn. |
| **Bounded turns** | Must honor a turn-cap so a runaway tool loop doesn't cost hours or dollars. |
| **16k+ context** | The composed prompt is ~4 KB but leaves room for tools, outputs, and streaming reasoning. |

Adapters that can't meet all five don't fit — e.g. a pure single-shot
LLM CLI with no tool support is excluded by design.

## The adapter protocol

Each adapter is a directory `adapters/<name>/` containing an executable
`run` that takes **no arguments** and reads its context from env vars:

| env var | content |
|---|---|
| `ROGUEBASH_SYSTEM_PROMPT` | full composed system prompt |
| `ROGUEBASH_USER_MESSAGE` | the player's input for this turn |
| `ROGUEBASH_TOOLS_DIR` | absolute path to `tools/` (MCP-shaped scripts) |
| `ROGUEBASH_RUN_DIR` | absolute path to the XDG run dir |
| `ROGUEBASH_SCENARIOS` | absolute path to `scenarios/` |
| `ROGUEBASH_MAX_TURNS` | integer cap on tool-call rounds |

The adapter:
1. Invokes the underlying agent with the given context
2. Runs whatever tool-call loop the agent needs (tool results are
   emitted as `ledger.jsonl` events by the tools themselves, regardless
   of adapter)
3. Prints the final narrated prose to **stdout**
4. Exits 0 on success, non-zero on failure

The adapter is otherwise free to translate however it needs — pass the
system prompt as a flag or on stdin, spin up an MCP server, use a
child process. Roguebash doesn't care, as long as stdout is prose.

## Provided adapters

### `local/` — sibling [agent-bash](https://github.com/aaronsb/agent-bash) `agent`

Default. Wraps our locally-built `agent` script (tool discovery via
directory, multi-turn loop, reasoning toggle). Works against
`askd`-started llama.cpp-vulkan.

### `goose/` — Block's Goose CLI

Sketch only (not yet functional). Goose consumes tools as MCP servers,
so this adapter exposes `tools/` as an MCP endpoint and invokes
`goose run` with that extension configured. Contributions welcome.

## Authoring a new adapter

Drop `adapters/<name>/run` into the repo, make it executable, make
sure it honors the protocol above. Add a short `README.md` in the
same directory noting any agent-specific setup.

To select an adapter, set in `delve.toml`:

```toml
[agent]
adapter = "<name>"
```

(Config file support is part of lane 10 integration.)
