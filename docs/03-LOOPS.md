# The loops

Status: specification, v1.
Companion to [02-ARCHITECTURE.md](02-ARCHITECTURE.md) (what the agents are) and [04-EVALUATION.md](04-EVALUATION.md) (how they are judged).

This document defines every loop as a **contract**.
A loop that cannot state its exit condition as something a machine can check is not a loop —
it is a person watching an agent work.

## 0. Why loops, and which kind

Two mechanisms, used for different things:

- **`/goal <condition>`** — work until a stated condition holds. Used when we can say what "done" is.
- **`/loop <interval> <prompt>`** — re-run on a timer. Used for watching things that change on their own.

Every loop below declares which it uses, and states its exit condition in a form a small checker model
can evaluate without judgement calls.
"Improve the ranking" is not an exit condition.
"`pytest tests/physics` passes and `metrics/summary.json` exists with `recall@10` populated" is.

## 1. The loop hierarchy

```
L4  WATCH LOOP            /loop 6h — new literature, new structures → invalidate caches
 │
L3  IMPROVEMENT LOOP      the meta-loop: propose a change to the loop itself,
 │   (versions the loops) evaluate it, promote or reject
 │        │
 │        └── L2  EVALUATION LOOP   score a loop version on DeorphBench
 │                   │              (controls → ablations → benchmark → report)
 │                   │
 │                   └── L1  TARGET LOOP   one protein → one dossier
 │                              │
 │                              ├── L1.1 evidence  (5 channels, parallel)
 │                              ├── L1.2 hypothesise
 │                              ├── L1.3 falsify        ◀─┐ iterate until
 │                              └── L1.4 fuse + calibrate │ no survivor changes
 │                                          └──────────────┘
L0  BENCHMARK LOOP        builds DeorphBench. Runs rarely. Strictly isolated
                          from every scoring loop
```

Read it bottom-up: `L1` produces a dossier, `L2` scores many dossiers, `L3` changes the thing that produced them.
`L0` and `L4` are maintenance loops that feed the others.

**The critical isolation rule:** `L0` may read post-cutoff data; `L1` and `L2` may not.
They never run in the same session.
`scripts/guard.py`, wired as a `PreToolUse` hook, refuses to start `L1`/`L2`
if the session has touched post-cutoff sources. See [07-VERSIONING.md](07-VERSIONING.md).

---

## L0 — Benchmark loop

**Purpose.** Build and maintain `DeorphBench`: the retrospective time-split ground truth.
**Why it is a loop.** Curation is incremental, the criteria get revised as edge cases appear,
and each revision must be re-applied to all items.

| | |
|---|---|
| **Type** | `/goal` |
| **Trigger** | Manual; or `L4` detects a new curated release |
| **Agent** | `curator` (+ `auditor` for the sample check) |
| **Inputs** | Cutoff date `C`, freeze date `F`, inclusion criteria from [04-EVALUATION.md §1.2](04-EVALUATION.md) |
| **Outputs** | `benchmarks/deorphbench-<C>-<F>.parquet`, `benchmarks/curation-log.md`, `benchmarks/splits/` |

**Steps.**

1. Enumerate candidate proteins: orphan at `C` per GtoPdb / UniProt / ChEMBL snapshots dated ≤ `C`.
2. For each, search post-`C` literature for an endogenous-ligand assignment.
3. **Date each assignment by earliest primary publication**, not database release. Record preprint and journal dates separately.
4. Apply inclusion criteria I1–I5; record the reason for every exclusion.
5. Assign `date_confidence` and `prior_speculation` flags.
6. Cluster by sequence identity (30%) and Bemis–Murcko scaffold; assign `dev` / `val` / `sealed` by cluster.
7. Encrypt `sealed`. Write the snapshot manifest.
8. `auditor` re-derives a 10% random sample from primary sources independently.

**Exit condition.**
```
benchmarks/deorphbench-<C>-<F>.parquet exists;
tests/controls/test_split_disjoint.py passes;
curation-log.md records a decision for every candidate considered;
auditor sample disagreement rate < 10% and is reported.
```

**Failure modes.**
Too few items passing I1–I5 — the honest response is to lower the cutoff (2015) or add orthologues as a stratum,
**not** to relax the criteria.
Relaxing inclusion criteria to grow N is the one change this loop may not make autonomously;
it requires a human decision recorded in `benchmarks/curation-log.md`.

---

## L1 — Target loop

**Purpose.** One protein in, one audited, calibrated `TargetDossier` out.
This is the loop a researcher runs.

| | |
|---|---|
| **Type** | `/goal` |
| **Trigger** | A target enters the queue (`TASKS.md`) |
| **Inputs** | UniProt accession, loop version, snapshot manifest, cutoff (benchmark mode) or `now` (discovery mode) |
| **Outputs** | `runs/<run-id>/dossier/<acc>.json` + rendered Markdown |

