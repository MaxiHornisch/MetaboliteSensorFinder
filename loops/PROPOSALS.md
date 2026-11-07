# Loop change proposals

The backlog for loop `L3`. Ranked by expected value per unit cost.

Each proposal must name **the metric it is supposed to move and by how much**, before it is run.
A proposal without a stated expected effect is not testable:
an agent evaluating its own change will otherwise find *something* that improved and report that.

Most of these will die on `dev`, cheaply. That is the point of the ordering.

---

## Ranked backlog

### P-001 — Discount agreement between correlated evidence channels

**Status:** next up.
**Change:** `fusion.correlation_discount: true`.
**Metric:** `selective_accuracy@20%_coverage`, expected **+0.05**. Secondary: `ece` down, `false_confidence_rate` down.

**Rationale.** The fused probability assumes channel independence.
When `homology` transfers a ligand from template T and `screening` docks against a structure derived from T,
those are one piece of evidence wearing two hats.
Both channels are individually correct; only their combination lies.
This is the main mechanism by which the architecture would produce over-confidence,
and over-confidence is the failure that costs a lab money.

**Expected cost:** negligible compute; the correlation matrix is estimated on `val`.
**Risk:** the matrix is estimated on small N and is itself uncertain. May over-discount and lose recall.

---

### P-002 — Add a co-folding affinity channel alongside docking

**Status:** queued, blocked by T-014.
**Change:** `channels.screening.cofolding.model: boltz2`, `affinity_head: true`.
**Metric:** `recall@10`, expected **+0.08**.

**Rationale.** A co-folding model with an affinity head has different failure modes from classical docking.
Disagreement between the two is informative and must be reported rather than averaged away —
agreement from two methods that fail differently is worth more than either alone.

**Expected cost:** substantial GPU. Budget bump required, which the loopspec diff will make visible.
**Risk:** the co-folding model's training data may include post-cutoff complexes. **This is leak L5 and must be
checked before the channel is enabled on any benchmark split** — a model trained past the cutoff
cannot be used in a time-split evaluation without reporting the contamination.

---

### P-003 — Conformational ensembles for cryptic pockets

**Status:** queued.
**Change:** `channels.structure.ensemble.method: af2_subsampled`, `n_conformers: 8`.
**Metric:** `recall@10` on the subset of targets whose apo structure shows no usable pocket, expected **+0.10**.
Pre-registered on that subset specifically, not on the whole benchmark, where it would be diluted to nothing.

**Rationale.** Cryptic pockets are closed in the apo structure. One conformer cannot find them.
**Risk:** more conformers means more chances for a spurious hit in an outlier conformer.
Must be paired with the `template_dependence` attack and with conformer attribution in the screener's output,
or it will inflate results rather than improve them.

---

### P-004 — Require colocalisation for mQTL evidence

**Status:** queued.
**Change:** `channels.genetics.require_colocalisation: true`.
**Metric:** `false_confidence_rate`, expected **−0.03**. Secondary: `recall@10` expected to **drop** slightly.

**Rationale.** Loci contain several genes; attributing a metabolite QTL to the target rather than a neighbour
turns the strongest channel into a false one.
**This proposal is expected to make the headline recall worse** and is proposed anyway,
because it should make the confidence honest. If it improves recall, something is wrong and we should look.

---

### P-005 — Give the falsifier a larger attack budget on surviving hypotheses

**Status:** queued.
**Change:** budget reallocation; attacks per surviving hypothesis raised.
**Metric:** `false_confidence_rate`, expected **−0.02**.

**Rationale.** Surviving hypotheses are where the cost of being wrong is concentrated. Attack them harder.

---

### P-006 — `--blind-targets` as the default configuration

**Status:** parked, pending T-025.
**Change:** identifier obfuscation on by default.
**Metric:** the gap between `clean` and `contaminated` contamination bins, expected to **narrow**.

**Rationale.** It is the strongest available contamination control.
**Why it is parked:** it badly degrades retrieval, since the agent cannot look anything up by name.
Currently reported as a separate configuration rather than the headline.
Making it the default is a MAJOR decision about what the project is measuring.

