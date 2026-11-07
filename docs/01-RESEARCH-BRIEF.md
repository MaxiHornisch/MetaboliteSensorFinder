# Research brief: prior art, and what is actually wrong with it

Status: literature synthesis, v1. Compiled 2026-11-07.
Companion to [00-PROBLEM.md](00-PROBLEM.md) (the problem) and [04-EVALUATION.md](04-EVALUATION.md) (what we do about it).

**How to read the confidence column.** Claims marked `verify` have not been checked against the primary
source by a human and must be before any of this is cited in a write-up.
The loop itself treats this document as a starting point, not as evidence:
nothing here enters an evidence channel without being re-derived with provenance.

---

## 1. Where the field is

### 1.1 Experimental deorphanization

The ligands that have been assigned were, almost without exception, found by experiment —
ligand fishing from tissue extracts, reverse pharmacology against metabolite libraries,
or serendipity in a phenotype screen.
Computation has contributed to prioritisation, rarely to the assignment itself.

Illustrative recent assignments, useful because they show what a real success looks like:

| Target | Assigned ligand | Note | Confidence |
|---|---|---|---|
| GPR35 | kynurenic acid (also 2-oleoyl LPA proposed) | Frequently described as "recently deorphanized"; the assignment rests on activity plus tissue co-localisation, and a second candidate ligand persists — a good example of an assignment that is real but not clean | medium, `verify` |
| GPR15 | a peptide from the uncharacterised gene *C10orf99* | Shows that the ligand can itself come from a dark gene — out of our small-molecule scope, but instructive | medium, `verify` |
| P2RY8 | S-geranylgeranyl-L-glutathione | A modified glutathione conjugate: the answer was a molecule few libraries would contain | medium, `verify` |
| HNF4α | linoleic acid | Nuclear receptor, not GPCR. The authors argued that some earlier assignments may not reflect what is actually bound in vivo | medium, `verify` |

Two lessons we build on:

- **The answer is often not in the obvious library.** P2RY8 and similar cases argue for explicit library-coverage reporting — a dossier must state what the search *could not* have found. Implemented as the `chemist` coverage statement.
- **Assignments are contestable.** GPR35 has competing candidate ligands; the HNF4α work explicitly questions prior assignments. Ground truth is not clean, and the benchmark needs a `disputed` pool rather than a pretence of certainty.

### 1.2 How many orphans

Commonly cited: roughly 100 orphan class A GPCRs, with ~87 for the rhodopsin-like family specifically
(`verify`; the count moves as assignments are made and contested).
For the wider proteome, the "20–35% uncharacterised" figure is definition-dependent —
it depends entirely on where you draw the line, and the cleanest operationalisation is the
Pharos/IDG **`Tdark`** development level: targets that are not `Tclin`, `Tchem` or `Tbio`,
where `Tbio` requires a fractional publication count above 5.

We could not find a current published `Tdark` percentage, so `T-001` recomputes it from the live
resource and records the definition and query date alongside the number.
Quoting a range without its definition is failure mode D1.

### 1.3 Computational approaches, and how they are evaluated

| Approach | What it does | Evaluation used | Our read |
|---|---|---|---|
| Classical docking (Vina and descendants) | Pose generation + empirical score | Redocking RMSD; enrichment against decoys | Sound for poses. **Weak for ranking different molecules** — the central error when used for deorphanization |
| Co-folding with an affinity head (e.g. Boltz-2, MIT-licensed, open weights) | Predicts structure *and* binding affinity; reported as approaching FEP accuracy at a fraction of the cost | Held-out affinity sets | Genuinely promising and a strong single-model baseline. **But its training data likely postdates our cutoffs**, which makes it leak L5 in a time-split unless handled explicitly |
| Ligand-based transfer / chemogenomics | Transfer ligands from similar proteins | Random, scaffold, or held-out-target splits | Strong where homology exists; by definition weakest exactly where orphans live |
| Deep GPCR–ligand models (DeepGPCR, GPCR-IPL and similar) | Learn interaction patterns | Mostly random or scaffold splits | Performance is largely a function of the split. Hard to compare across papers |
| Geometric/evolutionary models for the GPCR–metabolome interactome (e.g. G-LEAP, 2026 preprint) | Systematic deorphanization across the metabolome | Random, ligand **and protein** splits; the protein split is framed as the deorphanization scenario | **The closest current work to ours.** Reported ROC-AUC roughly 0.69–0.71 baseline vs ~0.82 full model on the protein split (`verify`) |
| Peptide-agonist prediction from predicted active-state complexes (DeorphaNN, 2025 preprint) | Peptide GPCR agonists | Leave-one-GPCR-family-out | Peptides, so outside our scope. Group-based splits, not temporal |

