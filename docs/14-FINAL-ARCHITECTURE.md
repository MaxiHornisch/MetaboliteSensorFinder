# Final architecture, and the MVP that implements its first slice

Status: v1, 2026-11-07. Reconciles [02](02-ARCHITECTURE.md), [03](03-LOOPS.md), [04](04-EVALUATION.md),
[11](11-PRIOR-ARCHITECTURE.md), [12](12-PIPELINE-EXECUTION.md) and [13](13-SCREENING-LOOPS.md).
Where [04-EVALUATION.md](04-EVALUATION.md) conflicts with anything here, 04 wins.

This document is the architecture of record. The earlier documents keep their reasoning, but where
they disagree with this one, this one decides and says why in §3.

---

## 1. What the architecture is

Two products share one harness:

1. **Target loop (L1).** One protein in, one audited, calibrated dossier out. Evidence comes from
   five independent channels. The prior three-stage funnel (bindPredict → PSICHIC → docking) is
   one of those channels, not the whole method ([11 §3.2](11-PRIOR-ARCHITECTURE.md)).
2. **Screen (domain × ligand).** Protein domains in, a score for every domain and pair out, with
   advancement decided by calibrated thresholds. This is the staged pipeline in
   [12](12-PIPELINE-EXECUTION.md). It runs as a channel inside L1 and as a standalone batch.

Both are judged by the same evaluation in [04](04-EVALUATION.md). The screen does not get a
separate, looser standard.

```
                      ┌────────────────── EVALUATION (04) ──────────────────┐
                      │ controls → metrics (val) → thresholds lock → sealed │
                      └──────────────▲──────────────────────────────▲───────┘
                                     │ scores, labels               │ promote/reject
 ORCHESTRATOR (Claude Code, Opus) ───┤  plans · dispatches · reads summaries only
                                     │
   ┌─────────── L1 TARGET LOOP ──────┴────────┐        ┌──── SCREEN (12, 13) ────────────┐
   │ librarian  structuralist  chemist        │        │ runner (script, no LLM)          │
   │ geneticist comparativist  [screen ch.]   │◀──────▶│   ingest → manifest → batches    │
   │        → hypothesizer → falsifier        │ channel│   → workers → thresholds.lock    │
   │        → fusion/calibrator → auditor     │        │ bindPredict · PSICHIC · DiffDock │
   └──────────────────────────────────────────┘        └──────────────────────────────────┘
          state: runs/<id>/ (manifest.json, batches/, metrics/, audit/, trace.jsonl)
```

## 2. Layers

| Layer | Owns | Built now? |
|---|---|---|
| Data contracts | Typed rows at every boundary, SHA-256 per item and per output | **Yes**: `msf.screen.ingest`, `msf.screen.runner` |
| Runner | Batching, checkpoints, count-in = count-out, retries, resume | **Yes**, tested on simulation |
| Workers | bindPredict, PSICHIC, DiffDock behind one HTTP contract | **No**. No hosts or GPUs have been provided |
| Thresholds | `loops/screen-thresholds.yaml`, uncalibrated until S3 fits it on `val` | Lock file exists; **uncalibrated** |
| Evaluation | Controls first, then calibration metrics on `val`, `sealed` once | Metrics: 2 functions. Controls: simulation only |
| Agents | Roster in [13 §1.1](13-SCREENING-LOOPS.md), existing 13 agents plus `simulator` | Definitions exist; not exercised on real data |
| Leakage guards | Hooks and `scripts/guard.py` | Existing; screen-specific hook not yet added |

## 3. Reconciliation: what changed from the prior design, and why

