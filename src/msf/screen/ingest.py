"""Ingest the domain CSV for the screen (docs/12 §4).

Every input row ends up in exactly one bucket: screened, context or rejected.
Count-in equals count-out, and that is checked before the function returns.

    screened  entry_type == domain, passed validation. These go to the workers.
    context   entry_type == family. Kept as context only. Not screened, so a
              family span is never counted twice alongside the domains inside it.
    rejected  failed validation, with a reason. Written to the manifest, never dropped.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = (
    "uniprot_id", "gene_name", "protein_name", "interpro_id", "interpro_name",
    "entry_type", "domain_start", "domain_end", "domain_sequence",
)
STANDARD_RESIDUES = frozenset("ACDEFGHIKLMNPQRSTVWY")
# Domains this short are flagged, not excluded. A length alone does not make a peptide: the
# input has 28 EGF-like and similar domains of 30 aa or fewer. Peptide exclusion under I4
# (docs/04 §1.2) needs a full-length protein context we do not have here, so it is not applied.
SHORT_DOMAIN_MAX_LENGTH = 30


@dataclass(frozen=True)
class Row:
    row_no: int
    uniprot_id: str
    gene_name: str
    protein_name: str
    interpro_id: str
    interpro_name: str
    entry_type: str
    start: int
    end: int
    sequence: str
    flags: tuple[str, ...]

    @property
    def domain_id(self) -> str:
        return f"{self.uniprot_id}:{self.start}-{self.end}:{self.interpro_id}"

    @property
    def sequence_sha256(self) -> str:
        return hashlib.sha256(self.sequence.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class IngestResult:
    screened: list[Row]
    context: list[Row]
    rejected: list[dict]
    counts: dict
    file_sha256: str


def _parse(row_no: int, raw: dict, seen: set[tuple[str, str]]) -> tuple[Row | None, str | None]:
    entry = (raw["entry_type"] or "").strip()
    if entry not in ("domain", "family"):
        return None, f"unknown entry_type {entry!r}"
    try:
        start, end = int(raw["domain_start"]), int(raw["domain_end"])
    except (TypeError, ValueError):
        return None, "non-integer coordinates"
    if not 1 <= start <= end:
        return None, "coordinates out of order"
    sequence = (raw["domain_sequence"] or "").strip().upper()
    if len(sequence) != end - start + 1:
        return None, f"length {len(sequence)} != span {end - start + 1}"
    bad = sorted(set(sequence) - STANDARD_RESIDUES)
    if bad:
        return None, f"non-standard residues {bad}"

    row = Row(
        row_no=row_no,
        uniprot_id=raw["uniprot_id"].strip(),
        gene_name=raw["gene_name"].strip(),
        protein_name=raw["protein_name"].strip(),
        interpro_id=raw["interpro_id"].strip(),
        interpro_name=raw["interpro_name"].strip(),
        entry_type=entry,
        start=start,
        end=end,
        sequence=sequence,
        flags=(("short_domain",)
               if entry == "domain" and len(sequence) <= SHORT_DOMAIN_MAX_LENGTH else ()),
    )
    key = (entry, row.domain_id)
    if key in seen:
        return None, "duplicate domain_id"
    seen.add(key)
    return row, None


def ingest(path: Path) -> IngestResult:
    """Validate a domain CSV and split it into screened, context and rejected rows."""
    path = Path(path)
    file_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    screened: list[Row] = []
    context: list[Row] = []
    rejected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    rows_in = 0

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing columns {missing}")
        for row_no, raw in enumerate(reader, start=2):
            rows_in += 1
            row, reason = _parse(row_no, raw, seen)
            if reason is not None:
                rejected.append({"row_no": row_no, "reason": reason})
            elif row.entry_type == "domain":
                screened.append(row)
            else:
                context.append(row)

    counts = {
        "rows_in": rows_in,
        "screened": len(screened),
        "context": len(context),
        "rejected": len(rejected),
    }
    if rows_in != len(screened) + len(context) + len(rejected):
        raise AssertionError(f"count-in != count-out: {counts}")
    return IngestResult(screened, context, rejected, counts, file_sha256)
