"""Simulated DiffDock worker: planted truth, scripted scores, no network, no real docking.

DiffDock is not installed. This module lets the runner, validators and checkpointing be
exercised against a DiffDock-shaped worker. Every row it returns is labelled
`worker == "simulated-diffdock"`. Its scores are NOT evidence about any ligand or domain.
"""

from __future__ import annotations

import hashlib
import math

from msf.screen.runner import output_sha256


def _u(seed: str, key: str) -> float:
    """Deterministic value in [0, 1) from a seed and a key. No random module state."""
    return int(hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()[:12], 16) / 16**12


def band_for(score: float) -> str:
    if score > 0:
        return "high"
    if score >= -1.5:
        return "moderate"
    return "low"


class SimulatedDiffDock:
    """Scripted DiffDock-shaped worker. Positives score around +0.5, negatives around -2.5."""

    name = "simulated-diffdock"
    version = "0.1.0"

    def __init__(
        self,
        truth: set[str],
        seed: str,
        *,
        ligand_heavy_atoms: dict[str, int] | None = None,
        size_bias: bool = False,
        corrupt_jobs: frozenset[int] = frozenset(),
        drop_ids: frozenset[str] = frozenset(),
        empty_pose_ids: frozenset[str] = frozenset(),
    ) -> None:
        self.truth = truth
        self.seed = seed
        self.ligand_heavy_atoms = ligand_heavy_atoms or {}
        self.size_bias = size_bias
        self.corrupt_jobs = corrupt_jobs
        self.drop_ids = drop_ids
        self.empty_pose_ids = empty_pose_ids
        self._jobs: dict[str, tuple[int, list[dict]]] = {}
        self._submitted = 0

    def _heavy(self, item_id: str) -> int:
        ligand_id = item_id.split("|", 1)[-1]
        return self.ligand_heavy_atoms.get(ligand_id, self.ligand_heavy_atoms.get(item_id, 0))

    def _score(self, item_id: str) -> float:
        jitter = _u(self.seed, "score|" + item_id) * 2 - 1
        if item_id in self.truth:
            score = 0.5 + jitter * 0.4
        else:
            score = -2.5 + jitter * 0.6
        if self.size_bias:
            score += 0.05 * self._heavy(item_id)
        return round(score, 6)

    def submit(self, stage: str, items: list[dict]) -> str:
        job_no = self._submitted
        self._submitted += 1
        job_id = f"diffdock-job-{job_no}"
        self._jobs[job_id] = (job_no, list(items))
        return job_id

    def fetch(self, job_id: str) -> list[dict]:
        job_no, items = self._jobs[job_id]
        rows: list[dict] = []
        for item in items:
            item_id, sha = item["item_id"], item["sha256"]
            if item_id in self.drop_ids:
                continue
            score = self._score(item_id)
            rows.append({
                "item_id": item_id,
                "input_sha256": sha,
                "status": "scored",
                "score": score,
                "confidence_band": band_for(score),
                "pose_count": 0 if item_id in self.empty_pose_ids else 10,
                "clash_count": int(_u(self.seed, "clash|" + item_id) * 3),
                "plddt_domain": round(60 + _u(self.seed, "plddt|" + item_id) * 35, 2),
                "worker": self.name,
                "output_sha256": output_sha256(item_id, sha, score),
            })
        if job_no in self.corrupt_jobs and rows:
            rows[0] = {**rows[0], "output_sha256": "0" * 64}
        return rows


def validate_docking_row(row: dict) -> list[str]:
    """Return every problem with a docking row. An empty list means the row is valid."""
    problems: list[str] = []
    if row.get("pose_count", 0) < 1:
        problems.append("empty pose set")
    if row.get("clash_count", 0) < 0:
        problems.append(f"negative clash count: {row.get('clash_count')!r}")
    plddt = row.get("plddt_domain")
    if not isinstance(plddt, (int, float)) or not 0 <= plddt <= 100:
        problems.append(f"plddt_domain out of [0, 100]: {plddt!r}")
    score = row.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
        problems.append(f"invalid score: {score!r}")
    elif row.get("confidence_band") != band_for(score):
        problems.append(
            f"confidence_band {row.get('confidence_band')!r} inconsistent with score {score}")
    return problems
