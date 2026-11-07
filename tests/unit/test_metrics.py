"""Metric implementations verified against analytically known values.

These are real tests. Where a closed-form answer exists we assert it exactly; where only
bounds or orderings are analytic we assert those. A metric implementation that is merely
plausible is how an evaluation quietly reports the wrong number, so each function here is
pinned by a case whose answer was derived by hand rather than by running the code.
"""

import math

import numpy as np
import pytest

from msf.eval.metrics import (
    bedroc,
    bootstrap_ci,
    brier_score,
    decision_utility,
    enrichment_factor,
    expected_calibration_error,
    false_confidence_rate,
    mean_reciprocal_rank,
    paired_bootstrap_delta,
    recall_at_k,
    risk_coverage_curve,
    selective_accuracy_at_coverage,
)

# ------------------------------------------------------------------------- ranking


def test_recall_at_k_exact():
    # ranks 1, 2, 4, 50 -> at k=5 three of four are found.
    assert recall_at_k([1, 2, 4, 50], k=5) == pytest.approx(0.75)
    assert recall_at_k([1, 2, 4, 50], k=1) == pytest.approx(0.25)
    assert recall_at_k([1, 2, 4, 50], k=50) == pytest.approx(1.0)


def test_recall_at_k_rejects_zero_and_negative_ranks():
    """Ranks are 1-indexed. A 0 would silently inflate every recall."""
    with pytest.raises(ValueError):
        recall_at_k([0, 1], k=1)
    with pytest.raises(ValueError):
        recall_at_k([1, 2], k=0)


def test_mrr_exact():
    # (1/1 + 1/2 + 1/4) / 3 = 1.75 / 3
    assert mean_reciprocal_rank([1, 2, 4]) == pytest.approx(1.75 / 3)


def test_enrichment_factor_exact():
    # 1000 candidates, 1% cutoff = top 10. All 10 actives inside -> perfect enrichment.
    assert enrichment_factor(list(range(1, 11)), n_total=1000, fraction=0.01) == pytest.approx(100.0)
    # Half inside -> half the enrichment.
    ranks = list(range(1, 6)) + list(range(900, 905))
    assert enrichment_factor(ranks, n_total=1000, fraction=0.01) == pytest.approx(50.0)


def test_enrichment_factor_of_random_is_about_one():
    """EF is a multiplier over random, so a uniform spread must land near 1."""
    rng = np.random.default_rng(0)
    ranks = rng.choice(np.arange(1, 10_001), size=500, replace=False).tolist()
    assert enrichment_factor(ranks, n_total=10_000, fraction=0.01) == pytest.approx(1.0, abs=0.6)


def test_bedroc_bounds_and_extremes():
    """Perfect early enrichment approaches 1, worst approaches 0."""
    perfect = bedroc(list(range(1, 11)), n_total=1000, alpha=20.0)
    worst = bedroc(list(range(991, 1001)), n_total=1000, alpha=20.0)
    assert perfect == pytest.approx(1.0, abs=1e-3)
    assert worst == pytest.approx(0.0, abs=1e-3)
    assert 0.0 <= worst < perfect <= 1.0


def test_bedroc_is_early_weighted():
    """The whole point of BEDROC over AUC: moving actives earlier must matter a lot.

    Two rankings with identical AUC-relevant mass but different front-loading should
    separate sharply at alpha=20.
    """
    early = bedroc([1, 2, 3, 4, 5], n_total=1000, alpha=20.0)
    mid = bedroc([100, 101, 102, 103, 104], n_total=1000, alpha=20.0)
    assert early > mid
    assert early - mid > 0.5


def test_bedroc_rejects_out_of_range_ranks():
    with pytest.raises(ValueError):
        bedroc([1, 1001], n_total=1000)


# --------------------------------------------------------------------- calibration


def test_brier_score_exact():
    assert brier_score([1.0, 0.0], [True, False]) == pytest.approx(0.0)
    assert brier_score([0.0, 1.0], [True, False]) == pytest.approx(1.0)
    assert brier_score([0.5, 0.5], [True, False]) == pytest.approx(0.25)
    # (0.2-1)^2 + (0.9-1)^2 + (0.3-0)^2 = 0.64 + 0.01 + 0.09 = 0.74, /3
    assert brier_score([0.2, 0.9, 0.3], [True, True, False]) == pytest.approx(0.74 / 3)


