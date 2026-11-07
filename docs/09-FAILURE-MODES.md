# Failure modes

Status: living catalogue, v1.
Every entry is a specific way this project produces a wrong answer that looks right.

This file exists because the failures in this area are not random errors —
they are *systematic*, they *inflate* results, and they are *invisible in the output*.
A ranked list of ligands looks identical whether the pipeline is sound or broken.

Each entry has: what goes wrong, why it is seductive, how we detect it, and whether it is actually closed.

Legend — **Closed**: enforced structurally. **Mitigated**: measured or controlled, not eliminated. **Open**: known and unfixed.

---

## A. Evaluation failures

These are the worst, because they corrupt every number downstream.

### A1. Dating an assignment by database release — **Closed**

A ligand pairing appearing in ChEMBL v30 may have been published years before v30 shipped.
Date by release and your "post-cutoff" items leak across the cutoff.

*Why it is seductive:* release dates are trivially available; publication dates require following
every record to its primary reference, which is slow.

*Detection:* every item carries `date_confidence` with a reason; the curator must record a primary
reference; the auditor re-derives a 10% sample independently.

*Note:* this failure makes results look **better**, which is why it would never be caught by sanity-checking the output.

### A2. Homologue split across splits — **Closed**

A protein in `dev` whose 80%-identical homologue is in `sealed`.

*Detection:* `tests/controls/test_split_disjoint.py` runs all-vs-all identity between splits.
Splitting is by sequence-similarity *cluster*, never by protein.

### A3. Decoy separability — **Closed**

Decoys distinguishable from actives on physicochemical properties alone.
Enrichment metrics computed against such a set measure property differences, not binding.

*Why it is seductive:* it produces excellent AUC, and the decoys look reasonable by inspection.

*Detection:* a logistic model on descriptors alone must score near chance.
If it does not, `chemist` must regenerate the set before `screener` runs.

### A4. Model memorisation — **Mitigated, cannot be closed**

The language model's training data contains the post-cutoff literature.
The agent may recall the answer and construct an evidence trail backwards to it.

*Why it is the hardest one:* it produces excellent benchmark numbers and a worthless method,
and there is no way to remove knowledge from a model.

*Mitigation:* closed-book contamination probe per item; metrics reported per contamination bin;
a scored non-LLM pipeline path; a schema requirement of ≥2 independent non-LLM channels;
an optional `--blind-targets` mode.

*Residual:* the probe measures *elicitable* recall, a lower bound. The `clean` bin is optimistic
in an unknown direction. **This is the project's single largest unresolved threat to validity.**

### A5. Tuning on the test set — **Closed procedurally**

An agent iterating for hours will overfit any split it can read, with no ill intent.

*Detection:* `sealed` is encrypted; only a human can unseal it; every unseal is logged with the loop version.
A loop version with five unseal events against it has been tuned on the test set, and the log says so.

*Residual:* a human who has seen the numbers cannot unsee them. See [07-VERSIONING.md §9](07-VERSIONING.md).

### A6. Benchmark drift — **Closed**

Improving the score by changing the benchmark rather than the method.

*Detection:* guards forbid `L1`/`L2`/`L3` from writing to `benchmarks/` at all.
Benchmark changes go through `L0` with a recorded human decision.
A MAJOR version bump marks prior results incomparable.

### A7. Relaxing inclusion criteria to grow N — **Open, human-gated**

The benchmark will be small. The obvious fix is to loosen I1–I5. That invalidates it.

*Mitigation:* the `curator` is explicitly forbidden from doing this autonomously;
it must propose an earlier cutoff, more families, or orthologues instead.
Any relaxation requires a human decision in `benchmarks/curation-log.md`.

*Why it stays open:* it is a judgement call, and a determined human can always justify one.

### A8. Reporting a pooled metric — **Closed**

A pooled number hides that the method works on one protein family and fails on the rest.

*Detection:* the `statistician` refuses to emit a pooled metric without its strata.

### A9. Missing the popularity baseline — **Closed**

