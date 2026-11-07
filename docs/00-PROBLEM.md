# The open problem: endogenous ligand assignment for orphan human proteins

Status: problem statement, v1.
Audience: judges, scientists joining the project, and agents working the loop.

## In one sentence

For a large fraction of human proteins we know the sequence and, increasingly, the fold,
but we do not know which small molecule they bind —
and the field has no honest, reproducible way to measure whether a computational method gets this right.

## The biology, stated plainly

A protein is a molecular machine with a binding site.
A *ligand* is the small molecule that site is shaped for:
a metabolite, a lipid, an ion, a signalling molecule.
Knowing the pair (protein, ligand) is what turns a gene name into a mechanism:
it tells you what pathway the protein sits in, what happens when it breaks,
and what a drug would have to mimic or block.

A protein with no known ligand is called an **orphan**.
Orphan receptors, orphan transporters and uncharacterised enzymes are not rare curiosities —
they are a standing fraction of the human proteome,
and they are systematically under-studied
because the absence of a known ligand makes every downstream assay harder to design.

Two properties make this hard in a way that defeats naive computation:

1. **Proteins move.**
   A binding site is not a fixed cavity.
   Many pockets are *cryptic*: closed in the unbound (apo) structure, opening only when the ligand arrives.
   Structure predictors trained largely on bound (holo) crystal structures
   will happily emit a confident-looking apo model whose pocket geometry is simply wrong for the question being asked.
2. **The search is open-ended.**
   For a drug programme you ask "does molecule X bind protein P?".
   For deorphanization you ask "which molecule, out of everything the human body makes, binds protein P?" —
   a search over an ill-defined set, with no guarantee the answer is in it.

The combination is why this area produces so much confident nonsense.
A scoring function that is weakly correlated with reality,
pointed at a pocket that may not exist,
searching a library that may not contain the answer,
will still return a ranked list with a best hit and a plausible-sounding rationale.
Nothing in that pipeline is built to say "I do not know".

## The numbers, and how much we trust them

We state these carefully,
because the loop's credibility starts here
and inflated framing numbers are the easiest thing for a judge to check.

| Claim | Figure | Confidence | How to verify |
|---|---|---|---|
| Human protein-coding genes | ~19,000–20,000 | High; stable across recent annotation releases | UniProt human reference proteome count |
| Share of human proteins functionally under-characterised | commonly quoted as roughly 20–35% | **Medium — definition-dependent** | Recompute from Pharos/TCRD development levels (the `Tdark` share) and report the definition used |
| Orphan class A GPCRs with no agreed endogenous ligand | roughly 100; ~87 often cited for the rhodopsin-like family | Medium; the count moves as assignments are made and contested | IUPHAR/BPS Guide to Pharmacology orphan list; GPCRdb |
| Average cost to bring one drug to market | ~$2.6B, 10–12 years | **Low–medium — contested** | An industry capitalised-cost estimate; independent analyses give materially lower numbers. Cite the source, not the number alone |
| Wet-lab failure rate for candidate binders | often described as ~90% | **Low — not a single measurable quantity** | Depends entirely on assay, library and stage. We do not rely on it |

**No metric in this project is built on the contested figures.**
They motivate the work; they are not evidence.
The first task in the loop (`T-001`) recomputes the two figures we actually use —
the orphan count and the `Tdark` share — from primary sources, and writes the result with its query date.
See [09-FAILURE-MODES.md](09-FAILURE-MODES.md) on framing-number inflation as a tracked failure mode.

## Why the problem is still open

Not for want of methods. It is open because of how methods are evaluated.

- **Docking scores are not affinities.**
  Empirical scoring functions rank *poses* adequately and rank *molecules* poorly.
  Using a raw docking score as a cross-ligand ranking signal is the most common error in this literature.
- **Benchmarks reward memorisation.**
  Standard decoy sets are separable on physicochemical properties alone,
  so a model can score well without learning anything about binding.
  This has been demonstrated repeatedly and is still widely ignored.
