"""Loop drivers: L1 (one target) and L2 (score a loop version).

Narrative contracts are in docs/03-LOOPS.md and are normative. This module is the
executable form of them. Where the two disagree, the document wins and this module is
wrong.
"""

from __future__ import annotations


def run_target(loop: str, target: str, cutoff: str | None = None,
               run_id: str | None = None) -> None:
    """Loop L1: one protein, one audited, calibrated dossier.

    Ordering that matters:
      1. Five evidence channels in parallel subagents, NOT seeing each other. Their
         independence is what the fusion step assumes.
      2. screener runs only if structuralist returned a usable or marginal pocket
         verdict. On no_usable_pocket the channel is skipped, not forced.
      3. falsifier on every hypothesis, bounded at the loopspec refinement limit. At the
         bound a hypothesis passes forward WITH its unresolved attack attached.
      4. fusion applies the correlation discount, then calibration, then abstention.
      5. auditor re-derives every claim before scribe renders anything.

    Exits only when the dossier validates, every claim traces to an evidence id, the
    auditor reports zero unsupported claims, and either a probability or an abstention
    with a reason is recorded.
    """
    raise NotImplementedError("T-019. Blocked on the channel implementations T-012 to T-018.")


def evaluate_loop(loop: str, split: str = "dev") -> None:
    """Loop L2: score a loop version against DeorphBench.

    Controls run BEFORE metrics and abort on failure. That ordering is the point of the
    function: a benchmark number computed on a pipeline that failed its negative controls
    is worse than no number, because it will be believed.

    Refuses outright if split is sealed: unsealing requires an interactive human via
    scripts/unseal.py, and this code path cannot do it.
    """
    if split == "sealed":
        raise PermissionError(
            "The sealed split cannot be opened from code. A human runs scripts/unseal.py, "
            "once per loop version, and the unseal is recorded in a published log. "
            "See docs/07-VERSIONING.md section 4."
        )
    raise NotImplementedError("T-020. Blocked on T-019 and the baselines T-011.")
