# Combat

Combat is structured into rounds and turns. Each round represents approximately 6 seconds of in-game time. During a round, each participant takes one turn.

---

## Initiative

At the start of combat, every participant rolls initiative to determine the order of turns.

**Formula:** d20 + Dexterity modifier

- Turns proceed in **descending order** (highest initiative acts first).
- **Ties:** The DM decides the order among tied DM-controlled creatures. Tied players decide among themselves, or the DM can have them roll a d20 each (higher goes first).
- Initiative order remains the same from round to round unless a feature changes it.

---

## Surprise

The DM determines whether anyone involved in the combat encounter is surprised. A creature that doesn't notice a threat is surprised at the start of the encounter.

- A surprised creature **cannot move or take actions** on its first turn of combat.
- A surprised creature **cannot take reactions** until its first turn ends.
- A creature can be surprised even if other members of its group are not.

---

## Your Turn

On your turn, you can **move** and **take one action**. You decide the order of your movement and action, and can break up movement before, during, and after your action.

### Components of a Turn
1. **Movement** — Move up to your speed in feet.
2. **Action** — One action (Attack, Cast a Spell, Dash, etc.).
3. **Bonus Action** — Only if a class feature, spell, or ability specifically grants one. Maximum one per turn.
4. **Free Object Interaction** — One free interaction with an object or the environment (open a door, draw a weapon, pick up a dropped item). A second object interaction requires the Use an Object action.

---

## Movement

- You can move up to your **speed** in feet on your turn.
- Movement can be broken up freely around your action and bonus action.
- **Difficult terrain** costs **2 feet of movement per 1 foot moved** (e.g., moving 1 foot through rubble costs 2 feet of your speed).
- Moving through a **nonhostile creature's space** is allowed; moving through a **hostile creature's space** is not (unless the creature is at least two sizes larger or smaller).
- You **cannot willingly end your movement** in another creature's space.
- **Dropping prone** costs no extra movement. **Standing up** costs half your total speed (not half your remaining movement).
- If your speed is reduced to 0 (e.g., by grapple), you cannot stand up from prone.

---

## Actions in Combat

### Attack
Make one melee or ranged attack. Some features (such as Extra Attack) allow multiple attacks as part of the Attack action.

**Melee attack roll:** d20 + Strength modifier + proficiency bonus (if proficient with the weapon)
**Ranged attack roll:** d20 + Dexterity modifier + proficiency bonus (if proficient with the weapon)
**Damage roll:** weapon damage die + ability modifier (same ability used for the attack roll)

Finesse weapons allow the attacker to choose STR or DEX for both attack and damage rolls. Thrown weapons use STR for melee throws (or DEX if finesse).

### Cast a Spell
Cast a spell that has a casting time of 1 action. See spellcasting rules for full details. If you cast a spell as a bonus action, the only other spell you can cast on that turn is a cantrip with a casting time of 1 action.

### Dash
Gain extra movement equal to your speed (after applying modifiers) for the current turn. This effectively doubles your movement for the turn.

### Disengage
Your movement doesn't provoke opportunity attacks for the rest of the turn.

### Dodge
Until the start of your next turn:
- Any attack roll made against you has **disadvantage**, provided you can see the attacker.
- You make Dexterity saving throws with **advantage**.
- You lose this benefit if you are **incapacitated** or if your speed drops to 0.

### Help
You assist another creature in completing a task. The assisted creature gains **advantage on the next ability check** it makes for the task you are helping with, provided it makes the check before the start of your next turn.

Alternatively, you can aid an ally in attacking a creature within 5 feet of you. The ally gains **advantage on its next attack roll** against that creature, provided the attack is made before the start of your next turn.

### Hide
Make a Dexterity (Stealth) check. You must be in a position where you can plausibly hide (behind cover, heavily obscured, etc.). If you succeed, you gain the benefits of being an unseen attacker or target:
- **Unseen attacker:** You have advantage on your attack roll. Hit or miss, your location is revealed when you attack.
- **Unseen target:** Attacks against you have disadvantage. Attacker must guess your location; if wrong, the attack automatically misses.

### Ready
Prepare an action to take later in the round, in response to a specific trigger you define.
- Describe the trigger and the action you will take.
- When the trigger occurs, you can use your **reaction** to take the readied action, or choose to ignore the trigger.
- If you ready a spell, you cast it on your turn (using the slot and concentration if applicable) and hold it with concentration until the trigger. If your concentration breaks before the trigger, the spell is wasted.

