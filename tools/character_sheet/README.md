# character_sheet

Render `character.json` as human-readable terminal text. Read-only;
emits no ledger event.

## Smoke test

```bash
# (assumes /tmp/rb_smoke is set up per tools/skill_check/README.md)
ROGUEBASH_RUN_DIR=/tmp/rb_smoke \
  echo '{}' | ./tools/character_sheet/character_sheet
```

Expected output includes header, class/level/XP line, HP/AC/speed/gold
line, ability scores with modifiers, proficiencies, status effects
(if any), and an inventory listing with weapon damage annotations.
