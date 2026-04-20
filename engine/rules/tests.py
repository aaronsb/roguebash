"""Unit tests for ``engine.rules``.

Run with::

    python3 -m unittest engine.rules.tests -v

All tests are stdlib-only. Randomized helpers (`d20`, `roll`, `attack`,
`skill_check`) accept an injected ``random.Random`` which the tests use
to pin outcomes without globally reseeding.
"""

from __future__ import annotations

import random
import unittest

from engine.rules import ability, attack, checks, dice, hp, parser


# ---------------------------------------------------------------------------
# test helpers
# ---------------------------------------------------------------------------


class FakeRandom(random.Random):
    """A ``random.Random`` whose ``randint(1, N)`` drains a pre-seeded queue.

    Lets us pin exactly what each die shows. Any non-``randint`` randomness
    falls through to the base class. If the queue is exhausted we raise so
    the test fails loudly rather than silently reading from the real RNG.
    """

    def __init__(self, faces):
        super().__init__()
        self._faces = list(faces)
        self._i = 0

    def randint(self, a, b):  # type: ignore[override]
        if self._i >= len(self._faces):
            raise AssertionError(
                f"FakeRandom exhausted after {self._i} draws; asked for randint({a}, {b})"
            )
        v = self._faces[self._i]
        self._i += 1
        if not (a <= v <= b):
            raise AssertionError(
                f"FakeRandom face {v} out of range [{a}, {b}] at draw #{self._i}"
            )
        return v

    def drained(self) -> bool:
        return self._i == len(self._faces)


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


class ParserTests(unittest.TestCase):
    def test_parse_signed_int(self):
        self.assertEqual(parser.parse_signed_int("+4"), 4)
        self.assertEqual(parser.parse_signed_int("-1"), -1)
        self.assertEqual(parser.parse_signed_int("0"), 0)
        self.assertEqual(parser.parse_signed_int("7"), 7)
        self.assertEqual(parser.parse_signed_int(3), 3)
        with self.assertRaises(ValueError):
            parser.parse_signed_int("++4")

    def test_parse_dice_term(self):
        t = parser.parse_dice_term("2d6")
        self.assertEqual((t["count"], t["sides"], t["keep"]), (2, 6, None))
        t = parser.parse_dice_term("d20")
        self.assertEqual((t["count"], t["sides"]), (1, 20))
        t = parser.parse_dice_term("2d20kh1")
        self.assertEqual((t["count"], t["sides"], t["keep"], t["keep_n"]), (2, 20, "kh", 1))
        t = parser.parse_dice_term("2d20KL1")
        self.assertEqual(t["keep"], "kl")
        with self.assertRaises(ValueError):
            parser.parse_dice_term("hello")

    def test_parse_dice_expr(self):
        terms = parser.parse_dice_expr("2d6+3")
        self.assertEqual(len(terms), 2)
        self.assertEqual(terms[0][0], 1)
        self.assertEqual(terms[0][1]["count"], 2)
        self.assertEqual(terms[0][1]["sides"], 6)
        self.assertEqual(terms[1], (1, 3))

        terms = parser.parse_dice_expr("1d20-1")
        self.assertEqual(terms[1], (-1, 1))

        # leading sign allowed
        terms = parser.parse_dice_expr("+1d8")
        self.assertEqual(terms[0][0], 1)

        with self.assertRaises(ValueError):
            parser.parse_dice_expr("")
        with self.assertRaises(ValueError):
            parser.parse_dice_expr("2d6+")

    def test_parse_hp_expression(self):
        self.assertEqual(parser.parse_hp_expression(12), "12")
        self.assertEqual(parser.parse_hp_expression("12"), "12")
        self.assertEqual(parser.parse_hp_expression("2d6+2"), "2d6+2")
        self.assertEqual(parser.parse_hp_expression("11 (2d8+2)"), "2d8+2")


# ---------------------------------------------------------------------------
# dice
# ---------------------------------------------------------------------------


