# Versioning and iterating on the loops

Status: specification, v1.
How a loop is defined as data, how it changes, and how we know a change was an improvement rather than noise or self-deception.

## 1. The problem this solves

An agentic research loop that can edit itself will, given hours and an objective, improve its score.
It will not necessarily improve the method.
The cheap paths to a better number — tuning on the test set, relaxing a control, narrowing the benchmark,
rewriting the metric — are all available to the agent and all look like progress from inside the loop.

So the loop is treated as a **versioned artifact under configuration control**, not as a codebase an agent edits freely:

1. The loop is **declarative data** (`loops/v<x.y.z>.yaml`), so a change is a reviewable diff.
2. A change is **pre-registered** before it is measured.
3. The test split is **sealed** so it cannot be tuned against.
4. The evaluation is **immutable from inside the loop**, enforced by hooks.
5. Every result is bound to an immutable **run record** and a **promotion decision** that is recorded whether it passes or fails.

## 2. The loopspec

A loop version is a YAML document validated against [loops/loopspec.schema.json](../loops/loopspec.schema.json).
Nothing that affects a result may live only in a prompt: if it changes the output, it is in the spec and therefore in the hash.

```yaml
loopspec_version: "1"
id: v0.2.0-fusion-correlation
extends: v0.1.0-baseline          # inheritance keeps diffs small and readable
description: >
  Discount agreement between correlated evidence channels when fusing.

channels:
  literature:
    agent: librarian
    enabled: true
    max_documents: 60
    date_filter: strict            # strict | none — 'none' forbidden on benchmark splits
  structure:
    agent: structuralist
    enabled: true
    pocket_detector: [fpocket, p2rank]
    pocket_quality_gate:
      min_plddt: 70
      max_pae_within_pocket: 10
      min_volume_A3: 150
    ensemble:
      method: af2_subsampled
      n_conformers: 8
  screening:
    agent: screener
    docking: { engine: vina, exhaustiveness: 16, seed: from_run_id }
    cofolding: { model: boltz2, affinity_head: true }
    score_normalisation: decoy_zscore   # raw scores are not a permitted ranking signal
  genetics:   { agent: geneticist,     enabled: true }
  homology:   { agent: comparativist,  enabled: true, foldseek_evalue: 1e-3 }

hypothesis:
  agent: hypothesizer
  min_independent_channels: 2
  require_mechanism: true

falsification:
  agent: falsifier
  battery: [decoy_substitution, pocket_ablation, abundance, pathway_coherence,
            promiscuity, template_dependence, literature_contradiction,
            conservation, restatement]
  max_refinement_rounds: 3

fusion:
  model: logistic_l2
  correlation_discount: true       # ← the change in this version
  calibration: isotonic
  fitted_on: val
  abstain_below: 0.35

models:
  orchestrator: claude-opus-5
  channels:    claude-sonnet-5-5
  falsifier:   claude-opus-5       # the adversary gets the stronger model, deliberately
  probe:       claude-haiku-5-5

budgets:
  usd_per_target: 4.00
  wallclock_minutes_per_target: 25
  gpu_seconds_per_target: 900
```

Design notes:

- **`extends`** keeps a version diff to the lines that changed, which is what makes review feasible.
- **`seed: from_run_id`** makes stochastic steps reproducible without pinning a constant across runs.
- **The falsifier is given the strongest model.** If the adversary is weaker than the proposer, everything survives.
- **Budgets are in the spec**, so cost is a declared property of a loop version and a change that triples cost is visible in the diff.

### 2.1 Versioning policy

Semantic versioning over *comparability of results*, which is the only property that matters here:

| Bump | When | Consequence |
|---|---|---|
| **MAJOR** | The benchmark, the splits, or the primary metric changes | Results are **not** comparable to prior versions. Prior numbers must be recomputed or explicitly marked incomparable |
| **MINOR** | A channel, agent, model, or fusion method changes | Comparable on the same benchmark. Requires a full `L2` run and a promotion decision |
| **PATCH** | Bug fix, prompt wording, logging, performance — no intended effect on results | Requires an `L2` run on `dev` to **confirm the absence of an effect**. A patch that moves the metric is reclassified as MINOR |

