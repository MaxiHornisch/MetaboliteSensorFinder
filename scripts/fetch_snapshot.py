#!/usr/bin/env python3
"""Fetch and verify the pinned data snapshots named in a manifest (task T-005).

Closes leak L2. During a benchmark run the loop may not touch a live endpoint; it reads
these snapshots instead. The guard hook blocks live egress, and this script is how the
data gets there legitimately.

Every file is SHA-256 verified against the manifest. A mismatch aborts the run rather
than warning: a silently altered snapshot invalidates every number computed from it, and
would do so invisibly.

Note on what is achievable. Only a minority of our sources publish a dated archive.
Where none exists, the manifest records the closest available pin AND the gap in months
as declared residual L2 exposure. See docs/06-DATA-SOURCES.md section 5. An undeclared
gap is a bug; a declared one is a limitation.

Usage:
    python scripts/fetch_snapshot.py --manifest snap_2018-01-01_v1
    python scripts/fetch_snapshot.py --manifest snap_2018-01-01_v1 --verify-only
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--verify-only", action="store_true",
                    help="Check hashes of what is already on disk; download nothing.")
    ap.parse_args()

    raise NotImplementedError(
        "T-005. Must: resolve the manifest, fetch each source at its pinned release, "
        "verify SHA-256, record retrieval date and record counts, and refuse to proceed "
        "on any mismatch."
    )


if __name__ == "__main__":
    sys.exit(main())