class DiceTests(unittest.TestCase):
    def test_d20_rolls_in_range(self):
        # 1000 real rolls, each in [1, 20].
        rng = random.Random(12345)
        for _ in range(1000):
            result = dice.d20(rng=rng)
            self.assertGreaterEqual(result["roll"], 1)
            self.assertLessEqual(result["roll"], 20)
            self.assertEqual(result["total"], result["roll"])  # mod=0
            self.assertEqual(result["nat1"], result["roll"] == 1)
            self.assertEqual(result["nat20"], result["roll"] == 20)

    def test_d20_with_mod(self):
        rng = FakeRandom([15])
        result = dice.d20(mod=3, rng=rng)
        self.assertEqual(result["roll"], 15)
        self.assertEqual(result["total"], 18)
        self.assertEqual(result["mod"], 3)

    def test_d20_advantage_keeps_higher(self):
        # pair of dice: 7, 18 — advantage keeps 18
        rng = FakeRandom([7, 18])
        result = dice.d20(adv=True, rng=rng)
        self.assertEqual(result["rolls"], [7, 18])
        self.assertEqual(result["roll"], 18)
        self.assertFalse(result["nat1"])

    def test_d20_disadvantage_keeps_lower(self):
        rng = FakeRandom([20, 4])
        result = dice.d20(dis=True, rng=rng)
        self.assertEqual(result["rolls"], [20, 4])
        self.assertEqual(result["roll"], 4)
        self.assertFalse(result["nat20"])

    def test_d20_adv_and_dis_cancel(self):
        # When both set, only one d20 is rolled — FakeRandom queue length proves it.
        rng = FakeRandom([11])
        result = dice.d20(adv=True, dis=True, rng=rng)
        self.assertEqual(result["rolls"], [11])
        self.assertEqual(result["roll"], 11)
        self.assertTrue(rng.drained())

    def test_roll_simple_expr(self):
        # 2d6 rolls as [4, 5], + 3 = 12
        rng = FakeRandom([4, 5])
        r = dice.roll("2d6+3", rng=rng)
        self.assertEqual(r["total"], 12)
        self.assertEqual(r["terms"][0]["kind"], "dice")
        self.assertEqual(r["terms"][0]["rolls"], [4, 5])
        self.assertEqual(r["terms"][1], {"sign": 1, "kind": "mod", "value": 3})

    def test_roll_subtraction(self):
        rng = FakeRandom([6])
        r = dice.roll("1d8-2", rng=rng)
        self.assertEqual(r["total"], 4)

    def test_roll_keep_highest(self):
        # 2d20kh1 with [9, 14] → keep 14
        rng = FakeRandom([9, 14])
        r = dice.roll("2d20kh1", rng=rng)
        self.assertEqual(r["total"], 14)
        self.assertEqual(r["terms"][0]["kept"], [14])

    def test_roll_keep_lowest(self):
        rng = FakeRandom([9, 14])
        r = dice.roll("2d20kl1", rng=rng)
        self.assertEqual(r["total"], 9)


# ---------------------------------------------------------------------------
# ability
# ---------------------------------------------------------------------------


class AbilityTests(unittest.TestCase):
    def test_modifier_formula(self):
        self.assertEqual(ability.modifier(10), 0)
        self.assertEqual(ability.modifier(11), 0)
        self.assertEqual(ability.modifier(12), 1)
        self.assertEqual(ability.modifier(18), 4)
        self.assertEqual(ability.modifier(20), 5)
        # Floor division: 3 → -4 (not -3), matches PHB table.
        self.assertEqual(ability.modifier(3), -4)
        self.assertEqual(ability.modifier(1), -5)
        self.assertEqual(ability.modifier(8), -1)
        self.assertEqual(ability.modifier(30), 10)

    def test_proficiency_bonus_tiers(self):
        for lvl in range(1, 5):
            self.assertEqual(ability.proficiency_bonus(lvl), 2)
        for lvl in range(5, 9):
            self.assertEqual(ability.proficiency_bonus(lvl), 3)
        for lvl in range(9, 13):
            self.assertEqual(ability.proficiency_bonus(lvl), 4)
        for lvl in range(13, 17):
            self.assertEqual(ability.proficiency_bonus(lvl), 5)
        for lvl in range(17, 21):
            self.assertEqual(ability.proficiency_bonus(lvl), 6)

    def test_proficiency_bonus_out_of_range(self):
        with self.assertRaises(ValueError):
            ability.proficiency_bonus(0)
        with self.assertRaises(ValueError):
            ability.proficiency_bonus(21)


# ---------------------------------------------------------------------------
# checks — skill_check & save_throw
# ---------------------------------------------------------------------------


