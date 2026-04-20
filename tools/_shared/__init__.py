"""Shared helpers for roguebash tool entrypoints.

Both the mechanics-lane and exploration-lane tools read the same state
files and catalogs, reshape the same weapons, and resolve the same
in-room targets. Rather than reimplement that per tool, everything lives
here as small stdlib-only helpers.

Nothing in this package takes over a tool's contract — tools still own
their own `--schema`, stdin-parsing, and stdout narration. These
functions are just arithmetic + lookups + a thin state-load wrapper.
"""
