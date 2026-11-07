from __future__ import annotations

from msf.screen.diffdock_sim import SimulatedDiffDock, band_for, validate_docking_row
from msf.screen.runner import validate_batch

SEED = "test-diffdock"
DOMAINS = [f"DOM{i:03d}" for i in range(10)]
LIGANDS = ["LIGA", "LIGB", "LIGC", "LIGD"]
PAIRS = [f"{d}|{lig}" for d in DOMAINS for lig in LIGANDS]
TRUTH = {p for k, p in enumerate(PAIRS) if k % 4 == 0}
EXPECTED = [{"item_id": p, "sha256": f"sha-{p}"} for p in PAIRS]


def _fetch_all(worker: SimulatedDiffDock, items: list[dict]) -> list[dict]:
    return worker.fetch(worker.submit("docking", items))


def test_positives_score_higher_than_negatives_on_average():
    rows = _fetch_all(SimulatedDiffDock(TRUTH, SEED), EXPECTED)
    pos = [r["score"] for r in rows if r["item_id"] in TRUTH]
    neg = [r["score"] for r in rows if r["item_id"] not in TRUTH]
    assert sum(pos) / len(pos) > sum(neg) / len(neg) + 2.0


def test_band_boundaries():
    assert band_for(0.0) == "moderate"
    assert band_for(-1.5) == "moderate"
    assert band_for(-1.6) == "low"
    assert band_for(0.01) == "high"


def test_corrupt_job_fails_and_retry_passes():
    worker = SimulatedDiffDock(TRUTH, SEED, corrupt_jobs=frozenset({0}))
    bad = _fetch_all(worker, EXPECTED)
    assert validate_batch(EXPECTED, bad)
    good = _fetch_all(worker, EXPECTED)
    assert validate_batch(EXPECTED, good) == []


def test_dropped_id_is_missing_from_rows():
    drop = PAIRS[3]
    worker = SimulatedDiffDock(TRUTH, SEED, drop_ids=frozenset({drop}))
    rows = _fetch_all(worker, EXPECTED)
    assert drop not in {r["item_id"] for r in rows}
    problems = validate_batch(EXPECTED, rows)
    assert any("count mismatch" in p for p in problems)


def test_empty_pose_ids_fail_validate_docking_row():
    empty = PAIRS[5]
    worker = SimulatedDiffDock(TRUTH, SEED, empty_pose_ids=frozenset({empty}))
    rows = {r["item_id"]: r for r in _fetch_all(worker, EXPECTED)}
    assert "empty pose set" in validate_docking_row(rows[empty])
    other = next(r for k, r in rows.items() if k != empty)
    assert validate_docking_row(other) == []


def test_size_bias_raises_score_for_larger_ligands():
    item = PAIRS[0]
    lig = item.split("|", 1)[1]
    plain = _fetch_all(SimulatedDiffDock(TRUTH, SEED), EXPECTED)
    biased = _fetch_all(
        SimulatedDiffDock(TRUTH, SEED, size_bias=True, ligand_heavy_atoms={lig: 40}), EXPECTED)
    base = {r["item_id"]: r["score"] for r in plain}
    shifted = {r["item_id"]: r["score"] for r in biased}
    assert shifted[item] > base[item]
    assert abs((shifted[item] - base[item]) - 2.0) < 1e-5


def test_output_identical_across_two_runs_with_same_seed():
    a = _fetch_all(SimulatedDiffDock(TRUTH, SEED), EXPECTED)
    b = _fetch_all(SimulatedDiffDock(TRUTH, SEED), EXPECTED)
    assert a == b
    assert all(r["worker"] == "simulated-diffdock" for r in a)
