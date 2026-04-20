# save_game

Explicit snapshot. State already persists atomically after every
mutation, so this tool is mostly UX — the DM calls it so the player
hears "saved at turn N." Re-writes character.json / world.json /
graph.json through the atomic save path (heals any stale `.tmp`
siblings from a prior crash) and emits a `tool_call` ledger event.

## Smoke test

```bash
ROGUEBASH_RUN_DIR=/tmp/rb_smoke echo '{}' | ./tools/save_game/save_game
```
