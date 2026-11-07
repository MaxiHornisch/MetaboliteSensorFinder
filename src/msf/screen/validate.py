"""Schema and integrity validation of a screen run directory (docs/02 §4, docs/14 §2).

Validation is code, not a prompt. Returns every problem found, never just the first.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from msf.screen.runner import read_scores

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "artifacts.schema.json"


def _validator(defname: str) -> jsonschema.Draft202012Validator:
    root = json.loads(SCHEMA.read_text(encoding="utf-8"))
    wrapper = {"$ref": f"#/$defs/{defname}", "$defs": root["$defs"]}
    return jsonschema.Draft202012Validator(wrapper)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_run(run_dir: Path) -> list[str]:
    run_dir = Path(run_dir)
    problems: list[str] = []

    evidence = _read_jsonl(run_dir / "evidence" / "evidence.jsonl")
    ev_ids = set()
    ev_val = _validator("EvidenceItem")
    for e in evidence:
        for err in ev_val.iter_errors(e):
            problems.append(f"evidence {e.get('evidence_id')}: {err.message}")
        ev_ids.add(e.get("evidence_id"))

    hyps = _read_jsonl(run_dir / "hypotheses" / "hypotheses.jsonl")
    h_val = _validator("Hypothesis")
    for h in hyps:
        for err in h_val.iter_errors(h):
            problems.append(f"hypothesis {h.get('hypothesis_id')}: {err.message}")
        for ref in h.get("supporting_evidence", []):
            if ref not in ev_ids:
                problems.append(f"hypothesis {h.get('hypothesis_id')} cites missing evidence {ref}")

    d_val = _validator("TargetDossier")
    for path in sorted((run_dir / "dossiers").glob("*.json")):
        dossier = json.loads(path.read_text(encoding="utf-8"))
        for err in d_val.iter_errors(dossier):
            problems.append(f"dossier {path.name}: {err.message}")

    for stage in ("bindpredict", "psichic"):
        if not read_scores(run_dir / "stages", stage):
            problems.append(f"stage {stage} has no rows")
    return problems