def test_ece_is_near_zero_for_a_perfectly_calibrated_predictor():
    """Outcomes drawn as Bernoulli(p) are calibrated by construction."""
    rng = np.random.default_rng(7)
    probs = rng.uniform(0.0, 1.0, size=4000)
    outcomes = rng.uniform(size=4000) < probs
    assert expected_calibration_error(probs, outcomes, n_bins=10) < 0.03


def test_ece_detects_systematic_overconfidence():
    """A model claiming 0.9 and being right half the time must score about 0.4."""
    probs = [0.9] * 1000
    outcomes = [True] * 500 + [False] * 500
    assert expected_calibration_error(probs, outcomes, n_bins=10) == pytest.approx(0.4, abs=1e-6)


def test_ece_uses_equal_mass_bins():
    """Equal-width bins leave the extremes nearly empty, which is where a confident
    model is wrong. Equal-mass binning must populate every bin it creates."""
    probs = [0.95] * 100
    outcomes = [False] * 100
    assert expected_calibration_error(probs, outcomes, n_bins=10) == pytest.approx(0.95)


def test_ece_does_not_split_tied_probabilities_across_bins():
    """Regression for a real bug: ECE must not depend on the ORDER of the input.

    Naive equal-mass binning cuts by count, so a thousand identical 0.9 predictions get
    scattered across ten bins and the score becomes a function of how the rows happened
    to be sorted. All identical claims belong in one bin, giving |0.9 - 0.5| = 0.4.
    """
    probs = [0.9] * 1000
    ordered = [True] * 500 + [False] * 500
    interleaved = [True, False] * 500
    shuffled = list(
        np.random.default_rng(0).permutation(np.array(ordered, dtype=bool)).tolist()
    )

    expected = 0.4
    for outcomes in (ordered, interleaved, shuffled):
        assert expected_calibration_error(probs, outcomes, n_bins=10) == pytest.approx(
            expected, abs=1e-9
        )


def test_ece_is_invariant_to_row_order_in_general():
    """The same property on a realistic mixture of tied and untied predictions."""
    rng = np.random.default_rng(21)
    probs = np.concatenate([np.full(300, 0.7), np.full(300, 0.3), rng.uniform(size=400)])
    outcomes = rng.uniform(size=1000) < probs

    perm = rng.permutation(1000)
    a = expected_calibration_error(probs, outcomes, n_bins=10)
    b = expected_calibration_error(probs[perm], outcomes[perm], n_bins=10)
    assert a == pytest.approx(b, abs=1e-9)


# ------------------------------------------------------------- selective prediction


def test_risk_coverage_curve_shape():
    probs = [0.9, 0.8, 0.7, 0.1, 0.05]
    outcomes = [True, True, False, False, False]
    cov, acc = risk_coverage_curve(probs, outcomes)
    assert cov.tolist() == pytest.approx([0.2, 0.4, 0.6, 0.8, 1.0])
    # cumulative hits 1,2,2,2,2 over 1..5
    assert acc.tolist() == pytest.approx([1.0, 1.0, 2 / 3, 0.5, 0.4])


def test_selective_accuracy_at_coverage_exact():
    probs = [0.9, 0.8, 0.7, 0.1, 0.05]
    outcomes = [True, True, False, False, False]
    assert selective_accuracy_at_coverage(probs, outcomes, 0.2) == pytest.approx(1.0)
    assert selective_accuracy_at_coverage(probs, outcomes, 0.6) == pytest.approx(2 / 3)
    assert selective_accuracy_at_coverage(probs, outcomes, 1.0) == pytest.approx(0.4)


def test_selective_accuracy_beats_full_coverage_for_a_useful_model():
    """The property that makes this the primary metric: being selective should help.

    A model whose confidence carries information must score better on its top 20% than
    over everything. If it does not, the probabilities are decoration.
    """
    rng = np.random.default_rng(3)
    probs = rng.uniform(size=500)
    outcomes = rng.uniform(size=500) < probs
    top = selective_accuracy_at_coverage(probs, outcomes, 0.2)
    allc = selective_accuracy_at_coverage(probs, outcomes, 1.0)
    assert top > allc


