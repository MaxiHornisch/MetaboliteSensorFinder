# ADR-0003: Score calibration and abstention above recall

Status: accepted
Date: 2026-11-07

## Context

The natural headline metric for a ranking problem is recall@k: how often is the true ligand in the top k.
It is what the field reports and what a leaderboard wants.

But the output of this loop is consumed by someone allocating experiments.
A confident wrong answer costs a wet-lab experiment; a correctly-hedged answer costs nothing and
preserves the budget for a better lead. Those two outcomes are not symmetric, and recall@k treats them
as if they were.

The dominant failure in this area is also not poor ranking — it is confident fabrication.
Every component of the standard stack returns a best answer whether or not one exists.
A metric that only rewards being right cannot distinguish a method that knows when it does not know.

## Decision

The pre-registered **primary** metric is **selective accuracy at 20% coverage**:
how often the loop is right about the 20% of targets it is most confident about.

Alongside it, as gates rather than scores:

- **false-confidence rate < 0.10** on negative controls, pre-registered;
- a loop version that **never abstains cannot be promoted**, whatever its ranking metrics say.

Recall@k, MRR, BEDROC and EF@1% remain reported, per stratum, as secondary metrics.
AUC-ROC is reported and **never** used for a decision.

## Alternatives rejected

**Recall@k as primary.** Comparable to the literature, and rewards a method that guesses confidently on
every target. It is precisely the metric that produced the state of affairs we are reacting to.

**A single blended score.** Tempting for a leaderboard; hides the trade-off that the researcher needs
to see, and the blending weights become an unexamined value judgement.

**Decision utility `U` as primary.** We do compute it, and it is the most decision-relevant single number.
Rejected as *primary* because it depends on a hit-to-experiment cost ratio that is lab-specific and that
we would be inventing. Reported with a sensitivity sweep instead, so a reader can locate their own ratio.

**Expected calibration error as primary.** A method that abstains on everything has perfect ECE.
Needs to be paired with a coverage term, which is what selective accuracy already is.

## Consequences

**Cost — our headline number will look worse than the literature's.**
Selective accuracy at 20% coverage on a strict time split is not comparable to recall@k on a random
split, and ours will be lower. We accept this and will say why, every time.

**Cost — it is harder to explain.** "Right about the 20% it is surest of" needs a sentence of setup,
where "recall@10" does not. The researcher UX carries that explanatory burden.

**Cost — calibration needs data to fit**, and with small N the calibrator is itself uncertain.
Fitted on `val` only, and the reliability diagram is reported with per-bin counts so a reader can see
how thin the bins are.

**Benefit.** The gate matches the actual cost structure of the downstream decision.
It also makes abstention a first-class engineering target rather than a thing to be apologised for,
which changed the architecture: the falsifier, the two-channel requirement and the
`no_usable_pocket` verdict all exist because abstention is scored.