def _pc(level=5, **stats):
    base = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}
    base.update(stats)
    return {"level": level, "stats": base}


class ChecksTests(unittest.TestCase):
    def test_skill_check_pass_and_fail(self):
        # Character with +5 total modifier (dex 20 at level 1, unproficient → +5 flat).
        # Simpler: supply exact mod via stats.
        # dex 14 = +2 mod, proficient at level 5 (+3 prof) → +5 total.
        char = _pc(level=5, dex=14)

        # roll 10 + mod 5 = 15 vs DC 10 → pass
        rng = FakeRandom([10])
        r = checks.skill_check(char, "dex", 10, proficient=True, rng=rng)
        self.assertEqual(r["mod"], 5)
        self.assertEqual(r["roll"], 10)
        self.assertEqual(r["total"], 15)
        self.assertTrue(r["pass"])
        self.assertEqual(r["dc"], 10)
        self.assertEqual(r["ability"], "dex")

        # roll 4 + mod 5 = 9 vs DC 10 → fail
        rng = FakeRandom([4])
        r = checks.skill_check(char, "dex", 10, proficient=True, rng=rng)
        self.assertEqual(r["total"], 9)
        self.assertFalse(r["pass"])

    def test_skill_check_no_proficiency(self):
        char = _pc(level=5, wis=14)  # +2 mod, +3 prof if proficient
        rng = FakeRandom([10])
        r = checks.skill_check(char, "wis", 12, proficient=False, rng=rng)
        # 10 + 2 = 12 vs DC 12 → pass (>=)
        self.assertEqual(r["mod"], 2)
        self.assertEqual(r["total"], 12)
        self.assertTrue(r["pass"])

    def test_skill_check_advantage(self):
        char = _pc(level=1, dex=12)  # +1 mod
        rng = FakeRandom([3, 17])
        r = checks.skill_check(char, "dex", 15, advantage=True, rng=rng)
        # keep 17, + 1 = 18 ≥ 15
        self.assertEqual(r["roll"], 17)
        self.assertEqual(r["total"], 18)
        self.assertTrue(r["pass"])

    def test_save_throw_uses_same_formula(self):
        char = _pc(level=1, con=16)  # +3 mod
        rng = FakeRandom([10])
        r = checks.save_throw(char, "con", 12, proficient=False, rng=rng)
        self.assertEqual(r["mod"], 3)
        self.assertEqual(r["total"], 13)
        self.assertTrue(r["pass"])

    def test_unknown_ability_raises(self):
        char = _pc(level=1)
        with self.assertRaises(ValueError):
            checks.skill_check(char, "luck", 10, rng=FakeRandom([10]))


# ---------------------------------------------------------------------------
# attack
# ---------------------------------------------------------------------------