| # | Topic | Source says | Final decision | Why |
|---|---|---|---|---|
| R1 | Gates | PSICHIC ≥ 7.5; Vina < −8.0 ([11 §1](11-PRIOR-ARCHITECTURE.md)) | Decoy-calibrated z-score and library percentile, cut fitted on `val` | Raw scores track ligand size. 04 §5 and [screener.md](../.claude/agents/screener.md) forbid them as ranking signals |
| R2 | bindPredict signal | "≥ 2 small-molecule anchors" | Per-residue probability, reduced to a domain score; cut calibrated | Public README: it predicts binding *residues* for metal, nucleic-acid and small-molecule classes. It does not score a specific ligand ([12 §2](12-PIPELINE-EXECUTION.md)) |
| R3 | Structure for DiffDock | AlphaFold DB for every domain ([12 §6](12-PIPELINE-EXECUTION.md) phase 5) | **Discovery mode only.** On benchmark cutoffs, use experimental or homology structures | AlphaFold DB postdates the 2015 and 2018 cutoffs, so a predicted model is future information (leak L5b, [04 §2](04-EVALUATION.md)). **This conflict was not in 12** |
| R4 | Model training data | PSICHIC proposed as sequence channel ([11 P-008](11-PRIOR-ARCHITECTURE.md)) | Allowed only with a recorded training-data date. Otherwise run labelled `contaminated-model` | Leak L5c, [04 §2](04-EVALUATION.md) |
| R5 | Throughput | "~100k SMILES/hour" for PSICHIC ([11 §1](11-PRIOR-ARCHITECTURE.md)) | Not used. Measured in phase 3 | Not verified; the pilot measures it |
| R6 | Ligand library | HMDB in 12 and `Agent_v1.txt` | Benchmark runs: ChEBI + LIPID MAPS. Discovery runs: HMDB IDs and a download script | HMDB is CC BY-NC ([04 §9](04-EVALUATION.md)). **Still needs a human decision (D-LIB)** |
| R7 | Baselines | Funnel described, not measured ([11 §6](11-PRIOR-ARCHITECTURE.md)) | Funnel added as a baseline row, alongside the 04 §5.3 baselines | A serious method that must be measured, not assumed superseded |
| R8 | Short domains | Peptides out of scope under I4 | `short_domain` (≤ 30 aa) is flagged, **not** excluded. Peptide exclusion is a runner contract, not applied yet | A length alone does not identify a peptide. The input's 28 short domains are EGF-like and similar domains. See §5 |
| R9 | Count integrity | "Store all scores" ([12 D5](12-PIPELINE-EXECUTION.md)) | Enforced in code: every row is written, including excluded and error rows. A missing item fails the batch | Silent drops are the failure this project exists to prevent |
| R10 | Uncalibrated thresholds | Thresholds named but not derived ([11 §3.4](11-PRIOR-ARCHITECTURE.md)) | With `calibrated: false`, every `advanced` is `null`, not `false` | A null cannot be mistaken for a rejection in a report |

## 4. Loops

Loop mechanics follow [03](03-LOOPS.md). Each loop has a machine-checkable exit condition.

| Loop | Scope | Mechanism | Status |
|---|---|---|---|
| L0 Benchmark | Build DeorphBench | `/goal` | Not started |
| L1 Target | One protein → dossier | `/goal` | Not started. The screen is its channel |
| L2 Evaluation | Score a version | `/goal`, controls first | Controls in the simulation suite only |
| L3 Improvement | Change the loop, promote or reject | `/goal`, overnight | Not started |
| L4 Watch | Keep the repo aware | `/loop 6h` | Not started |
| S0 Calibration build | Labelled domain–ligand set | `/goal` | **Blocked: no labels in the input** (§5) |
| S1 Simulation | Test the harness with planted truth | `msf screen simulate` | **Passing: 6 of 6** on the real domains |
| S2 Execution | Real batches through workers | `msf screen run` | **Blocked: no workers** |
| S3 Evaluation | Controls, calibration, sealed once | `/goal` | Blocked on S0 and S2 |
| S4 Improvement | Screen proposals | `/goal` | Blocked on S3 |
| S5 Watch | Worker health | `/loop 30m` | Blocked on workers |

The order is fixed: **S0 before S3**, and no S2 score is interpreted before S3 has fitted and locked a
threshold. S1 may run at any time, because it touches no real data.

## 5. Input review: `input/Test_sequences.csv`

Profiled by script; no part of the 413 rows was loaded into context.

