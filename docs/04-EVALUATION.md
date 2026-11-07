# Evaluation: how we know whether the loop is right

Status: specification, v1. This is the normative document of the project.
If any other document contradicts it, this one wins.

Everything else here — the agents, the tools, the web app — exists to be measured by what is in this file.
A method that cannot be evaluated by this protocol is not part of the project.

## 0. Principles

1. **The evaluation is designed before the method, and frozen before the method is tuned.**
   Metrics, splits and promotion thresholds are written into a pre-registration file
   and hashed into the run record. See [07-VERSIONING.md](07-VERSIONING.md).
2. **Any result that cannot be reproduced from the run record does not exist.**
3. **A control that passes is a bug.**
   Negative controls are not decoration. They are the primary bug-detection mechanism,
   and they run on every loop version before any headline metric is believed.
4. **Abstention beats a wrong answer.**
   The loop is scored on a utility that penalises confident errors more than it rewards confident hits,
   because the downstream cost is an experiment.
5. **We report the metric we pre-registered, including when it is bad.**

## 1. `DeorphBench`: a retrospective time-split benchmark

### 1.1 Why time, not target

The existing evaluation practice in ligand prediction uses random, ligand-scaffold, or held-out-target splits.
Held-out-target is the strongest of these and is the closest analogue to deorphanization:
whole proteins are removed from training, and the method must generalise across protein space.

It still answers the wrong question.
The real question is not "can you generalise across proteins"
but **"restricted to what was knowable in year Y, would this loop have found the ligand that the field published in year Y+k?"**

A time split answers that directly, and it has a property no other split has:
**the ground truth arrived independently of us.**
Nobody constructed the positive set to be findable.
The field found these ligands by experiment, for its own reasons, after the cutoff.
That is as close to a prospective trial as a retrospective benchmark can get.

We found no such benchmark for endogenous ligand assignment.
Building it is the primary deliverable.

### 1.2 Construction

```
                 cutoff C (default: 2018-01-01)
   ─────────────────────────────┼──────────────────────────────▶ time
     EVIDENCE WINDOW            │        GROUND-TRUTH WINDOW
     everything the loop may    │        the assignments the loop
     see: literature, DBs,      │        must recover; strictly
     structures, annotations    │        withheld from all tools
```

A benchmark item is a tuple:

```
(uniprot_acc, ligand_chebi_id, orphan_at_C, first_assignment_date,
 evidence_class, confidence, source_refs, split)
```

**Inclusion criteria** — all must hold:

| # | Criterion | Rationale |
|---|---|---|
| I1 | Protein had **no** agreed endogenous small-molecule ligand in IUPHAR/GtoPdb, ChEMBL or UniProt as of cutoff `C` | It must have been a genuine orphan, not a protein we merely chose to ignore |
| I2 | An endogenous ligand was reported **after** `C` and is recorded in a curated resource at freeze date `F` | The ground truth is third-party and citable |
| I3 | The assignment is supported by ≥1 direct binding or activity measurement, not inference alone | Excludes "proposed" pairings that were never shown |
| I4 | The ligand is a small molecule or lipid present in a human metabolite reference set | Keeps the search space defined; peptides are out of scope (see [00-PROBLEM.md](00-PROBLEM.md)) |
| I5 | The pairing has not been retracted or substantively contested at freeze date `F` | Contested pairings go to a separate `disputed` pool, scored but reported apart |

**Exclusion criteria:**

- Proteins whose assignment is a trivial consequence of close homology to an already-assigned protein
  (>60% sequence identity in the binding region to a pre-cutoff assigned protein) move to an `easy` stratum
  and are reported separately. They are not removed — recovering them is a sanity check, not an achievement.
- Pairings where the only evidence post-dates `F`.

### 1.3 The date problem, stated honestly

Assigning a date to a fact is the weakest joint in this benchmark. Three failure modes:

- **Database-release dates are not discovery dates.**
  A pairing first appearing in ChEMBL v30 may have been published years earlier.
  Prior work on pseudo-time-splits has flagged exactly this.
  *Mitigation:* we date items by **earliest primary publication** (Europe PMC / Crossref date of the first
  paper reporting the binding), never by database release. The database is used only to find the paper.
- **Preprints precede journal publication.**
  *Mitigation:* we take the earliest of preprint and journal date, and record both.
- **Reviews leak forward.**
  A pre-cutoff review may speculate about a ligand later confirmed.
  *Mitigation:* speculation is not an assignment under I3, but a pre-cutoff speculation is recorded in the item
  as `prior_speculation: true`, and recovery rates are reported split by this flag.
  If the loop only recovers items that were already speculated about, that is a much weaker result and must be visible.