class AttackTests(unittest.TestCase):
    def test_statblock_weapon_hit(self):
        # Giant frog bite: +3 to hit, 1d6+1 piercing.
        weapon = {"name": "bite", "to_hit": "+3", "damage": "1d6+1", "damage_type": "piercing"}
        # d20 face 15 + 3 = 18 vs AC 12 → hit; damage d6 face 4 + 1 = 5.
        rng = FakeRandom([15, 4])
        r = attack.attack({}, weapon, target_ac=12, rng=rng)
        self.assertTrue(r["hit"])
        self.assertFalse(r["crit"])
        self.assertEqual(r["to_hit_total"], 18)
        self.assertEqual(r["damage"], 5)
        self.assertEqual(r["damage_type"], "piercing")
        self.assertEqual(r["damage_rolls"], [4])

    def test_statblock_weapon_miss(self):
        weapon = {"name": "bite", "to_hit": "+3", "damage": "1d6+1"}
        rng = FakeRandom([5])  # 5 + 3 = 8 < 15
        r = attack.attack({}, weapon, target_ac=15, rng=rng)
        self.assertFalse(r["hit"])
        self.assertEqual(r["damage"], 0)
        self.assertEqual(r["damage_rolls"], [])

    def test_nat20_crit_doubles_damage_dice_not_modifier(self):
        # Weapon: 1d8+3, crit should roll 1d8 twice and add +3 once.
        # d20=20 (nat20), damage dice: 5, 6 → dice total 11 + 3 mod = 14.
        weapon = {"to_hit": "+5", "damage": "1d8+3", "damage_type": "slashing"}
        rng = FakeRandom([20, 5, 6])
        r = attack.attack({}, weapon, target_ac=99, rng=rng)
        self.assertTrue(r["crit"])
        self.assertTrue(r["hit"])  # nat20 always hits
        self.assertEqual(r["damage"], 14)          # 5 + 6 + 3 (not 5 + 6 + 6)
        self.assertEqual(r["damage_rolls"], [5, 6])

    def test_nat20_multi_dice_crit(self):
        # 2d6+2 crit → roll 4 dice total, add +2 once.
        # faces: 3, 4 (first), 5, 6 (crit reroll). Sum dice = 18, + 2 = 20.
        weapon = {"to_hit": "+0", "damage": "2d6+2"}
        rng = FakeRandom([20, 3, 4, 5, 6])
        r = attack.attack({}, weapon, target_ac=5, rng=rng)
        self.assertTrue(r["crit"])
        self.assertEqual(r["damage"], 20)
        self.assertEqual(r["damage_rolls"], [3, 4, 5, 6])

    def test_nat1_auto_miss(self):
        weapon = {"to_hit": "+20", "damage": "1d6"}
        rng = FakeRandom([1])
        r = attack.attack({}, weapon, target_ac=5, rng=rng)
        self.assertFalse(r["hit"])
        self.assertTrue(r["fumble"])
        self.assertEqual(r["damage"], 0)

    def test_character_weapon_uses_stats_and_proficiency(self):
        # Attacker: level 5 (prof +3), str 16 (+3 mod). Weapon: 1d8 slashing,
        # ability=str, proficient. Expected to-hit mod = +6, damage += +3.
        attacker = {"level": 5, "stats": {"str": 16}}
        weapon = {
            "name": "longsword",
            "damage_dice": "1d8",
            "damage_type": "slashing",
            "ability": "str",
            "proficient": True,
        }
        # d20=12 → 12 + 6 = 18 hit vs AC 15; damage die 5 → 5 + 3 = 8
        rng = FakeRandom([12, 5])
        r = attack.attack(attacker, weapon, target_ac=15, rng=rng)
        self.assertEqual(r["to_hit_mod"], 6)
        self.assertEqual(r["to_hit_total"], 18)
        self.assertTrue(r["hit"])
        self.assertEqual(r["damage"], 8)


# ---------------------------------------------------------------------------
# hp
# ---------------------------------------------------------------------------


class HpTests(unittest.TestCase):
    def test_apply_damage_basic(self):
        new = hp.apply_damage({"current": 12, "max": 12}, 5)
        self.assertEqual(new, {"current": 7, "max": 12})

    def test_apply_damage_clamps_at_zero(self):
        new = hp.apply_damage({"current": 3, "max": 12}, 100)
        self.assertEqual(new, {"current": 0, "max": 12})

    def test_apply_damage_does_not_mutate_input(self):
        h = {"current": 10, "max": 10}
        hp.apply_damage(h, 4)
        self.assertEqual(h, {"current": 10, "max": 10})

    def test_heal_basic(self):
        new = hp.heal({"current": 3, "max": 12}, 5)
        self.assertEqual(new, {"current": 8, "max": 12})

    def test_heal_clamps_at_max(self):
        new = hp.heal({"current": 10, "max": 12}, 50)
        self.assertEqual(new, {"current": 12, "max": 12})

    def test_heal_from_zero(self):
        # Stabilization case — any healing brings us above 0.
        new = hp.heal({"current": 0, "max": 10}, 1)
        self.assertEqual(new["current"], 1)

    def test_is_dead(self):
        self.assertFalse(hp.is_dead({"current": 1, "max": 10}))
        self.assertTrue(hp.is_dead({"current": 0, "max": 10}))
        self.assertTrue(hp.is_dead({"current": -3, "max": 10}))

    def test_tuple_shape_roundtrips(self):
        new = hp.apply_damage((8, 10), 3)
        self.assertEqual(new, (5, 10))
        new = hp.heal((5, 10), 20)
        self.assertEqual(new, (10, 10))

    def test_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            hp.apply_damage({"current": 5, "max": 10}, -1)
        with self.assertRaises(ValueError):
            hp.heal({"current": 5, "max": 10}, -1)


if __name__ == "__main__":
    unittest.main()
