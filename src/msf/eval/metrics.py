"""Evaluation metrics. Real implementations, verified against analytic values.

Normative definitions: docs/04-EVALUATION.md section 4. Where this module and that
document disagree, the document wins and this module is wrong.

Design notes that are not obvious from the signatures:

* Ranking metrics take ranks, not scores, so that the caller has already decided how
  ties break. Silent tie-handling is a classic source of inflated enrichment.
* `expected_calibration_error` uses equal-MASS bins, not equal-width. Equal-width bins
  are nearly empty at the extremes, which is exactly where miscalibration lives.
* Every aggregate returns a point estimate only. Confidence intervals come from
  `bootstrap_ci` / `paired_bootstrap_delta`, and the report generator refuses a point
  estimate without one.
* AUC-ROC is deliberately absent. It is reported elsewhere for comparability and is never
  used for a decision, because it is dominated by the irrelevant tail of the ranking.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

__all__ = [
    "recall_at_k",
    "mean_reciprocal_rank",
    "enrichment_factor",
    "bedroc",
    "brier_score",
    "expected_calibration_error",
    "risk_coverage_curve",
    "selective_accuracy_at_coverage",
    "false_confidence_rate",
    "decision_utility",
    "bootstrap_ci",
    "paired_bootstrap_delta",
]


# --------------------------------------------------------------------------- ranking


def recall_at_k(ranks: Sequence[int], k: int) -> float:
    """Fraction of items whose true answer appears in the top k. Ranks are 1-indexed.

    The researcher-facing quantity: how many candidates must I test?
    A rank of 0 or less is invalid; absence is expressed by a rank beyond the library.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    ranks = list(ranks)
    if not ranks:
        raise ValueError("no items")
    if any(r < 1 for r in ranks):
        raise ValueError("ranks are 1-indexed; use a rank beyond the library for 'not found'")
    return sum(1 for r in ranks if r <= k) / len(ranks)


def mean_reciprocal_rank(ranks: Sequence[int]) -> float:
    """Mean of 1/rank. Rank-sensitive single-number summary."""
    ranks = list(ranks)
    if not ranks:
        raise ValueError("no items")
    if any(r < 1 for r in ranks):
        raise ValueError("ranks are 1-indexed")
    return float(np.mean([1.0 / r for r in ranks]))


def enrichment_factor(ranks: Sequence[int], n_total: int, fraction: float = 0.01) -> float:
    """Enrichment over random at the top `fraction` of the library.

    Interpretable as a multiplier: EF=10 means ten times better than picking at random.
    """
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    if n_total < 1:
        raise ValueError("n_total must be >= 1")
    cutoff = max(1, int(math.floor(fraction * n_total)))
    hit_rate = recall_at_k(ranks, cutoff)
    return hit_rate / fraction


def bedroc(ranks: Sequence[int], n_total: int, alpha: float = 20.0) -> float:
    """Boltzmann-enhanced discrimination of ROC (Truchon & Bayly, 2007).

    Early-weighted: at alpha=20 roughly 80% of the weight sits in the top 8% of the
    ranking, which is the only part anyone will ever test. Bounded in [0, 1].

    Used instead of AUC-ROC for enrichment decisions. One active per target is the normal
    case here, which is a regime where BEDROC is well behaved but the value depends
    strongly on n_total -- so never compare BEDROC across libraries of different size.
    """
    ranks = list(ranks)
    n = len(ranks)
    if n == 0:
        raise ValueError("no items")
    if n_total < n:
        raise ValueError("n_total must be >= number of actives")
    if any(r < 1 or r > n_total for r in ranks):
        raise ValueError("ranks must lie in [1, n_total]")
    if alpha <= 0:
        raise ValueError("alpha must be > 0")

    ra = n / n_total
    if math.isclose(ra, 1.0):
        return 1.0

    sum_exp = float(np.sum(np.exp(-alpha * np.asarray(ranks, dtype=float) / n_total)))
    # Expected value of the same sum under a random ranking.
    denom = (1.0 - math.exp(-alpha)) / (n_total * (math.exp(alpha / n_total) - 1.0))
    rie = (sum_exp / n) / denom

    factor = (ra * math.sinh(alpha / 2.0)) / (
        math.cosh(alpha / 2.0) - math.cosh(alpha / 2.0 - alpha * ra)
    )
    offset = 1.0 / (1.0 - math.exp(alpha * (1.0 - ra)))
    return float(min(1.0, max(0.0, rie * factor + offset)))