### L1.1 Evidence (parallel)

Five channels run as independent subagents. **They do not see each other's output** —
this preserves the independence the fusion step assumes, and prevents one channel anchoring the rest.

| Channel | Produces | Gate |
|---|---|---|
| `librarian` | Dated claims with citations | Every item carries `source_date ≤ cutoff` or is dropped at the tool boundary |
| `structuralist` | Structures, pLDDT/PAE mask, pockets, conformational ensemble | **Emits a pocket verdict. If no pocket passes quality gating, docking is skipped and the channel reports `no usable pocket` rather than docking a bad model** |
| `chemist` | Candidate library + property-matched decoys, protonated at pH 7.4 | Decoy property-match test must pass |
| `geneticist` | mQTL / GWAS / co-expression / pathway context | — |
| `comparativist` | Structural + sequence neighbours, transferred ligands, pocket conservation | Reports identity to nearest assigned protein |

`screener` runs after `structuralist` and `chemist`, and only if the pocket verdict allows it.

**Exit condition.** All five channels have written an `EvidenceBundle` that validates against the schema,
or have explicitly reported `no evidence` with a reason. An empty channel is a valid, recorded result.

### L1.2 Hypothesise

`hypothesizer` receives the merged bundle and emits ranked hypotheses.
The schema validator rejects any hypothesis citing fewer than two independent non-LLM channels,
or lacking a mechanism that references specific pocket residues.

**Exit condition.** ≥1 schema-valid hypothesis, **or** an explicit `no hypothesis` with reasons.

### L1.3 Falsify — the inner iteration

This is where the loop actually loops.

```
for each hypothesis:
    run the attack battery (02-ARCHITECTURE §5)
    if killed      → record and drop
    if weakened    → record; return to L1.2 for refinement, max 3 rounds
    if survived    → promote to fusion
```

Refinement is bounded at 3 rounds, because an unbounded critique loop converges on
text that satisfies the critic rather than on a better hypothesis.
When the bound is hit, the hypothesis is passed forward **with the unresolved attack attached**,
not silently accepted.

**Exit condition.**
```
every hypothesis has a falsification record with outcome in {survived, killed};
no hypothesis has an unexamined attack from the standard battery;
round count ≤ 3.
```

### L1.4 Fuse and calibrate

Apply channel weights and the correlation discount; produce `p(correct)`; decide abstention against the
pre-registered threshold. `fusion` refuses to run if the session has `sealed` in scope.

Then `auditor` re-derives every claim in the dossier from artifacts, and `scribe` renders it.

**L1 exit condition.**
```
dossier validates against schema;
every claim traces to an evidence_id with reproducible provenance;
auditor reports zero unsupported claims;
p(correct) is present, or abstention is recorded with a reason;
"what would change our mind" names a concrete experiment.
```

**L1 failure modes.**

| Failure | Response |
|---|---|
| No usable structure | Run with structure channel empty; report reduced confidence. Do **not** fabricate a model |
| Candidate library does not contain the true ligand | Unknowable at runtime. Reported as a coverage statistic, and bounded on the benchmark by checking library membership of known answers |
| All hypotheses killed | A valid, publishable outcome. Dossier is emitted with abstention and the kill record |
| Auditor finds unsupported claims | Return to `scribe`; if it recurs twice, halt the target and flag for human review |

---

## L2 — Evaluation loop

**Purpose.** Score one loop version against `DeorphBench`.
**This loop runs the controls before the benchmark, and stops if they fail.**
That ordering is deliberate: a benchmark number computed on a broken pipeline is worse than no number,
because it will be believed.

| | |
|---|---|
| **Type** | `/goal` |
| **Trigger** | `L3` proposes a candidate version, or a release is cut |
| **Inputs** | Loop version, split (`dev`/`val`/`sealed`), pre-registration file |
| **Outputs** | `runs/<run-id>/metrics/`, `reports/<version>-<split>.md` |

**Steps.**

1. Verify the environment: `scripts/doctor.py` green; snapshot manifest hashes match.
2. **Physics regressions** ([04-EVALUATION.md §6](04-EVALUATION.md)). Any failure → abort.
3. **Negative controls** ([§5.1](04-EVALUATION.md)). Any control producing confident answers → abort, open a bug task.
4. Contamination probe over all items; assign bins.
5. Run `L1` over every benchmark item, in parallel, seeded from the run ID.
6. Baselines ([§5.3](04-EVALUATION.md)) on the identical item set.
7. Ablations ([§5.2](04-EVALUATION.md)).
8. `statistician`: metrics per stratum and per contamination bin, bootstrap CIs, paired comparison to incumbent.
9. Render the report, including the reliability diagram and the risk–coverage curve.