Every item carries `date_confidence` in `{high, medium, low}` with a reason.
Headline metrics are computed on `date_confidence >= medium`; the full set is reported alongside.

### 1.4 Splits

| Split | Purpose | Access |
|---|---|---|
| `dev` | Loop development, prompt iteration, debugging | Open. Agents may read it freely |
| `val` | Weight fitting for evidence fusion, calibration fitting, threshold selection | Open to the fitting step only; not visible to prompt-authoring agents |
| `sealed` | Promotion decisions and reported headline numbers | **Encrypted at rest.** Unsealed only by an explicit human-run command, which appends to an unseal log |

The sealed split is the mechanism that stops the loop from tuning on its own test set.
An agent iterating for hours will otherwise, with no ill intent, overfit any set it can see.
`sealed` is stored as an age-encrypted blob; `scripts/unseal.py` requires a human-supplied key,
records who unsealed it and against which loop version, and refuses to run twice for the same loop version
without an explicit `--force` that is itself logged.

**Stratification.** All splits are stratified by protein family (GPCR / SLC / NR / enzyme / other),
ligand class (amino-acid-like, lipid, nucleotide, organic acid, other), and `date_confidence`,
so that per-stratum metrics are reportable and a single family cannot dominate the headline.

**Grouping.** Split assignment is by **sequence-similarity cluster**, not by protein.
Homologues above 30% identity land in the same split.
Splitting homologues across splits is leakage, and it is the easiest mistake to make.

## 2. The leakage taxonomy

Each row is a way to get a good number for a bad reason. Each has a closing mechanism and a test.

| # | Leak | Closed by | Test |
|---|---|---|---|
| L1 | Future literature reaches a retrieval tool | Hard date filter in the retrieval MCP layer; every retrieved document carries a date and is rejected post-cutoff at the tool boundary, not by prompt instruction | `tests/controls/test_date_filter.py` — inject a post-cutoff document, assert it never reaches the agent |
| L2 | Future annotations reach a database tool | Pinned database snapshots dated ≤ `C`; the loop may not query live endpoints during benchmark runs | `tests/controls/test_snapshot_pinning.py` — assert no network egress to live DB hosts during a benchmark run |
| L3 | Homologue in another split | Cluster-level splitting at 30% identity | `tests/controls/test_split_disjoint.py` — all-vs-all identity between splits below threshold |
| L4 | Ligand-scaffold leakage (same scaffold in `dev` and `sealed`) | Bemis–Murcko scaffold grouping applied jointly with sequence clustering | same test |
| L5 | Structure leakage — the holo co-crystal of the answer exists in the structure DB snapshot | Structures deposited after `C` excluded; **additionally**, any structure of the target with *any* ligand is flagged, and results reported with and without those targets | `tests/controls/test_structure_cutoff.py` |
| L5b | **Predicted-structure anachronism** — AlphaFold DB postdates both the 2015 and 2018 cutoffs entirely, so *any* predicted model is future information at those cutoffs | `allowed_structure_sources` in the loopspec restricted to `[experimental, homologue]` on early-cutoff splits; the guard refuses a predicted model | `tests/controls/test_structure_cutoff.py` |
| L5c | **Model-weight anachronism** — a co-folding or affinity model whose training data postdates `C` cannot respect the cutoff no matter what we feed it | Such a channel is disabled on early-cutoff splits, or enabled only as a separately-reported, explicitly-contaminated configuration. Gating condition on proposal `P-002` | Process; recorded in the run manifest |
| L6 | Decoy separability — the negative set is distinguishable on properties alone | Property-matched decoys plus the full metabolome as background; report performance against both | `tests/controls/test_decoy_property_match.py` — a logistic model on physicochemical descriptors alone must score near chance |
| L7 | **Model memorisation** — the LLM already knows the post-cutoff answer | Cannot be closed. Measured instead; see §3 | `tests/controls/test_contamination_probe.py` |
| L8 | Human leakage — a developer reads the sealed answers and adjusts prompts | Sealed split encrypted; unseal log reviewed in the run record | Process, not test. Reported in the unseal log |

L7 deserves emphasis because it is the one most teams would silently get wrong.

## 3. Contamination: the problem a time split cannot solve