---

## 2. The gap

### 2.1 Nobody holds out time

Held-out-*target* splits are the current best practice and are explicitly framed as simulating
deorphanization: remove whole receptors, predict their ligands.

Searching the current literature, **we found no retrospective time-split benchmark for endogenous
ligand assignment.** A 2025 review in the area argues that future benchmarks *should* use scaffold and
time-split evaluation and points at curated sources that could support it — which is a reasonable
indication that it has not been done.

The distinction matters and is not cosmetic:

| Split | Question answered |
|---|---|
| Random | Can you interpolate within your data? (Almost always yes; almost always uninformative) |
| Scaffold | Can you generalise to new chemistry? |
| Held-out target | Can you generalise across protein space? |
| **Time** | **Would this method have made the discovery?** |

Only the last one is the question a researcher deciding whether to trust the output actually has.
And a time split has a property none of the others has:
**the ground truth arrived independently of the benchmark designer.**
The field found these ligands by experiment, for its own reasons, after the cutoff.
Nobody — including us — constructed the positive set to be findable.

### 2.2 Why nobody has done it

Three real obstacles, which we inherit rather than solve:

1. **N is small.** Genuine post-cutoff deorphanizations meeting strict criteria are plausibly tens. Wide confidence intervals are unavoidable and we state them.
2. **Dating facts is hard.** Database release dates are not discovery dates. Prior work building pseudo-time-splits from ChEMBL versions explicitly flagged that first appearance in a later release does not establish that the data was reported later. This is why our protocol dates by earliest primary publication and carries a `date_confidence` field.
3. **Language models already know the answers.** This is new since the earlier benchmarking literature was written, and it is the obstacle most likely to be mishandled. A time split constrains *tools*, not pretraining. See §3.

### 2.3 Benchmarks that reward memorisation

Independently of deorphanization, ligand-based classification benchmarks have been shown to
reward memorisation over generalisation, and standard decoy sets to be separable on
physicochemical properties alone.
This is a decade-old finding that is still routinely ignored,
and it is why our decoy construction carries a mandatory property-match test
(a descriptor-only classifier must score near chance) rather than a convention.

---

## 3. The contamination problem, which is ours and is new

The earlier benchmarking literature predates models trained on the entire biomedical corpus.
Its tools could be constrained by a cutoff. A language model cannot be.

An agent asked to deorphanize a protein may simply recall the post-cutoff answer and then assemble a
plausible evidence trail backwards to it. This produces excellent benchmark numbers and a worthless method,
and it is invisible in the output — the evidence trail looks like reasoning because it is written as reasoning.

We treat it as unresolvable and therefore measurable:

- a **closed-book probe** per item (direct, multiple-choice, and identifier-stripped), giving a contamination score and a `clean` / `partial` / `contaminated` bin;
- **every headline metric reported per bin**, with the `clean` bin as the honest number;
- a **scored non-LLM pipeline path**, so the model's contribution is measured rather than assumed;
- a **schema requirement** of ≥2 independent non-LLM evidence channels, so naming the right ligand with no mechanism scores zero;
- an optional **`--blind-targets`** mode that strips identifiers from agent-visible context.

Residual, stated in [04-EVALUATION.md §9](04-EVALUATION.md):
the probe measures *elicitable* recall, which is a lower bound on what the model knows.
The `clean` bin is optimistic in an unknown direction.
**This is the project's largest unresolved threat to validity**, and we would rather name it than
let a good number stand on it.