Most proteins bind common metabolites. Ranking by "how often is this anyone's ligand"
is shockingly strong, and a method that does not beat it has learned nothing.

*Detection:* the report generator refuses to emit a results table without the popularity column.

### A10. Survivorship bias in the positive set — **Open, unfixable**

Ligands that *were* found are not a random sample of ligands that exist.
They are biased toward abundant, easily assayed metabolites in well-funded families.
Performance on `DeorphBench` therefore **overestimates** performance on the orphans that remain,
which are harder by selection.

*Mitigation:* report family and ligand-class strata so the bias is visible. We cannot correct it.

### A11. Licence propagation into the deliverable — **Open**

Our primary ground-truth source (GtoPdb) is ODbL + CC BY-SA 4.0, and ChEMBL is CC BY-SA 3.0.
If the curated benchmark counts as an adapted database, share-alike propagates into the thing we
most want others to reuse.

*Why it is seductive:* it is invisible until release, and the easy move is to assume facts are
unprotectable and ship anyway.

*Mitigation:* `DeorphBench` ships as identifiers plus a reproduction script rather than as
redistributed data; `AVOID`-licensed sources are excluded from the default configuration by a test,
not by a promise.

*Why it stays open:* we are not qualified to settle whether CC BY-SA "adapted material" or the EU
*sui generis* right applies, and getting it wrong harms success criterion 1 directly.
See [06-DATA-SOURCES.md](06-DATA-SOURCES.md) §4.

### A13. A data API that fails open on a bad filter — **Closed**

The ChEMBL REST API accepts a malformed filter parameter, ignores it, and returns the **full**
unfiltered result set with HTTP 200.
A typo in a date filter therefore does not error — it silently returns everything, including
post-cutoff records, and the run proceeds normally.

*Why it is the nastiest one in this category:* every other leak requires someone to do something wrong.
This one requires only a typo, and the failure signature is indistinguishable from success.

*Detection:* every date-filtered query wrapper asserts `filtered_count < unfiltered_count`
before returning, and records both counts in the evidence provenance.
A filter that changed nothing is treated as a failed filter, not an empty result.
Generalised: **no retrieval wrapper may trust that a filter was applied — it must verify it.**

### A14. A metric that depends on input row order — **Closed**

Equal-mass ECE binning cuts by count. With tied predictions — a model emitting 0.9 a
thousand times — the cut lands mid-tie, scattering identical claims across bins,
and the score becomes a function of **how the rows happened to be sorted** rather than of
the data. The same predictions and the same outcomes scored 0.5 or 0.4 depending on order.

*Why it is seductive:* the implementation looks obviously correct, the metric returns a
plausible number, and nothing in a pipeline would ever flag it.

*Detection:* bin boundaries are pushed past tie groups, so identical probabilities always
share a bin. Pinned by `test_ece_does_not_split_tied_probabilities_across_bins` and a
general permutation-invariance test.

*Found by:* writing the test first and getting an answer that disagreed with the
hand-derived one. The implementation was wrong, not the test.
This is the clearest argument in the repository for the project's own rule that a metric
must be pinned by a case whose answer was derived by hand.

### A12. Index date mistaken for publication date — **Closed**

Literature indexes record when *they* indexed a paper, not when it was published.
A paper published 2017-12-31 can carry a Europe PMC first-index date of 2019-03-26 —
a real, verified example.
Date-filtering a *current* index is therefore provably not the same as querying the index as it stood at `C`.

*Detection:* items are dated by publication, cross-checked against Crossref, and a date that
resolves only from an index field is marked `date_confidence: low`.

---

## B. Scientific failures

### B1. Raw docking score as a cross-ligand ranking signal — **Closed**

Empirical scoring functions rank poses within one ligand acceptably and rank different molecules poorly.

*Why it is seductive:* the score has energy units, so it looks like an affinity.

*Detection:* the schema rejects a raw score submitted as a ranking.
Only decoy-calibrated z-scores and library percentiles are permitted.

### B2. Docking into a pocket that does not exist — **Closed**

