"""Tests for engine.generator.

Run with:
    python3 -m unittest engine.generator.tests -v

Coverage per the task spec:
- Same seed → byte-identical graph.json
- Output validates against the graph.json shape in engine/state/README.md
- BFS(start, goal) succeeds in the generated graph
- Every room referenced in macro edges exists in the rooms dict
- Faction refs in area populations resolve to real faction IDs
- Missing catalog refs are skipped, not crashed
"""

from __future__ import annotations

import io
import json
import unittest
from collections import deque
from pathlib import Path

from engine.generator.catalogs import Catalogs, load_catalogs
from engine.generator.compat import compatible, matches_any
from engine.generator.generate import generate
from engine.generator.spawns import resolve_room_spawns


# All tests run against the real scenarios/ directory of the repo.
# The generator is a pure function of (seed, scenario-catalogs, macro_nodes).
_SCENARIOS = Path(__file__).resolve().parent.parent.parent / "scenarios"
_SCENARIO = "barrow_swamp"


def _bfs_reaches(
    adjacency: dict[str, list[str]],
    start: str,
    goal: str,
) -> bool:
    if start == goal:
        return True
    seen = {start}
    q: deque[str] = deque([start])
    while q:
        cur = q.popleft()
        for nxt in adjacency.get(cur, []):
            if nxt in seen:
                continue
            if nxt == goal:
                return True
            seen.add(nxt)
            q.append(nxt)
    return False


def _room_adjacency(graph: dict) -> dict[str, list[str]]:
    """Flatten the per-room exits dict into an adjacency list."""
    adj: dict[str, list[str]] = {}
    for rid, room in graph["rooms"].items():
        neighbors = [v for v in room["exits"].values() if v]
        adj[rid] = sorted(set(neighbors))
    return adj


