# biomes — canonical set

Every room and area carries a `biome` field. The macro + micro generators
use the biome as the head of a room id (`swamp.boardwalk_gate`) and as a
first-pass compatibility key (`compatible_with: ["swamp.*"]`). Authors
should prefer one of these eight canonical values; the generator's glob
expansion in `engine/generator/micro.py::_expand_pool` keys off the
prefix and knows these.

## The eight canonical biomes

| biome | one-liner |
|---|---|
| `swamp` | Standing water, rot, fog; wetlands, fens, bogs. |
| `forest` | Woodland with living canopy — pine, oak, mixed — damp or dry. |
| `desert` | Arid, sand- or stone-floored, extreme heat or cold nights. |
| `mountain` | High slopes, scree, snowline; above the tree-line or on it. |
| `cavern` | Natural underground — caves, grottos, lava tubes, flooded halls. |
| `tomb` | Carved burial spaces — crypts, ossuaries, reliquaries, barrows. |
| `ruin` | Built work abandoned and half-reclaimed — old roads, walls, temples. |
| `urban` | Inhabited or recently-inhabited built space — villages, towns, camps. |

## Open-set biomes

The canonical eight are a soft authoring convention, not a hard schema.
**Creature `tags` may carry biome-like labels outside the eight** — for
example a `monster.mine_canary` entry tagged `["beast","mine"]` is
legal even though `mine` is not a canonical biome, and spawners will
still match it against rooms whose tags include `mine`.

Follow lane 7's precedent: treat biome as an open set of strings. Keep
the canonical eight as the default for *rooms and areas* (where the
generator's prefix logic depends on them); narrower tags are fine on
spawn catalogs.

Use judgment when a new concept is on the boundary — if you find
yourself wanting `jungle` or `tundra`, consider whether it's really a
variant of `forest` or `mountain` first. A new biome means a new set
of compatibility relationships the generator has to learn.
