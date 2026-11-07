# Screening loops: agents, execution, evaluation and simulation

Status: plan, v1. Nothing has been run. No worker has been contacted.
Companion to [12-PIPELINE-EXECUTION.md](12-PIPELINE-EXECUTION.md), which defines *what* runs (worker contracts, data schemas, phases 0–5).
This document defines *who decides what, when,* and the loop contracts that gate each phase.
Where [04-EVALUATION.md](04-EVALUATION.md) conflicts with either document, it wins.
Loop mechanics follow [03-LOOPS.md](03-LOOPS.md).

---

## 1. Division of labour

| Concern | Owner | Why |
|---|---|---|
| Dispatch, batching, checkpoints, checksum checks, retries | **`runner`** (Python script, no LLM) | Deterministic. Tokens spent here buy nothing (12 §1, D1) |
| Model inference | **workers** (bindPredict, PSICHIC, DiffDock) | Pinned, containerised, one contract (12 §3) |
| Threshold choice, metric judgement, pass/fail of gates | **agents** below, and the loops in §3 | Judgement is needed; numbers must come from artifacts |
| Thresholds used in a run | **frozen file** `thresholds.lock.yaml`, hash in the manifest | Changing them mid-run is the screening version of benchmark drift |

The runner may read thresholds but cannot write them. Only S3 (fit on `val`) and S4 (pre-registered proposal) produce a new lock file.

### 1.1 Agent roster for the screen

| Agent | Role in the screen | Writes | Restriction | Model |
|---|---|---|---|---|
| `curator` | Builds the labelled domain–ligand calibration set (S0) | `benchmarks/screen/` | Never in the same session as S2/S3 (existing rule) | per existing definition |
| `structuralist` | AlphaFold DB fetch, locate domain, trim, pLDDT and PAE-in-pocket gate. Emits the verdict that gates DiffDock | `runs/*/screen/structure/` | Must emit a verdict before any DiffDock job is submitted | existing |
| `screener` | Interprets worker outputs. Converts PSICHIC and DiffDock scores to decoy-calibrated z-scores and percentiles. Reports pose quality | `runs/*/screen/scores/` | **Raw PSICHIC or DiffDock scores are never a cross-ligand ranking.** Same prohibition as docking (existing `screener.md`) | sonnet (existing) |
| `falsifier` | Attacks DiffDock hits only: decoy ligands, shuffled-domain control, trimmed-region ablation, template dependence | `runs/*/screen/falsification/` | Read-only on hits | **strongest model**, per CLAUDE.md |
| `statistician` | Funnel recall, calibration (ECE, Brier), bootstrap CIs, baselines | `runs/*/screen/metrics/` | Refuses a table without the popularity column | existing |
| `auditor` | Re-derives every number in the report from artifacts | `runs/*/screen/audit/` | Read-only everywhere | existing |
| `scribe` | Report and JOURNAL entries | `reports/`, `JOURNAL.md` | Cannot add facts absent from the audited report | existing |
| `simulator` (**new**) | Generates synthetic truth and mock worker outputs for S1 | `tests/simulation/` | No network route to real worker hosts. No access to `benchmarks/` or sealed data | sonnet |

No agent is needed for dispatch (D1). Adding an agent for it would only add tokens.

---

## 2. Execution: what happens to one batch

```
runner: build manifest (item_id + sha256 per input)
   → POST /jobs to worker
   → poll GET /jobs/{id}                    (runner, not an agent)
   → GET /jobs/{id}/results, verify SHA-256 (reject on mismatch, retry the batch)
   → schema-validate every row              (reject the batch on any invalid row)
   → write ALL rows to scores/<stage>.parquet
   → apply thresholds.lock.yaml → advanced flag
   → checkpoint runs/<id>/screen/batches/<n>.done
```

Two invariants the runner enforces, and S2 checks:

- **Count in = count out.** Every manifest item yields either a score row or an explicit error row. A missing item is a failure, not a skip.
- **Resumable.** A completed batch is never recomputed. A failed batch is retried from its manifest.

---

## 3. Loops

