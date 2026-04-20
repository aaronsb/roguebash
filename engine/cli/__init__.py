"""engine.cli — implementation behind the `delve` command.

The `bin/delve` script is a thin dispatch shim; everything substantive
lives here as importable modules:

- ``engine.cli.config``     — TOML + default config layering
- ``engine.cli.backend``    — llama.cpp endpoint health probe
- ``engine.cli.character``  — tier-0 character creation
- ``engine.cli.hooks``      — parse the scenario.md opening hook
- ``engine.cli.commands``   — the cmd_* subcommand implementations

Importing this package is cheap — submodules are imported lazily by
the commands.
"""
