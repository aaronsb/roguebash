---
name: roll
description: "Roll dice for D&D 5e. Supports XdY+Z notation, advantage, disadvantage, ability checks, saves, and attacks."
---

# /roll — Dice Rolling Engine

Parse the user's roll request and execute it using bash. Always show the full breakdown.

## Parsing Rules
- `/roll` or `/roll d20` — roll a single d20
- `/roll XdY` — roll X dice with Y sides (e.g., `/roll 2d6`)
- `/roll XdY+Z` or `/roll XdY-Z` — roll with modifier
- `/roll adv` or `/roll advantage` — roll 2d20, take higher
- `/roll disadv` or `/roll disadvantage` — roll 2d20, take lower
- `/roll check STR +5` — ability check (d20 + modifier)
- `/roll save DEX +3 DC 15` — saving throw with pass/fail
- `/roll attack +7` — attack roll
- `/roll attack +7 adv` — attack roll with advantage
- `/roll init +2` — initiative roll
- `/roll 4d6kh3` — roll 4d6, keep highest 3 (stat generation)
- `/roll stats` — generate a full set of 6 ability scores (4d6 drop lowest x6)

## Execution

Use bash with `$RANDOM` for all rolls. **Always show every die result.** Be transparent.

### Bash Patterns

```bash
# Single d20
R=$((RANDOM % 20 + 1)); echo "🎲 d20: **$R**"

# XdY (e.g., 3d8)
for((i=0;i<X;i++)); do D=$((RANDOM%Y+1)); echo -n "$D "; S=$((S+D)); done; echo "= **$S**"

# XdY+Z
# Roll the dice as above, then add Z to the total

# Advantage (2d20, take higher)
R1=$((RANDOM%20+1)); R2=$((RANDOM%20+1)); BEST=$((R1>R2?R1:R2)); echo "🎲 Advantage: $R1, $R2 → **$BEST**"

# Disadvantage (2d20, take lower)
R1=$((RANDOM%20+1)); R2=$((RANDOM%20+1)); WORST=$((R1<R2?R1:R2)); echo "🎲 Disadvantage: $R1, $R2 → **$WORST**"

# Ability check: d20 + modifier
R=$((RANDOM%20+1)); MOD=5; echo "🎲 d20: $R + $MOD = **$((R+MOD))**"

# Save vs DC
R=$((RANDOM%20+1)); MOD=3; DC=15; T=$((R+MOD))
echo "🎲 Save: d20=$R + $MOD = $T vs DC $DC: $([ $T -ge $DC ] && echo '**PASS**' || echo '**FAIL**')"

# Stat generation: 4d6 drop lowest, x6
for stat in 1 2 3 4 5 6; do
  rolls=(); for((i=0;i<4;i++)); do rolls+=($((RANDOM%6+1))); done
  sorted=($(printf '%s\n' "${rolls[@]}" | sort -n))
  total=$((sorted[1]+sorted[2]+sorted[3]))
  echo "Stat $stat: ${rolls[*]} → drop ${sorted[0]} → **$total**"
done
```

## Output Format

Always show:
1. What was rolled (dice notation)
2. Individual die results
3. Modifiers applied
4. **Final total** (bolded)
5. Pass/fail if a DC was specified
6. "**Natural 20!**" or "**Natural 1!**" for d20 rolls when applicable (including critical hit/miss implications in combat)