A predicted model of an orphan has unreliable pocket geometry precisely because no experimental
structure constrains it. Docking proceeds anyway and returns a normal-looking ranked list.

*Detection:* `structuralist` must emit a `pocket_verdict` before `screener` may run,
gating on pLDDT **and** PAE *within* the pocket. PAE matters more: a pocket can be built from
high-pLDDT residues whose relative positions are unconstrained.
`no_usable_pocket` blocks the channel.

### B3. Single-conformer artifacts — **Mitigated**

A hit driven by one outlier conformer out of eight in an ensemble.

*Detection:* `screener` reports conformer attribution; the falsifier's `template_dependence`
attack removes the driving structure and re-runs.

### B4. Correlated channels counted as independent — **Mitigated**

`homology` transfers a ligand from template T; `screener` docks against a structure derived from T.
Fusion treats them as two channels. Confidence inflates.

*Why it is the subtlest one:* both channels are individually correct. Only their *combination* lies.

*Detection:* the falsifier's `restatement` attack traces each channel to its origin;
`fusion` applies a correlation discount using a matrix estimated on `val`.

*Residual:* the correlation matrix is estimated on small N and is itself uncertain.

### B5. Promiscuous molecules as apparent hits — **Closed**

Large, flexible, highly charged molecules score well against everything.
They are a scoring-function bias, not a finding.

*Detection:* the falsifier's `promiscuity` attack scores the ligand against ≥100 unrelated proteins.
`screener` also checks whether scores correlate with molecular weight — the fastest way to detect that
the pipeline is measuring size rather than fit.

### B6. The true ligand is not in the library — **Open, bounded**

If the candidate library lacks the answer, no downstream step can find it and nothing errors.

*Mitigation:* on the benchmark, library membership of known answers is checked and reported as a
coverage statistic, bounding the problem. In discovery mode it is unknowable at runtime,
so every dossier carries an explicit statement of what the search could not have found.

### B7. Chirality-blind scoring — **Open, declared**

Classical docking distinguishes enantiomers poorly. For a metabolome full of stereoisomers this matters.

*Status:* `test_chirality_sensitivity` is marked `xfail` with a reason rather than omitted.
Known limitations are encoded as expected failures so they stay visible.

### B8. Protonation and tautomer errors — **Closed**

A carboxylate modelled neutral changes every downstream score and produces no error message.

*Detection:* `test_protonation_invariance`; InChIKey round-trip checks after every format conversion.
Format conversion silently mangling structures is the most common unreported bug in pipelines like this.

### B9. Co-expression over-interpreted — **Closed**

Co-expression reflects shared tissue specificity and cell-type composition as readily as pathway membership.

*Detection:* `geneticist` must report the coefficient and a null distribution, never an adjective.
The `auditor` flags "strong co-expression" attached to a rho of 0.31 as `OVERSTATED`.

### B10. mQTL attributed to the wrong gene — **Mitigated**

Loci contain several genes. Attributing a metabolite QTL to the target rather than a neighbour
turns the strongest channel into a false one.

*Mitigation:* colocalisation evidence required where available; explicit attribution-confidence
field per mQTL; absence of colocalisation must be stated.

### B11. Using a predicted structure that did not exist at the cutoff — **Closed**

AlphaFold DB postdates both the 2015 and 2018 cutoffs entirely.
Any predicted model is future information at those dates, however reasonable it looks.

*Why it is seductive:* without predicted models most orphans have no structure at all,
so the structure channel goes dark and the loop looks worse. The temptation is to "just use the model".

*Detection:* `allowed_structure_sources` in the loopspec, enforced by the guard.
The honest consequence — that `DeorphBench` at an early cutoff partly measures working *without* a
structure — is stated in [04-EVALUATION.md §9](04-EVALUATION.md) rather than worked around.

### B12. A model whose training data postdates the cutoff — **Mitigated**

A co-folding or affinity model cannot respect a cutoff its weights already crossed,
no matter what inputs we give it.

