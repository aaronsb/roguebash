# skill_check

Roll a 5e ability check: d20 + ability mod + proficiency (if proficient)
vs a DC. Emits a `skill_check` ledger event.

## Smoke test

```bash
mkdir -p /tmp/rb_smoke
cat > /tmp/rb_smoke/character.json <<'JSON'
{"name":"test","race":"h","class":"r","level":3,
 "stats":{"str":10,"dex":16,"con":12,"int":10,"wis":14,"cha":8},
 "hp":{"current":24,"max":24},"ac":14,"speed":30,
 "proficiencies":["stealth"],"inventory":[],"status_effects":[],"gold":0}
JSON
cat > /tmp/rb_smoke/world.json <<'JSON'
{"current_room":"r0","revealed":{},"mode":"exploration","turn":1}
JSON
echo '{}' > /tmp/rb_smoke/graph.json

ROGUEBASH_RUN_DIR=/tmp/rb_smoke \
  echo '{"ability":"dex","dc":15,"proficient":true}' \
  | ./tools/skill_check/skill_check
```

Expected: a line like `DEX check DC 15: rolled X + 5 (proficient) = Y, <verdict>.`
and a ledger entry in `/tmp/rb_smoke/ledger.jsonl`.
