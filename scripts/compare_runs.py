#!/usr/bin/env python3
"""Paired comparison between two runs, on identical items (task T-023).

Two jobs:

1. Reproduction check. Given a run id and the recorded result in runs/INDEX.md, re-derive
   and report which fields diverged, and whether the divergence sits inside the recorded
   non-determinism of the tools involved. A result not reproducible from its run record
   does not exist.

2. Version comparison. Paired bootstrap on the items both runs actually covered.
   Unpaired comparison across versions is refused, not warned about: it is the standard
   way a version difference gets overstated.

Usage:
    python scripts/compare_runs.py r_8f3a1c runs/INDEX.md
    python scripts/compare_runs.py r_8f3a1c r_2b91de --metric selective_accuracy_at_20pct
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_a")
    ap.add_argument("run_b", help="Another run id, or runs/INDEX.md for a reproduction check.")
    ap.add_argument("--metric", default=None)
    ap.parse_args()

    raise NotImplementedError(
        "T-023. Must: refuse unpaired comparison, report BCa bootstrap CIs over 10000 "
        "resamples on shared items, and decline to call a difference whose CI includes "
        "zero an improvement."
    )


if __name__ == "__main__":
    sys.exit(main())
