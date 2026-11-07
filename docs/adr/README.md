# Architecture decision records

One file per decision that was not obvious, recording **what was rejected and why**.

A decision record without a rejected alternative is not a decision, it is a description.
The rejected options are the useful part: they are what a later reader needs in order to tell
whether the decision still holds.

| | Decision | Status |
|---|---|---|
| [0001](0001-time-split-over-target-split.md) | Hold out time, not proteins | Accepted |
| [0002](0002-guards-are-structural.md) | Enforce every leakage control in a hook, not a prompt | Accepted |
| [0003](0003-calibration-is-the-primary-metric.md) | Score calibration and abstention above recall | Accepted |
| [0004](0004-benchmark-is-the-deliverable.md) | The benchmark is the product; the method is the experiment | Accepted |

## Open questions, not yet decided

Recorded in [02-ARCHITECTURE.md §9](../02-ARCHITECTURE.md):
the fusion model family, how to credit a partially-correct answer,
whether `--blind-targets` should be the default, and set-valued ground truth for multi-ligand targets.

## Format

```markdown
# ADR-NNNN: <decision in the imperative>

Status: proposed | accepted | superseded by ADR-NNNN
Date: YYYY-MM-DD

## Context
What forced a choice.

## Decision
What we do.

## Alternatives rejected
Each with the reason. This is the section that matters.

## Consequences
What this costs us, including what it makes harder.
```