---

## 4. What we take from the prior art

| Taken | From | How it appears here |
|---|---|---|
| Held-out-target splitting as the baseline practice to beat | G-LEAP and related work | We keep cluster-level protein splitting *and* add the time split on top |
| Property-matched decoys are mandatory, not optional | The memorisation-benchmarks literature | `tests/controls/test_leakage.py::test_decoys_not_separable_on_properties_alone`, which blocks the screener |
| Database versions are a poor proxy for time | Pseudo-time-split work on ChEMBL | Dating by earliest primary publication; `date_confidence` on every item |
| Co-folding affinity heads are a strong, cheap baseline | Boltz-2 | Proposal `P-002`, gated on first checking its training cutoff against ours |
| Structural homology finds relatives sequence search misses | Foldseek and structural-search practice | The `comparativist` channel; often the single most informative cheap signal for an orphan |
| Assignments are contestable and sometimes revised | HNF4α work; the GPR35 situation | The `disputed` pool; ground-truth uncertainty stated as an inherited limitation |
| Metabolite QTLs are near-causal evidence | Metabolite-GWAS literature | The `geneticist` channel, with mandatory gene-attribution confidence |

## 5. What we are not claiming

- Not that our method will outperform the published models. We have no result yet, and [04-EVALUATION.md §9](04-EVALUATION.md) explains why ours may well look worse on a harder, honester split — which would be a finding, not a failure.
- Not that a time split is strictly better than a target split. It answers a different question and has its own defect: **survivorship bias**. Ligands that were found are biased toward abundant, easily assayed metabolites in well-funded families, so performance on `DeorphBench` overestimates performance on the orphans that remain.
- Not that we have surveyed this literature exhaustively. One day, with search tools. Anything marked `verify` is unconfirmed, and a missed prior benchmark is entirely possible — **if a retrospective time-split deorphanization benchmark does exist, finding it is more valuable to us than our own build**, and we would rather adopt it than duplicate it.

## 6. Open questions worth a loop

Ranked by what we would attack first with more time:

1. **How large can a strict time-split benchmark get?** Multiple cutoffs (2015 / 2018 / 2021), orthologues, and non-GPCR families. `N` determines what is claimable, so this is question one.
2. **How much of a co-folding model's apparent skill survives a cutoff it cannot respect?** Testable by comparing its performance on pre- and post-its-own-training-cutoff items.
3. **Does the pocket charge-class constraint alone beat the full pipeline?** A deliberately humbling baseline: eliminating most of the metabolome by pocket electrostatics is nearly free. If it matches the loop, the loop is not earning its cost.
4. **Does partial credit change the picture?** Predicting "a short-chain fatty acid" when the answer is butyrate is substantially right, and exact-match recovery scores it zero.
5. **Is the popularity baseline beatable at all** on genuinely hard, low-homology orphans?

---

## Appendix: the initial research input

> **Resolved 2026-11-07.** The research was supplied directly as a saved page
> (`input/BaseSearch.html`, a seventeen-turn conversation) after the retrieval attempts below failed.
> It is reconciled against this project in **[11-PRIOR-ARCHITECTURE.md](11-PRIOR-ARCHITECTURE.md)**,
> which is the document to read: it covers what the prior design proposed,
> what we adopted, what we changed and why, and what it contributes that we had missed.
>
> Two things in it bear directly on this brief:
> **bindPredict** and **PSICHIC** are sequence-based methods that need no structural database,
> which makes them a direct answer to the early-cutoff structure gap recorded in
> [04-EVALUATION.md §9](04-EVALUATION.md) as unavoidable. Queued as `P-007` and `P-008`.
>
> The record of the failed retrieval is kept below, because the project worked without the input
> for most of its duration and that shaped what got built.

This brief was commissioned to **complement** a prior piece of research supplied as a link:
`https://share.google/aimode/AjHkx1oh4BsPfK7Xw`.

