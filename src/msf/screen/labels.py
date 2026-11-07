"""Known domain-ligand labels for the screen, from the supplied binding table (docs/13 §3 S0).

Only exact domain matches are labelled: same UniProt accession and the same start and end.
Every label carries its source and an explicit date status. The table is undated, so no
label can enter a time-split benchmark (L0) on its own. Labels here are calibration and
harness positives, and every report must say so.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from msf.screen.ingest import IngestResult

BINDING_REQUIRED = ("uniprot_id", "domain_start", "domain_end", "chebi", "ligand_name",
                    "binding_site", "binding_site_evidence")


@dataclass(frozen=True)
class LabelReport:
    labels: list[dict]
    protein_only: int
    ligands: int
    matched_domains: int
    source_sha256: str


def _key(uniprot: str, start: int, end: int) -> tuple[str, int, int]:
    return (uniprot, start, end)


def load_labels(binding_csv: Path, screened: list) -> LabelReport:
    """Match the binding table to screened domains by exact (uniprot, start, end)."""
    csv.field_size_limit(10**9)
    path = Path(binding_csv)
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in BINDING_REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing columns {missing}")
        bind = list(reader)

    spans = {_key(r.uniprot_id, r.start, r.end): r for r in screened}
    proteins = {r.uniprot_id for r in screened}
    labels: list[dict] = []
    matched: set[str] = set()
    protein_only = 0
    seen: set[tuple[str, str]] = set()
    for b in bind:
        uniprot = b["uniprot_id"].strip()
        start, end = int(b["domain_start"]), int(b["domain_end"])
        row = spans.get(_key(uniprot, start, end))
        if row is None:
            if uniprot in proteins:
                protein_only += 1
            continue
        pair = (row.domain_id, b["chebi"].strip())
        if pair in seen:
            continue
        seen.add(pair)
        matched.add(row.domain_id)
        labels.append({
            "domain_id": row.domain_id,
            "uniprot_id": uniprot,
            "chebi": b["chebi"].strip(),
            "ligand_name": b["ligand_name"].strip(),
            "binding_site": b["binding_site"].strip(),
            "binding_site_evidence": b["binding_site_evidence"].strip() or None,
            "source": "metabolite_binding_sequences_human.csv",
            "source_sha256": source_sha,
            "date_status": "undated",
            "time_split_usable": False,
            "contamination_bin": "not_probed",
        })
    labels.sort(key=lambda x: (x["domain_id"], x["chebi"]))
    return LabelReport(labels, protein_only, len({x["chebi"] for x in labels}),
                       len(matched), source_sha)


def write_labels(report: LabelReport, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(report.labels, sort_keys=True).encode()).hexdigest()[:12]
    path = out_dir / f"labels-{digest}.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in report.labels:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def smiles_coverage(workbook: Path, chebi_names: dict[str, str]) -> dict:
    """Which labelled ligands have a SMILES in the supplied workbook.

    The workbook has names and ChEMBL IDs, not ChEBI IDs, so matching is by name only and
    case-insensitive. Any name that does not match is reported, not guessed.
    """
    import openpyxl

    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() for h in rows[0]]
    idx = {h: i for i, h in enumerate(header)}
    need = ("Metabolite_name", "Canonical_SMILES")
    if not all(n in idx for n in need):
        raise ValueError(f"workbook needs columns {need}, found {header}")
    by_name = {str(r[idx["Metabolite_name"]]).strip().lower(): str(r[idx["Canonical_SMILES"]]).strip()
               for r in rows[1:] if r and r[idx["Metabolite_name"]]}
    matched = {c: by_name[n.lower()] for c, n in chebi_names.items() if n.lower() in by_name}
    return {"supplied": len(by_name), "matched_labelled_ligands": len(matched),
            "matched": sorted(matched), "unmatched_labelled_ligands": len(chebi_names) - len(matched)}
