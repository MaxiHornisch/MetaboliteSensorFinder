"""Batch runner for one screening stage (docs/12 §3, docs/13 §2 and §3 S2).

Invariants, each enforced in code and each covered by tests/unit/test_screen_runner.py:

  * count-in equals count-out for every batch. A missing item fails the batch.
  * every returned score is checked against its input hash and an output hash.
  * a failed batch is retried, up to max_retries, then raises BatchFailed.
  * a batch is checkpointed atomically. A completed batch is never recomputed.
  * every row is written, including excluded and error rows. Filtering sets an
    `advanced` flag and never removes a row (D5).
  * with uncalibrated thresholds nothing advances. `advanced` is None, not False.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from msf.screen.ingest import Row


class BatchFailed(RuntimeError):
    """A batch failed validation on every attempt. The run stops; nothing is skipped."""


class Worker(Protocol):
    name: str
    version: str

    def submit(self, stage: str, items: list[dict]) -> str:
        """Submit eligible items ({item_id, sha256}). Returns a job id."""

    def fetch(self, job_id: str) -> list[dict]:
        """Return one row per submitted item: a scored row or an explicit error row."""


@dataclass(frozen=True)
class Thresholds:
    calibrated: bool
    cuts: dict[str, float] = field(default_factory=dict)
    source: str | None = None

    def advance(self, stage: str, row: dict) -> tuple[bool | None, str]:
        if row.get("status") == "excluded":
            return None, "excluded"
        if row.get("status") == "error":
            return False, "error"
        if not self.calibrated:
            return None, "uncalibrated"
        return bool(row["score"] >= self.cuts[stage]), "calibrated"


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def output_sha256(item_id: str, input_sha256: str, score: float) -> str:
    return hashlib.sha256(_canonical(
        {"item_id": item_id, "input_sha256": input_sha256, "score": score})).hexdigest()


def validate_batch(expected: list[dict], rows: list[dict]) -> list[str]:
    """Return every problem found. An empty list means the batch is accepted."""
    problems: list[str] = []
    want = {e["item_id"]: e["sha256"] for e in expected}
    got_ids = [r.get("item_id") for r in rows]
    if len(got_ids) != len(expected) or len(set(got_ids)) != len(got_ids):
        problems.append(f"count mismatch: expected {len(expected)} rows, got {len(got_ids)}")
    for row in rows:
        item_id = row.get("item_id")
        if item_id not in want:
            problems.append(f"unexpected item {item_id!r}")
            continue
        if row.get("input_sha256") != want[item_id]:
            problems.append(f"input hash mismatch for {item_id}")
            continue
        if row.get("status") == "error":
            continue
        score = row.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
            problems.append(f"invalid score for {item_id}: {score!r}")
            continue
        if row.get("output_sha256") != output_sha256(item_id, want[item_id], float(score)):
            problems.append(f"output checksum mismatch for {item_id}")
    return problems


@dataclass(frozen=True)
class Item:
    """Anything the runner can schedule: a domain, or a domain-ligand pair."""

    item_id: str
    input_sha256: str
    flags: tuple[str, ...] = ()


def _as_item(x: Row | Item) -> Item:
    if isinstance(x, Item):
        return x
    return Item(item_id=x.domain_id, input_sha256=x.sequence_sha256, flags=x.flags)


def wire_id(blind_salt: str, item_id: str) -> str:
    """Opaque id sent to a worker. Without the salt, a worker cannot tell which item is which."""
    return hashlib.sha256(f"{blind_salt}|{item_id}".encode()).hexdigest()[:20]


def _batches(items: list[Item], batch_size: int) -> list[list[Item]]:
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def run_stage(
    stage: str,
    rows: list[Row] | list[Item],
    worker: Worker,
    run_dir: Path,
    thresholds: Thresholds,
    *,
    batch_size: int = 100,
    max_retries: int = 2,
    max_batches: int | None = None,
    blind_salt: str | None = None,
) -> dict:
    """Run one stage over every row. `max_batches` stops early, to simulate a kill.

    With `blind_salt`, the worker sees only opaque wire ids (docs/11 P-009). The stored row keeps
    the real item_id and records its wire_id. The output checksum covers the wire id, because
    that is what the worker signed.
    """
    batches_dir = Path(run_dir) / "batches"
    batches_dir.mkdir(parents=True, exist_ok=True)
    items = [_as_item(r) for r in rows]
    summary = {"stage": stage, "rows_in": len(items), "rows_out": 0,
               "retries": 0, "batches_run": 0, "batches_skipped": 0}

    for n, batch in enumerate(_batches(items, batch_size)):
        if max_batches is not None and summary["batches_run"] >= max_batches:
            break
        path = batches_dir / f"{stage}-{n:05d}.jsonl"
        if path.exists():
            summary["batches_skipped"] += 1
            summary["rows_out"] += sum(1 for _ in path.open(encoding="utf-8"))
            continue

        eligible_items = [r for r in batch if "peptide_out_of_scope" not in r.flags]
        out: list[dict] = [
            {"item_id": r.item_id, "input_sha256": r.input_sha256, "status": "excluded",
             "advanced": None, "advance_status": "excluded"}
            for r in batch if "peptide_out_of_scope" in r.flags
        ]

        if eligible_items:
            if blind_salt is None:
                sent = {r.item_id: r.item_id for r in eligible_items}
            else:
                sent = {r.item_id: wire_id(blind_salt, r.item_id) for r in eligible_items}
            back = {w: orig for orig, w in sent.items()}
            eligible = [{"item_id": sent[r.item_id], "sha256": r.input_sha256}
                        for r in eligible_items]
            worker_rows: list[dict] | None = None
            problems: list[str] = []
            for attempt in range(max_retries + 1):
                job = worker.submit(stage, eligible)
                candidate = worker.fetch(job)
                problems = validate_batch(eligible, candidate)
                if not problems:
                    worker_rows = candidate
                    break
                summary["retries"] += 1
            if worker_rows is None:
                raise BatchFailed(f"{stage} batch {n}: {'; '.join(problems)}")
            for row in worker_rows:
                if blind_salt is not None:
                    row["wire_id"] = row["item_id"]
                    row["item_id"] = back[row["item_id"]]
            out.extend(worker_rows)

        for row in out:
            advanced, status = thresholds.advance(stage, row)
            row["advanced"] = advanced
            row["advance_status"] = status
        if len(out) != len(batch):
            raise BatchFailed(f"{stage} batch {n}: count mismatch {len(out)} != {len(batch)}")

        out.sort(key=lambda r: r["item_id"])
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            for row in out:
                handle.write(_canonical(row).decode("utf-8") + "\n")
        os.replace(tmp, path)
        summary["batches_run"] += 1
        summary["rows_out"] += len(out)

    return summary


def read_scores(run_dir: Path, stage: str) -> list[dict]:
    rows: list[dict] = []
    for path in sorted((Path(run_dir) / "batches").glob(f"{stage}-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def scores_hash(run_dir: Path) -> str:
    """Hash of every batch file in order. Two runs with equal hashes wrote identical scores."""
    digest = hashlib.sha256()
    for path in sorted((Path(run_dir) / "batches").glob("*.jsonl")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_thresholds(path: Path) -> Thresholds:
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return Thresholds(
        calibrated=bool(data.get("calibrated", False)),
        cuts={k: float(v) for k, v in (data.get("cuts") or {}).items()},
        source=data.get("calibration_source"),
    )
