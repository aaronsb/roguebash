# cast_spell

Apply a spell's mechanical effect. **MVP: five inline spells** —
`cure_wounds`, `magic_missile`, `shield`, `bless`, `guidance`. A
`spells.jsonl` catalog is pending and will replace the inline table
in `_impl.py`.

## Smoke test

```bash
# (assumes /tmp/rb_fight is set up per tools/attack/README.md)

# Heal the PC.
ROGUEBASH_RUN_DIR=/tmp/rb_fight ROGUEBASH_SCENARIOS="$PWD/scenarios" \
  echo '{"spell":"cure_wounds","target":"self"}' \
  | ./tools/cast_spell/cast_spell

# Damage the giant rat.
ROGUEBASH_RUN_DIR=/tmp/rb_fight ROGUEBASH_SCENARIOS="$PWD/scenarios" \
  echo '{"spell":"magic_missile","target":"giant rat"}' \
  | ./tools/cast_spell/cast_spell

# Apply a status effect.
ROGUEBASH_RUN_DIR=/tmp/rb_fight ROGUEBASH_SCENARIOS="$PWD/scenarios" \
  echo '{"spell":"shield"}' \
  | ./tools/cast_spell/cast_spell
```

## Deferred

- **`spells.jsonl` catalog.** The tool hardcodes five spells for the MVP.
- **Spell slot tracking.** `character.json` doesn't yet declare
  `spell_slots`; if the field is absent we log the cast without
  decrementing (and say so in the output).
- **Attack-roll / save-DC spells.** The MVP spells are all auto-apply;
  a proper catalog will need a spec for "target makes a DEX save"
  (delegates to `save_throw`) and "roll to hit vs AC" (delegates to
  the attack logic).
- **Concentration tracking** and spell-duration countdowns.
