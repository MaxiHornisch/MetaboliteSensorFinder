# Tasks

Prioritised. The loop takes the top unblocked task, does it, updates this file, and appends to `JOURNAL.md`.

Status: `todo` · `doing` · `blocked` · `done` · `dropped`
Priority: `P0` must exist for the project to mean anything · `P1` needed for a credible result · `P2` improves it · `P3` later

---

## P0 — the spine

| ID | Task | Status | Exit condition | Notes |
|---|---|---|---|---|
| T-001 | Recompute the framing numbers from primary sources | todo | `docs/data/framing-numbers.json` exists with orphan count and `Tdark` share, each with source, query date and definition | The quoted 20–35% and $2.6B figures are definition-dependent and contested. No metric may depend on them — see `docs/00-PROBLEM.md` |
| T-002 | Write the `loopspec` JSON schema and validate `v0.1.0-baseline.yaml` against it | **done** 2026-11-07 | `pytest tests/unit/test_loopspec.py` — **16 passed** | Schema before implementation. The tests assert the guarantees, not just conformance: no raw docking score as a ranking signal, fusion fittable only on `val`, ≥2 independent channels, bounded refinement, no `AVOID`-licensed library, no predicted structures at an early cutoff |
| T-003 | Define and validate the `EvidenceItem` / `Hypothesis` / `TargetDossier` schemas | todo | Round-trip tests pass; a hand-written example dossier validates | The contracts in `docs/02-ARCHITECTURE.md` §4 |
| T-004 | `scripts/doctor.py` — tool readiness table | **done** 2026-11-07 | Runs; **Tier 0 green** on a fresh Python 3.12.10 venv; exits 1 with a per-tool reason when something is missing | Running it immediately found a bug in itself: `pytest` was checked as a PATH executable, which misses a venv install. Now checked as a module |
| T-005 | Snapshot manifest fetcher with SHA-256 verification | todo | `scripts/fetch_snapshot.py --manifest snap_2018-01-01_v1` verifies hashes and fails loudly on mismatch | Leak L2 control |
| T-006 | Date-filter enforcement at the MCP/tool boundary | todo | `tests/controls/test_date_filter.py` passes: an injected post-cutoff document never reaches an agent | **Highest-value single task.** Leak L1. Must be structural, not prompted |
| T-007 | `L0` first pass: build `DeorphBench` at cutoff 2018-01-01 | blocked by T-005, T-006 | `benchmarks/deorphbench-2018-01-01-*.parquet` exists; `curation-log.md` records a decision per candidate; split-disjointness test passes | Report honest item count. If N is too small to support our claims, that is the finding |
| T-008 | Negative control suite | blocked by T-003 | All six controls in `tests/controls/` run and the pipeline fails them as expected | A control that passes is a bug |
| T-009 | Physics regression suite | todo | `pytest tests/physics` passes; redocking within 2 Å on ≥80% of a fixed 30-complex set | Independent of the benchmark. Catches a misconfigured stack |
| T-010 | Contamination probe | blocked by T-007 | Every benchmark item has a contamination score and bin; `tests/controls/test_contamination_probe.py` passes | Without this, no recovery number is interpretable |

| T-036 | Metric implementations, verified against analytic values | **done** 2026-11-07 | `pytest tests/unit/test_metrics.py` — **27 passed** | `src/msf/eval/metrics.py`: recall@k, MRR, EF, BEDROC, Brier, ECE, risk–coverage, selective accuracy, false-confidence rate, decision utility, BCa bootstrap, paired bootstrap. Writing the tests first caught a real bug — see failure mode A14 |

## P1 — a credible result

