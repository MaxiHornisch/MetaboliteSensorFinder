"""Loop L0: build DeorphBench.

The only module permitted to read post-cutoff data. It must never execute in a session
that also scores a loop version; scripts/guard.py session-isolation enforces this.

Protocol is frozen in benchmarks/curation-protocol.md and is normative.
"""

from __future__ import annotations


def build_benchmark(cutoff: str, freeze: str) -> None:
    """Build the benchmark for one cutoff and freeze date.

    The step that determines validity is dating. An assignment is dated by EARLIEST
    PRIMARY PUBLICATION, never by database release, and never by a literature index date.
    A pairing appearing in a later release may have been published years earlier, and a
    real verified example exists of a paper published 2017-12-31 carrying an index date
    of 2019-03-26. Getting this wrong makes results look BETTER, so nothing downstream
    would catch it.

    Orphan status at the cutoff is established from the GtoPdb archived dump for the
    release current at that date, not by filtering the live database.

    This function may NOT relax inclusion criteria I1 to I5 to increase the item count.
    If N is too small, the permitted responses are an earlier cutoff, more protein
    families, or non-human orthologues as a separate stratum. Any relaxation needs a
    human decision recorded in benchmarks/curation-log.md.
    """
    raise NotImplementedError(
        "T-007. Blocked on the snapshot machinery T-005 and the date filter T-006. "
        "Report the honest item count per stratum when implemented: if the benchmark is "
        "too small to support the claims the project wants to make, that is the single "
        "most important thing to report, and it goes in JOURNAL.md BEFORE anyone "
        "computes a metric against it."
    )
