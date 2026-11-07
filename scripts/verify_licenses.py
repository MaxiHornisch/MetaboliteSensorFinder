#!/usr/bin/env python3
"""Re-verify every data source licence against its official page (task T-035).

Licences change, and getting one wrong is exactly what makes a repository undonatable.
docs/06-DATA-SOURCES.md carries a verification date per source; this script refreshes it
and fails if a verdict moved.

It also enforces the policy in docs/06-DATA-SOURCES.md section 4 as a TEST rather than a
promise: no source marked AVOID may appear in the default configuration, and no
share-alike source may have its raw records committed to this repository.

Four of our own priors turned out wrong when first checked (LIPID MAPS, STRING and HPA
were each misremembered, and Open Targets Genetics no longer exists separately), which is
the reason this runs on a schedule instead of being a one-off.

Usage:
    python scripts/verify_licenses.py                 # refresh and report drift
    python scripts/verify_licenses.py --assert-policy # CI gate: AVOID sources unused
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assert-policy", action="store_true",
                    help="Exit non-zero if an AVOID source is reachable from the default config.")
    ap.parse_args()

    raise NotImplementedError(
        "T-035. Must: re-fetch each licence page, diff the verdict against "
        "docs/06-DATA-SOURCES.md, update verification dates, and fail on drift. "
        "Sources that block automated access (HMDB behind Cloudflare, ZINC) must be "
        "reported as requiring a human rather than silently skipped."
    )


if __name__ == "__main__":
    sys.exit(main())