| Property | Value |
|---|---|
| Rows | 413 |
| Proteins | 100 |
| `entry_type` | 257 `domain`, 156 `family` |
| Rejected by validation | 0 (length, coordinates, alphabet, duplicates all clean) |
| Domains to screen | 257, from 74 proteins |
| Family rows | Context only, never screened (avoids counting a span twice) |
| Proteins with family rows only | 26. They reach the output as context, not as screen items |
| Short domains (≤ 30 aa) | 28. Flagged, not excluded (R8) |
| Domain length | min 12, median 78, max 693 |

**The input has no ligand labels.** It gives sequences and InterPro annotations only. Two consequences:

- **S0 cannot run.** Recall, calibration and every S3 metric need known domain–ligand pairs.
  Those must be supplied. The plan assumed this ([12 §8](12-PIPELINE-EXECUTION.md)).
- **Stage 1 can run without ligands** (bindPredict scores domains alone), so the sequences are
  enough for phase 1–2 once workers exist.

One entry is worth noting: `A0A0C5B5G6` (MOTS-c, 16 aa) is listed as a `family`, so it is context,
not a screen item. That is the right outcome, but it means the peptide rule would not have caught it
anyway.

## 6. MVP: what it does, and what it does not

**Built and tested.** `msf screen ingest`, `msf screen simulate`, and the runner invariants.

| Command | Result on the real CSV |
|---|---|
| `msf screen ingest --input ..\input\Test_sequences.csv` | Manifest written. Counts 413 / 257 / 156 / 0 |
| `msf screen simulate --input ..\input\Test_sequences.csv` | 6 of 6 scenarios pass. Exit 0 |
| `msf screen run --input …` | Raises `NotImplementedError` naming the missing workers. Exit 1. **Intended** |

Simulation scenarios, all on the real domains with planted truth:

| Scenario | What it shows | Result |
|---|---|---|
| `planted_recall` | Recall on planted positives | 1.0 |
| `size_artifact_detected` | Score-vs-length correlation rises from −0.04 (clean) to 0.61 (artifact), so the detector fires | Pass (cut 0.3, provisional) |
| `corrupt_batch_retried` | Bad checksum rejected, retry gives output identical to a clean run | Pass |
| `silent_drop_rejected` | Dropped item fails the batch with "count mismatch" | Pass |
| `resume_byte_identical` | Kill after one batch, then resume: hash equals uninterrupted run | Pass |
| `uncalibrated_advances_nothing` | 257 rows written, none advanced | Pass |

**Test suite:** 59 passed, 31 xfailed (baseline was 43 passed). The 31 xfails are pre-existing,
unimplemented tasks. No tests in `tests/controls/` were changed.

**Not built.** Real workers (phase 1), the S0 label set, S3 metrics on real data, DiffDock, the
falsifier on screen hits, and a screen-specific leakage hook for R3.

**Known weaknesses in the MVP.** The size-artifact cut (0.3) is provisional and set by hand; it is
recorded as such in `metrics.py`. The simulation tests the harness, not any scientific claim.

## 7. Environment and run records

- Python 3.11 was not on the PATH (only a Store stub). Installed `uv` and Python 3.11.18 for this
  project. This is local tooling, not a worker install.
- `uv sync --extra dev` completed. `runs/` is git-ignored, so run directories stay local.
- The simulation writes `simulation/summary.json` with a `SIMULATION` label on every result.

## 8. Blocking decisions

1. **D-LIB**: ligand library. Benchmark runs need ChEBI + LIPID MAPS per [04 §9](04-EVALUATION.md). Confirm this, or name a library.
2. **Labels**: supply the known domain–ligand pairs (S0). Without them, no metric on real data can be produced.
3. **Workers**: which hosts, and which GPUs and VRAM, run A, B, C ([12 §8](12-PIPELINE-EXECUTION.md)).
4. **R3**: confirm that DiffDock on benchmark cutoffs uses experimental or homology structures only.
5. **Duplicate file**: `docs/09-PIPELINE-EXECUTION.md` is an earlier copy of `docs/12-PIPELINE-EXECUTION.md`. Delete it? Not touched.

---

*Written material in this repository is licensed CC BY 4.0.*
