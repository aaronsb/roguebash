# engine/rules — 5e math

Shared implementation for:
- d20 rolls with advantage/disadvantage
- Ability modifiers from scores
- Skill check resolution (roll + mod vs DC)
- Saving throws
- Attack rolls (to-hit, damage, crits on 20)
- HP, AC, condition tracking

Used by tools under `tools/skill_check`, `tools/save_throw`, `tools/attack`,
`tools/cast_spell`. Tools import these helpers rather than reimplementing.

Keep the helpers small and pure — they take numbers in, return numbers
out. State mutation is the tool's responsibility, not the rule engine's.