def test_false_confidence_rate_exact():
    """Fed negative controls only: fraction given p > threshold."""
    assert false_confidence_rate([0.6, 0.4, 0.7], threshold=0.5) == pytest.approx(2 / 3)
    assert false_confidence_rate([0.1, 0.2, 0.3], threshold=0.5) == pytest.approx(0.0)


def test_decision_utility_exact():
    # Recommends the two above 0.5: one hit (+10), one miss (-1).
    probs = [0.9, 0.8, 0.1]
    outcomes = [True, False, True]
    assert decision_utility(probs, outcomes, recommend_above=0.5) == pytest.approx(9.0)


def test_decision_utility_of_total_abstention_is_zero():
    """Abstaining everywhere earns nothing and costs nothing. It must not be negative,
    or the metric would punish the honest answer."""
    assert decision_utility([0.1, 0.2], [True, True], recommend_above=0.9) == 0.0


# --------------------------------------------------------------------- uncertainty


def test_bootstrap_ci_brackets_the_point_estimate():
    rng = np.random.default_rng(11)
    x = rng.normal(5.0, 1.0, size=200)
    point, lo, hi = bootstrap_ci(x, np.mean, n_resamples=2000, seed=1)
    assert lo < point < hi
    assert point == pytest.approx(float(np.mean(x)))


def test_bootstrap_ci_narrows_as_n_grows():
    """A basic sanity property. If it fails, the resampling is wrong."""
    rng = np.random.default_rng(12)
    small = bootstrap_ci(rng.normal(0, 1, 30), np.mean, n_resamples=1500, seed=2)
    large = bootstrap_ci(rng.normal(0, 1, 600), np.mean, n_resamples=1500, seed=2)
    assert (small[2] - small[1]) > (large[2] - large[1])


def test_bootstrap_ci_covers_the_true_mean_about_95_percent_of_the_time():
    """Calibration of the interval itself. Loose bound; catches a broken estimator."""
    rng = np.random.default_rng(13)
    covered = 0
    trials = 60
    for i in range(trials):
        sample = rng.normal(0.0, 1.0, size=60)
        _, lo, hi = bootstrap_ci(sample, np.mean, n_resamples=600, seed=i)
        covered += int(lo <= 0.0 <= hi)
    assert covered / trials > 0.85


def test_paired_bootstrap_of_identical_runs_is_zero_and_contains_zero():
    x = [0.1, 0.5, 0.9, 0.3, 0.7, 0.2]
    delta, lo, hi = paired_bootstrap_delta(x, x, n_resamples=1000, seed=4)
    assert delta == pytest.approx(0.0)
    assert lo <= 0.0 <= hi


def test_paired_bootstrap_detects_a_consistent_improvement():
    """A uniform +0.2 on every item must produce an interval excluding zero."""
    a = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    b = [v + 0.2 for v in a]
    delta, lo, hi = paired_bootstrap_delta(a, b, n_resamples=2000, seed=5)
    assert delta == pytest.approx(0.2)
    assert lo > 0.0


def test_paired_bootstrap_refuses_unpaired_input():
    """Unpaired comparison across loop versions is the standard way a difference gets
    overstated, so the function refuses rather than warning."""
    with pytest.raises(ValueError, match="identical items"):
        paired_bootstrap_delta([0.1, 0.2, 0.3], [0.1, 0.2])


def test_empty_input_raises_everywhere():
    """An empty result must never silently become 0.0 -- that is a real finding
    (no items) masquerading as a bad score."""
    for fn, args in [
        (recall_at_k, ([], 1)),
        (mean_reciprocal_rank, ([],)),
        (brier_score, ([], [])),
        (expected_calibration_error, ([], [])),
        (false_confidence_rate, ([],)),
        (bootstrap_ci, ([],)),
    ]:
        with pytest.raises(ValueError):
            fn(*args)