**Exit condition.**
```
metrics/summary.json exists and validates;
controls_passed == true;
every pre-registered metric is populated with a CI;
the report contains the popularity baseline column;
reports/<version>-<split>.md committed.
```

**Failure modes.**
Aborting at step 2 or 3 is the loop working correctly.
The one thing this loop must never do is *relax a control to get past it* —
`scripts/guard.py` treats modification of `tests/controls/` during an `L2` run as a hard error.

---

## L3 — Improvement loop (the meta-loop)

**Purpose.** Change the loop itself, safely. This is the answer to "how do we version and iterate".

| | |
|---|---|
| **Type** | `/goal`, usually run overnight |
| **Trigger** | Manual, or a backlog of proposals in `loops/PROPOSALS.md` |
| **Inputs** | Incumbent loop version, proposal backlog |
| **Outputs** | A new `loops/v<x.y.z>.yaml`, a `CHANGELOG.md` entry, promote-or-reject decision |

**Steps.**

1. Read `loops/PROPOSALS.md`, ranked by expected value per unit cost.
2. Take the top proposal. Write it as a **diff to the loopspec**, not as a prose intention.
3. Write a pre-registration naming the metric the change is supposed to move, and by how much, *before running it*.
4. Run `L2` on `dev` → if the effect is absent, stop and record. Most proposals die here, cheaply.
5. Run `L2` on `val` → fit weights and thresholds.
6. If and only if the proposal still looks good: a human unseals `sealed`, `L2` runs once, result is final.
7. Apply the promotion gate ([04-EVALUATION.md §8](04-EVALUATION.md)). Promote or reject.
8. Record the outcome in `loops/CHANGELOG.md` **whether promoted or rejected**, with numbers.

**Exit condition.**
```
the top proposal has a recorded decision in loops/CHANGELOG.md with
its pre-registration hash, the metric delta and its CI;
loops/PROPOSALS.md updated.
```

**Why step 3 matters.**
Without a stated expected effect, an agent evaluating its own change will find *something* that improved
and report that. Naming the metric first turns the loop from a search for good news into a test.

**Failure modes.**
The dangerous one is **silent benchmark drift**: a proposal that improves the score by changing the benchmark
rather than the method. The guard forbids `L3` from writing to `benchmarks/` at all;
benchmark changes go through `L0` with a human decision.

---

## L4 — Watch loop

**Purpose.** The world changes. Keep the repo aware of it.

| | |
|---|---|
| **Type** | `/loop 6h` |
| **Trigger** | Timer |
| **Outputs** | Appends to `TASKS.md`, `JOURNAL.md`; invalidates affected caches |

Checks: new structures for queued targets; new publications matching open hypotheses;
new curated releases; long-running compute jobs; failed runs needing retry.

**Important:** in benchmark mode the watch loop may not inject post-cutoff findings into an active run.
It writes to the task list, which a human or `L0` triages.
A watch loop with write access to running evidence is leak L1 with extra steps.

---

## 2. Running them

```bash
# One target, discovery mode
/goal a validated dossier exists at runs/latest/dossier/Q9HC97.json \
      with zero unsupported claims from the auditor

# Score the current loop version on dev
/goal reports/v0.1.0-dev.md exists, controls_passed is true, \
      and every pre-registered metric has a confidence interval

# Overnight improvement loop
/goal the top proposal in loops/PROPOSALS.md has a recorded promote-or-reject \
      decision in loops/CHANGELOG.md with its metric delta and CI

# Keep watch while something long runs
/loop 6h check queued jobs and new releases, and log anything new to JOURNAL.md
```

The standing loop prompt that accompanies these lives in [PROMPT.md](../PROMPT.md),
which any new session can resume from with `/goal continue the goal described in PROMPT.md`.

## 3. Loop design rules

Learned constraints, each of which exists because the opposite fails.

1. **Every loop states a machine-checkable exit condition.** Otherwise it never ends.
2. **Every atomic step runs in its own subagent.** The orchestrator's context stays for planning.
3. **State in files, decisions in the journal, never in context.**
4. **Controls run before metrics, and a control failure aborts.**
5. **Critique loops are bounded.** Unbounded critique optimises for the critic.
6. **A loop may not modify its own evaluation.** Enforced by hook, not by instruction.
7. **Write the expected effect before measuring it.**
8. **Record rejections.** A changelog of what failed is stronger evidence than a list of what shipped.
9. **An empty result is a result.** `no evidence`, `no hypothesis` and `abstain` are first-class outputs.
10. **Commit after each finished task**, so the git history is the audit trail.

---

*Written material in this repository is licensed CC BY 4.0.*
