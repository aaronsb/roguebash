# attack

Full 5e weapon attack: to-hit vs AC, on hit roll damage, emit `attack`
+ `damage` ledger events. On HP reaching 0 emit `death`. Monster HP is
rolled from the catalog's `hp` dice expression on first contact and
persisted into `graph.json` so subsequent attacks decrement the same
instance.

## Smoke test

```bash
# Minimal run dir with a giant rat in the current room.
mkdir -p /tmp/rb_fight
cat > /tmp/rb_fight/character.json <<'JSON'
{"name":"test","race":"h","class":"r","level":3,
 "stats":{"str":10,"dex":16,"con":12,"int":10,"wis":14,"cha":8},
 "hp":{"current":24,"max":24},"ac":14,"speed":30,
 "proficiencies":["longbow","shortsword"],
 "inventory":[{"ref":"item.shortsword","qty":1}],
 "status_effects":[],"gold":0}
JSON
cat > /tmp/rb_fight/world.json <<'JSON'
{"current_room":"r0","revealed":{},"mode":"combat","turn":1}
JSON
cat > /tmp/rb_fight/graph.json <<'JSON'
{"seed":1,"macro":[],
 "rooms":{"r0":{"area":"a","exits":{"north":null,"south":null,"east":null,"west":null},
                "spawns":{"items":[],"monsters":[{"ref":"monster.giant_rat"}],"hazards":[]},
                "flags":{}}}}
JSON

ROGUEBASH_RUN_DIR=/tmp/rb_fight ROGUEBASH_RESOURCES="$PWD/resources" \
  echo '{"target":"giant rat","weapon":"shortsword"}' \
  | ./tools/attack/attack
# Subsequent invocations will hit the same rat (HP persisted in graph.json).
```

## Deferred

- **Resistance / vulnerability / immunity.** Catalogs carry these but
  we pass damage through raw.
- **Multi-instance target disambiguation.** If two giant rats share a
  room, we always hit the first alive one. The caller would need to
  pass an instance index or the DM would need to kill one before
  targeting the other.
- **PC death saves.** At 0 HP we emit `death`; the 5e
  three-save stabilization loop is not implemented.