### Search
Devote your attention to finding something. Depending on the search, the DM might ask for a Wisdom (Perception) check or an Intelligence (Investigation) check.

### Use an Object
When an object requires your action for its use (such as drinking a potion, applying a healing kit, or using a second object interaction beyond your free one), you take the Use an Object action.

---

## Bonus Actions

You can take a bonus action **only when a special ability, spell, or feature states that you can do something as a bonus action.** You otherwise have no bonus action to take.

- You can take only **one bonus action per turn**.
- You choose when to take the bonus action during your turn, unless the timing is specified.
- Anything that deprives you of your ability to take actions also prevents bonus actions.

---

## Reactions

Certain features, spells, and situations allow you to take a reaction. A reaction is an instant response to a trigger.

- You can take **one reaction per round**. It resets at the **start of your turn**.
- A reaction can occur on your turn or on someone else's turn.
- Common reactions: opportunity attacks, the Shield spell, Counterspell, readied actions.

---

## Making an Attack

### Attack Rolls
**d20 + ability modifier + proficiency bonus** (if proficient with the weapon or spell)

- **Natural 20:** The attack hits regardless of AC. This is a **critical hit** (see below).
- **Natural 1:** The attack misses regardless of modifiers.
- If the total equals or exceeds the target's **Armor Class (AC)**, the attack hits.

### Melee Attacks
- Standard reach: **5 feet** (some weapons have the Reach property, extending to 10 feet).
- Use **Strength** modifier for attack and damage rolls.
- **Finesse** weapons: choose Strength or Dexterity.
- **Unarmed strikes:** 1 + Strength modifier bludgeoning damage (proficient).

### Ranged Attacks
- Each ranged weapon has a **normal range** and a **long range** (e.g., shortbow 80/320).
- Attacking at **long range** imposes **disadvantage** on the attack roll.
- Attacking beyond long range is impossible.
- **Disadvantage if a hostile creature is within 5 feet** of you and can see you (and is not incapacitated).

### Two-Weapon Fighting
When you take the Attack action with a **light melee weapon** in one hand, you can use a **bonus action** to make one attack with a different **light melee weapon** in the other hand.

- You do **not add your ability modifier to the damage** of the bonus attack, unless the modifier is negative.
- The Two-Weapon Fighting fighting style (available to fighters and rangers) removes this restriction, letting you add the ability modifier to the bonus attack's damage.

---

## Opportunity Attacks

When a hostile creature that you can see moves **out of your reach**, you can use your **reaction** to make **one melee attack** against that creature.

- The attack interrupts the provoking creature's movement, occurring just before the creature leaves your reach.
- You can avoid provoking opportunity attacks by taking the **Disengage** action, by being teleported, or by being moved against your will (pushed, pulled, etc. without using your movement, action, or reaction).

---

## Grappling

When you want to grab a creature, you can use the **Attack action** to make a special melee attack: a grapple. You must have at least one free hand.

- **Check:** Your Strength (Athletics) vs. the target's Strength (Athletics) or Dexterity (Acrobatics) (target's choice).
- **Target:** The creature must be **no more than one size larger** than you and within your reach.
- **Success:** The target gains the **grappled** condition (speed becomes 0).
- **Moving a grappled creature:** You can drag or carry the grappled creature, but your speed is halved (unless the creature is two or more sizes smaller than you).

### Escaping a Grapple
The grappled creature can use its **action** to attempt to escape.
- **Check:** Target's Strength (Athletics) or Dexterity (Acrobatics) vs. your Strength (Athletics).

---

## Shoving

Using the **Attack action**, you can make a special melee attack to shove a creature.

- **Target:** Must be no more than **one size larger** than you and within your reach.
- **Check:** Your Strength (Athletics) vs. the target's Strength (Athletics) or Dexterity (Acrobatics) (target's choice).
- **Success:** You either knock the target **prone** or push it **5 feet away** from you (your choice).

---

## Cover

Walls, trees, creatures, and other obstacles can provide cover during combat.

| Cover Type | Bonus | Description |
|-----------|-------|-------------|
| **Half Cover** | +2 to AC and Dexterity saving throws | Obstacle blocks at least half the body (low wall, furniture, another creature) |
| **Three-Quarters Cover** | +5 to AC and Dexterity saving throws | Obstacle blocks about three-quarters of the body (portcullis, arrow slit, thick tree trunk) |
| **Full Cover** | Cannot be targeted directly | Completely concealed by an obstacle. Can still be affected by area effects that reach around the cover |

---

## Damage and Healing

