"""Glue for `msf screen`: ingest, manifest, and the two modes that exist today.

    ingest      validate the CSV and write a manifest. Runs anywhere, no workers needed.
    simulate    loop S1 on the ingested domains, with planted truth. No network.
    run         real workers. Not configured. Raises rather than pretending to run.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from msf.screen.ingest import SHORT_DOMAIN_MAX_LENGTH, IngestResult, ingest
from msf.screen.runner import Thresholds, load_thresholds
from msf.screen.simulate import run_simulation_suite

REPO = Path(__file__).resolve().parents[3]
DEFAULT_THRESHOLDS = REPO / "loops" / "screen-thresholds.yaml"


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_manifest(run_root: Path, body: dict) -> tuple[str, Path]:
    run_id = hashlib.sha256(_canonical(body)).hexdigest()[:16]
    run_dir = run_root / f"screen-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_bytes(_canonical({**body, "run_id": run_id}))
    return run_id, run_dir


def build_manifest(
    result: IngestResult, input_path: Path, mode: str, thresholds: Thresholds
) -> dict:
    """Manifest body. Contains no timestamps, so the same input gives the same run id."""
    return {
        "schema": "msf.screen.manifest/v1",
        "mode": mode,
        "input": {"path": Path(input_path).name, "sha256": result.file_sha256},
        "counts": result.counts,
        "rejected": result.rejected,
        "rules": {"short_domain_max_length": SHORT_DOMAIN_MAX_LENGTH,
                  "short_domain_excluded": False, "stage_order": ["bindpredict"]},
        "thresholds": {
            "calibrated": thresholds.calibrated,
            "cuts": thresholds.cuts,
            "source": thresholds.source,
        },
        "screened_ids_sha256": hashlib.sha256(
            _canonical({"ids": [r.domain_id for r in result.screened]})).hexdigest(),
    }


def cmd_ingest(input_path: Path, run_root: Path, thresholds_path: Path | None = None) -> Path:
    result = ingest(input_path)
    thresholds = load_thresholds(thresholds_path or DEFAULT_THRESHOLDS)
    body = build_manifest(result, input_path, "ingest", thresholds)
    _, run_dir = _write_manifest(run_root, body)
    return run_dir


def cmd_simulate(input_path: Path, run_root: Path) -> tuple[Path, list[dict]]:
    result = ingest(input_path)
    body = build_manifest(result, input_path, "simulation", Thresholds(calibrated=False))
    _, run_dir = _write_manifest(run_root, body)
    results = run_simulation_suite(out_dir=run_dir / "simulation", rows=result.screened)
    summary = {"generated": datetime.now(UTC).isoformat(timespec="seconds"),
               "label": "SIMULATION. Not evidence about any protein.",
               "results": results}
    (run_dir / "simulation" / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return run_dir, results


def cmd_run(input_path: Path, run_root: Path) -> None:
    raise NotImplementedError(
        "msf screen run: no worker endpoints are configured. Workers A/B/C need hosts and "
        "GPUs that have not been provided (docs/12 §8). Use `msf screen simulate` to test the "
        "harness; it does not produce scores for any protein."
    )
