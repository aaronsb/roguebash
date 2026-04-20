"""Config loading for delve.

Layered: DEFAULT_CONFIG <- $XDG_CONFIG_HOME/roguebash/delve.toml <- ./delve.toml.
Later layers override earlier ones (shallow merge per top-level section).
CLI flags override all of this in the command implementations.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path


DEFAULT_CONFIG: dict = {
    "agent": {
        "adapter": "local",
        "max_turns": 12,
        # The llama.cpp-compatible endpoint delve probes before starting
        # a run. Override in delve.toml if your adapter points elsewhere.
        "endpoint": "127.0.0.1:8765",
    },
    "generator": {
        "default_scenario": "barrow_swamp",
        "default_macro_nodes": 10,
    },
}


def load_config(repo_root: Path) -> dict:
    cfg = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    candidates = [
        Path(xdg) / "roguebash" / "delve.toml",
        repo_root / "delve.toml",
    ]
    for p in candidates:
        if not p.is_file():
            continue
        try:
            with p.open("rb") as fh:
                user = tomllib.load(fh)
            for section, values in user.items():
                cfg.setdefault(section, {}).update(values)
        except Exception as e:
            print(f"delve: ignoring malformed config at {p}: {e}", file=sys.stderr)
    return cfg
