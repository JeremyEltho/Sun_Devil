#!/usr/bin/env python3
"""Backward-compatible entry point.

The analysis tool has grown into the :mod:`drivetrain` package with a proper
CLI in ``analyze.py``. ``python filter.py`` still works exactly as before
(interactive prompts, then plots), it just delegates to the new pipeline.

    python filter.py            # interactive, same as always
    python analyze.py --help    # full CLI: vehicle params, thresholds, batch mode
"""

from analyze import main

if __name__ == "__main__":
    raise SystemExit(main())
