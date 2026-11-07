"""Loop S1 (docs/13 §3): the simulation suite must pass before any real worker is used."""

from __future__ import annotations

from pathlib import Path

from msf.screen.simulate import run_simulation_suite


def test_all_simulation_scenarios_pass(tmp_path: Path) -> None:
    results = run_simulation_suite(n_items=60, out_dir=tmp_path, seed="test")
    failed = [r for r in results if not r["passed"]]
    assert failed == [], failed


def test_suite_covers_the_required_scenarios(tmp_path: Path) -> None:
    results = run_simulation_suite(n_items=60, out_dir=tmp_path, seed="test")
    names = {r["scenario"] for r in results}
    assert names == {
        "planted_recall",
        "size_artifact_detected",
        "corrupt_batch_retried",
        "silent_drop_rejected",
        "resume_byte_identical",
        "uncalibrated_advances_nothing",
    }