A time split prevents *tools* from seeing the future.
It does nothing about the language model, whose training data contains the post-cutoff literature.
An agent asked to deorphanize GPR-something may simply recall the answer and then construct
a plausible evidence trail backwards to it.

This would produce excellent benchmark numbers and a worthless method.

We handle it in four ways:

**3.1 Measure it.** For every benchmark item, before the loop runs, a **closed-book probe**
asks a tool-less model the question directly, several ways:

- *direct*: "What is the endogenous ligand of {protein}?"
- *multiple-choice*: the true ligand among property-matched distractors.
- *masked*: the protein described only by sequence features and expression pattern, with identifiers stripped.

Each item receives a **contamination score** in [0,1].
Items are binned `clean` / `partial` / `contaminated`, and **every headline metric is reported per bin.**
The `clean` bin is the honest number. If the `clean` bin is empty or tiny, we say so.

**3.2 Report net of it.** Headline recovery is reported as
`recovery(clean)` with a bootstrap CI, alongside `recovery(all)`.
A large gap between them is itself a reportable finding about the field's benchmarking practice.

**3.3 Make recall insufficient.**
A hypothesis is only accepted with mechanistic evidence attached — pocket, pose, conservation, co-expression, genetic support.
Naming a ligand with no supporting channel scores zero.
This is enforced in the output schema: `ligand_id` without ≥2 independent non-LLM evidence channels is rejected by the validator,
not by a prompt.

**3.4 Score the pipeline separately from the narrative.**
We report two numbers for every configuration:

- **Pipeline score** — ranking produced by the non-LLM evidence channels only (structure, co-expression, genetics, chemistry).
  Immune to memorisation by construction.
- **Loop score** — the full agentic loop.

If the loop score greatly exceeds the pipeline score on contaminated items but not on clean items,
the loop is recalling, not reasoning. That comparison is in the standard report.

**Identifier obfuscation (optional mode).** `--blind-targets` replaces gene names and accessions with opaque IDs
throughout the agent-visible context, leaving sequence, structure and expression intact.
It degrades retrieval (the agent cannot look things up by name) and so is reported as a separate configuration,
not as the headline. It is the strongest available contamination control and the most expensive.

## 4. Metrics

### 4.1 Ranking

Over a candidate library of size N (default: human metabolome reference set, ~10⁴ molecules):

| Metric | Definition | Why |
|---|---|---|
| `recall@k`, k ∈ {1,5,10,50,100} | fraction of items whose true ligand appears in the top k | The researcher-facing quantity: how many do I have to test? |
| `MRR` | mean reciprocal rank of the true ligand | Single-number summary, rank-sensitive |
| `BEDROC(α=20)` | early-weighted enrichment | Standard where only the top of the list will ever be tested; α=20 ≈ 80% of weight in the top 8% |
| `EF@1%` | enrichment factor at 1% | Interpretable multiplier over random |
| `AUC-ROC` | — | **Reported but never used for decisions.** It is dominated by the irrelevant tail |

Ranking metrics are reported **per stratum** (family × ligand class × contamination bin), never only pooled.
A pooled number hides that the method works on one family and fails on the rest.

### 4.2 Calibration — the metric that matters most

The loop outputs, for each hypothesis, a probability `p` that it is correct.
A researcher allocating experiments needs that number to mean what it says.

- **Brier score** over all hypotheses.
- **Expected calibration error (ECE)**, 10 equal-mass bins, with a reliability diagram in every report.
- **Risk–coverage curve**: accuracy among the top `c` fraction the loop is most confident about, for `c` in (0,1].
  This is the curve a lab actually plans against.
- **Selective accuracy at 20% coverage** as the single pre-registered calibration headline.

A method with lower recall and honest probabilities is preferred to a method with higher recall and
probabilities that mean nothing. The promotion gate in [07-VERSIONING.md](07-VERSIONING.md) encodes this.

### 4.3 Abstention

Negative-control targets (§5) have no correct answer. For these:

- **False-confidence rate**: fraction of negative controls on which the loop emits a hypothesis with `p > 0.5`.
  Pre-registered target: **< 0.10**.
- **Abstention precision / recall** treating "no confident ligand" as a prediction class.

A loop that never abstains is disqualified from promotion regardless of its ranking metrics.

### 4.4 Decision utility

A single scalar for comparing loop versions, reflecting that a false positive costs an experiment:

```
U = Σ_hypotheses [ p_true · V_hit − (1 − p_true) · C_experiment ] over hypotheses the loop recommends testing
```