*Detection:* such channels are disabled on early-cutoff splits, or run only as a separately-reported,
explicitly-contaminated configuration. This is the gating condition on proposal `P-002`.

*Residual:* the same argument applies to the language model, and there it cannot be fixed at all — see A4.

### B13. Library coverage gap forced by licensing — **Open, bounded**

HMDB is the natural human-metabolite reference set and is CC BY-NC, so we cannot use it.
The redistributable substitutes have worse coverage, so the true ligand is more likely to be absent
from the search space — and when it is absent, nothing errors.

*Mitigation:* library-membership of known answers is reported as a coverage statistic on the benchmark,
and every dossier states what the search could not have found.
A scientific limitation created by a licence, and labelled as such rather than disguised as a design choice.

---

## C. Agentic failures

### C1. Claim drift — **Closed**

A claim hedged in the evidence, firmer in the hypothesis, stated as fact in the report.
Each step small; the result wrong.

*Why it dominates:* it requires no bad reasoning anywhere. It is an accumulation of reasonable paraphrase.

*Detection:* the `auditor` re-derives every claim from the underlying artifact — not from the evidence
summary, which is where drift hides. `librarian` must attach a verbatim `quote` to every claim.

### C2. Unbounded critique loops — **Closed**

A hypothesis refined against a critic indefinitely converges on text that satisfies the critic,
not on a better hypothesis.

*Detection:* refinement bounded at 3 rounds. At the bound the hypothesis is passed forward
**with the unresolved attack attached**, not silently accepted.

### C3. An adversary that can edit what it attacks — **Closed**

An agent with both roles will, over a long run, quietly soften the target.

*Detection:* the `falsifier` is read-only on hypotheses, by tool restriction.

### C4. Prompt-level guardrails treated as guarantees — **Closed**

"Do not use post-cutoff sources" in a prompt is a suggestion that will eventually be ignored.

*Detection:* every leakage control is a hook or an MCP wrapper that refuses the call.
See [07-VERSIONING.md §5](07-VERSIONING.md).

### C5. Context exhaustion mid-run — **Closed**

A long run fills the context and the agent loses the thread.

*Detection:* state in files (`TASKS.md`, `JOURNAL.md`, `PROMPT.md`, run records);
every atomic step in its own subagent; the orchestrator never computes.

### C6. Silent prompt drift across a long session — **Open**

Agent definitions are in git, but a long interactive session can change behaviour without a version bump.

*Mitigation:* the orchestrator is instructed to reflect behavioural prompt changes into the loopspec
and bump the version. This is a convention and is imperfectly enforced. Genuinely open.

### C7. Finding *something* that improved — **Closed**

An agent evaluating its own change will find some metric that moved and report that one.

*Detection:* pre-registration names the metric and the expected effect *before* the run.
A report whose metric differs from its pre-registration is labelled **exploratory**
and excluded from promotion.

---

## D. Presentation failures

### D1. Inflated framing numbers — **Closed**

"$2.6B per drug", "90% failure rate", "20–35% uncharacterised" are contested or definition-dependent.
Quoting them without qualification is the easiest thing for a reader to check and the fastest way
to lose their trust.

*Detection:* [00-PROBLEM.md](00-PROBLEM.md) carries a confidence column for every framing number;
no metric depends on any of them; `T-001` recomputes the two we use from primary sources.

### D2. Hedged language covering an unsupported claim — **Closed**

"May suggest" does not convert an unsupported statement into a supported one.

*Detection:* the `auditor` treats hedging as orthogonal to support and flags it.

### D3. A confident-looking dossier for a target with no evidence — **Closed**

*Detection:* abstention is a first-class output; `scribe` is instructed to write a thin document
when the audited dossier is thin; empty channels appear in the dossier with the queries that
came back empty.

---

## How to use this file

- Before believing a result, check which of these could produce it.
- When a new failure is found, add it here **before** fixing it, with the run that exposed it.
- When a control is added, link it to the entry it closes.
- An entry moving from **Open** to **Closed** requires a test, not an intention.

---

*Written material in this repository is licensed CC BY 4.0.*
