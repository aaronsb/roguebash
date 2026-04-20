"""engine.prompt — system-prompt composer.

Builds the per-turn system prompt for the DM agent. See README for the
prose-bubbling contract; the rule is that every prose field in the
scenario catalogs exists precisely so this composer can surface it at
the right time.

Public API:

    from engine.prompt import build_system_prompt
    prompt = build_system_prompt(run_dir, repo_root)

Stdlib only. Zero LLM calls.
"""

from __future__ import annotations

from .compose import build_system_prompt

__all__ = ["build_system_prompt"]