with `V_hit` and `C_experiment` set in the pre-registration (defaults: 10 and 1, i.e. a hit is worth ten wasted
experiments). `U` is reported with a sensitivity sweep over the ratio, because the right ratio is lab-specific.

### 4.5 Cost

Wall-clock, GPU-seconds, tokens and USD per target.
A method is not useful if a target costs more than the experiment it replaces.
Reported in every run record; not a promotion gate, but a reported trade-off curve against `U`.

## 5. Negative controls and ablations

Run before any headline metric is believed. Each is a target the loop processes blind.

### 5.1 Negative controls (must fail to produce confident answers)

| Control | Construction | Expected |
|---|---|---|
| `scrambled-sequence` | Real target, residues shuffled preserving composition | No confident hypothesis. Catches pipelines keyed on composition |
| `shuffled-pairs` | Real proteins, ground truth permuted | Recovery at chance. Catches evaluation-harness bugs |
| `sham-pocket` | Docking box placed on a surface patch with no detected pocket | Scores indistinguishable from random molecules |
| `mirror-protein` | D-amino-acid mirror image of the structure | Chirality-blind scoring functions produce identical scores — a known failure revealed |
| `designed-void` | A target whose "pocket" is solvent | Abstention |
| `true-orphan-hold` | Genuine current orphans with no known ligand at freeze date | No ground truth, but **confidence distribution must resemble the negative controls, not the positives**. If the loop is as confident here as on solved cases, its confidence is meaningless |

`true-orphan-hold` is the subtlest and most informative. It is also where the loop's real output lives:
these are the targets a researcher would actually care about.

### 5.2 Ablations (measure what each component contributes)

Each channel is removed in turn and the full metric suite recomputed:

- `−structure` (no docking / no co-folding)
- `−literature` (no retrieval)
- `−coexpression`
- `−genetics` (no metabolite-QTL evidence)
- `−chemistry` (no ligand-similarity transfer from homologues)
- `−falsifier` (adversarial agent disabled)
- `−LLM` (pipeline only, as in §3.4)
- `random-ranker` and `popularity-ranker` baselines

An ablation that does not hurt is a component to delete.
This is reported as a contribution table in every release.

### 5.3 Baselines that must be beaten

A new loop version is not interesting unless it beats all of these on the same split:

| Baseline | Why it is hard to beat |
|---|---|
| **Popularity** — rank metabolites by how often they appear as ligands anywhere | Shockingly strong. Most proteins bind common metabolites. Any method failing to beat this has learned nothing |
| **Nearest structural neighbour** — Foldseek to the closest protein with a known ligand, transfer its ligand | The cheapest real method; often excellent |
| **Family prior** — most common ligand class for the Pfam family | Catches family-level signal with no target-specific work |
| **Docking only** — raw docking score over the library | The thing the field actually does |
| **Co-folding affinity only** — a co-folding model's affinity head over the library | The current strong single-model approach |

Reporting a result without the popularity baseline is the most common way to overstate a method in this field.
It is a required column in every results table; the report generator refuses to emit a table without it.

## 6. Physics and pipeline regression tests

These are pass/fail, run in CI, and independent of the benchmark.
They catch the class of bug where the whole scientific stack is silently misconfigured.

| Test | Assertion |
|---|---|
| `test_redock_rmsd` | Re-docking a ligand into its own co-crystal structure recovers the crystal pose within 2.0 Å RMSD on ≥80% of a fixed 30-complex set |
| `test_crossdock_degrades` | Cross-docking into a different holo structure of the same protein is worse than redocking but better than random — a sanity ordering |
| `test_known_affinity_correlation` | Spearman correlation with measured affinity on a fixed held-out set is within the pre-registered band. **Both a floor and a ceiling**: a suspiciously high correlation indicates leakage, not success |
| `test_protonation_invariance` | Scores are stable under correct alternative protonation states at pH 7.4 |
| `test_chirality_sensitivity` | Enantiomer pairs with known differential activity are distinguished. Expected to **fail** for classical docking — recorded as a known limitation, not hidden |
| `test_units_and_signs` | Affinity units, log conventions and score signs round-trip correctly. Catches the most embarrassing and most common bug class |
| `test_determinism` | Same input and seed gives the same output, bit-for-bit where the tool allows |

`test_chirality_sensitivity` is expected to fail for some configurations and is marked `xfail` with a reason.
Known limitations are encoded as expected failures rather than omitted — see [09-FAILURE-MODES.md](09-FAILURE-MODES.md).

## 7. Statistics