# ----------------------------------------------------------------------- calibration


def brier_score(probs: Sequence[float], outcomes: Sequence[bool]) -> float:
    """Mean squared error of the predicted probabilities. Lower is better."""
    p = np.asarray(probs, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.shape != y.shape:
        raise ValueError("probs and outcomes must be the same length")
    if p.size == 0:
        raise ValueError("no items")
    if np.any((p < 0) | (p > 1)):
        raise ValueError("probabilities must lie in [0, 1]")
    return float(np.mean((p - y) ** 2))


def expected_calibration_error(
    probs: Sequence[float], outcomes: Sequence[bool], n_bins: int = 10
) -> float:
    """ECE over equal-MASS bins.

    Equal-mass rather than equal-width: equal-width bins are nearly empty at the extremes,
    which is precisely where a confident model is wrong and where we most need to measure.

    Report this alongside a reliability diagram with per-bin counts. ECE alone hides how
    thin the bins are, and with our N they will be thin.
    """
    p = np.asarray(probs, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.shape != y.shape:
        raise ValueError("probs and outcomes must be the same length")
    if p.size == 0:
        raise ValueError("no items")
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")

    order = np.argsort(p, kind="stable")
    p, y = p[order], y[order]
    n = p.size

    # Bin boundaries must never split a group of tied probabilities.
    #
    # Naive equal-mass binning cuts wherever the count says, which for tied predictions
    # puts identical claims in different bins and makes the result depend on the INPUT
    # ORDER of the outcomes -- not on the data. A model that says 0.9 a thousand times
    # and is right half the time then scores differently depending on how the rows were
    # sorted, which is nonsense. Found by a test, not by reading the code.
    boundaries: list[int] = []
    for k in range(1, min(n_bins, n)):
        t = int(round(k * n / min(n_bins, n)))
        while 0 < t < n and p[t] == p[t - 1]:
            t += 1  # push the cut past the tie group
        if 0 < t < n:
            boundaries.append(t)
    edges = [0, *sorted(set(boundaries)), n]

    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        if hi <= lo:
            continue
        weight = (hi - lo) / n
        total += weight * abs(float(np.mean(p[lo:hi])) - float(np.mean(y[lo:hi])))
    return total


def risk_coverage_curve(
    probs: Sequence[float], outcomes: Sequence[bool]
) -> tuple[np.ndarray, np.ndarray]:
    """Accuracy among the most-confident `c` fraction, for every achievable c.

    The curve a lab actually plans against: "if I only chase my top 20%, how often am I
    right?" Returns (coverage, selective_accuracy), both ascending in coverage.
    """
    p = np.asarray(probs, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.shape != y.shape:
        raise ValueError("probs and outcomes must be the same length")
    if p.size == 0:
        raise ValueError("no items")

    order = np.argsort(-p)  # most confident first
    y_sorted = y[order]
    n = y_sorted.size
    coverage = np.arange(1, n + 1) / n
    accuracy = np.cumsum(y_sorted) / np.arange(1, n + 1)
    return coverage, accuracy


def selective_accuracy_at_coverage(
    probs: Sequence[float], outcomes: Sequence[bool], coverage: float = 0.20
) -> float:
    """The pre-registered PRIMARY metric (ADR-0003).

    How often the loop is right about the fraction of targets it is most confident about.
    Chosen over recall@k because the downstream cost of a confident error is a wasted
    experiment, and recall@k treats a confident error and a correct hedge as equivalent.
    """
    if not 0 < coverage <= 1:
        raise ValueError("coverage must be in (0, 1]")
    cov, acc = risk_coverage_curve(probs, outcomes)
    idx = int(np.searchsorted(cov, coverage, side="left"))
    idx = min(idx, acc.size - 1)
    return float(acc[idx])


def false_confidence_rate(probs: Sequence[float], threshold: float = 0.5) -> float:
    """Fraction of NEGATIVE CONTROLS given a probability above the threshold.

    Pass these the controls only -- targets with no correct answer. The pre-registered
    gate is < 0.10, and a loop version failing it cannot be promoted however good its
    ranking metrics are.
    """
    p = np.asarray(probs, dtype=float)
    if p.size == 0:
        raise ValueError("no controls")
    return float(np.mean(p > threshold))


def decision_utility(
    probs: Sequence[float],
    outcomes: Sequence[bool],
    recommend_above: float,
    value_hit: float = 10.0,
    cost_experiment: float = 1.0,
) -> float:
    """Expected utility of the set the loop recommends testing.

    Encodes the asymmetry the ranking metrics ignore: a confident wrong answer costs an
    experiment. Report with a sensitivity sweep over value_hit / cost_experiment, because
    the right ratio is lab-specific and we would otherwise be inventing it.
    """
    p = np.asarray(probs, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.shape != y.shape:
        raise ValueError("probs and outcomes must be the same length")
    picked = p > recommend_above
    if not np.any(picked):
        return 0.0  # abstaining everywhere is worth nothing, and costs nothing
    return float(np.sum(y[picked] * value_hit - (1.0 - y[picked]) * cost_experiment))


# ------------------------------------------------------------------------ uncertainty


def bootstrap_ci(
    values: Sequence[float],
    statistic=np.mean,
    n_resamples: int = 10_000,
    alpha: float = 0.05,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """BCa bootstrap interval over items. Returns (point, lo, hi).

    Bias-corrected and accelerated, because the plain percentile interval is noticeably
    off for skewed statistics on small samples -- and our samples will be small.

    No point estimate in this project is ever reported without one of these.
    """
    x = np.asarray(values, dtype=float)
    if x.size == 0:
        raise ValueError("no values")
    if x.size == 1:
        v = float(statistic(x))
        return v, v, v

    rng = np.random.default_rng(seed)
    point = float(statistic(x))

    idx = rng.integers(0, x.size, size=(n_resamples, x.size))
    boot = np.array([statistic(x[i]) for i in idx], dtype=float)

    # Bias correction.
    prop_less = float(np.mean(boot < point))
    prop_less = min(max(prop_less, 1e-9), 1 - 1e-9)
    z0 = _norm_ppf(prop_less)

    # Acceleration, by jackknife.
    jack = np.array(
        [statistic(np.delete(x, i)) for i in range(x.size)], dtype=float
    )
    jack_mean = float(np.mean(jack))
    diff = jack_mean - jack
    denom = 6.0 * (float(np.sum(diff**2)) ** 1.5)
    accel = float(np.sum(diff**3)) / denom if denom > 0 else 0.0

    def adjusted(prob: float) -> float:
        z = _norm_ppf(prob)
        adj = z0 + (z0 + z) / (1.0 - accel * (z0 + z))
        return float(np.clip(_norm_cdf(adj) * 100.0, 0.0, 100.0))

    lo = float(np.percentile(boot, adjusted(alpha / 2.0)))
    hi = float(np.percentile(boot, adjusted(1.0 - alpha / 2.0)))
    return point, lo, hi


def paired_bootstrap_delta(
    a: Sequence[float],
    b: Sequence[float],
    n_resamples: int = 10_000,
    alpha: float = 0.05,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """Paired comparison on IDENTICAL items. Returns (delta, lo, hi) for mean(b) - mean(a).

    Unpaired comparison between loop versions is forbidden by the report generator: it is
    the standard way a version difference gets overstated. Pairing removes item difficulty
    as a source of variance, which with our N is most of the variance.

    If the interval contains zero, the correct description is "not detectable at this N",
    never "an improvement".
    """
    xa = np.asarray(a, dtype=float)
    xb = np.asarray(b, dtype=float)
    if xa.shape != xb.shape:
        raise ValueError(
            "paired comparison requires identical items in the same order; "
            "got lengths %d and %d" % (xa.size, xb.size)
        )
    return bootstrap_ci(xb - xa, np.mean, n_resamples=n_resamples, alpha=alpha, seed=seed)


# --------------------------------------------------------------- small normal helpers
# Inlined so this module imports without scipy, which keeps the Tier 0 path light.


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF (Acklam's rational approximation, ~1e-9 absolute error)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