### Damage Types
| Type | Description |
|------|-------------|
| Acid | Corrosive spray, dissolving enzymes |
| Bludgeoning | Blunt force (clubs, falling, constriction) |
| Cold | Infernal chill, icy blasts |
| Fire | Flames, searing heat |
| Force | Pure magical energy (magic missile, spiritual weapon) |
| Lightning | Electrical jolts, arcing bolts |
| Necrotic | Life-draining, withering energy |
| Piercing | Puncturing (arrows, fangs, spears) |
| Poison | Venomous stings, toxic gas |
| Psychic | Mental assault |
| Radiant | Holy light, searing divine energy |
| Slashing | Cutting (swords, axes, claws) |
| Thunder | Concussive burst of sound |

### Resistance, Vulnerability, and Immunity
- **Resistance:** Creature takes **half damage** of that type (applied after all other modifiers).
- **Vulnerability:** Creature takes **double damage** of that type (applied after all other modifiers).
- **Immunity:** Creature takes **no damage** of that type.
- Multiple instances of resistance or vulnerability to the same type do not stack. The damage is halved or doubled only once.

---

## Critical Hits

When an attack roll is a **natural 20**, the attack is a critical hit.

- Roll **all of the attack's damage dice twice** and add them together. Then add any relevant modifiers as normal.
- Example: A longsword crit deals 2d8 + Strength modifier slashing damage instead of 1d8 + STR mod.
- Critical hits only apply to attack rolls, not saving throws or ability checks.

---

## Dropping to 0 Hit Points

### Death Saving Throws
When you start your turn with 0 hit points, you must make a **death saving throw** (a special saving throw not tied to any ability score).

- **Roll a d20.** No modifiers apply (unless a feature says otherwise).
- **10 or higher:** One success.
- **9 or lower:** One failure.
- **Natural 20:** You regain **1 hit point** and become conscious.
- **Natural 1:** Counts as **two failures**.
- **3 successes** (cumulative): You become **stable** (unconscious but no longer dying). You regain 1 HP after 1d4 hours if not healed before then.
- **3 failures** (cumulative): You **die**.
- Successes and failures reset to zero when you regain any hit points.

### Taking Damage at 0 HP
If you take damage while at 0 hit points:
- You automatically suffer one death save failure.
- A critical hit causes two death save failures.
- If the damage equals or exceeds your hit point maximum, you suffer **instant death**.

### Stabilizing a Creature
A creature can be stabilized with a **DC 10 Wisdom (Medicine) check** or by receiving **any amount of healing**.
- A stable creature at 0 HP is unconscious but does not make death saving throws.
- A stable creature that takes damage resumes making death saving throws.
- A stable creature that isn't healed regains 1 HP after 1d4 hours.

### Instant Death
If damage reduces you to 0 hit points and the **remaining damage equals or exceeds your hit point maximum**, you die instantly.

Example: A character with a max of 12 HP currently at 6 HP takes 18 damage. After dropping to 0 HP, there are 12 remaining damage points, which equals the max HP of 12. The character dies instantly.

### Knocking a Creature Out
When an attacker reduces a creature to 0 HP with a **melee attack**, the attacker can choose to knock the creature out. The creature falls **unconscious** and is **stable** rather than dying.

---

## Mounted Combat

### Mounting and Dismounting
- Mounting or dismounting costs **half your movement** (e.g., if your speed is 30 ft, you spend 15 ft to mount or dismount).
- You can mount a creature that is at least one size larger than you and has appropriate anatomy.

### Controlling a Mount
An **intelligent** mount acts independently and has its own turn and initiative.
A **controlled** mount (typical for trained mounts like warhorses):
- Acts on your initiative.
- Can only take the **Dash, Disengage, or Dodge** action on its turn.
- Moves as you direct.

### Forced Dismount
If an effect moves your mount against its will, you must make a **DC 10 Dexterity saving throw** or fall off, landing **prone** in a space within 5 feet.

If your mount is knocked **prone**, you can use your reaction to dismount as it falls and land on your feet. Otherwise, you are dismounted and fall prone in a space within 5 feet.

---

## Underwater Combat

- **Melee weapon attacks:** A creature that doesn't have a swimming speed (natural or granted by magic) has **disadvantage** on melee attack rolls unless the weapon is a dagger, javelin, shortsword, spear, or trident.
- **Ranged weapon attacks:** Automatically **miss** beyond normal range. At normal range, attacks have **disadvantage** unless the weapon is a crossbow, net, or weapon that is thrown like a javelin (including spear and trident).
- Creatures fully immersed in water have **resistance to fire damage**.