- **Uncertainty**: bootstrap over benchmark items, 10,000 resamples, BCa intervals. No point estimate is ever reported alone.
- **Comparisons**: paired bootstrap on the same items when comparing loop versions. Unpaired comparison across versions is forbidden by the report generator.
- **Multiplicity**: the pre-registration names **one** primary metric per release
  (`selective accuracy @20% coverage` by default).
  All others are secondary and reported with Benjamini–Hochberg control at q=0.05.
- **Power**: with a benchmark of order 10²–10³ items, differences below a few points are not detectable.
  The pre-registration states the minimum detectable effect, and the report refuses to describe
  a difference inside the CI as an improvement.
- **Seeds**: every stochastic component is seeded from the run ID; results are reported across ≥5 seeds with a spread.

## 8. Pre-registration and the promotion gate

Before a loop version runs against `sealed`:

1. `prereg/<loop-version>.yaml` is written, naming the primary metric, the threshold, the splits and the controls.
2. It is hashed; the hash goes into the run record.
3. The sealed split is unsealed by a human, once, logged.
4. Results are written whatever they are.

A loop version is **promoted** only if, on `sealed`:

- all negative controls pass (§5.1),
- all physics regressions pass (§6),
- false-confidence rate < 0.10,
- the primary metric improves over the incumbent with a paired bootstrap CI excluding zero,
- and it beats every baseline in §5.3.

Failing promotion is a normal outcome and is recorded in `loops/CHANGELOG.md` with the numbers.
The changelog of rejected versions is part of the evidence that the evaluation is real.

## 9. What is wrong with this evaluation

Stated plainly, because an evaluation doc without this section should not be trusted.

- **Small N.** Genuine post-cutoff deorphanizations meeting all inclusion criteria are rare — plausibly tens, not thousands. Confidence intervals will be wide and we will say so. Mitigations: multiple cutoffs (2015 / 2018 / 2021) giving nested benchmarks; inclusion of non-human orthologues as a separate stratum.
- **Contamination cannot be eliminated**, only measured, and our probe measures *elicitable* recall, which is a lower bound on what the model knows. The `clean` bin is therefore optimistic in an unknown direction.
- **Ground truth is itself uncertain.** Published endogenous-ligand assignments are sometimes wrong or later revised. We inherit the field's errors. The `disputed` pool partially exposes this; it does not fix it.
- **Survivorship in the positive set.** Ligands that were found are not a random sample of ligands that exist — they are biased toward abundant, easily assayed metabolites and well-funded protein families. Performance on `DeorphBench` therefore overestimates performance on the remaining orphans, which are harder by selection. We cannot correct this; we flag it, and we report the family/ligand-class strata so the bias is visible.
- **The negative controls are synthetic.** A pipeline could pass all of them and still fail on real hard cases.
- **No prospective validation.** Nothing here has been tested in a wet lab. Every number is retrospective.
- **At early cutoffs the structure channel is badly weakened, and not by our choice.** AlphaFold DB postdates both the 2015 and 2018 cutoffs, so an honest run at those dates has experimental and homology structures only. Most orphans have neither. This is a *correct* consequence of the time split and a severe handicap: it means `DeorphBench` at `C=2018` partly measures "can you work without a structure", which is a harder and different question. Later cutoffs trade this against less post-cutoff time for discoveries to accumulate. We report the structure-source distribution with every result so the effect is visible.
- **The ground truth is copyleft, and the benchmark's own licence is therefore unresolved.** Our primary orphan-status and assignment source, IUPHAR/BPS Guide to Pharmacology, is ODbL plus CC BY-SA 4.0. Whether the curated item list is an "adapted database" carrying share-alike, or a set of unprotectable facts, is a genuinely open question we are not qualified to settle — and the EU *sui generis* database right makes it more open, not less. Until it is settled, `DeorphBench` ships as **identifiers plus a reproduction script**, not as a redistributed dataset, and the licence question is stated rather than assumed away. See [06-DATA-SOURCES.md](06-DATA-SOURCES.md) §4. **This is a real obstacle to the project's primary deliverable being usable by others, which is success criterion 1.**
- **The candidate library is a licence compromise, not a scientific choice.** HMDB is the natural human-metabolite reference set and is CC BY-NC, so we cannot use it. ChEBI plus LIPID MAPS are redistributable substitutes with worse metabolome coverage. If the true ligand is outside that coverage, the loop cannot find it and nothing errors — bounded on the benchmark by the library-membership statistic, and stated in every dossier.

---

*Written material in this repository is licensed CC BY 4.0.*
