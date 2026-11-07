#!/usr/bin/env python3
"""Tool readiness check (task T-004).

Prints one row per tool the loop depends on, grouped by setup tier, and exits non-zero
if anything required by the requested tier is missing.

Nothing downstream can be trusted until this is green for the tier you intend to run,
so L2 calls it as its first step.

Usage:
    python scripts/doctor.py                # check tier 0 (the 15-minute path)
    python scripts/doctor.py --tier 1       # full CPU stack
    python scripts/doctor.py --tier 2       # GPU / cloud
    python scripts/doctor.py --json         # machine-readable, for the run manifest

Deliberately dependency-free: it must run before `uv sync` has worked, on a machine
where nothing else is installed yet.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Check:
    name: str
    tier: int
    kind: str  # "exe" | "module" | "env" | "path"
    probe: str
    why: str
    version_cmd: list[str] | None = None
    optional: bool = False
    # Filled in by run()
    ok: bool = field(default=False, init=False)
    detail: str = field(default="", init=False)


CHECKS: list[Check] = [
    # ---- Tier 0: schemas, metrics, reports. No GPU, no keys but Anthropic. ----
    Check("python>=3.11", 0, "module", "", "Everything.", optional=False),
    Check("pydantic", 0, "module", "pydantic", "Data contracts between agents."),
    Check("jsonschema", 0, "module", "jsonschema", "Loopspec and dossier validation."),
    Check("pyyaml", 0, "module", "yaml", "Loopspecs and evidence bundles."),
    Check("duckdb", 0, "module", "duckdb", "Run-record analytics; the web app queries it."),
    Check("pyarrow", 0, "module", "pyarrow", "Parquet run records and benchmark files."),
    Check("numpy", 0, "module", "numpy", "Metrics."),
    Check("scipy", 0, "module", "scipy", "Bootstrap confidence intervals."),
    Check("sklearn", 0, "module", "sklearn", "Isotonic/Platt calibration, decoy separability check."),
    # Checked as a module, not as an executable: inside a virtualenv that has not been
    # activated, `shutil.which("pytest")` misses a perfectly good install. Found by
    # running this script rather than by reading it.
    Check("pytest", 0, "module", "pytest", "Controls and physics regressions gate every run."),
    Check("git", 0, "exe", "git", "Run records pin a commit hash.", ["git", "--version"]),
    Check("ANTHROPIC_API_KEY", 0, "env", "ANTHROPIC_API_KEY", "The agents."),

    # ---- Tier 1: the full CPU scientific stack. ----
    Check("rdkit", 1, "module", "rdkit",
          "Library prep, protonation, tautomers, Bemis-Murcko scaffolds, decoy matching."),
    Check("openbabel", 1, "exe", "obabel", "Format conversion.", ["obabel", "-V"]),
    Check("vina", 1, "exe", "vina", "Docking.", ["vina", "--version"]),
    Check("fpocket", 1, "exe", "fpocket", "Pocket detection. Run alongside P2Rank."),
    Check("p2rank", 1, "exe", "prank", "Pocket detection. Disagreement with fpocket is signal."),
    Check("foldseek", 1, "exe", "foldseek",
          "Structural homology. The highest-value cheap signal for orphans, "
          "which are orphans partly because sequence search found them nothing."),
    Check("hmmer", 1, "exe", "jackhmmer", "Sequence homology and conservation."),
    Check("biopython", 1, "module", "Bio", "Structure parsing."),

    # Sequence-based channels (P-007, P-008). Each lives in a sibling repo with its
    # own virtualenv, because their torch pins are mutually incompatible: bindPredict
    # runs torch 2.14.1+cpu, PSICHIC is capped at 2.9.0+cpu by the torch_scatter
    # wheels. They are invoked as subprocesses, never imported.
    Check("bindPredict.weights", 1, "path",
          "bindPredict-repo/trained_models/checkpoint1.pt",
          "P-007 pocket-from-sequence channel. The 5-checkpoint bindEmbed21DL ensemble."),
    Check("bindPredict.venv", 1, "path", "bindPredict-repo/.venv/bin/python",
          "P-007. CPU torch venv; must not be shared with PSICHIC."),
    Check("psichic.weights", 1, "path",
          "PSICHIC/trained_weights/multitask_PSICHIC/model.pt",
          "P-008 interaction channel. CONTAMINATED to 2023-02-02 (leak L5c) - usable "
          "only as an explicitly contaminated configuration. See PSICHIC/PROVENANCE.md.",
          optional=True),
    Check("psichic.venv", 1, "path", "PSICHIC/.venv/bin/python",
          "P-008. Pinned to torch 2.9.0+cpu, the newest with torch_scatter wheels.",
          optional=True),

    # ---- Tier 2: GPU and cloud. ----
    Check("boltz", 2, "exe", "boltz", "Co-folding with an affinity head (proposal P-002).",
          optional=True),
    Check("torch+cuda", 2, "module", "torch", "GPU for co-folding.", optional=True),
    Check("modal", 2, "exe", "modal", "GPU dispatch if not running locally.", optional=True),
]


def have_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def version_of(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        line = (out.stdout or out.stderr).strip().splitlines()
        return line[0][:60] if line else "present"
    except (OSError, subprocess.SubprocessError):
        return "present"


def run(check: Check) -> Check:
    if check.name == "python>=3.11":
        check.ok = sys.version_info >= (3, 11)
        check.detail = sys.version.split()[0]
    elif check.kind == "module":
        check.ok = have_module(check.probe)
        check.detail = "importable" if check.ok else "not importable"
    elif check.kind == "exe":
        path = shutil.which(check.probe)
        check.ok = path is not None
        check.detail = version_of(check.version_cmd) if (path and check.version_cmd) else (
            "on PATH" if path else "not on PATH"
        )
    elif check.kind == "env":
        check.ok = bool(os.environ.get(check.probe))
        # Never print the value.
        check.detail = "set" if check.ok else "unset"
    elif check.kind == "path":
        # Sibling tool repos, each in its own virtualenv with its own torch pin.
        # They are never on PATH and must never be imported into this process.
        p = (REPO_ROOT.parent / check.probe)
        check.ok = p.exists()
        check.detail = "present" if check.ok else f"missing: {p}"
    return check


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", type=int, default=0, choices=[0, 1, 2],
                    help="Highest setup tier to check. See docs/05-TOOLS-SETUP.md.")
    ap.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = ap.parse_args()

    results = [run(c) for c in CHECKS if c.tier <= args.tier]

    if args.json:
        print(json.dumps(
            [{"name": c.name, "tier": c.tier, "ok": c.ok,
              "optional": c.optional, "detail": c.detail} for c in results],
            indent=2,
        ))
    else:
        width = max(len(c.name) for c in results)
        current_tier = -1
        for c in results:
            if c.tier != current_tier:
                current_tier = c.tier
                print(f"\n  Tier {current_tier}")
                print("  " + "-" * (width + 40))
            mark = "ok  " if c.ok else ("warn" if c.optional else "MISS")
            print(f"  [{mark}] {c.name:<{width}}  {c.detail:<22} {c.why}")

    required_missing = [c for c in results if not c.ok and not c.optional]
    optional_missing = [c for c in results if not c.ok and c.optional]

    if not args.json:
        print()
        if required_missing:
            print(f"  {len(required_missing)} required tool(s) missing: "
                  + ", ".join(c.name for c in required_missing))
            print("  See docs/05-TOOLS-SETUP.md for install instructions per tier.")
        else:
            print(f"  Tier {args.tier} ready.")
        if optional_missing:
            print(f"  Optional, not blocking: {', '.join(c.name for c in optional_missing)}")

    return 1 if required_missing else 0


if __name__ == "__main__":
    sys.exit(main())
