"""Loop S1: simulation (docs/13 §3). Planted truth, scripted workers, no network.

The simulated scores are NOT evidence about any protein. They exist to test the runner,
the validators, the checkpointing and the metrics, before any real worker is used.
Every result this module produces is labelled `simulation` in its output.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from msf.screen.ingest import Row
from msf.screen.metrics import SIZE_ARTIFACT_RHO, recall_on_positives, size_correlation
from msf.screen.runner import (
    BatchFailed,
    Thresholds,
    output_sha256,
    read_scores,
    run_stage,
    scores_hash,
)

SIM_CUT = 0.5
SIM_THRESHOLDS = Thresholds(
    calibrated=True,
    cuts={"bindpredict": SIM_CUT},
    source="simulation: planted truth, not a calibration on real data",
)


def _u(seed: str, key: str) -> float:
    """Deterministic value in [0, 1) from a seed and a key. No random module state."""
    return int(hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()[:12], 16) / 16**12


def planted_truth(item_ids: list[str], rate: float, seed: str) -> set[str]:
    return {i for i in item_ids if _u(seed + "|truth", i) < rate}


class SimulatedWorker:
    """Scripted worker. Positives score around 0.75, negatives around 0.25."""

    name = "simulated"
    version = "0.1.0"

    def __init__(
        self,
        truth: set[str],
        seed: str,
        *,
        lengths: dict[str, int] | None = None,
        size_artifact: bool = False,
        corrupt_jobs: frozenset[int] = frozenset(),
        drop_ids: frozenset[str] = frozenset(),
        invalid_ids: frozenset[str] = frozenset(),
    ) -> None:
        self.truth = truth
        self.seed = seed
        self.lengths = lengths or {}
        self.size_artifact = size_artifact
        self.corrupt_jobs = corrupt_jobs
        self.drop_ids = drop_ids
        self.invalid_ids = invalid_ids
        self._jobs: dict[str, tuple[int, list[dict]]] = {}
        self._submitted = 0

    def _score(self, item_id: str) -> float:
        base = 0.75 if item_id in self.truth else 0.25
        score = base + (_u(self.seed, item_id) - 0.5) * 0.3
        if self.size_artifact:
            score += self.lengths.get(item_id, 0) / 400.0
        return round(score, 6)

    def submit(self, stage: str, items: list[dict]) -> str:
        job_no = self._submitted
        self._submitted += 1
        job_id = f"job-{job_no}"
        self._jobs[job_id] = (job_no, list(items))
        return job_id

    def fetch(self, job_id: str) -> list[dict]:
        job_no, items = self._jobs[job_id]
        rows: list[dict] = []
        for item in items:
            item_id, sha = item["item_id"], item["sha256"]
            if item_id in self.drop_ids:
                continue
            if item_id in self.invalid_ids:
                rows.append({"item_id": item_id, "input_sha256": sha,
                             "score": "not-a-number", "output_sha256": "x"})
                continue
            score = self._score(item_id)
            rows.append({"item_id": item_id, "input_sha256": sha, "status": "scored",
                         "score": score,
                         "output_sha256": output_sha256(item_id, sha, score)})
        if job_no in self.corrupt_jobs and rows:
            rows[0] = {**rows[0], "output_sha256": "0" * 64}
        return rows


def _synthetic_rows(n_items: int, seed: str) -> list[Row]:
    rows = []
    for i in range(n_items):
        length = 40 + int(_u(seed + "|len", str(i)) * 360)
        sequence = "".join("ACDEFGHIKLMNPQRSTVWY"[int(_u(seed + "|aa", f"{i}|{j}") * 20)]
                           for j in range(length))
        rows.append(Row(
            row_no=i + 2, uniprot_id=f"SIM{i:04d}", gene_name="SIM", protein_name="simulated",
            interpro_id="IPRSIM", interpro_name="simulated", entry_type="domain",
            start=1, end=length, sequence=sequence, flags=(),
        ))
    return rows


def run_simulation_suite(
    *,
    n_items: int = 60,
    out_dir: Path,
    seed: str = "msf-sim-v1",
    rows: list[Row] | None = None,
) -> list[dict]:
    """Run every S1 scenario. Each result says whether it passed and why.

    Pass `rows` to run the suite on real ingested domains. Truth is still planted.
    """
    rows = rows if rows is not None else _synthetic_rows(n_items, seed)
    ids = [r.domain_id for r in rows]
    lengths = {r.domain_id: r.end - r.start + 1 for r in rows}
    truth = planted_truth(ids, rate=0.2, seed=seed)
    batch = max(1, len(rows) // 3)
    out_dir = Path(out_dir)
    results: list[dict] = []

    def fresh(name: str) -> Path:
        path = out_dir / name
        if path.exists():
            shutil.rmtree(path)
        return path

    def record(name: str, passed: bool, detail: str) -> None:
        results.append({"scenario": name, "passed": bool(passed), "detail": detail})

    happy_dir = fresh("happy")
    run_stage("bindpredict", rows, SimulatedWorker(truth, seed, lengths=lengths),
              happy_dir, SIM_THRESHOLDS, batch_size=batch)
    happy_scores = read_scores(happy_dir, "bindpredict")
    happy_hash = scores_hash(happy_dir)
    recall = recall_on_positives(happy_scores, truth)
    record("planted_recall", recall is not None and recall >= 0.95,
           f"recall on planted positives = {recall}")

    clean_rho = size_correlation(happy_scores, lengths)
    artifact_dir = fresh("size_artifact")
    run_stage("bindpredict", rows,
              SimulatedWorker(truth, seed, lengths=lengths, size_artifact=True),
              artifact_dir, SIM_THRESHOLDS, batch_size=batch)
    artifact_rho = size_correlation(read_scores(artifact_dir, "bindpredict"), lengths)
    record("size_artifact_detected",
           artifact_rho is not None and clean_rho is not None
           and artifact_rho > SIZE_ARTIFACT_RHO and clean_rho <= SIZE_ARTIFACT_RHO,
           f"rho clean={clean_rho} artifact={artifact_rho} cut={SIZE_ARTIFACT_RHO}")

    corrupt_dir = fresh("corrupt")
    corrupt = run_stage("bindpredict", rows,
                        SimulatedWorker(truth, seed, lengths=lengths, corrupt_jobs=frozenset({0})),
                        corrupt_dir, SIM_THRESHOLDS, batch_size=batch)
    record("corrupt_batch_retried",
           corrupt["retries"] == 1 and scores_hash(corrupt_dir) == happy_hash,
           f"retries={corrupt['retries']}, output identical to clean run="
           f"{scores_hash(corrupt_dir) == happy_hash}")

    drop_dir = fresh("drop")
    try:
        run_stage("bindpredict", rows,
                  SimulatedWorker(truth, seed, lengths=lengths, drop_ids=frozenset({ids[0]})),
                  drop_dir, SIM_THRESHOLDS, batch_size=batch)
        record("silent_drop_rejected", False, "dropped item was accepted")
    except BatchFailed as exc:
        record("silent_drop_rejected", "count mismatch" in str(exc), str(exc))

    resume_dir = fresh("resume")
    run_stage("bindpredict", rows, SimulatedWorker(truth, seed, lengths=lengths),
              resume_dir, SIM_THRESHOLDS, batch_size=batch, max_batches=1)
    run_stage("bindpredict", rows, SimulatedWorker(truth, seed, lengths=lengths),
              resume_dir, SIM_THRESHOLDS, batch_size=batch)
    record("resume_byte_identical", scores_hash(resume_dir) == happy_hash,
           "hash after kill-and-resume equals uninterrupted hash")

    uncal_dir = fresh("uncalibrated")
    run_stage("bindpredict", rows, SimulatedWorker(truth, seed, lengths=lengths),
              uncal_dir, Thresholds(calibrated=False), batch_size=batch)
    uncal = read_scores(uncal_dir, "bindpredict")
    record("uncalibrated_advances_nothing",
           all(r["advanced"] is None for r in uncal) and len(uncal) == len(rows),
           f"{len(uncal)} rows written, none advanced")

    return results
