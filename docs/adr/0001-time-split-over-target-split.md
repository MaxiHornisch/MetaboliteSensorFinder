# ADR-0001: Hold out time, not proteins

Status: accepted
Date: 2026-11-07

## Context

Ligand-prediction methods are evaluated on random, ligand-scaffold, or held-out-target splits.
Held-out-target is the strongest current practice and is explicitly framed in recent work as
simulating deorphanization: remove whole receptors, predict their ligands.

A researcher deciding whether to trust an orphan-ligand prediction does not actually want to know
whether a method generalises across protein space.
They want to know whether it would have found something real.
No existing split answers that.

## Decision

Build `DeorphBench` as a **retrospective time split**: proteins that were genuine orphans at a cutoff
date `C`, whose endogenous ligands the field reported after `C`, with everything post-`C` withheld from
every tool.

Keep cluster-level protein splitting *on top of* the time split, rather than instead of it —
the two controls are orthogonal.

## Alternatives rejected

**Held-out-target split alone.** Answers "can you generalise across proteins?", which is a proxy.
It also leaves the designer choosing the positive set, so the set can be — usually unintentionally —
selected for findability.

**Prospective validation.** The right answer scientifically, and unavailable: it requires a wet lab
and years. A retrospective time split is the closest approximation obtainable in a day.

**Synthetic held-out ligands** (mask known pairings and try to recover them).
Cheap and large-N, but the proteins are not orphans, so it measures recall of known biology rather than
discovery. It is also maximally exposed to model memorisation with no way to detect it.

**Random or scaffold splits.** Measure interpolation. Known to reward memorisation.

## Consequences

**Cost — small N.** Genuine post-cutoff deorphanizations meeting strict inclusion criteria are plausibly
tens, not thousands. Confidence intervals will be wide and most differences between loop versions will
not be detectable. We state the minimum detectable effect rather than pretending otherwise.

**Cost — dating is hard and is now a correctness-critical step.** Database release dates are not
discovery dates, so every item must be traced to its earliest primary publication.
This is the weakest joint in the benchmark and carries a `date_confidence` field.

**Cost — survivorship bias.** Ligands that *were* found are biased toward abundant, easily assayed
metabolites in well-funded protein families. `DeorphBench` therefore **overestimates** performance on
the orphans that remain. Uncorrectable; flagged, with strata reported so the bias is visible.

**Cost — it does not constrain the language model.** The model's training data contains the post-cutoff
literature. This is not a flaw in the decision but it does mean the split alone is insufficient,
and it forced the whole contamination-measurement apparatus ([04-EVALUATION.md §3](../04-EVALUATION.md)).
It also means a co-folding model trained past our cutoff cannot be used naively.

**Benefit.** The ground truth arrived independently of us.
Nobody constructed the positive set to be findable; the field found these ligands by experiment,
for its own reasons, after the cutoff.
That is as close to a prospective trial as a retrospective benchmark gets,
and it is the property none of the rejected alternatives has.
