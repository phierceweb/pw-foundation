"""``python -m pw_foundation.guards`` -> run the structural gate."""

from __future__ import annotations

import sys

from pw_foundation.guards.structure import run_cli

if __name__ == "__main__":
    sys.exit(run_cli())
