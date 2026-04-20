# scenario: barrow_swamp

## Pitch

The western marches have gone quiet the wrong way. The Crown's writ no
longer reaches past Oak Mill, a farming village that pays the Red Hollow
bandits in grain and silence. The old kings-road has collapsed into
ruin; the Barrow Swamp has reclaimed the waymarkers. Deeper in, a cult
called the Vigil of Ashes gathers at salt-burned cairns and sings down
what little remains, and the King's Crypt — sealed twice, by two
different hands, in two different centuries — is breathing again.

You are one more lone figure on the causeway. The swamp accepts you the
way it accepts anything that wades in.

## Tone

Scott Adams / Infocom bleakness in second person, with M. R. James
patience underneath it. Things are watching — not as a jump scare, as an
ambient fact. Not a single monster wears a name that announces what it
is; beauty, when it happens, is *unsettlingly* precise. Humor is dry and
rare.

## Victory condition

The run ends successfully when the player stands in **the King's Crypt
`tomb.sealed_vault` with the royal seal**, having done one of:

1. **Sealed it again.** The seal itself is the key. Placed on the
   sarcophagus of black glass, it re-closes the vault — from *inside*
   the wards, where the late king meant it to be closed from. The
   player is permitted to walk out the way they came, if the crypt
   lets them.
2. **Opened it.** The cult has wanted this for a generation. Opening
   the vault is a choice; the narration changes. This is a valid win
   if that's the run the player played — it's not the *good* ending,
   but it is an ending.

Either resolution prints the run-summary and deletes the live state.
There is no post-credits.

## Hook (opening narration seed)

> You have walked three days along the old highway. You were told to
> carry a thing that should not exist to a place where it could be
> buried. The man who gave you the commission did not look well. The
> thing in your satchel does not feel like a thing.
>
> Ahead, the road drops. The trees bend inward and the road becomes a
> boardwalk, and the boardwalk becomes a gate, and past the gate —
> the Barrow Swamp. You have been here before, but only in dreams, and
> only ever at dusk.

## Starting kit

Scenario-specific starting inventory is defined in the character-create
flow (see `engine/state/`) — the scenario supplies the narrative hook,
not the rations count. Recommended for a tier-0 start from the
`forest.trailhead` entrance: lantern, bedroll, dagger, and one *item
with weight* — the royal seal (`item.rusted_royal_seal`) — that the
player did not ask for.

## Factional spine

| faction | role in the spine |
|---|---|
| `faction.crown_patrol` | Absent law. The reason the player is needed. |
| `faction.oak_mill` | Neutral informant spine — villagers who will help for kindness, or for grain, but not for coin. |
| `faction.red_hollow` | First-act opposition. Bandits extorting Oak Mill and the highway. |
| `faction.iron_vein_clan` | Optional ally — a dwarven forge-clan who trade and remember debts for seven generations. |
| `faction.dune_wind_caravan` | Wandering ferrymen; can move the player, or the seal, further than legs allow. |
| `faction.greenwarden_circle` | Druidic law of the old covenants; will burn a cult-cairn without asking leave. |
| `faction.ashen_vigil` | Endgame antagonist; wants the vault opened, not sealed. |

## Notes

- **Overrides.** `overrides.jsonl` is not authored for this scenario;
  the unique item `item.rusted_royal_seal` is scenario-agnostic enough
  to live in `_common/items.jsonl`. Future scenarios that want a
  different MacGuffin at the end should use `overrides.jsonl` to
  re-key `item.rusted_royal_seal` to their own object.
- **Set pieces.** Authored rooms flagged `"set_piece"` in
  `rooms.jsonl` (`swamp.witch_hut`, `urban.drowned_cathedral`,
  `cavern.glowworm_cathedral`, `ruin.sunken_library`,
  `desert.glass_oasis`, `mountain.dragons_nest`, `tomb.sealed_vault`,
  `tomb.reliquary_crypt`) are guaranteed one per run because each
  tier's area declares one in `must_include`.
- **Biomes used:** swamp, forest, urban, cavern, ruin, desert,
  mountain, tomb — all eight canonical biomes. See
  `../_common/biomes.md`.