---

---

### P-007 — bindPredict as a sequence-based pocket channel

**Status:** queued. **Highest-value structural proposal.**
**Change:** add a `pocket_from_sequence` channel using Rostlab bindPredict (ProtT5 embeddings).
**Metric:** `recall@10` on targets with **no experimental structure and no close homologue**,
expected **+0.12**. Pre-registered on that subset, not pooled, where it would be diluted away.

**Rationale.** It predicts binding residues from sequence alone, needing no structural database.
That directly attacks the limitation we had written down as unavoidable: AlphaFold DB postdates the
2015 and 2018 cutoffs (leak L5b), so at an early cutoff the structure channel is nearly empty and
most orphans have neither an experimental structure nor a homologue.
From the prior architecture — see [docs/11-PRIOR-ARCHITECTURE.md](../docs/11-PRIOR-ARCHITECTURE.md).

**Risk.** Check the model's training cutoff against ours before enabling it on a benchmark split.
Its predicted residues are also a *set*, not a geometry, so the pocket-quality gate needs a
sequence-appropriate analogue — the PAE-within-pocket test does not apply.

---

### P-008 — PSICHIC as a sequence-based interaction channel

**Status:** queued, **blocked** on a training-cutoff check.
**Change:** add PSICHIC (physicochemical graph neural network) as an interaction channel.
**Metric:** `recall@10`, expected **+0.10**; and a large reduction in cost per target,
since it screens at roughly 100k SMILES/hour against docking's throughput.

**Rationale.** Sequence-based, so like `P-007` it works where no structure exists.
Fast enough to screen the full metabolome rather than a pre-filtered subset,
which bears directly on failure mode B13 (library coverage).

**Risk — this is the blocker.** Its training data almost certainly postdates our cutoffs: **leak L5c**.
A model whose weights crossed the cutoff cannot respect it whatever we feed in.
If contaminated it is still usable, but only as an explicitly contaminated configuration reported
apart from the headline. **Do not enable on a benchmark split before checking.**

---

### P-009 — Blind the executing agent with masked decoy batches

**Status:** queued. Cheap.
**Change:** the screening agent receives a randomised batch of 50 masked compounds —
49 property-matched decoys and 1 candidate — and does not know which is which.
**Metric:** the gap between `clean` and `contaminated` contamination bins, expected to **narrow**.

**Rationale.** Taken directly from the prior architecture, which had it and we did not.
We had decoys for *metric* purposes but never blinded the agent doing the execution,
so an agent that recognised the candidate could, in principle, treat it differently.
A per-target contamination control that costs almost nothing.

**Risk.** Masking must survive the whole call path. A compound identifiable from its SMILES string
is not masked, so the obfuscation has to be checked by a test rather than assumed.

---

## Rejected without testing

| Proposal | Why not |
|---|---|
| Use a larger model everywhere | Not a hypothesis about the method. Would change results without explaining anything, and makes every later comparison incomparable |
| Tune `abstain_below` to maximise recall | Tuning the abstention threshold against recall defeats the purpose of having one. The threshold is fitted on `val` against calibration, not recall |
| Add more decoys until enrichment looks better | Changes the metric, not the method. Decoy count is fixed by the property-match requirement |
| Drop the popularity baseline because it is "not a real method" | It is the hardest baseline to beat and the most informative. Keeping it is non-negotiable |

Recording rejections here, with reasons, is part of the evidence that the gate is real.

---

## Writing a proposal

```markdown
### P-0NN — <one line>

**Status:** queued | next up | running | done
**Change:** the loopspec diff, in spec terms, not prose intentions.
**Metric:** which pre-registered metric, which direction, minimum effect size.

**Rationale.** Why this should work.
**Expected cost.** Compute, money, wall-clock.
**Risk.** How this could make things worse, or look better while being worse.
```

A proposal that cannot name a metric and an effect size is not ready.
Send it back rather than running it.
