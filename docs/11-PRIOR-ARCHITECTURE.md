# The prior architecture, and what we changed

Status: reconciliation, v1. Written 2026-11-07, after reading the source research.

This project was commissioned to **improve and complement** an existing design —
the *Orphan-Catch Agentic Harness* — developed in a research conversation held before this work began
(`input/BaseSearch.html`, seventeen turns).

**We built most of this repository before reading it.**
That was a process failure on our side, and this document is the reconciliation:
what the prior design said, what we adopted, what we changed and why, and what each contributes
that the other lacks. Where we disagree with it, the disagreement is argued, not assumed.

---

## 1. What the prior architecture is

A **three-loop filtering funnel**, driven from a human protein sequence, with TDD gates and an
adversarial jury.

```
Human sequence
   │
   ▼
0. TDD ARCHITECT AGENT ── generates an immutable manifest.json and a negative-control suite
   │                       (pocket volume floor, disulfide count, negative-control ligand "C"
   │                        that must score worse than −3.0 kcal/mol)
   ▼
LOOP 1  CAVITY PRE-SELECTION      Rostlab bindPredict (ProtT5 embeddings)
        sequence → binding-site residue indices
        gate: pocket must contain ≥2 small-molecule anchors
   │
   ▼
LOOP 2  AFFINITY FIT MATRIX       PSICHIC (physicochemical graph neural network)
        screens ~100k SMILES/hour; passes the top 0.01% of scaffolds
        gate: affinity score ≥ 7.5                        ◀── re-screen loop
   │
   ▼
LOOP 3  GEOMETRIC CALIBRATION     AutoDock Vina
        grid centred on the Loop 1 anchors
        gate: energy < −8.0 kcal/mol and no steric clashes ◀── recalibrate loop
   │
   ▼
ADVERSARIAL JURY ── Structural Physicist vs. Bio-Chemist, unanimous vote
   │
   ▼
Verified target match → three_loop_final_artifact
```

A separate turn elaborates the agent roster: **Architect** (writes the TDD manifest),
**Builder** (executes folding and docking, deliberately *blind* — it receives a randomised batch of
50 masked compounds, 49 decoys and 1 true binder, and does not know which is which),
**Validator** (sanity-checks the artifacts: empty PDB files, truncated output, swapped coordinate
axes, missing hydrogens, under-sampled docking modes), and a **two-member Judge Panel**.

## 2. What we adopted, unchanged

The prior design gets several hard things right, and we kept them.

| Adopted | Where it lives now |
|---|---|
| **Specialised agents rather than one linear script** | Thirteen subagents in [.claude/agents/](../.claude/agents/) |
| **TDD for biology** — write the invariants before predicting anything | [docs/04-EVALUATION.md §6](04-EVALUATION.md); `tests/physics/` |
| **An immutable manifest locking success criteria before computation** | The run manifest in [02-ARCHITECTURE.md §6](02-ARCHITECTURE.md); the loopspec is hashed into it |
| **Negative controls as a first-class gate** | [04-EVALUATION.md §5.1](04-EVALUATION.md) — expanded from one to six |
| **An adversarial step before anything is believed** | The `falsifier` |
| **A validator checking that the code ran correctly, separately from whether the science is right** | The `auditor` — the same split, and we found independently that it catches more real problems than the science critic does |
| **Error recovery with bounded retries** | `max_refinement_rounds`, and the loop-3 retry cap carried over |
| **A machine-readable artifact as the output** | `TargetDossier` |

Two specific ideas we had **missed** and have now taken:

- **The blinded Builder.** Giving the execution agent 49 masked decoys and 1 true binder, so it cannot know which answer it is supposed to reach, is a clean per-target contamination control. We had decoys for *metric* purposes but had not blinded the executing agent. Added as proposal `P-009`.
- **The methane negative control.** A trivial ligand (`SMILES: C`) that must score worse than a floor is almost free and catches a scoring function that rewards anything. Added to the control suite.

## 3. What we changed, and why

### 3.1 Hard score thresholds → decoy-calibrated z-scores

**The prior design gates on `PSICHIC affinity ≥ 7.5` and `Vina energy < −8.0 kcal/mol`.**

This is the single change we feel most strongly about.
A Vina score is not an affinity, and −8.0 kcal/mol is not a fixed meaning —
it varies with target, pocket size and, most of all, ligand size.
Docking scores correlate strongly with molecular weight, so a −8.0 threshold
preferentially passes large, flexible molecules regardless of whether they bind.
Applied across a 100k-compound library, a fixed threshold selects for heaviness.

We replaced both with **decoy-calibrated z-scores and library percentiles**,
computed per target against property-matched decoys
(see [.claude/agents/screener.md](../.claude/agents/screener.md), and the loopspec schema,
which admits no option for a raw score).

This is not a disagreement about the tools — Vina and PSICHIC are the right tools —
it is about what their numbers mean when compared across molecules.

### 3.2 A pure funnel → a funnel that is one channel among several

