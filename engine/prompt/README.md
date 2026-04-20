# engine/prompt — system-prompt composer

Builds the system prompt for each turn. Called by `delve play` between
every model invocation.

## Inputs

Files read every turn:
- `prompts/dm_voice.md` (fixed persona, loaded once)
- Mode overlay: `prompts/exploration_mode.md` OR `prompts/combat_mode.md`
  (chosen by `world.json.mode`)
- A small rules excerpt (1–2 KB, picked dynamically — e.g. current
  monster stat block if in combat)
- `character.json` — the player's live sheet
- Current room block (see **Prose bubbling** below)
- Last ~5 entries from `ledger.jsonl`

## Output

A single assembled string passed as the `system` message to the model.
Target total size: **under ~4 KB**, to leave context window for tool
calls and the model's response at 16k context.

## Prose bubbling (load-bearing contract)

Every catalog entry in `scenarios/**/*.jsonl` carries prose fields that
exist **for one reason**: to surface into the system prompt when that
entity is contextually relevant. Authors write evocative short lines
because that's what the model will see.

The composer is responsible for **pulling the right prose into the
prompt at the right time**. Specific rules:

### Current room
Every turn, render the current room into the prompt from `graph.json`
(the answer key — `world.json` only tracks *what's revealed*, not the
content itself):

- **First entry** into a room: include `long_desc`
- **Subsequent visits**: include only `short_desc`
- Always include a list of **visible exits** (from `world.json.revealed[room].exits_known`)
- Always include **ambient_desc** from the containing area (gives the
  wider-world texture: "Fat flies bumble through air that smells of
  wet rope.")

### Room contents
Entities present in the room bubble up their short_desc:

- **Items** the player can see — each `item.short_desc` from the catalog
- **Monsters** in the room — each `monster.short_desc` plus name
- **NPCs** in the room — each `npc.short_desc`, name, species, role,
  **disposition** (hostile/wary/neutral/friendly), and — crucially —
  **`dialog_hooks`** (these are the improv anchors; the DM uses them to
  give the NPC a voice without inventing one from scratch)
- **Hazards** that have been triggered or noticed — `hazard.short_desc`
  (untriggered hazards are invisible until a skill check reveals them)

### Faction context
When the current area is controlled by or in the territory of a
faction, include a short faction block:

- `faction.name` + one-sentence essence from `faction.description`
- Player's current `relations.player_default` (hostile/wary/neutral/friendly)
- If alignment is set, include as a tone hint (one letter pair, e.g. `CE`)

Keep it to ~2–3 lines per active faction. The full description stays in
the catalog; only the essence surfaces.

### Combat mode additions
When `world.json.mode == "combat"`:

- For each combatant monster/NPC: full stat line from the catalog
  (name, AC, HP, attacks with to_hit/damage, `short_desc` for voice)
- Initiative order from ledger
- Round number

### Never bubble up
- `graph.json` as a whole — the model must not see the full map
- Rooms the player hasn't entered
- NPC `loot_table` contents — revealed only on death
- Monster exact HP values during combat — reveal "bloodied" at 50%, not numbers
- Faction internal `population_mix` — that's generation-time data

## Pseudocode

```python
def build_system_prompt(run_dir, repo_root):
    world = load_json(run_dir / "world.json")
    graph = load_json(run_dir / "graph.json")
    character = load_json(run_dir / "character.json")
    mode = world.get("mode", "exploration")

    parts = [
        read(repo_root / "prompts/dm_voice.md"),
        read(repo_root / f"prompts/{mode}_mode.md"),
        rules_excerpt(mode, world, graph),
        f"CHARACTER:\n{json.dumps(character, indent=2)}",
        render_current_room(world, graph),       # short/long desc + ambient
        render_room_contents(world, graph),      # items, monsters, NPCs, triggered hazards
        render_active_factions(world, graph),    # if area is under faction control
        render_recent_ledger(run_dir, n=5),
    ]
    return "\n\n---\n\n".join(p for p in parts if p)
```

## Authoring implication for content lanes

When writing prose fields in catalog JSONL files, keep in mind:

- **`short_desc`**: one sentence, present tense, what the player sees at
  a glance. "A hollow-eyed human in mismatched leather, bow ready."
  Not: "A dangerous level-1 bandit with 11 HP and a shortbow."
- **`long_desc`**: 2–4 sentences, surfaces on first room entry. Sensory,
  specific, one interesting detail.
- **`ambient_desc`**: one sentence on the *area* level. Smells, sounds,
  weather, weight of the place. Reused across every room in the area.
- **`dialog_hooks`**: 2–5 one-line prompts (not literal quotes). Each
  hook should communicate attitude + a thing the NPC might say or do.
  "demands gold, bow drawn" — not "DEMAND: The bandit demands gold."
- **`description`** (factions): a short paragraph. Only the essence
  bubbles up per turn, but the full paragraph is there for when the
  player digs in via `examine faction` or similar.

If prose goes in a JSONL field, assume the model will read it. Write it
like you're writing one line of a Scott Adams room description.