class TestDeterminism(unittest.TestCase):
    def test_same_seed_byte_identical(self) -> None:
        g1 = generate(seed=42, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        g2 = generate(seed=42, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        s1 = json.dumps(g1, indent=2, sort_keys=True, ensure_ascii=False)
        s2 = json.dumps(g2, indent=2, sort_keys=True, ensure_ascii=False)
        self.assertEqual(s1, s2)

    def test_different_seeds_probably_differ(self) -> None:
        # Not strictly required by the spec, but guards against a bug
        # where we accidentally seed from a constant.
        g1 = generate(seed=1, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        g2 = generate(seed=2, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        s1 = json.dumps(g1, sort_keys=True)
        s2 = json.dumps(g2, sort_keys=True)
        self.assertNotEqual(s1, s2)


class TestSchemaShape(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = generate(seed=1234, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)

    def test_top_level_keys(self) -> None:
        for key in ("seed", "macro", "rooms", "start_area", "goal_area"):
            self.assertIn(key, self.graph, f"missing top-level key: {key}")

    def test_macro_is_list_of_id_neighbors(self) -> None:
        self.assertIsInstance(self.graph["macro"], list)
        for entry in self.graph["macro"]:
            self.assertIn("id", entry)
            self.assertIn("neighbors", entry)
            self.assertIsInstance(entry["neighbors"], list)

    def test_room_has_cardinal_exits(self) -> None:
        for rid, room in self.graph["rooms"].items():
            for d in ("north", "east", "south", "west"):
                self.assertIn(d, room["exits"], f"room {rid} missing exit {d}")

    def test_spawns_are_ref_only(self) -> None:
        # graph.json strips `chance` (rolls done at generation time).
        for rid, room in self.graph["rooms"].items():
            for bucket in ("items", "monsters", "hazards"):
                for entry in room["spawns"][bucket]:
                    self.assertIn("ref", entry)
                    self.assertNotIn(
                        "chance",
                        entry,
                        f"{rid}.{bucket}: chance should be stripped in graph.json",
                    )


class TestMacroIntegrity(unittest.TestCase):
    def test_bfs_start_to_goal_via_rooms(self) -> None:
        graph = generate(seed=7, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        adj = _room_adjacency(graph)
        self.assertTrue(
            _bfs_reaches(adj, graph["start_room"], graph["goal_room"]),
            "BFS from start_room to goal_room failed",
        )

    def test_every_macro_edge_room_exists(self) -> None:
        """For each macro area entry, its declared entrance/exit rooms
        must exist in the global rooms dict (since those are the only
        rooms the macro layer can cross through)."""
        graph = generate(seed=99, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        rooms = graph["rooms"]
        for entry in graph["macro"]:
            aid = entry["id"]
            self.assertIn(entry["entrance_room"], rooms, f"{aid}: entrance missing")
            self.assertIn(entry["exit_room"], rooms, f"{aid}: exit missing")
            # Neighbors are area ids, not room ids — verify each has an area node.
            ids_in_macro = {e["id"] for e in graph["macro"]}
            for neigh in entry["neighbors"]:
                self.assertIn(neigh, ids_in_macro, f"{aid}: neighbor {neigh} not in macro")

    def test_every_room_exit_is_a_real_room(self) -> None:
        graph = generate(seed=11, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        rooms = graph["rooms"]
        for rid, room in rooms.items():
            for d, target in room["exits"].items():
                if target is None:
                    continue
                self.assertIn(target, rooms, f"{rid}.{d} points to missing room {target}")

    def test_room_area_attribution_is_exclusive(self) -> None:
        """Each macro area's declared entrance/exit rooms must be
        attributed to that area in the rooms dict. Regression guard
        against silent room-sharing between areas."""
        graph = generate(seed=42, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        for entry in graph["macro"]:
            aid = entry["id"]
            eid = entry["entrance_room"]
            xid = entry["exit_room"]
            self.assertEqual(
                graph["rooms"][eid]["area"],
                aid,
                f"entrance {eid} attributed to {graph['rooms'][eid]['area']}, not {aid}",
            )
            self.assertEqual(
                graph["rooms"][xid]["area"],
                aid,
                f"exit {xid} attributed to {graph['rooms'][xid]['area']}, not {aid}",
            )


class TestFactionRefs(unittest.TestCase):
    def test_faction_refs_resolve(self) -> None:
        graph = generate(seed=55, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        cat = load_catalogs(_SCENARIOS, _SCENARIO)
        for aid, info in graph["factions"].items():
            for fid in info["claimed_by"]:
                self.assertIn(fid, cat.factions, f"{aid}: unknown faction {fid}")

    def test_every_populated_npc_exists(self) -> None:
        graph = generate(seed=56, scenarios_dir=_SCENARIOS, scenario=_SCENARIO, macro_nodes=10)
        cat = load_catalogs(_SCENARIOS, _SCENARIO)
        for rid, room in graph["rooms"].items():
            for npc_id in room["npcs"]:
                self.assertIn(npc_id, cat.npcs, f"{rid}: unknown npc {npc_id}")


class TestMissingRefsTolerated(unittest.TestCase):
    def test_unresolvable_spawn_ref_is_skipped_not_crashed(self) -> None:
        # Fabricate a tiny in-memory catalog so we can inject a bad ref
        # without touching the real JSONL files.
        import random

        fake_room = {
            "id": "test.room",
            "type": "room",
            "name": "Test",
            "biome": "forest",
            "tier": 0,
            "tags": ["outdoor"],
            "compatible_with": [],
            "short_desc": "",
            "long_desc": "",
            "exits": {"north": None, "east": None, "south": None, "west": None},
            "spawns": {
                "items": [
                    {"ref": "item.lantern", "chance": 1.0},
                    {"ref": "item.DOES_NOT_EXIST", "chance": 1.0},
                ],
                "monsters": [],
                "hazards": [],
            },
            "flags": {},
        }
        cat = Catalogs(
            areas={},
            rooms={"test.room": fake_room},
            factions={},
            npcs={},
            monsters={},
            items={
                "item.lantern": {"id": "item.lantern", "name": "lantern"},
            },
            hazards={},
        )
        rng = random.Random(0)
        resolved = resolve_room_spawns(fake_room, cat, rng)
        refs = [e["ref"] for e in resolved["items"]]
        self.assertIn("item.lantern", refs)
        self.assertNotIn("item.DOES_NOT_EXIST", refs)

    def test_malformed_jsonl_line_does_not_crash_load(self) -> None:
        # Write a tmp scenarios dir with one broken line and verify load.
        import tempfile
        from pathlib import Path as _P

        with tempfile.TemporaryDirectory() as tmp:
            root = _P(tmp)
            common = root / "_common"
            scen = root / "demo"
            common.mkdir()
            scen.mkdir()
            (scen / "areas.jsonl").write_text(
                '{"id":"area.x","type":"area","name":"x","biome":"forest",'
                '"tier":0,"tags":[],"compatible_with":[],'
                '"rooms":{"min":1,"max":1,"pool":[]},'
                '"entrance_rooms":[],"exit_rooms":[]}\n'
                "{not valid json\n"
            )
            (scen / "rooms.jsonl").write_text("")
            (scen / "factions.jsonl").write_text("")
            (scen / "npcs.jsonl").write_text("")
            (common / "monsters.jsonl").write_text("")
            (common / "items.jsonl").write_text("")
            (common / "hazards.jsonl").write_text("")
            cat = load_catalogs(root, "demo")
            self.assertIn("area.x", cat.areas)

    def test_overrides_replace_common_entries_by_id(self) -> None:
        # Write a tmp scenarios layout with an overrides.jsonl that
        # redefines a common item. Scenario entry should win.
        import tempfile
        from pathlib import Path as _P

        with tempfile.TemporaryDirectory() as tmp:
            root = _P(tmp)
            common = root / "_common"
            scen = root / "demo"
            common.mkdir()
            scen.mkdir()
            (common / "monsters.jsonl").write_text("")
            (common / "hazards.jsonl").write_text("")
            (common / "items.jsonl").write_text(
                '{"id":"item.lantern","name":"common lantern","tier":0,'
                '"tags":["light"],"weight":2,"short_desc":"plain"}\n'
            )
            (scen / "areas.jsonl").write_text("")
            (scen / "rooms.jsonl").write_text("")
            (scen / "factions.jsonl").write_text("")
            (scen / "npcs.jsonl").write_text("")
            (scen / "overrides.jsonl").write_text(
                '{"id":"item.lantern","name":"scenario lantern","tier":0,'
                '"tags":["light","unique"],"weight":2,"short_desc":"special"}\n'
            )
            cat = load_catalogs(root, "demo")
            self.assertIn("item.lantern", cat.items)
            self.assertEqual(cat.items["item.lantern"]["name"], "scenario lantern")
            self.assertIn("unique", cat.items["item.lantern"]["tags"])


class TestCompat(unittest.TestCase):
    def test_glob_matches_biome(self) -> None:
        area_swamp = {"id": "area.barrow_swamp", "biome": "swamp", "tags": []}
        self.assertTrue(matches_any(area_swamp, ["swamp.*"]))
        self.assertFalse(matches_any(area_swamp, ["desert.*"]))

    def test_bidirectional_compat(self) -> None:
        a = {"id": "area.a", "biome": "forest", "tags": [], "compatible_with": ["swamp.*"]}
        b = {"id": "area.b", "biome": "swamp", "tags": [], "compatible_with": []}
        self.assertTrue(compatible(a, b))  # a's patterns match b
        # And reversed: no patterns on b, but the rule is OR, so still true.
        self.assertTrue(compatible(b, a))


if __name__ == "__main__":
    unittest.main()
