"""Tests for the prose-bubbling contract.

Strategy: build a temp run dir + temp scenarios dir seeded with canary
strings — some strings that MUST appear in the composed prompt, and
some that MUST NOT (e.g. NPC loot tables, exact monster HP, prose from
rooms the player has not entered).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engine.prompt.compose import build_system_prompt


# ---------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


def _build_fixture(tmp: Path) -> tuple[Path, Path]:
    """Return (run_dir, repo_root). Populates both with canary fixtures."""
    repo = tmp / "repo"
    run = tmp / "run"
    (repo / "prompts").mkdir(parents=True)
    (repo / "scenarios" / "_common").mkdir(parents=True)
    (repo / "scenarios" / "testscn").mkdir(parents=True)
    run.mkdir()

    # Prompts.
    (repo / "prompts" / "dm_voice.md").write_text(
        "DM_VOICE_CANARY: narrate terse second person.\n"
    )
    (repo / "prompts" / "exploration_mode.md").write_text(
        "EXPLORATION_OVERLAY_CANARY: no initiative.\n"
    )

    # Catalogs. Current room is "t.alpha" (should surface); "t.beta" is
    # in the graph but never revealed (must NOT surface).
    _write_jsonl(
        repo / "scenarios" / "testscn" / "rooms.jsonl",
        [
            {
                "id": "t.alpha",
                "type": "room",
                "name": "Alpha",
                "biome": "test",
                "short_desc": "SHORT_ALPHA_OK",
                "long_desc": "LONG_ALPHA_OK",
                "compatible_with": [],
            },
            {
                "id": "t.beta",
                "type": "room",
                "name": "Beta",
                "biome": "test",
                "short_desc": "FORBIDDEN_BETA",
                "long_desc": "FORBIDDEN_BETA_LONG",
                "compatible_with": [],
            },
        ],
    )
    _write_jsonl(
        repo / "scenarios" / "testscn" / "areas.jsonl",
        [
            {
                "id": "area.test",
                "type": "area",
                "name": "Test Area",
                "biome": "test",
                "tier": 0,
                "ambient_desc": "AMBIENT_CANARY_OK",
            }
        ],
    )
    _write_jsonl(
        repo / "scenarios" / "_common" / "items.jsonl",
        [
            {
                "id": "item.lamp",
                "name": "lamp",
                "short_desc": "ITEM_LAMP_SHORTDESC_OK",
            }
        ],
    )
    _write_jsonl(
        repo / "scenarios" / "_common" / "monsters.jsonl",
        [
            {
                "id": "monster.rat",
                "name": "rat",
                "short_desc": "MONSTER_RAT_SHORTDESC_OK",
                "ac": 10,
                "hp": "3",
                "attacks": [],
            }
        ],
    )
    _write_jsonl(
        repo / "scenarios" / "_common" / "hazards.jsonl",
        [
            {
                "id": "hazard.pit",
                "name": "pit",
                "short_desc": "HAZARD_PIT_SHORTDESC_UNTRIGGERED",
            }
        ],
    )
    _write_jsonl(
        repo / "scenarios" / "testscn" / "npcs.jsonl",
        [
            {
                "id": "npc.sage",
                "name": "sage",
                "species": "human",
                "role": "sage",
                "disposition_default": "neutral",
                "short_desc": "NPC_SAGE_SHORTDESC_OK",
                "dialog_hooks": ["hook: mentions the DIALOG_HOOK_CANARY"],
                "loot_table": ["FORBIDDEN_LOOT_TABLE_REF"],
            }
        ],
    )
    _write_jsonl(
        repo / "scenarios" / "testscn" / "factions.jsonl",
        [
            {
                "id": "faction.test",
                "name": "Test Faction",
                "tier": 1,
                "description": "FACTION_DESCRIPTION_CANARY_OK. Other sentences not expected.",
                "home_areas": ["area.test"],
                "relations": {"player_default": "wary"},
                "population_mix": {"sage": 1.0},
                "alignment": "TN",
            }
        ],
    )

    # Character.
    (run / "character.json").write_text(
        json.dumps(
            {
                "name": "TestHero",
                "race": "halfling",
                "class": "ranger",
                "level": 1,
                "stats": {"str": 10, "dex": 14, "con": 12, "int": 10, "wis": 14, "cha": 8},
                "hp": {"current": 10, "max": 10},
            }
        )
    )

    # World — player is in alpha, has been there before (so short_desc).
    (run / "world.json").write_text(
        json.dumps(
            {
                "current_room": "t.alpha",
                "mode": "exploration",
                "turn": 3,
                "revealed": {
                    "t.alpha": {
                        "exits_known": ["north"],
                        "inspected": True,
                        "items_taken": [],
                        "items_dropped": [],
                        "triggered_hazards": [],
                    }
                    # t.beta is NOT revealed — must not appear
                },
            }
        )
    )

    # Graph — includes t.beta (unvisited) to verify isolation, and a
    # monster in alpha with exact HP 7/10 (the HP numbers must not
    # appear in the prompt; only "unhurt"/"bloodied"/etc.).
    (run / "graph.json").write_text(
        json.dumps(
            {
                "scenario": "testscn",
                "seed": 1,
                "rooms": {
                    "t.alpha": {
                        "area": "area.test",
                        "exits": {"north": "t.beta"},
                        "spawns": {
                            "items": [{"ref": "item.lamp"}],
                            "monsters": [
                                {
                                    "ref": "monster.rat",
                                    "hp_current": 7,
                                    "hp_max": 10,
                                }
                            ],
                            "hazards": [{"ref": "hazard.pit"}],
                            "npcs": [{"ref": "npc.sage"}],
                        },
                    },
                    "t.beta": {
                        "area": "area.test",
                        "exits": {},
                        "spawns": {
                            "items": [],
                            "monsters": [],
                            "hazards": [],
                            "npcs": [],
                        },
                    },
                },
            }
        )
    )

    (run / "ledger.jsonl").write_text("")

    return run, repo


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


class ComposerProseBubblingTests(unittest.TestCase):
    def test_surfaces_the_right_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, repo = _build_fixture(Path(tmp))
            prompt = build_system_prompt(run, repo)

        # DM voice + mode overlay
        self.assertIn("DM_VOICE_CANARY", prompt)
        self.assertIn("EXPLORATION_OVERLAY_CANARY", prompt)

        # Current room short_desc (player has revisited)
        self.assertIn("SHORT_ALPHA_OK", prompt)

        # Ambient from the containing area
        self.assertIn("AMBIENT_CANARY_OK", prompt)

        # Room contents: item + monster + NPC short_descs
        self.assertIn("ITEM_LAMP_SHORTDESC_OK", prompt)
        self.assertIn("MONSTER_RAT_SHORTDESC_OK", prompt)
        self.assertIn("NPC_SAGE_SHORTDESC_OK", prompt)

        # NPC dialog hooks must bubble
        self.assertIn("DIALOG_HOOK_CANARY", prompt)

        # Faction essence (first sentence)
        self.assertIn("FACTION_DESCRIPTION_CANARY_OK", prompt)

        # Character rendering
        self.assertIn("TestHero", prompt)

    def test_excludes_forbidden_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, repo = _build_fixture(Path(tmp))
            prompt = build_system_prompt(run, repo)

        # Unvisited rooms MUST NOT bleed
        self.assertNotIn("FORBIDDEN_BETA", prompt)

        # NPC loot tables MUST NOT appear
        self.assertNotIn("FORBIDDEN_LOOT_TABLE_REF", prompt)

        # Untriggered hazards MUST NOT appear
        self.assertNotIn("HAZARD_PIT_SHORTDESC_UNTRIGGERED", prompt)

        # Exact monster HP numbers MUST NOT appear — check the two
        # distinctive integers the fixture put in graph.json.
        # "hp_current": 7, "hp_max": 10 → "7/10" should not be in prose.
        self.assertNotIn("hp_current", prompt)
        self.assertNotIn("7/10", prompt)

    def test_long_desc_on_first_entry(self):
        # Rebuild with a pristine revealed record so long_desc surfaces.
        with tempfile.TemporaryDirectory() as tmp:
            run, repo = _build_fixture(Path(tmp))
            world = json.loads((run / "world.json").read_text())
            world["revealed"] = {}  # pristine
            (run / "world.json").write_text(json.dumps(world))

            prompt = build_system_prompt(run, repo)

        self.assertIn("LONG_ALPHA_OK", prompt)


if __name__ == "__main__":
    unittest.main()
