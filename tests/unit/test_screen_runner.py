"""Runner invariants for the screen (docs/12 §3, docs/13 §2 and §3 S2).

The worker here is a scripted fake. No real worker is contacted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from msf.screen.ingest import Row
from msf.screen.runner import BatchFailed, Thresholds, run_stage, scores_hash
from msf.screen.simulate import SimulatedWorker, planted_truth


def _rows(n: int) -> list[Row]:
    seq = "MKTAYIAKQRQISFVKSHFSRQ"
    return [
        Row(
            row_no=i + 2,
            uniprot_id=f"P{i:03d}",
            gene_name="G",
            protein_name="n",
            interpro_id="IPR1",
            interpro_name="n",
            entry_type="domain",
            start=1,
            end=len(seq),
            sequence=seq,
            flags=(),
        )
        for i in range(n)
    ]


CALIBRATED = Thresholds(calibrated=True, cuts={"bindpredict": 0.5}, source="test")
UNCALIBRATED = Thresholds(calibrated=False, cuts={}, source=None)


def test_count_in_equals_count_out(tmp_path: Path) -> None:
    rows = _rows(10)
    worker = SimulatedWorker(truth=set(), seed="s")
    summary = run_stage("bindpredict", rows, worker, tmp_path, CALIBRATED, batch_size=4)
    assert summary["rows_out"] == summary["rows_in"] == 10


def test_silent_drop_fails_the_batch(tmp_path: Path) -> None:
    rows = _rows(4)
    worker = SimulatedWorker(truth=set(), seed="s", drop_ids={rows[1].domain_id})
    with pytest.raises(BatchFailed, match="count"):
        run_stage("bindpredict", rows, worker, tmp_path, CALIBRATED, batch_size=4)


def test_corrupt_output_is_rejected_and_retried(tmp_path: Path) -> None:
    rows = _rows(4)
    clean = run_stage(
        "bindpredict", rows, SimulatedWorker(truth=set(), seed="s"),
        tmp_path / "clean", CALIBRATED, batch_size=4,
    )
    flaky = run_stage(
        "bindpredict", rows, SimulatedWorker(truth=set(), seed="s", corrupt_jobs={0}),
        tmp_path / "flaky", CALIBRATED, batch_size=4,
    )
    assert flaky["retries"] == 1
    assert scores_hash(tmp_path / "clean") == scores_hash(tmp_path / "flaky")
    assert clean["rows_out"] == flaky["rows_out"]


def test_resume_after_kill_is_byte_identical(tmp_path: Path) -> None:
    rows = _rows(12)
    uninterrupted = tmp_path / "full"
    run_stage("bindpredict", rows, SimulatedWorker(truth=set(), seed="s"),
              uninterrupted, CALIBRATED, batch_size=4)

    resumed = tmp_path / "resumed"
    run_stage("bindpredict", rows, SimulatedWorker(truth=set(), seed="s"),
              resumed, CALIBRATED, batch_size=4, max_batches=2)
    run_stage("bindpredict", rows, SimulatedWorker(truth=set(), seed="s"),
              resumed, CALIBRATED, batch_size=4)

    assert scores_hash(uninterrupted) == scores_hash(resumed)


def test_uncalibrated_thresholds_advance_nothing(tmp_path: Path) -> None:
    rows = _rows(6)
    truth = planted_truth([r.domain_id for r in rows], rate=0.5, seed="s")
    run_stage("bindpredict", rows, SimulatedWorker(truth=truth, seed="s"),
              tmp_path, UNCALIBRATED, batch_size=3)
    assert scores_hash(tmp_path) is not None
    from msf.screen.runner import read_scores
    scored = read_scores(tmp_path, "bindpredict")
    assert len(scored) == 6
    assert all(r["advanced"] is None for r in scored)
    assert all(r["advance_status"] == "uncalibrated" for r in scored)


def test_peptides_are_excluded_but_still_written(tmp_path: Path) -> None:
    rows = _rows(3)
    rows[0] = Row(**{**rows[0].__dict__, "flags": ("peptide_out_of_scope",)})
    run_stage("bindpredict", rows, SimulatedWorker(truth=set(), seed="s"),
              tmp_path, CALIBRATED, batch_size=3)
    from msf.screen.runner import read_scores
    scored = read_scores(tmp_path, "bindpredict")
    assert len(scored) == 3
    excluded = [r for r in scored if r["status"] == "excluded"]
    assert [r["item_id"] for r in excluded] == [rows[0].domain_id]
