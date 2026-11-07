"""Stage metrics for the screen (docs/13 §4.2). Only what the MVP can compute today.

Every function returns None rather than a number when the inputs cannot support one.
A missing value is shown as missing, never as zero.
"""

from __future__ import annotations

from collections.abc import Iterable

from scipy.stats import spearmanr

# Provisional. Set on a simulation, not on real data. Recalibrate in S3 before use.
SIZE_ARTIFACT_RHO = 0.3


def _scored(rows: Iterable[dict]) -> list[dict]:
    return [r for r in rows if r.get("status") == "scored"]


def recall_on_positives(rows: Iterable[dict], truth: set[str]) -> float | None:
    positives = [r for r in _scored(rows) if r["item_id"] in truth]
    if not positives:
        return None
    if any(r["advanced"] is None for r in positives):
        return None
    return sum(bool(r["advanced"]) for r in positives) / len(positives)


def size_correlation(rows: Iterable[dict], lengths: dict[str, int]) -> float | None:
    """Spearman correlation between score and sequence length. High means the score tracks size."""
    scored = [r for r in _scored(rows) if r["item_id"] in lengths]
    if len(scored) < 3:
        return None
    rho, _ = spearmanr([r["score"] for r in scored], [lengths[r["item_id"]] for r in scored])
    return float(rho)