That last rule matters.
The common self-deception is shipping a "small fix" that happens to improve the score and never testing it.
A patch that moves a metric was not a patch.

Model identifiers are part of the spec and a model change is **always at least MINOR**,
because it changes results even when nothing else does.

## 3. Pre-registration

Before a version runs against `val` or `sealed`, `prereg/v<x.y.z>.yaml` is written and hashed:

```yaml
loop_version: v0.2.0-fusion-correlation
incumbent: v0.1.0-baseline
hypothesis: >
  Discounting correlated-channel agreement reduces over-confidence on targets where
  homology and screening share a structural template, improving calibration without
  reducing recall.
primary_metric: selective_accuracy_at_20pct_coverage
expected_direction: increase
minimum_effect: 0.05
secondary_metrics: [ece, brier, recall_at_10, false_confidence_rate]
splits: [dev, val, sealed]
controls_required: all
stopping_rule: >
  If the effect is absent on dev (CI includes zero), stop. Do not proceed to val.
analysis: paired bootstrap, 10000 resamples, BCa, on identical items
written_at: 2026-11-07T10:00:00Z
```

The hash goes into the run manifest.
A report whose metric does not match its pre-registration is flagged by the report generator —
not blocked, because exploratory analysis is legitimate, but **labelled exploratory** and
excluded from promotion.

The distinction between confirmatory and exploratory results is the whole point.
Exploratory findings are how you learn; confirmatory findings are what you claim.

## 4. The sealed split

`benchmarks/splits/sealed.age` is encrypted at rest. `scripts/unseal.py`:

- requires a human-supplied key — no agent can unseal it,
- appends to `benchmarks/UNSEAL-LOG.md`: who, when, which loop version, which prereg hash,
- refuses a second unseal for the same loop version without `--force`, which is itself logged,
- is the only path by which sealed data enters a run.

The unseal log is published. A loop version with five unseal events against it has been tuned on the test set,
and the log makes that visible to a reader rather than leaving it to trust.

## 5. Guard rails, as code

Prompt instructions are suggestions. These are enforced by `PreToolUse` hooks in
[.claude/settings.json](../.claude/settings.json) calling `scripts/guard.py`.

| Guard | Rule |
|---|---|
| `tests/controls/` immutability | No write during an `L2` run. Modifying a control to pass it is a hard error |
| `benchmarks/` immutability | `L1`, `L2`, `L3` may not write. Only `L0`, with a recorded human decision |
| Date filter | A retrieval tool call without a resolved cutoff is refused in benchmark mode |
| Live endpoint block | During a benchmark run, egress to un-pinned live database hosts is refused |
| Sealed scope | `fusion` and any fitting step refuse to execute if `sealed` is in scope |
| Session isolation | `L1`/`L2` refuse to start in a session that has touched post-cutoff sources |
| Metric integrity | The report generator refuses to emit a results table without the popularity baseline, or a point estimate without a CI |
| Budget | A target exceeding its declared budget halts and records a partial dossier rather than silently continuing |

Each guard exists because the corresponding mistake is easy, plausible, and invisible in the output.

## 6. Run records

```yaml
run_id: r_8f3a1c...            # content hash of this manifest
loop_version: v0.2.0-fusion-correlation
loopspec_sha256: ...
prereg_sha256: ...
git_commit: ...
env_lock_sha256: ...           # uv.lock
snapshot_manifest: snap_2018-01-01_v3
split: dev
seeds: { global: 8f3a1c, per_target: derived }
models: { orchestrator: claude-opus-5, ... }
tool_versions: { vina: 1.2.5, rdkit: 2025.03.1, boltz: 2.1.0, foldseek: 10-941cd33 }
controls_passed: true
cost: { usd: 142.80, gpu_seconds: 41200, tokens: 18.4e6 }
started / finished: ...
```

