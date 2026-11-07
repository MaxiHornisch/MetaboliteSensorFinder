"""Physics regressions: does the scientific stack actually work?

Independent of the benchmark. These catch the class of bug where the whole stack is
silently misconfigured and still returns a normal-looking ranked list.

Pass/fail. Gates L2. See docs/04-EVALUATION.md section 6.
"""

import pytest

pytestmark = pytest.mark.physics

REDOCK_RMSD_THRESHOLD_A = 2.0
REDOCK_SUCCESS_FRACTION = 0.80


@pytest.mark.xfail(reason="T-009 not implemented", strict=False)
def test_redock_rmsd():
    """Re-docking a ligand into its own co-crystal recovers the crystal pose within
    2.0 A RMSD on at least 80% of the fixed 30-complex fixture set."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-009 not implemented", strict=False)
def test_crossdock_degrades_but_beats_random():
    """A sanity ORDERING, not an absolute threshold.

    Cross-docking into a different holo structure of the same protein must be worse
    than redocking and better than random. If that ordering breaks, something
    fundamental is misconfigured.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-009 not implemented", strict=False)
def test_known_affinity_correlation_within_band():
    """Spearman correlation with measured affinity must sit inside a pre-registered band.

    Note the CEILING as well as the floor: a suspiciously high correlation indicates
    leakage, not success.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-013 not implemented", strict=False)
def test_protonation_invariance():
    """Scores stable under correct alternative protonation states at pH 7.4.

    A carboxylate modelled neutral changes every downstream score and produces no
    error message at all.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="classical docking distinguishes enantiomers poorly", strict=False)
def test_chirality_sensitivity():
    """DECLARED LIMITATION, kept visible rather than omitted.

    Enantiomer pairs with known differential activity should be distinguished.
    Classical docking largely cannot do this, which matters for a metabolome full of
    stereoisomers. Recorded as an expected failure so it stays in the test report
    instead of being quietly dropped.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-009 not implemented", strict=False)
def test_units_and_signs_round_trip():
    """Affinity units, log conventions and score signs round-trip correctly.

    The most embarrassing and most common bug class in this kind of pipeline.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-009 not implemented", strict=False)
def test_inchikey_survives_format_conversion():
    """Format conversion silently mangling structures is the most common unreported
    bug in pipelines like this. Round-trip every conversion and compare InChIKeys."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-023 not implemented", strict=False)
def test_determinism():
    """Same input and seed gives the same output, bit-for-bit where the tool allows.

    The run manifest records which tools cannot be made deterministic.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-014 not implemented", strict=False)
def test_scores_not_merely_tracking_molecular_weight():
    """The fastest way to detect that the pipeline measures size rather than fit.

    If docking score correlates strongly with molecular weight across the library,
    the top hits are a scoring-function bias and not a finding.
    """
    raise NotImplementedError