In a strict funnel, **a Loop 1 miss is unrecoverable**.
If bindPredict puts the anchors in the wrong place, Loops 2 and 3 search the wrong pocket and
return a confident answer about it. Nothing downstream can detect this, because every subsequent
step is conditioned on the first.

We kept the funnel — it is cheap and it is the right default — but made it **one evidence channel**
rather than the whole pipeline, running alongside literature, genetics, homology and co-expression
([02-ARCHITECTURE.md §2](02-ARCHITECTURE.md)). The channels are independent, so a structural miss
degrades confidence instead of silently redirecting the search.

The cost is real: five channels are more expensive than three sequential gates.
The funnel remains available as a low-cost configuration.

### 3.3 A jury that votes to accept → an adversary that tries to kill

The two-member Judge Panel voting unanimously is a reasonable design, and our change is a matter of
incentive rather than structure. A judge asked *"should this pass?"* is doing a different job from an
agent instructed *"destroy this, and you succeed when you do."*

Two further adjustments:

- Our `falsifier` **cannot edit what it attacks**. An agent with both roles quietly softens the target over a long run.
- It gets the **strongest model available**, deliberately. If the adversary is weaker than the proposer, everything survives and the panel is theatre.

The nine-attack battery is an expansion of the same idea the Judge Panel expresses.

### 3.4 The thing the prior design does not have: an evaluation

This is the substantive gap, and closing it became the whole project.

The Orphan-Catch harness specifies gates — `≥2 anchors`, `≥7.5`, `<−8.0 kcal/mol` — but there is
**no way to know whether the pipeline works**. The thresholds are stated, not derived.
Nothing measures how often the funnel is right, nothing calibrates its confidence,
nothing establishes that it beats a trivial baseline, and nothing prevents it from returning a
confident answer for a protein that binds nothing.

So we added:

- **`DeorphBench`** — a retrospective time-split benchmark. Would this have made the discovery?
- **Calibration as the primary metric** — a probability a lab can plan against ([ADR-0003](adr/0003-calibration-is-the-primary-metric.md)).
- **Abstention as a scored output** — the loop must be able to say *no confident ligand*, and is measured on whether it does so for targets that have none.
- **Baselines that must be beaten** — above all the popularity baseline, which is embarrassingly strong and which a funnel with invented thresholds will not obviously beat.
- **A leakage taxonomy** enforced in hooks rather than prompts.

A funnel with uncalibrated gates and no benchmark is exactly the apparatus that produces
"digital hallucinations and costly real-world failures" — the problem the research set out to solve.
The gates are the right *shape*; they need to be derived from data rather than chosen.

## 4. What the prior design contributes that we had missed

Reading it changed our tooling in two concrete ways.

**bindPredict is more valuable to us than we realised, and solves a real problem we had found.**
It predicts binding residues **from sequence alone**, via ProtT5 embeddings.
We had independently discovered that AlphaFold DB postdates our 2015 and 2018 cutoffs entirely
(leak L5b), which leaves the structure channel nearly empty at an early cutoff —
most orphans have no experimental structure and no close homologue.
A sequence-based pocket predictor is not subject to that constraint in the same way,
because it needs no structural database at all.
**That makes bindPredict a direct answer to a limitation we had written down as unavoidable.**
Added as proposal `P-007`.

**PSICHIC is a sequence-based interaction model**, so it likewise works without a structure.
Added as proposal `P-008`, with one gating condition: its training data almost certainly postdates
our cutoffs, which is leak L5c. It must be checked, and if contaminated it can still be used —
reported as an explicitly contaminated configuration rather than in the headline.

Both are cheap relative to docking and both attack the hardest case we have.

## 5. Honest note on process

The brief said *"here is the initial research which I want you to complement."*
We could not retrieve the link (an EU consent gate, three attempts) and proceeded without it,
documenting the gap. The research was later supplied as a saved page and is the basis of this document.

Two consequences worth stating:

- **Convergence is weak evidence.** We arrived independently at specialised agents, TDD, negative controls, an adversarial step, a separate validator, and file-based state. That the two designs agree is mildly reassuring about those choices — but we would have reached a better architecture faster by reading first, and the blinded Builder shows what independence cost us.
- **We should have blocked on the input rather than working around it.** The honest move, in hindsight, was to say "I cannot read this, please supply it" before building, not after.

## 6. Where to go next

Reconciliation tasks, not yet done:

| | |
|---|---|
| `P-007` | Add bindPredict as a sequence-based pocket channel. Highest value: it addresses the early-cutoff structure gap |
| `P-008` | Add PSICHIC as a sequence-based interaction channel, gated on a training-cutoff check |
| `P-009` | Blind the executing agent with masked decoy batches |
| — | Benchmark the three-loop funnel *as a baseline* on `DeorphBench`. It is a serious method and deserves to be in the baseline table rather than only described here |

That last one matters. The prior architecture should not be treated as superseded —
it should be **measured**. If the funnel beats our evidence-fusion design on the benchmark,
the funnel is right and we should say so.

---

*Written material in this repository is licensed CC BY 4.0.*
