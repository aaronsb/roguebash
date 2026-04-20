# scenario: highland_keep

> **Status: skeleton scaffold.** This scenario exists to prove the
> scenario-packaging model works. It has 4 areas, 6 rooms, 2 factions,
> and 5 NPCs — enough to drive the generator end-to-end and no more.
> Lane 13 (or a follow-up) should flesh this out: more rooms per area,
> a proper mid-tier ramp, interior corridors, and NPCs populated from
> the faction role pools.

## Pitch

High on the old mountain road, past the foothill bells, the Iron Vein
clan's **Highland Keep** has been under siege for three seasons too
long. The besiegers call themselves the **Bone-Banner Horde** — a
loose confederation of raiders under a chieftain who claims to have
eaten the last one. Their standards are painted skulls, and the paint
is not always paint.

The forge inside the keep burns brighter than a forge under siege
should burn. That light is what the Bone-Banner are really here for.

You come up the trail with a pack and a grudge, or a commission, or
nothing at all. The bells above the foothill gate are fouled with old
cobweb and they will not ring for you.

## Tone

Colder and more Beowulf than the barrow_swamp run. A siege has the
tone of a held breath. Dwarves count weapons, jokes are short, debts
are long. The Bone-Banner are not a cackling horde — they are patient
and they are laughing at something the player doesn't yet understand.

## Victory condition

The run ends successfully when the player stands in **the Throne of
Bone (`mountain.throne_of_bone`) with the Bone-Banner chieftain
(`npc.bone_banner_chieftain`) dead**, having:

1. Either **broken the siege** — carried word back to the Highland
   Keep defenders that their chieftain is down, and the keep's gate
   opens from within — victory by lifted siege, good ending.
2. Or **burned the forge** — with the chieftain gone, the keep falls
   to whatever comes next. The player walks out alone. Still a win,
   but the forge-master's ledger has your name in it now, alongside
   the chieftain's.

Either resolution prints the run-summary and deletes the live state.

## Hook (opening narration seed)

> You have come up the foothill trail and the bells above the arch
> have not rung. They are dwarven work, three of them, one cracked,
> and someone has left offerings at the base of the arch: a scrap
> of steel, a wedge of dry cheese, a child's tin soldier with the
> paint gone.
>
> Above you, somewhere up the slope, a horn answers a horn. Neither
> of them is a friendly sound.

## Factional spine

| faction | role |
|---|---|
| `faction.highland_defenders` | The besieged dwarven forge-clan. Wary but not hostile; will trade news and access for real help. |
| `faction.bone_banner` | The besieging horde. Hostile on sight, led by `npc.bone_banner_chieftain`. |

## Scope notes

- **Skeleton rooms** are authored thin: each area's `must_include` list
  effectively *is* the whole area. `rooms.min`/`max` are set low so
  generation doesn't fail on the small pool. A proper flesh-out adds
  5–10 more rooms per area and widens the pool.
- **Items** referenced in NPC `loot_table`s come from
  `_common/items.jsonl`; no `overrides.jsonl` is authored.
- **No NPCs** yet carry a role that matches `faction.bone_banner`'s
  `roles` list *and* appears in enough numbers for
  `factions.py::populate_area` to fill the camp with variety — that's
  the kind of texture that a follow-up lane should add.
- **Biomes used:** mountain (all of it). This scenario intentionally
  lives in one biome so the siege feels claustrophobic. A future
  variant could open a cavern sub-area beneath the keep to add tonal
  contrast.