| ID | Task | Status | Exit condition | Notes |
|---|---|---|---|---|
| T-011 | Implement the five baselines | blocked by T-007 | Each baseline scores the benchmark; popularity baseline is a required column in every table | Beating popularity is the real bar |
| T-012 | `structuralist` channel incl. pocket quality gating | todo | Emits a `pocket_verdict`; refuses to pass a model failing the PAE-within-pocket gate | The gate is the point, not the docking |
| T-013 | `chemist` channel + property-matched decoys | todo | Decoy property-match test scores near chance on a descriptor-only classifier | If this fails, every enrichment metric is meaningless |
| T-014 | `screener` channel, z-score only | blocked by T-012, T-013 | Raw score submitted as a ranking signal is rejected by the schema | The prohibition in `.claude/agents/screener.md` |
| T-015 | `librarian`, `geneticist`, `comparativist` channels | todo | Each writes a schema-valid bundle or a documented empty one | Empty channels with query logs are valid results |
| T-016 | `falsifier` attack battery | blocked by T-003 | All nine standard attacks execute and record outcomes; `restatement` correctly detects a shared template | `restatement` is the one that matters most |
| T-017 | `fusion` + isotonic calibration, fitted on `val` | blocked by T-007 | Reliability diagram renders; refuses to run with `sealed` in scope | |
| T-018 | `auditor` provenance re-derivation | blocked by T-003 | Detects a deliberately overstated claim in a seeded test dossier | Test it with a planted error |
| T-019 | End-to-end `L1` on one target | blocked by T-012..T-018 | A validated dossier with zero unsupported auditor findings | The first real output |
| T-020 | `L2` on `dev`, full report | blocked by T-019, T-011 | `reports/v0.1.0-dev.md` with controls, strata, baselines, CIs | |
| T-021 | Guard hooks | todo | Modifying `tests/controls/` during an `L2` run is a hard error | `docs/07-VERSIONING.md` §5 |
| T-032 | Resolve the `DeorphBench` licence question | todo | A written position on whether the curated item list inherits GtoPdb share-alike, reviewed by someone competent to judge | **Blocks success criterion 1.** Until resolved, ship identifiers + reproduction script only. `docs/06-DATA-SOURCES.md` §4 |
| T-033 | Build the ChEBI + LIPID MAPS candidate library and measure its coverage gap vs HMDB | todo | Library exists; the fraction of known endogenous ligands it contains is reported | HMDB is CC BY-NC and unusable. We need to know what the substitution costs us, in numbers |
| T-034 | Enforce `allowed_structure_sources` in the guard | todo | A predicted model on a 2018-cutoff split is refused | Leak L5b. AlphaFold DB postdates the cutoff entirely |
| T-035 | Confirm the 25 `UNVERIFIED` licence items | blocked, needs human | Each resolved to a verdict in `docs/06-DATA-SOURCES.md` | Must happen before any public release |

## P2 — useful

| ID | Task | Status | Exit condition |
|---|---|---|---|
| T-022 | Static dossier renderer (web v0) | todo | A single self-contained HTML file per dossier, works offline |
| T-023 | `runs/INDEX.md` ledger + `scripts/compare_runs.py` | todo | A reproduction can be diffed against its recorded result |
| T-024 | Nested cutoffs (2015 / 2021) | blocked by T-007 | Three benchmarks exist; N reported for each |
| T-025 | `--blind-targets` contamination mode | blocked by T-010 | Runs end to end; reported as a separate configuration |
| T-026 | Co-folding affinity channel alongside docking | blocked by T-014 | Disagreement between the two is reported, not averaged |
| T-027 | Web app over Parquet run records | blocked by T-022 | Drill-down from leaderboard to raw artifact |

## P3 — later

| ID | Task | Status |
|---|---|---|
| T-028 | Set-valued ground truth for multi-ligand targets | todo |
| T-029 | Chemical-similarity-graded recovery metric | todo |
| T-030 | Peptide ligands (currently out of scope) | todo |
| T-031 | Second sealed split held outside the dev loop | todo |

---

## Dropped

| ID | Task | Why |
|---|---|---|
| — | *(none yet)* | Record dropped tasks here with the reason, rather than deleting them |

## Blocked, needing a human

| What | Who | Why |
|---|---|---|
| Relaxing any inclusion criterion I1–I5 | problem owner | `L0` may not do this autonomously. It is the most tempting corner to cut and invalidates the benchmark |
| Unsealing `sealed` | problem owner | Requires the key and goes in `benchmarks/UNSEAL-LOG.md` |
| Confirming database licences before release | problem owner | See `docs/06-DATA-SOURCES.md`; anything marked UNVERIFIED must be confirmed |