**We could not retrieve it.** Three attempts, three URL forms, on 2026-11-07.
The share redirects to `google.com/share.google`, which redirects to `consent.google.com`
with `gl=DE&hl=de` — an EU cookie-consent gate that no automated client can pass.
Google AI-mode shares are not publicly fetchable.

What the redirect chain *does* expose is the originating query, URL-decoded from the
`continue` parameter:

> **"proteins and their ligand metabolic problem. answer in english"**

So we know what was asked, but not what was answered.
A Google AI-mode response to that query is a generated overview assembled from web sources —
a tertiary explainer, not primary research, and not a citable artifact.
On the project's own standard it would not be admissible as evidence anyway:
it carries no stable locator, no date, and no provenance per claim
(see the `EvidenceItem` contract in [02-ARCHITECTURE.md §4.1](02-ARCHITECTURE.md)).

**How we complemented it regardless.**
An overview answering that query would reliably cover: what a protein and a ligand are,
the lock-and-key framing, why orphan receptors matter, the rough scale of the uncharacterised
proteome, and the general promise of computational screening.
That material is covered in [00-PROBLEM.md](00-PROBLEM.md), rebuilt from primary sources,
with two deliberate departures:

| An overview would say | We say instead |
|---|---|
| "20–35% of human proteins are uncharacterised"; "$2.6B per drug"; "90% wet-lab failure" | The same figures, each with a **confidence rating and a verification route**. Two are contested or definition-dependent, and **no metric in this project depends on any of them** |
| Computational screening can accelerate ligand discovery | It can, *and* the field cannot currently tell whether a given method works, because the evaluation does not answer the question a researcher has. That gap, not the acceleration, is what we build on |

**The risk this leaves.**
If the original research contained a specific finding, dataset or direction we have now
contradicted or duplicated, we would not know.
The honest mitigation is cheap: paste the text, and we will reconcile it against this brief.
Until then this appendix stands as the record of an input we were asked to build on and could not read.

## Sources

Consulted on 2026-11-07. Listed so each claim can be traced; none has been verified against the
primary source by a human.

- [Geometric-Evolutionary Deep Learning Decodes the Human GPCR-Metabolome Interactome and Enables Systematic De-Orphanization](https://www.biorxiv.org/content/10.64898/2026.02.21.707232v1.full) (bioRxiv, 2026) — protein-split deorphanization evaluation
- [DeorphaNN: Virtual screening of GPCR peptide agonists](https://www.biorxiv.org/content/10.1101/2025.03.19.644234v1.full) (bioRxiv, 2025)
- [Most Ligand-Based Classification Benchmarks Reward Memorization Rather than Generalization](https://arxiv.org/pdf/1706.06619) — the pseudo-time-split caveat and decoy separability
- [Revolutionizing GPCR–ligand predictions: DeepGPCR](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11167311/)
- [GPCR-IPL score](https://academic.oup.com/bib/article/25/2/bbae105/7631473)
- [Frontiers in Bioinformatics review (2025)](https://www.frontiersin.org/journals/bioinformatics/articles/10.3389/fbinf.2025.1712577/full) — calls for scaffold and time-split evaluation as future work
- [Introducing Boltz-2](https://boltz.bio/boltz2) and [MIT Jameel Clinic](https://jclinic.mit.edu/boltz-2-towards-accurate-and-efficient-binding-affinity-prediction/) — open co-folding with an affinity head
- [The GPCR deorphanization landscape](https://orbi.uliege.be/bitstream/2268/220327/1/The%20GPCR%20deorphanization%20landscape_Preprint.pdf)
- [Novel approaches leading towards peptide GPCR de-orphanisation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7042120/) — orphan counts; GPR15 and P2RY8 examples
- [GPR75: Advances, Challenges in Deorphanization](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12071931/) — GPR35 and kynurenic acid
- [Identification of an Endogenous Ligand Bound to a Native Orphan Nuclear Receptor](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0005609) — HNF4α; questions prior assignments
- [Pharos 2023: an integrated resource for the understudied human proteome](https://pubmed.ncbi.nlm.nih.gov/36624666/) — the `Tdark` definition

---

*Written material in this repository is licensed CC BY 4.0.*