Each loop declares its exit condition as something a checker can evaluate. Phase numbers refer to [12 §6](12-PIPELINE-EXECUTION.md#6-phases).

### S0 — Calibration build (`/goal`, gates phase 0 → 3)

**Purpose.** Produce the labelled set used for thresholds and metrics.
**Agent:** `curator`, then `auditor` on a 10% sample.
**Steps.**
1. Collect known domain–ligand pairs with a direct measurement, each with its source and date.
2. Collect domains with no recorded small-molecule ligand. Label them **unlabelled**, not negative (see §4.1).
3. Build property-matched decoy ligands for each positive (≥50, as in `screener.md`).
4. Split by sequence cluster at 30% identity, then stratify. Use the same `dev` / `val` / `sealed` rules as [04 §1.4](04-EVALUATION.md#14-splits).
5. Record the ligand library source and its licence (see decision D-LIB, §5).

**Exit condition.**
```
benchmarks/screen/calibration-<date>.parquet exists;
tests/controls/test_split_disjoint.py passes for the screen set;
decoy property-match test passes (logistic model on descriptors near chance);
screen-curation-log.md has a decision for every excluded pair;
auditor sample disagreement < 10% and reported.
```

### S1 — Simulation (`/goal`, gates phase 2)

**Purpose.** Test the runner, the checkpointing, the validators and the statistics **before any real compute is spent**. The simulator plants known truth and mock workers return outputs that follow it.
**Agent:** `simulator`. Mock workers are scripts implementing the same contract as the real ones.

**Scenarios to plant.**

| Scenario | Planted behaviour | What must happen |
|---|---|---|
| Known positives at a known rate | Scores drawn higher for planted pairs | Recall on positives matches the planted rate within tolerance |
| Popularity artifact | Scores correlated with ligand popularity | Popularity baseline beats the model; report flags it |
| Size artifact | Scores correlated with molecular weight | `screener` size check fires (existing rule) |
| Corrupted batch | One batch returns a wrong checksum | Runner rejects it and retries; no partial write |
| Invalid row | One row fails schema | Batch rejected; error row recorded |
| Mid-batch kill | Runner killed after batch 3 | Resume gives byte-identical outputs to an uninterrupted run |
| Silent drop | Worker omits 1 item | Count-in ≠ count-out raises an error |

**Exit condition.**
```
all S1 scenarios pass;
simulated recall on planted positives within the pre-registered tolerance;
resume-after-kill output hash == uninterrupted output hash;
no network egress to worker hosts during the run (checked by hook).
```

### S2 — Execution (`/goal` per batch set, gates phases 3–5)

**Purpose.** Run the real workers over the manifest, batch by batch.
**Agents:** `runner` (script), `structuralist` before any DiffDock batch, `screener` after each stage.
**Exit condition, per stage.**
```
every manifest item has a score row or an explicit error row;
all output checksums verified;
thresholds.lock.yaml hash recorded in every batch file;
advanced flags computed from the locked thresholds only.
```
For DiffDock, add: `structuralist` verdict `usable` or `marginal` exists for every submitted domain.

### S3 — Evaluation (`/goal` per release, gates phase 3 sign-off and phase 4 completion)

**Purpose.** Decide whether a screen configuration is trustworthy. Controls run first; a control failure stops the loop, as in [03 §L2](03-LOOPS.md#l2--evaluation-loop).
**Agents:** `statistician`, `screener`, `auditor`, `scribe`.

**Steps.**
1. Environment: pinned versions and weight hashes match the manifest. Determinism check: same input twice, same output.
2. Negative controls on `val`:
   - shuffled domain–ligand pairs: must not advance at the rate real pairs do;
   - scrambled sequences (composition preserved): must not produce confident hits;
   - decoy-only ligand sets: must score near the decoy distribution.
   Any control producing confident answers → abort and open a bug task.
3. Stage metrics on `val` (§4).
4. Fit thresholds on `val` to meet the pre-registered recall floor. Write `thresholds.lock.yaml` with its calibration source.
5. Unseal `sealed` once, by a human, logged (per [04 §1.4](04-EVALUATION.md#14-splits)). Apply the locked thresholds. No refit.
6. Report: funnel table with positives lost at each stage, calibration, per-stratum results, popularity column, thresholds with reasons.

**Exit condition.**
```
metrics/summary.json validates;
controls_passed == true;
pre-registered metrics populated with CIs;
popularity baseline column present;
reports/screen-<version>-<split>.md written.
```

### S4 — Improvement (`/goal`, overnight, as L3)

**Purpose.** Change the screen safely: a stage order, a threshold rule, an added ablation.
**Steps.** Take the top proposal in `loops/SCREEN-PROPOSALS.md`. Write it as a diff to the screen config. Pre-register the expected metric change before running. Run S3 on `dev`, stop if no effect, then `val`, then a human unseals `sealed` for the final run. Record promote or reject in `loops/CHANGELOG.md` either way.
**Forbidden:** writing to `benchmarks/` (existing L3 guard).

### S5 — Watch (`/loop 30m`)

**Purpose.** Keep the worker fleet observable while a long batch runs.
**Checks:** `/health` on each worker, queue depth, disk, failed batches awaiting retry.
**Writes:** `JOURNAL.md` only. It cannot edit thresholds, batches already done, or sealed data.

---

## 4. Evaluation specifics for the screen

These apply the rules in [04](04-EVALUATION.md) to a screen. They do not replace them.

### 4.1 Labels are weak
A domain with no recorded ligand is **unlabelled**. It is not a negative, because nobody measured it. Two consequences:
- Precision cannot be computed from unlabelled pairs. Report recall on positives, and report decoy-based specificity instead.
- Stage 1 (bindPredict) is scored against a domain-level label "binds ≥1 small molecule". That label is itself noisy, and the report says so.

### 4.2 Metrics per stage
| Stage | Primary | Secondary |
|---|---|---|
| bindPredict | Recall of positives retained at the stage threshold | Residue-level agreement where pocket residues are known |
| PSICHIC | Recall@k of the true ligand within the library, **vs popularity and random baselines** | Decoy z-score distribution; percentile within library |
| DiffDock | Pose quality on positives where a reference pose exists | Band distribution; falsifier survival rate |
| End to end | Recall@k over all positives, with CIs | Funnel loss table; per-stratum recall |

The pre-registered **primary** metric is `selective accuracy @20% coverage` per [04 §7](04-EVALUATION.md#7-statistics), applied to the calibrated final score. Everything above is secondary, with BH control at q = 0.05.

### 4.3 Calibration
- Raw PSICHIC scores are pair-scored across ligands. They are not probabilities and not cross-ligand ranks. Calibrate on `val` (isotonic or Platt), report a reliability diagram, and report the calibration source.
- DiffDock confidence bands are a **pose-quality** signal. They are never presented as a probability of binding (12 §2 already says so; this makes it a gate).

### 4.4 Recall floors and the funnel cost
Thresholds are chosen so that stage recall on `val` meets a pre-registered floor (proposed default: 0.90 per stage). The report states the cost: fraction of library-domain pairs advanced per stage, and the GPU-hours that implies.

### 4.5 Contamination
PSICHIC, bindPredict and DiffDock weights were trained on data with unknown cutoffs. For a **benchmark** run this is a L5c-type issue: the manifest records each weight's training-data date where documented, and the run is labelled `contaminated-model` if not. For a **discovery** run it is recorded but does not block.

---

## 5. Decisions and conflicts (need the user)

**D-LIB — ligand library licence conflict.** [04 §9](04-EVALUATION.md#9-what-is-wrong-with-this-evaluation) says HMDB cannot be used (CC BY-NC) and names ChEBI plus LIPID MAPS as the substitutes. [12](12-PIPELINE-EXECUTION.md) and `Agent_v1.txt` use HMDB. **Default in this plan:** benchmark runs (S0–S3) use ChEBI plus LIPID MAPS, as 04 requires. Discovery runs may use HMDB IDs, shared as IDs and a download script only. Confirm, or tell me the library you want.

**D-FILE — duplicate plan files.** I first wrote the pipeline plan as `docs/09-PIPELINE-EXECUTION.md`. It now appears as `docs/12-PIPELINE-EXECUTION.md`, with the same content. [04](04-EVALUATION.md) also references `09-FAILURE-MODES.md`, which does not exist. Recommend keeping 12 and deleting my 09 copy. I have not deleted it.

**Still open from 12 §8:** worker hosts and GPUs, cloud GPU budget, and whether the pipeline runs as Claude Code subagents (recommended) or as the `Agent_v1.txt` Managed Agents config.

**New, from this plan:** whether a benchmark run uses only ligands with pre-cutoff training data (the stricter option) or accepts `contaminated-model` runs labelled as such.

---

## 6. Hooks and guards

| Rule | Enforcement |
|---|---|
| S1 has no network route to worker hosts | Hook denies connections to worker addresses when `MSF_MODE=simulation` |
| S0 and S2/S3 never share a session | Existing `scripts/guard.py` |
| Sealed split only after a logged human unseal | Existing `scripts/unseal.py` |
| `thresholds.lock.yaml` cannot change during S2 | Runner reads it read-only; hash checked per batch |
| No `tests/controls/` edits during S3 | Existing hard error |

---

## 7. Outputs, layout

```
runs/<id>/screen/
├── manifest.yaml                 weights hashes, library hash, thresholds.lock hash, prereg hash
├── thresholds.lock.yaml
├── batches/<stage>-<n>.done
├── scores/{bindpredict,psichic,diffdock}.parquet    ALL rows, never filtered
├── structure/                    structuralist verdicts
├── falsification/                falsifier records for DiffDock hits
├── metrics/summary.json
├── audit/                        auditor findings
└── trace.jsonl
prereg/screen-<version>.yaml
loops/screen-<version>.yaml
reports/screen-<version>-<split>.md
```

---

## 8. Done means

The screen is finished for a release when:
1. S1 passes (simulation), S2 has completed every batch for the release set, and
2. S3 has produced a report on `val`, and
3. a human has unsealed `sealed` once and S3 has produced the final report with the locked thresholds.

A release that fails the recall floor or any control is reported as such. That outcome is recorded in the changelog, as [04 §8](04-EVALUATION.md#8-pre-registration-and-the-promotion-gate) requires.

---

*Written material in this repository is licensed CC BY 4.0.*
