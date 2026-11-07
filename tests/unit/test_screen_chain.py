"""The simulated chain: validation, blinding, the two-channel validator, and the controls."""

from __future__ import annotations

import json
from pathlib import Path

from msf.screen.chain import run_chain
from msf.screen.ingest import Row
from msf.screen.runner import Item, Thresholds, output_sha256, read_scores, run_stage, wire_id
from msf.screen.validate import validate_run

SEQ = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDA"


def _rows(n: int) -> list[Row]:
    return [Row(row_no=i + 2, uniprot_id=f"P{i:03d}", gene_name="G", protein_name="n",
                interpro_id="IPR1", interpro_name="n", entry_type="domain",
                start=1, end=len(SEQ), sequence=SEQ, flags=())
            for i in range(n)]


class Recorder:
    """A worker that records what it was sent, then scores every item 0.1."""

    name = "recorder"
    version = "0"

    def __init__(self) -> None:
        self.seen: list[str] = []
        self._jobs: dict[str, list[dict]] = {}

    def submit(self, stage: str, items: list[dict]) -> str:
        self.seen.extend(i["item_id"] for i in items)
        job = f"j{len(self._jobs)}"
        self._jobs[job] = items
        return job

    def fetch(self, job_id: str) -> list[dict]:
        return [{"item_id": i["item_id"], "input_sha256": i["sha256"], "status": "scored",
                 "score": 0.1, "output_sha256": output_sha256(i["item_id"], i["sha256"], 0.1)}
                for i in self._jobs[job_id]]


def test_chain_output_validates(tmp_path: Path) -> None:
    summary = run_chain(_rows(40), tmp_path / "run", seed="t")
    assert validate_run(tmp_path / "run") == []
    assert summary["counts"]["domains"] == 40


def test_single_channel_hypotheses_are_rejected_and_kept_on_record(tmp_path: Path) -> None:
    run_chain(_rows(40), tmp_path / "run", seed="t")
    rejected = json.loads((tmp_path / "run" / "hypotheses" / "rejected.json").read_text())
    assert all("single independent channel" in r["reason"] for r in rejected)
    stored = [json.loads(line) for line in
              (tmp_path / "run" / "hypotheses" / "hypotheses.jsonl").read_text().splitlines()
              if line.strip()]
    assert all(len(h["supporting_evidence"]) >= 2 for h in stored)


def test_methane_control_is_not_vacuous(tmp_path: Path) -> None:
    summary = run_chain(_rows(40), tmp_path / "run", seed="t")
    assert summary["controls"]["methane"]["n"] > 0
    assert summary["controls"]["methane"]["pass"] is True


def test_blinded_worker_sees_only_opaque_ids(tmp_path: Path) -> None:
    worker = Recorder()
    items = [Item(item_id=f"P{i}|SIM-L00", input_sha256="a" * 64) for i in range(3)]
    run_stage("psichic", items, worker, tmp_path, Thresholds(calibrated=False),
              blind_salt="salt")
    assert worker.seen == [wire_id("salt", i.item_id) for i in items]
    stored = read_scores(tmp_path, "psichic")
    assert {r["item_id"] for r in stored} == {i.item_id for i in items}
    assert {r["wire_id"] for r in stored} == set(worker.seen)