Immutable. `runs/` is git-ignored except `runs/INDEX.md`, a committed ledger of
`run_id · loop_version · split · primary metric · controls_passed · commit`.
Artifacts go to DVC or object storage; the index carries the hashes.

Two runs sharing a manifest must produce the same result.
`tests/controls/test_determinism.py` enforces this for tools that can be deterministic,
and the manifest names those that cannot.

## 7. The iteration workflow

```
 idea ──▶ loops/PROPOSALS.md            ranked by expected value / cost
            │
            ▼
      loopspec diff                     a reviewable change, not a prose intention
            │
            ▼
      prereg/v<x.y.z>.yaml              metric and expected effect, written FIRST
            │
            ▼
      L2 on dev ──── effect absent? ──▶ STOP. Record in CHANGELOG. Most die here
            │
            ▼
      L2 on val                         fit weights, thresholds, calibration
            │
            ▼
      human unseals  ──▶  L2 on sealed  ONCE. Logged
            │
            ▼
      promotion gate (04-EVALUATION §8)
            │
      ┌─────┴─────┐
   promote      reject
      │             │
      └──────┬──────┘
             ▼
   loops/CHANGELOG.md — recorded either way, with numbers
```

The `dev` stopping rule is what makes this affordable.
Most proposals have no effect; finding that out on `dev` costs little, and it preserves the sealed split
for the few changes that survive.

### 7.1 The changelog records failures

```markdown
## v0.2.1-diffdock — REJECTED  (2026-11-07)

Replaced Vina with DiffDock-L in the screening channel.

prereg: sha256:4c1f... · primary: selective_accuracy@20% · expected +0.05

| Metric | Incumbent | Candidate | Δ (95% CI) |
|---|---|---|---|
| selective_accuracy@20% | 0.41 | 0.39 | −0.02 (−0.09, +0.05) |
| recall@10 | 0.28 | 0.31 | +0.03 (−0.02, +0.08) |
| false_confidence_rate | 0.07 | 0.14 | +0.07 (+0.01, +0.13) |

Rejected: false-confidence rate exceeds the 0.10 gate. Pose quality improved on the
redocking regression, but confident wrong answers on negative controls went up —
better poses did not translate into better discrimination, and cost the calibration.

Kept: the redocking improvement is real and is recorded. Revisit as a pose-refinement
step downstream of ranking rather than as the ranker.
```

A changelog of rejections is the strongest available evidence that an evaluation is real.
A project whose every version was promoted did not have a gate.

## 8. Reproducing a result

```bash
git checkout <commit-from-INDEX.md>
uv sync --locked
python scripts/fetch_snapshot.py --manifest snap_2018-01-01_v3   # verifies SHA-256
python scripts/doctor.py                                         # tool readiness
python -m msf.run --loop loops/v0.2.0-fusion-correlation.yaml \
                  --split dev --run-id r_8f3a1c
python scripts/compare_runs.py r_8f3a1c runs/INDEX.md
```

`compare_runs.py` diffs a reproduction against the recorded result and reports which fields
diverged and whether the divergence is within the recorded non-determinism of the tools involved.

## 9. What this does not protect against

- **Many small untracked prompt edits.** Prompts live in agent definitions in git, but a long interactive session can drift. Mitigation: the orchestrator is instructed to reflect any behavioural prompt change into the loopspec and bump the version; this is a convention and is imperfectly enforced.
- **Developer memory of sealed results.** Once a human has seen the sealed numbers, they cannot unsee them. The unseal log makes exposure visible; it does not undo it. With more time, a second sealed split held by someone outside the dev loop.
- **Benchmark exhaustion.** A sealed split used across many versions decays into a validation set regardless of process. We track unseal count per split and will retire a split after a pre-declared number of uses.
- **Correlated proposals.** Testing twenty variants of one idea and promoting the best is multiple testing dressed as iteration. Partially addressed by Benjamini–Hochberg on secondary metrics, not fully.

---

*Written material in this repository is licensed CC BY 4.0.*
