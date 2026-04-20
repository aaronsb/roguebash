# save_throw

5e saving throw — mechanically identical to `skill_check` (d20 + mod vs
DC), distinct ledger event name. Accepts either a bare ability (`"wis"`)
or a full phrase (`"wisdom save vs fear"`).

## Smoke test

```bash
# (assumes /tmp/rb_smoke is set up per tools/skill_check/README.md)
ROGUEBASH_RUN_DIR=/tmp/rb_smoke \
  echo '{"save_type":"wisdom save vs fear","dc":12}' \
  | ./tools/save_throw/save_throw
```
