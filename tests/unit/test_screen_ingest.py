"""Ingest rules for the domain CSV (docs/12 §4, docs/13 §2).

Count-in must equal count-out: every input row ends up as screened, context or rejected.
Nothing is dropped silently.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from msf.screen.ingest import REQUIRED_COLUMNS, ingest

HEADER = ",".join(REQUIRED_COLUMNS)
REAL_INPUT = Path(__file__).resolve().parents[3] / "input" / "Test_sequences.csv"


def _write(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "in.csv"
    path.write_text("\n".join((HEADER, *lines)) + "\n", encoding="utf-8")
    return path


def test_valid_domain_is_screened(tmp_path: Path) -> None:
    path = _write(tmp_path, "P1,G1,name,IPR1,n,domain,1,10,MKTAYIAKQR")
    result = ingest(path)
    assert [r.domain_id for r in result.screened] == ["P1:1-10:IPR1"]
    assert result.rejected == []


def test_family_rows_are_context_not_screened(tmp_path: Path) -> None:
    path = _write(tmp_path, "P1,G1,name,IPR2,n,family,1,10,MKTAYIAKQR")
    result = ingest(path)
    assert result.screened == []
    assert len(result.context) == 1


def test_length_mismatch_is_rejected_with_reason(tmp_path: Path) -> None:
    path = _write(tmp_path, "P1,G1,name,IPR1,n,domain,1,12,MKTAYIAKQR")
    result = ingest(path)
    assert result.screened == []
    assert "length 10 != span 12" in result.rejected[0]["reason"]


def test_non_standard_residue_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "P1,G1,name,IPR1,n,domain,1,10,MKTAYIAKQX")
    result = ingest(path)
    assert "non-standard residues" in result.rejected[0]["reason"]


def test_short_domain_is_flagged_not_dropped(tmp_path: Path) -> None:
    path = _write(tmp_path, "P2,G2,egf,IPR3,n,domain,1,16,MRWQEMGYIFYPRKLR")
    result = ingest(path)
    assert len(result.screened) == 1
    assert "short_domain" in result.screened[0].flags
    assert "peptide_out_of_scope" not in result.screened[0].flags


def test_duplicate_domain_is_rejected_second_time(tmp_path: Path) -> None:
    line = "P1,G1,name,IPR1,n,domain,1,10,MKTAYIAKQR"
    result = ingest(_write(tmp_path, line, line))
    assert len(result.screened) == 1
    assert result.rejected[0]["reason"] == "duplicate domain_id"


def test_count_in_equals_count_out(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "P1,G1,name,IPR1,n,domain,1,10,MKTAYIAKQR",
        "P1,G1,name,IPR2,n,family,1,10,MKTAYIAKQR",
        "P1,G1,name,IPR3,n,domain,1,3,MKTAYIAKQR",
    )
    result = ingest(path)
    assert result.counts["rows_in"] == 3
    assert result.counts["rows_in"] == (
        len(result.screened) + len(result.context) + len(result.rejected)
    )


@pytest.mark.skipif(not REAL_INPUT.exists(), reason="input CSV not present on this machine")
def test_real_input_counts_are_stable() -> None:
    result = ingest(REAL_INPUT)
    assert result.counts["rows_in"] == 413
    assert len(result.screened) == 257
    assert len(result.context) == 156
    assert result.rejected == []
    assert sum("short_domain" in r.flags for r in result.screened) == 28
