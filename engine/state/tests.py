"""Tests for engine.state.

Run with:
    python3 -m unittest engine.state.tests -v

Every test sandboxes `$XDG_STATE_HOME` into a tempdir so we never touch
the real `~/.local/state/roguebash/`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import unittest
from pathlib import Path

from engine.state import archive, character, io, ledger, paths, world


class _XdgSandbox(unittest.TestCase):
    """Base class that isolates XDG_STATE_HOME per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._old_xdg = os.environ.get("XDG_STATE_HOME")
        os.environ["XDG_STATE_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        if self._old_xdg is None:
            os.environ.pop("XDG_STATE_HOME", None)
        else:
            os.environ["XDG_STATE_HOME"] = self._old_xdg


# ---- io --------------------------------------------------------------


class TestIO(_XdgSandbox):

    def test_save_and_load_roundtrip(self):
        data = {"a": 1, "nested": {"b": [1, 2, 3]}, "s": "héllo"}
        target = Path(self._tmp.name) / "x.json"
        io.save_json(target, data)
        self.assertTrue(target.exists())
        self.assertEqual(io.load_json(target), data)

    def test_save_json_is_atomic_via_tmpfile(self):
        """After save_json returns, no stray `.tmp` should remain."""
        target = Path(self._tmp.name) / "y.json"
        io.save_json(target, {"ok": True})
        leftover = list(target.parent.glob("*.tmp"))
        self.assertEqual(leftover, [])

    def test_save_json_creates_parents(self):
        target = Path(self._tmp.name) / "deep" / "nested" / "z.json"
        io.save_json(target, {"deep": True})
        self.assertEqual(io.load_json(target), {"deep": True})

    def test_save_json_overwrites(self):
        target = Path(self._tmp.name) / "over.json"
        io.save_json(target, {"v": 1})
        io.save_json(target, {"v": 2})
        self.assertEqual(io.load_json(target), {"v": 2})

    def test_append_jsonl_parseable(self):
        target = Path(self._tmp.name) / "events.jsonl"
        io.append_jsonl(target, {"a": 1})
        io.append_jsonl(target, {"a": 2})
        io.append_jsonl(target, {"a": 3})
        lines = target.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        parsed = [json.loads(ln) for ln in lines]
        self.assertEqual(parsed, [{"a": 1}, {"a": 2}, {"a": 3}])


# ---- paths -----------------------------------------------------------


class TestPaths(_XdgSandbox):

    def test_state_root_honors_xdg(self):
        self.assertEqual(paths.state_root(), Path(self._tmp.name) / "roguebash")

    def test_state_root_falls_back_to_home(self):
        os.environ.pop("XDG_STATE_HOME", None)
        # Should fall back to ~/.local/state/roguebash — don't create it,
        # just check the shape.
        got = paths.state_root()
        self.assertEqual(got.name, "roguebash")
        self.assertEqual(got.parent.name, "state")

    def test_make_run_id_shape(self):
        when = _dt.datetime(2026, 4, 20, 9, 5)
        rid = paths.make_run_id(4815162342, "Ibri Copperfoot", now=when)
        self.assertEqual(rid, "4815162342-ibri-copperfoot-202604200905")

    def test_make_run_id_slugifies_weird_names(self):
        when = _dt.datetime(2026, 1, 1, 0, 0)
        rid = paths.make_run_id(1, "  ✨Ëlf_Ranger!! ", now=when)
        self.assertTrue(rid.startswith("1-"))
        self.assertIn("elf-ranger", rid)
        self.assertTrue(rid.endswith("202601010000"))

    def test_make_run_id_empty_name_fallback(self):
        when = _dt.datetime(2026, 1, 1, 0, 0)
        rid = paths.make_run_id(7, "!!!", now=when)
        self.assertEqual(rid, "7-player-202601010000")

    def test_list_runs_empty(self):
        self.assertEqual(paths.list_runs(), [])
        self.assertIsNone(paths.latest_run())

    def test_list_runs_sees_alive_and_archive(self):
        # alive
        alive_id = "1-alpha-202601010000"
        paths.run_dir(alive_id).mkdir(parents=True)
        # archived + dead
        dead_id = "2-beta-202601010001"
        d = paths.archive_dir() / dead_id
        d.mkdir(parents=True)
        ledger.death(d / "ledger.jsonl", turn=5, actor="player", cause="leech")

        runs = dict(paths.list_runs())
        self.assertEqual(runs.get(alive_id), "alive")
        self.assertEqual(runs.get(dead_id), "dead")

    def test_list_runs_classifies_victory(self):
        won_id = "3-gamma-202601010002"
        d = paths.archive_dir() / won_id
        d.mkdir(parents=True)
        ledger.victory(d / "ledger.jsonl", turn=42, player="player", goal="ziggurat")
        runs = dict(paths.list_runs())
        self.assertEqual(runs[won_id], "won")

    def test_latest_run_newest_first(self):
        a = paths.run_dir("1-a-202601010000")
        b = paths.run_dir("2-b-202601010001")
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        # Force b newer.
        later = _dt.datetime(2026, 6, 1).timestamp()
        os.utime(b, (later, later))
        self.assertEqual(paths.latest_run(), "2-b-202601010001")


# ---- character -------------------------------------------------------


def _sample_char() -> character.Character:
    return character.Character(
        name="Ibri",
        race="halfling",
        class_="ranger",
        level=1,
        xp=0,
        stats={"str": 10, "dex": 16, "con": 12, "int": 10, "wis": 14, "cha": 8},
        hp={"current": 12, "max": 12},
        ac=14,
        speed=25,
        proficiencies=["longbow", "stealth"],
        inventory=[{"ref": "item.longbow", "qty": 1}],
        status_effects=[],
        gold=0,
    )


class TestCharacter(_XdgSandbox):

    def test_roundtrip_preserves_class_key(self):
        ch = _sample_char()
        d = ch.to_dict()
        self.assertIn("class", d)
        self.assertNotIn("class_", d)
        self.assertEqual(d["class"], "ranger")
        again = character.Character.from_dict(d)
        self.assertEqual(again.class_, "ranger")
        self.assertEqual(again.to_dict(), d)

    def test_save_load_roundtrip_via_run_id(self):
        rid = "1-ibri-202601010000"
        paths.run_dir(rid).mkdir(parents=True)
        ch = _sample_char()
        ch.save(rid)
        loaded = character.Character.load(rid)
        self.assertEqual(loaded.to_dict(), ch.to_dict())

    def test_take_damage_clamps_at_zero(self):
        ch = _sample_char()
        ch.hp = {"current": 5, "max": 12}
        self.assertEqual(ch.take_damage(3), 2)
        self.assertEqual(ch.take_damage(99), 0)
        # Already at 0: stays at 0, doesn't go negative.
        self.assertEqual(ch.take_damage(5), 0)
        self.assertEqual(ch.hp["current"], 0)

    def test_take_damage_ignores_negative(self):
        ch = _sample_char()
        before = ch.hp["current"]
        self.assertEqual(ch.take_damage(-4), before)

    def test_heal_clamps_at_max(self):
        ch = _sample_char()
        ch.hp = {"current": 5, "max": 12}
        self.assertEqual(ch.heal(3), 8)
        self.assertEqual(ch.heal(100), 12)

    def test_add_item_merges_qty(self):
        ch = _sample_char()
        ch.add_item("item.arrows", 10)
        ch.add_item("item.arrows", 5)
        arrows = [e for e in ch.inventory if e["ref"] == "item.arrows"]
        self.assertEqual(len(arrows), 1)
        self.assertEqual(arrows[0]["qty"], 15)

    def test_remove_item_decrements_then_deletes(self):
        ch = _sample_char()
        ch.add_item("item.arrows", 3)
        self.assertTrue(ch.remove_item("item.arrows", 1))
        self.assertEqual(
            [e for e in ch.inventory if e["ref"] == "item.arrows"][0]["qty"], 2
        )
        self.assertTrue(ch.remove_item("item.arrows", 10))
        self.assertFalse(any(e["ref"] == "item.arrows" for e in ch.inventory))
        self.assertFalse(ch.remove_item("item.nope"))

    def test_status_set_clear_idempotent(self):
        ch = _sample_char()
        ch.set_status("poisoned")
        ch.set_status("poisoned")
        self.assertEqual(ch.status_effects.count("poisoned"), 1)
        self.assertTrue(ch.clear_status("poisoned"))
        self.assertFalse(ch.clear_status("poisoned"))


# ---- world -----------------------------------------------------------


class TestWorld(_XdgSandbox):

    def test_enter_room_updates_current_and_reveals(self):
        w = world.World(current_room="swamp.boardwalk_gate")
        self.assertNotIn("swamp.sunken_grove", w.revealed)
        w.enter_room("swamp.sunken_grove")
        self.assertEqual(w.current_room, "swamp.sunken_grove")
        self.assertIn("swamp.sunken_grove", w.revealed)
        rec = w.revealed["swamp.sunken_grove"]
        self.assertEqual(rec["exits_known"], [])
        self.assertFalse(rec["inspected"])

    def test_reveal_exit_is_idempotent(self):
        w = world.World(current_room="r1")
        w.reveal_exit("north")
        w.reveal_exit("north")
        w.reveal_exit("east")
        self.assertEqual(w.revealed["r1"]["exits_known"], ["north", "east"])

    def test_mark_inspected_and_item_taken(self):
        w = world.World(current_room="r1")
        w.mark_inspected()
        w.mark_item_taken("item.lantern")
        self.assertTrue(w.revealed["r1"]["inspected"])
        self.assertEqual(w.revealed["r1"]["items_taken"], ["item.lantern"])

    def test_set_mode_validates(self):
        w = world.World(current_room="r1")
        w.set_mode("combat")
        self.assertEqual(w.mode, "combat")
        with self.assertRaises(ValueError):
            w.set_mode("picnic")

    def test_tick_turn(self):
        w = world.World(current_room="r1")
        self.assertEqual(w.tick_turn(), 1)
        self.assertEqual(w.tick_turn(), 2)
        self.assertEqual(w.turn, 2)

    def test_save_load_roundtrip(self):
        rid = "1-test-202601010000"
        paths.run_dir(rid).mkdir(parents=True)
        w = world.World(current_room="r1")
        w.enter_room("r2")
        w.reveal_exit("south")
        w.tick_turn()
        w.save(rid)
        loaded = world.World.load(rid)
        self.assertEqual(loaded.to_dict(), w.to_dict())


# ---- ledger ----------------------------------------------------------


class TestLedger(_XdgSandbox):

    def test_appends_produce_parseable_jsonl(self):
        p = Path(self._tmp.name) / "ledger.jsonl"
        ledger.narration(p, 1, "You stand at a gate.")
        ledger.tool_call(p, 1, "look", {}, "ok")
        ledger.skill_check(p, 2, "dex", 11, 14, 3, 17, True)
        ledger.damage(p, 2, "player", 3, "piercing", "hazard.leech_pool")

        lines = p.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 4)
        events = [json.loads(ln) for ln in lines]
        self.assertEqual(events[0]["type"], "narration")
        self.assertEqual(events[0]["t"], 1)
        self.assertEqual(events[2]["pass"], True)
        self.assertNotIn("pass_", events[2])
        self.assertEqual(events[3]["type"], "damage")
        # The README event table lists `type` as a damage-event field
        # (damage type: piercing/fire/...), which collides with the
        # outer event-type discriminator. We resolve the collision by
        # serializing the damage type as `damage_type` so the JSON is
        # unambiguous; see ledger.damage docstring.
        self.assertEqual(events[3]["damage_type"], "piercing")
        self.assertEqual(events[3]["amount"], 3)
        self.assertEqual(events[3]["source"], "hazard.leech_pool")

    def test_tail_skips_blank_and_partial(self):
        p = Path(self._tmp.name) / "ledger.jsonl"
        ledger.narration(p, 1, "one")
        ledger.narration(p, 2, "two")
        # Manually inject a bad line + a blank.
        with p.open("a", encoding="utf-8") as fh:
            fh.write("\n")
            fh.write('{"incomplete":')  # no newline, no closing brace
        ledger.narration(p, 3, "three")
        got = ledger.tail(p, n=5)
        self.assertEqual([e["text"] for e in got], ["one", "two", "three"])

    def test_tail_returns_last_n_only(self):
        p = Path(self._tmp.name) / "ledger.jsonl"
        for i in range(10):
            ledger.narration(p, i, f"n{i}")
        got = ledger.tail(p, n=5)
        self.assertEqual([e["text"] for e in got], ["n5", "n6", "n7", "n8", "n9"])

    def test_tail_missing_file(self):
        self.assertEqual(ledger.tail(Path(self._tmp.name) / "nope.jsonl"), [])


