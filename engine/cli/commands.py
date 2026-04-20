"""Subcommand implementations for the `delve` CLI.

Each function signature is ``(args, config, repo_root) -> int`` so the
dispatch layer in ``bin/delve`` stays uniform.
"""

from __future__ import annotations

import argparse
import json
import os
import random as _random
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Optional

from engine.generator.generate import generate
from engine.prompt.compose import build_system_prompt
from engine.state import archive as _archive
from engine.state import ledger as _ledger
from engine.state.io import load_json, save_json
from engine.state.paths import (
    CHARACTER_FILE,
    GRAPH_FILE,
    LEDGER_FILE,
    WORLD_FILE,
    list_runs,
    make_run_id,
    run_dir as _run_dir,
    state_root,
)

from engine.cli.backend import check_endpoint
from engine.cli.character import make_character
from engine.cli.hooks import opening_hook


# =====================================================================
# Shared helpers
# =====================================================================


def _resolve_run_id(explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    alive = [rid for rid, st in list_runs() if st == "alive"]
    if not alive:
        return None
    alive.sort(key=lambda rid: _run_dir(rid).stat().st_mtime, reverse=True)
    return alive[0]


def _create_run(args: argparse.Namespace, config: dict, repo_root: Path) -> str:
    """Generate a world, write the run's four files, seed the opening hook.
    Returns the run_id. Raises on any failure."""
    seed = args.seed if args.seed is not None else _random.randrange(1, 2**31)
    scenario = args.scenario or config["generator"]["default_scenario"]
    macro_nodes = args.macro_nodes or config["generator"]["default_macro_nodes"]
    name = args.name or "Wanderer"

    if scenario == "random":
        scenarios_dir = repo_root / "scenarios"
        candidates = sorted(
            p.name for p in scenarios_dir.iterdir()
            if p.is_dir() and not p.name.startswith(("_", "."))
        )
        if not candidates:
            raise RuntimeError("no scenarios found under scenarios/")
        scenario = _random.Random(seed).choice(candidates)

    graph = generate(
        seed=seed,
        scenarios_dir=repo_root / "scenarios",
        scenario=scenario,
        macro_nodes=macro_nodes,
        verbose=False,
    )

    run_id = make_run_id(seed, name)
    rd = _run_dir(run_id)
    rd.mkdir(parents=True, exist_ok=True)

    save_json(rd / GRAPH_FILE, graph)
    save_json(rd / CHARACTER_FILE, make_character(name=name, race=args.race, cls=args.cls))
    save_json(rd / WORLD_FILE, {
        "current_room": graph.get("start_room"),
        "mode": "exploration",
        "turn": 0,
        "revealed": {},
    })
    _ledger.narration(rd, 0, opening_hook(repo_root, scenario))
    return run_id


# =====================================================================
# Subcommands
# =====================================================================


def cmd_new(args, config: dict, repo_root: Path) -> int:
    try:
        print(_create_run(args, config, repo_root))
        return 0
    except Exception as e:
        print(f"delve: {e}", file=sys.stderr)
        return 1


def cmd_start(args, config: dict, repo_root: Path) -> int:
    """Easy-mode: probe backend, surface any alive run, else new-and-play."""
    up, endpoint = check_endpoint(config)
    if not up:
        print(
            f"delve: no llama.cpp-compatible endpoint reachable at {endpoint}",
            file=sys.stderr,
        )
        print("delve needs a running LLM backend. If you installed agent-bash:",
              file=sys.stderr)
        print("    askd start", file=sys.stderr)
        print("Otherwise, start your adapter's backend before running `delve start`.",
              file=sys.stderr)
        return 1
    print(f"[backend ok at {endpoint}]")

    alive = [rid for rid, st in list_runs() if st == "alive"]
    if alive:
        alive.sort(key=lambda rid: _run_dir(rid).stat().st_mtime, reverse=True)
        most_recent = alive[0]
        print()
        print(f"You already have an ongoing run: {most_recent}")
        print()
        print("    delve play               # resume it")
        print(f"    delve abandon {most_recent}")
        print("    delve start              # start fresh after abandoning")
        return 0

    try:
        run_id = _create_run(
            types.SimpleNamespace(
                scenario=None, seed=None, name="Wanderer",
                cls="ranger", race="halfling", macro_nodes=None,
            ),
            config,
            repo_root,
        )
    except Exception as e:
        print(f"delve: failed to create run: {e}", file=sys.stderr)
        return 1

    print(f"[new run: {run_id}]\n")
    return cmd_play(
        types.SimpleNamespace(run_id=run_id), config, repo_root
    )


def cmd_list(args, config: dict, repo_root: Path) -> int:
    runs = list_runs()
    if not runs:
        print("(no runs)")
        return 0
    for run_id, status in runs:
        rd = _run_dir(run_id) if status == "alive" else state_root() / "_archive" / run_id
        name = "?"
        current = "?"
        try:
            name = load_json(rd / CHARACTER_FILE).get("name", "?")
        except Exception:
            pass
        try:
            current = load_json(rd / WORLD_FILE).get("current_room", "?")
        except Exception:
            pass
        print(f"{status:6s}  {run_id:45s}  {name:20s}  {current}")
    return 0


def cmd_show(args, config: dict, repo_root: Path) -> int:
    run_id = _resolve_run_id(args.run_id)
    if not run_id:
        print("delve: no alive runs to show", file=sys.stderr)
        return 1
    rd = _run_dir(run_id)
    if not rd.is_dir():
        rd = state_root() / "_archive" / run_id
    if not rd.is_dir():
        print(f"delve: run not found: {run_id}", file=sys.stderr)
        return 1
    ch = load_json(rd / CHARACTER_FILE)
    w = load_json(rd / WORLD_FILE)
    print(f"=== run {run_id} ===")
    print(json.dumps(ch, indent=2))
    print()
    print(f"Mode: {w.get('mode')}    Turn: {w.get('turn')}    "
          f"Current room: {w.get('current_room')}")
    return 0


def cmd_abandon(args, config: dict, repo_root: Path) -> int:
    rd = _run_dir(args.run_id)
    if not rd.is_dir():
        print(f"delve: no live run named {args.run_id}", file=sys.stderr)
        return 1
    if input(f"delete {rd}? [y/N] ").strip().lower() != "y":
        print("aborted")
        return 0
    shutil.rmtree(rd)
    print(f"deleted {args.run_id}")
    return 0


# =====================================================================
# Play loop
# =====================================================================


def _invoke_adapter(
    adapter_path: Path,
    repo_root: Path,
    rd: Path,
    system_prompt: str,
    user_msg: str,
    max_turns: int,
) -> subprocess.CompletedProcess:
    """Run the configured adapter with ROGUEBASH_* env set."""
    env = os.environ.copy()
    env["ROGUEBASH_SYSTEM_PROMPT"] = system_prompt
    env["ROGUEBASH_USER_MESSAGE"] = user_msg
    env["ROGUEBASH_TOOLS_DIR"] = str(repo_root / "tools")
    env["ROGUEBASH_RUN_DIR"] = str(rd)
    env["ROGUEBASH_SCENARIOS"] = str(repo_root / "scenarios")
    env["ROGUEBASH_MAX_TURNS"] = str(max_turns)
    return subprocess.run(
        [str(adapter_path)], env=env, capture_output=True, text=True
    )


def _terminal_event(rd: Path) -> Optional[str]:
    """Scan recent ledger events for a run-ending event; return its type or None."""
    for e in reversed(_ledger.tail(rd / LEDGER_FILE, n=10)):
        t = e.get("type")
        if t in ("death", "victory"):
            return t
    return None


def _run_one_turn(
    rd: Path,
    repo_root: Path,
    adapter_path: Path,
    adapter_name: str,
    max_turns: int,
) -> Optional[str]:
    """Read one player input, invoke the adapter, persist the turn.
    Returns 'death' / 'victory' to end the run, 'eof' on Ctrl-D, or None
    to continue."""
    w = load_json(rd / WORLD_FILE)
    turn = int(w.get("turn", 0)) + 1
    system_prompt = build_system_prompt(rd, repo_root)

    try:
        user_msg = input("> ")
    except EOFError:
        print()
        return "eof"

    proc = _invoke_adapter(adapter_path, repo_root, rd, system_prompt, user_msg, max_turns)
    narration = (proc.stdout or "").strip()
    if proc.returncode != 0:
        print(
            f"[adapter {adapter_name} exited {proc.returncode}] "
            f"{(proc.stderr or '').strip()[:400]}",
            file=sys.stderr,
        )
    if narration:
        print(narration + "\n")
        _ledger.narration(rd, turn, narration)

    w["turn"] = turn
    save_json(rd / WORLD_FILE, w)
    return _terminal_event(rd)


def cmd_play(args, config: dict, repo_root: Path) -> int:
    run_id = _resolve_run_id(args.run_id)
    if not run_id:
        print("delve: no alive runs. Start one with `delve new`.", file=sys.stderr)
        return 1
    rd = _run_dir(run_id)
    if not rd.is_dir():
        print(f"delve: run not found: {run_id}", file=sys.stderr)
        return 1

    adapter_name = config["agent"]["adapter"]
    adapter_path = repo_root / "adapters" / adapter_name / "run"
    if not adapter_path.is_file():
        print(f"delve: adapter not found: {adapter_path}", file=sys.stderr)
        return 1
    max_turns = int(config["agent"]["max_turns"])

    print(f"playing {run_id} — Ctrl-C to save and quit.\n")
    try:
        while True:
            result = _run_one_turn(rd, repo_root, adapter_path, adapter_name, max_turns)
            if result == "eof":
                return 0
            if result == "death":
                print("\n[you have died.]")
                _archive.archive_run(run_id, cause="death")
                return 0
            if result == "victory":
                print("\n[you have won.]")
                _archive.archive_run(run_id, cause="victory")
                return 0
    except KeyboardInterrupt:
        print("\n[save + exit]")
        return 0
