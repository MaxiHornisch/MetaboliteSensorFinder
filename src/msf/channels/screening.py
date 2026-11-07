"""Screening channel: docking and co-folding against a gated pocket.

Carries the central scientific prohibition of the project.

A raw docking score is never a cross-ligand ranking signal. Empirical scoring functions
rank poses within one ligand acceptably and rank different molecules against each other
poorly. What this module emits instead is a decoy-calibrated z-score and a library
percentile. The loopspec schema admits no option for a raw score, and the artifact schema
rejects one.
"""

from __future__ import annotations


def screen(target: str, pocket_verdict: dict, library: str, run_id: str) -> dict:
    """Score a library against one gated pocket.

    Preconditions, all hard:
      * pocket_verdict is usable or marginal. On no_usable_pocket this returns an empty
        bundle with that reason and does NOT dock anyway.
      * the decoy property-match test has passed, otherwise every enrichment number
        computed downstream is meaningless while looking excellent.

    Always reported, because each is a known artifact rather than a finding:
      * whether anything separated from the decoys at all (often nothing does)
      * disagreement between docking and co-folding, never averaged away
      * any hit driven by a single outlier conformer
      * whether scores correlate with molecular weight, which is the fastest way to
        detect that the pipeline is measuring size rather than fit
    """
    raise NotImplementedError("T-014. Blocked on T-012 (structure) and T-013 (chemistry).")
