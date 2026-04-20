"""Module entrypoint — enables `python3 -m engine.generator ...`.

Delegates to `generate.main` so the CLI logic lives in one place.
"""

from __future__ import annotations

import sys

from .generate import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
