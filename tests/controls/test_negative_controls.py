"""Negative controls: targets with no correct answer.

A control that PASSES -- that is, a pipeline that produces a confident answer here --
is a bug, not a result. These gate L2 and abort the run on failure.

See docs/04-EVALUATION.md section 5.1.
"""

import pytest

pytestmark = pytest.mark.controls

FALSE_CONFIDENCE_GATE = 0.10  # pre-registered


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_scrambled_sequence_yields_no_confident_hypothesis():
    """Residues shuffled preserving composition. Catches pipelines keyed on composition."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_shuffled_pairs_recover_at_chance():
    """Real proteins, permuted ground truth. Catches evaluation-harness bugs."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_sham_pocket_scores_like_random():
    """Docking box on a surface patch with no detected pocket."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_mirror_protein_is_distinguished():
    """D-amino-acid mirror image.

    A chirality-blind scoring function returns identical scores for the mirror image.
    Expected to reveal a real limitation of classical docking rather than to pass.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_designed_void_triggers_abstention():
    """A 'pocket' that is solvent. The loop must abstain."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_true_orphans_resemble_negatives_not_positives():
    """The most informative control.

    Genuine current orphans have no ground truth, but the loop's CONFIDENCE
    distribution on them must resemble the negative controls rather than the solved
    cases. If the loop is as confident here as on solved targets, its confidence
    means nothing -- and these are exactly the targets a researcher cares about.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-008 not implemented", strict=False)
def test_false_confidence_rate_below_gate():
    """Fraction of negative controls given p > 0.5 must be under the pre-registered gate."""
    raise NotImplementedError