- **Homology leakage is pervasive.**
  Validate on a protein similar to something in your reference data and you measure recall, not generalisation.
  Deorphanization is by definition the low-homology regime,
  so a benchmark without an identity cutoff measures the wrong thing.
- **There is no retrospective deorphanization benchmark.**
  This is the gap we target.
  Held-out-*target* splits exist — hold out whole receptors, predict their ligands —
  but we found no benchmark that holds out *time*:
  take proteins that were genuinely orphans at a cutoff date, hide everything published after it,
  and ask whether a method recovers the ligand the field later found.
  Reviews in the area explicitly call for scaffold and time-split evaluation as future work.

A held-out-target split asks "can you generalise across proteins?".
A held-out-time split asks the actual question:
**"would this loop have made the discovery?"**
That is what a researcher deciding whether to trust the output needs to know,
and it is the question nobody has answered.

## What this project does

We build and evaluate a **multi-agent research loop for endogenous ligand assignment**,
with three commitments:

1. **The benchmark is the product.**
   The primary deliverable is `DeorphBench` —
   a reproducible, time-split retrospective benchmark built by the loop from primary sources,
   with a frozen curation protocol and a sealed split.
   A method is only interesting here if it moves a number on it.
2. **Abstention is a first-class output.**
   The loop must be able to return *no confident ligand*,
   and is scored on whether it does so on negative controls where no answer exists.
   Calibration is measured, not assumed.
3. **Every claim is falsified before it is reported.**
   A dedicated adversarial agent receives each surviving hypothesis and a budget to kill it.
   Only hypotheses that survive a genuine attempt at destruction reach the researcher.

## How results are checked computationally

The rubric for this event asks that the problem be *checkable by computation*. Concretely:

- **Retrospective recovery.**
  Restricted to pre-cutoff evidence, does the loop rank the later-confirmed ligand in its top-k?
  Measured as recall@k, MRR and BEDROC on `DeorphBench`.
- **Physics regression.**
  Does the docking stack reproduce known co-crystal poses within 2 Å RMSD on redocking,
  and degrade as expected on cross-docking?
  Pass/fail, run in CI.
- **Negative controls.**
  Scrambled sequences, shuffled pairs and sham pockets must *not* score like real targets.
  A control that passes is a bug, not a result.
- **Calibration.**
  Brier score and expected calibration error on the loop's stated confidence, plus a risk–coverage curve.
- **Contamination probe.**
  A closed-book probe measures how much the language model already knows the post-cutoff answer,
  so recovery numbers can be reported net of memorisation.
  See [04-EVALUATION.md](04-EVALUATION.md).

Each is a test in [tests/](../tests/),
and each is a condition a `/goal` can check without a human in the loop.

## Scope and non-goals

**In scope:** human proteins; endogenous small-molecule and lipid ligands;
hypothesis generation, ranking, falsification and calibrated reporting.

**Out of scope, deliberately:**

- Peptide and protein ligands — different methods, different benchmark. Noted as future work.
- De novo drug design or lead optimisation. We assign natural ligands; we do not invent molecules.
- Any claim of experimental validation.
  Nothing here is wet-lab validated.
  The loop produces *prioritised, falsified hypotheses with stated confidence*,
  and its value rests entirely on whether that prioritisation is better calibrated than the alternatives.

## Success criteria for this project

In descending order of importance:

1. `DeorphBench` exists, is reproducible from the curation protocol, and is usable by others —
   **even if our own method performs poorly on it.**
2. The loop's reported confidence is calibrated on the sealed split.
3. The loop abstains on negative controls.
4. The loop recovers a non-trivial fraction of post-cutoff ligand assignments above a stated baseline,
   net of measured contamination.

An honest negative result on (4), with (1)–(3) solid, is an outcome we would publish.

---

*Written material in this repository is licensed CC BY 4.0. See [LICENSE-CC-BY-4.0](../LICENSE-CC-BY-4.0).*