# ---- archive ---------------------------------------------------------


class TestArchive(_XdgSandbox):

    def _setup_run(self, rid: str) -> Path:
        d = paths.run_dir(rid)
        d.mkdir(parents=True)
        # Add something in the ledger so turn inference works.
        ledger.narration(d / "ledger.jsonl", 3, "midpoint")
        (d / "character.json").write_text('{"name":"Ibri"}', encoding="utf-8")
        return d

    def test_archive_run_moves_dir(self):
        rid = "1-test-202601010000"
        src = self._setup_run(rid)
        self.assertTrue(src.is_dir())

        dst = archive.archive_run(rid, cause="hazard.leech_pool")

        self.assertFalse(src.exists())
        self.assertTrue(dst.is_dir())
        self.assertEqual(dst, paths.archive_dir() / rid)
        # Files came with it.
        self.assertTrue((dst / "character.json").exists())
        self.assertTrue((dst / "ledger.jsonl").exists())

    def test_archive_run_appends_death_event(self):
        rid = "2-test-202601010000"
        self._setup_run(rid)
        dst = archive.archive_run(rid, cause="hazard.leech_pool")
        events = list(ledger.iter_events(dst / "ledger.jsonl"))
        last = events[-1]
        self.assertEqual(last["type"], "death")
        self.assertEqual(last["cause"], "hazard.leech_pool")
        self.assertEqual(last["actor"], "player")
        # Turn was inferred from the max existing `t` (3).
        self.assertEqual(last["t"], 3)

    def test_archive_run_victory_kind(self):
        rid = "3-test-202601010000"
        self._setup_run(rid)
        dst = archive.archive_run(rid, cause="goal.sunken_library", kind="victory")
        last = list(ledger.iter_events(dst / "ledger.jsonl"))[-1]
        self.assertEqual(last["type"], "victory")
        self.assertEqual(last["goal"], "goal.sunken_library")

    def test_archive_run_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            archive.archive_run("nope-nope-nope", cause="???")

    def test_archive_run_refuses_to_clobber(self):
        rid = "4-test-202601010000"
        self._setup_run(rid)
        archive.archive_run(rid, cause="x")
        # Re-create a new live run with the same id and try again.
        self._setup_run(rid)
        with self.assertRaises(FileExistsError):
            archive.archive_run(rid, cause="x")


if __name__ == "__main__":
    unittest.main()
