"""Leakage controls L2-L6 and L8. See docs/04-EVALUATION.md section 2."""

import pytest

pytestmark = pytest.mark.controls


@pytest.mark.xfail(reason="T-005 not implemented", strict=False)
def test_snapshot_pinning_blocks_live_endpoints():
    """L2: during a benchmark run, no egress to un-pinned live database hosts."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-005 not implemented", strict=False)
def test_snapshot_hashes_verified_on_fetch():
    """L2: a tampered snapshot fails SHA-256 verification and the run aborts."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-007 not implemented", strict=False)
def test_splits_are_sequence_disjoint():
    """L3: all-vs-all identity between splits is below 30%.

    Splitting is by similarity CLUSTER, never by individual protein. A protein in dev
    whose 80%-identical homologue sits in sealed is leakage, and it is the easiest
    mistake in this whole area to make by accident.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-007 not implemented", strict=False)
def test_splits_are_scaffold_disjoint():
    """L4: Bemis-Murcko scaffolds do not cross splits."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-007 not implemented", strict=False)
def test_structures_after_cutoff_excluded():
    """L5: no structure deposited after the cutoff is reachable.

    Additionally, any structure of the target with ANY ligand is flagged, and results
    are reported both with and without those targets.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-013 not implemented", strict=False)
def test_decoys_not_separable_on_properties_alone():
    """L6: the most consequential decoy test.

    A logistic model on physicochemical descriptors alone must score near chance at
    separating actives from decoys. If it does not, every enrichment metric computed
    against this decoy set measures property differences rather than binding, while
    producing an excellent-looking AUC.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-010 not implemented", strict=False)
def test_contamination_probe_assigns_a_bin_to_every_item():
    """L7: cannot be closed, only measured.

    A time split stops tools from seeing the future. It does nothing about the model,
    whose training data contains the post-cutoff literature. Every item must carry a
    contamination score so that metrics can be reported per bin.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-021 not implemented", strict=False)
def test_sealed_split_cannot_be_read_by_an_agent():
    """L8: sealed is encrypted; unsealing requires an interactive human key."""
    raise NotImplementedError
