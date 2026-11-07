#!/usr/bin/env python3
"""Structural guards (task T-021). Wired as Claude Code hooks in .claude/settings.json.

Why this file exists
--------------------
Every leakage and integrity control in docs/04-EVALUATION.md is enforced HERE, as a tool
that refuses the call, rather than as an instruction in a prompt. A prompt is a
suggestion. A hook that exits non-zero is a guarantee.

The failures these prevent are all easy, plausible, and invisible in the output:
relaxing a control to get past it, docking against a live database mid-benchmark,
letting a post-cutoff paper into an evidence channel, or improving a score by editing
the benchmark instead of the method.

Hooks receive the tool call as JSON on stdin and block the call by exiting non-zero
with an explanation on stderr. The explanation is shown to the agent, so it should say
what rule was hit and what to do instead.

Subcommands
-----------
immutable-paths    Refuse writes to tests/controls/ during an L2 run, and to
                   benchmarks/ from any loop other than L0.
date-filter        Refuse retrieval without a resolved cutoff in benchmark mode.
bash-egress        Refuse live-endpoint egress during a benchmark run; refuse any
                   agent-initiated invocation of scripts/unseal.py.
validate-schemas   Validate written EvidenceItem / Hypothesis / TargetDossier files.
session-isolation  Refuse to start L1/L2 in a session that has touched post-cutoff data.

Run mode is read from the MSF_LOOP and MSF_SPLIT environment variables, set by
`msf run`. Absence of MSF_LOOP means interactive development, where the guards that
depend on run mode do not apply -- but the unseal and sealed-split guards always do.
"""

from __future__ import annotations

import json
import os
import sys

# --- Paths no loop may modify, and the loop that owns each -------------------

IMMUTABLE_DURING_RUN = {
    "tests/controls/": (
        "Negative and leakage controls may not be modified during an evaluation run. "
        "Modifying a control to pass it is failure mode A-eval. If you believe a "
        "control is wrong, record that in JOURNAL.md and leave it for a human."
    ),
    "benchmarks/": (
        "Only loop L0 (the curator), with a recorded human decision, may write to "
        "benchmarks/. Improving a score by changing the benchmark rather than the "
        "method is failure mode A6."
    ),
    "prereg/": (
        "A pre-registration is immutable once its hash is in a run manifest. "
        "Write a new one for a new loop version."
    ),
}

# Hosts that must only be reached through a pinned snapshot during a benchmark run.
LIVE_DATA_HOSTS = (
    "rest.uniprot.org", "www.ebi.ac.uk", "rcsb.org", "files.rcsb.org",
    "alphafold.ebi.ac.uk", "www.ebi.ac.uk/chembl", "hmdb.ca", "www.guidetopharmacology.org",
    "string-db.org", "gtexportal.org", "proteinatlas.org", "api.platform.opentargets.org",
    "www.ebi.ac.uk/europepmc", "eutils.ncbi.nlm.nih.gov", "api.openalex.org",
)

BENCHMARK_SPLITS = {"dev", "val", "sealed"}


def deny(message: str) -> None:
    """Block the tool call. The message is shown to the agent."""
    print(f"BLOCKED by scripts/guard.py: {message}", file=sys.stderr)
    sys.exit(2)


def allow() -> None:
    sys.exit(0)


def read_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def in_benchmark_run() -> bool:
    return os.environ.get("MSF_SPLIT", "") in BENCHMARK_SPLITS


# --- Subcommands -------------------------------------------------------------

def immutable_paths(payload: dict) -> None:
    path = (payload.get("tool_input", {}) or {}).get("file_path", "")
    norm = path.replace("\\", "/")
    for protected, reason in IMMUTABLE_DURING_RUN.items():
        if protected in norm:
            if protected == "benchmarks/" and os.environ.get("MSF_LOOP") == "L0":
                continue  # the curator owns this directory
            if protected == "tests/controls/" and not in_benchmark_run():
                continue  # free to edit outside an evaluation run
            deny(reason)
    allow()


def date_filter(payload: dict) -> None:
    if not in_benchmark_run():
        allow()
    cutoff = os.environ.get("MSF_CUTOFF")
    if not cutoff:
        deny(
            "Retrieval during a benchmark run requires a resolved cutoff date "
            "(MSF_CUTOFF). Without it, post-cutoff sources leak into evidence "
            "channels -- leak L1 -- and every downstream number becomes "
            "uninterpretable, in the direction of looking better."
        )
    url = (payload.get("tool_input", {}) or {}).get("url", "")
    if any(host in url for host in LIVE_DATA_HOSTS):
        deny(
            f"Live data endpoint {url} is not reachable during a benchmark run. "
            "Use the pinned snapshot named in the run manifest (leak L2). "
            "See docs/06-DATA-SOURCES.md."
        )
    allow()


def bash_egress(payload: dict) -> None:
    cmd = (payload.get("tool_input", {}) or {}).get("command", "")
    if "scripts/unseal.py" in cmd:
        deny(
            "The sealed split cannot be unsealed from inside an agent. It requires an "
            "interactive human key, and every unseal is recorded in "
            "benchmarks/UNSEAL-LOG.md against a loop version. Ask the human."
        )
    if in_benchmark_run() and any(
        tool in cmd for tool in ("curl", "wget", "http ")
    ) and any(host in cmd for host in LIVE_DATA_HOSTS):
        deny(
            "Live data endpoint egress during a benchmark run (leak L2). "
            "Use the pinned snapshot from the run manifest."
        )
    allow()


def validate_schemas(payload: dict) -> None:
    # TODO(T-003): validate written artifacts against src/msf/schemas/.
    # Unvalidated data crossing an agent boundary is how agentic pipelines silently
    # corrupt: a claim drifts from its evidence and nothing errors.
    allow()


def session_isolation(payload: dict) -> None:
    # TODO(T-021): refuse to start L1/L2 in a session that has already touched
    # post-cutoff sources. The curator (L0) may read post-cutoff data; nothing that
    # scores may. They must never share a session.
    allow()


SUBCOMMANDS = {
    "immutable-paths": immutable_paths,
    "date-filter": date_filter,
    "bash-egress": bash_egress,
    "validate-schemas": validate_schemas,
    "session-isolation": session_isolation,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in SUBCOMMANDS:
        print(f"usage: guard.py {{{'|'.join(SUBCOMMANDS)}}}", file=sys.stderr)
        sys.exit(64)
    SUBCOMMANDS[sys.argv[1]](read_hook_input())


if __name__ == "__main__":
    main()
