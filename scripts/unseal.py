#!/usr/bin/env python3
"""Unseal the test split. The only path by which sealed data enters a run.

This is a deliberate chokepoint, not a convenience. An agent iterating for hours will
overfit any split it can read, with no ill intent and no visible symptom. Encryption plus
a published log is the only mechanism we have that does not rely on discipline.

Properties this script must keep:

  * No agent can run it. `.claude/settings.json` denies the Bash pattern, and
    `scripts/guard.py bash-egress` blocks it again at the hook layer. It also refuses to
    run without an interactive TTY, so it cannot be driven from a pipe.
  * The key is never stored. It is prompted for, used, and dropped. It is not in .env.
  * Every unseal appends to benchmarks/UNSEAL-LOG.md: who, when, which loop version,
    which pre-registration hash.
  * A second unseal for the same loop version requires --force, which is also logged.

The log is published. A loop version with five unseal events against it has been tuned on
the test set, and a reader can see that rather than having to trust us.

Usage:
    python scripts/unseal.py --loop-version v0.2.0-fusion-correlation \
                             --prereg prereg/v0.2.0-fusion-correlation.yaml
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import hashlib
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEALED = ROOT / "benchmarks" / "splits" / "sealed.age"
OUT_DIR = ROOT / "benchmarks" / "splits" / "sealed"
LOG = ROOT / "benchmarks" / "UNSEAL-LOG.md"


def die(msg: str, code: int = 1) -> None:
    print(f"unseal: {msg}", file=sys.stderr)
    raise SystemExit(code)


def already_unsealed_for(loop_version: str) -> bool:
    if not LOG.exists():
        return False
    return any(
        loop_version in line and line.startswith("|") and "never unsealed" not in line
        for line in LOG.read_text(encoding="utf-8").splitlines()
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--loop-version", required=True)
    ap.add_argument("--prereg", required=True, type=pathlib.Path,
                    help="Pre-registration file. Required: unsealing without one makes the "
                         "result exploratory, and exploratory results cannot be promoted.")
    ap.add_argument("--force", action="store_true",
                    help="Unseal again for a loop version already unsealed. Logged as forced.")
    ap.add_argument("--note", default="", help="Why. Goes in the published log.")
    args = ap.parse_args()

    # Refuse non-interactive invocation. An agent, a CI job, or a pipe gets nothing.
    if not sys.stdin.isatty():
        die("refusing to run without an interactive terminal. The sealed split requires a "
            "human. If you are an agent, this is working as intended: ask the human.", 77)

    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_SESSION"):
        die("refusing to run inside a Claude Code session. Open a separate terminal.", 77)

    if not SEALED.exists():
        die(f"no sealed split at {SEALED.relative_to(ROOT)}. Build it with loop L0 first.")

    if not args.prereg.exists():
        die(f"pre-registration not found: {args.prereg}. Write it BEFORE unsealing - that "
            "ordering is the whole point (docs/07-VERSIONING.md section 3).")

    prereg_sha = hashlib.sha256(args.prereg.read_bytes()).hexdigest()

    if already_unsealed_for(args.loop_version) and not args.force:
        die(f"{args.loop_version} has already been unsealed. Re-unsealing means tuning on the "
            "test set. If you genuinely need it, pass --force; it will be logged as forced.")

    print(f"\n  Loop version : {args.loop_version}")
    print(f"  Pre-reg      : {args.prereg}  (sha256 {prereg_sha[:16]}...)")
    print(f"  Forced       : {args.force}")
    print("\n  This unseal will be recorded in a PUBLISHED log.\n")
    if input("  Type UNSEAL to continue: ").strip() != "UNSEAL":
        die("aborted.", 0)

    who = getpass.getuser()
    key = getpass.getpass("  Decryption key (not echoed, not stored): ")
    if not key:
        die("empty key.")

    # TODO(T-007): invoke age with the supplied key and extract to OUT_DIR.
    # Deliberately not implemented until the sealed split exists, so that this script
    # cannot appear to succeed against nothing.
    del key
    die("sealed split decryption is not implemented yet (T-007). Nothing was unsealed.", 3)

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"| {now} | {who} | {args.loop_version} | `{prereg_sha}` | "
                 f"{'YES' if args.force else 'no'} | {args.note} |\n")
    print(f"\n  Unsealed to {OUT_DIR.relative_to(ROOT)} and logged.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
