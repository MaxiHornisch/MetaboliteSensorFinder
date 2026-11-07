# Glossary

For readers coming from either side of the biology/engineering line.
Terms whose everyday meaning differs from their meaning here are marked **⚠**.

## Biology and chemistry

**Apo / holo** — A structure solved without (apo) or with (holo) its ligand bound.
Structure predictors are trained largely on holo structures, which is why a predicted apo model of an
orphan can have confidently wrong pocket geometry.

**Cryptic pocket** — A binding site closed in the apo structure that only opens when the ligand arrives.
A single conformer cannot find one; this is what conformational ensembles are for.

**Deorphanization** — Assigning a ligand to a protein that had none.

**Endogenous ligand** — The molecule the body itself makes that a protein is shaped for,
as opposed to a synthetic drug. This project assigns endogenous ligands only.

**Enantiomer** — Non-superimposable mirror-image stereoisomers.
Classical docking distinguishes them poorly, which matters for a metabolome full of stereoisomers.
Recorded as a declared limitation.

**GPCR / NR / SLC** — G-protein-coupled receptor, nuclear receptor, solute carrier.
The three protein families with the most orphans and the most tractable pockets.

**Orphan** — A protein with no known endogenous ligand. **⚠** Unrelated to "orphan drug".

**Orthologue** — The same gene in a different species. Used here for conservation checks:
if the residues a proposed mechanism relies on are not conserved, the mechanism is weak.

**pLDDT / PAE** — Confidence outputs of a structure predictor.
pLDDT is per-residue; PAE is pairwise *relative* position error.
**For pockets, PAE matters more**: a pocket can be built entirely from high-pLDDT residues
whose relative positions are unconstrained.

**Pocket / binding site** — The cavity a ligand occupies. **⚠** Not a fixed feature; see *cryptic pocket*.

**mQTL** — Metabolite quantitative trait locus: genetic variation associating with a metabolite level.
Our only near-causal evidence channel. **⚠** Loci contain several genes, so attributing an mQTL to the
target rather than a neighbour is a real failure mode.

**Redocking / cross-docking** — Docking a ligand back into its own co-crystal structure (redocking),
or into a different structure of the same protein (cross-docking).
Our basic physics regression: redocking must succeed, cross-docking must be worse but beat random.

## Evaluation

**Abstention** — Returning "no confident ligand". **⚠** A first-class, scored output here, not an error.
A loop version that never abstains cannot be promoted.

**BEDROC(α=20)** — An early-weighted enrichment metric, concentrating roughly 80% of its weight in the
top 8% of the ranking. Used because only the top of a list will ever be tested.

**Calibration** — Whether a stated probability means what it says: of the hypotheses given p=0.7,
about 70% should be correct. Measured with Brier score, ECE and a reliability diagram.
**The project's most important metric**, because the output is used to allocate experiments.

**Contamination** — **⚠** Here: the language model already knowing a post-cutoff answer from pretraining.
A time split constrains tools, not training data. Cannot be eliminated; measured with a closed-book probe
and reported as `clean` / `partial` / `contaminated` bins.

**Decoys** — Molecules assumed not to bind, used as a negative set.
**⚠** Must be *property-matched*: naively chosen decoys are separable on physicochemical properties alone,
and enrichment computed against them measures nothing while looking excellent.

**Leakage** — Information from outside the allowed evidence window reaching the method.
Catalogued L1–L8 in [04-EVALUATION.md §2](04-EVALUATION.md).
**⚠** Leakage almost always makes results look *better*, which is why it is never caught by sanity-checking output.

**Negative control** — A target with no correct answer: scrambled sequence, sham pocket, mirror-image protein.
**⚠ A control that *passes* — produces a confident answer — is a bug, not a result.**

**Popularity baseline** — Ranking metabolites by how often they are anyone's ligand.
Shockingly strong, because most proteins bind common metabolites.
A required column in every results table; a method that does not beat it has learned nothing.

**Pre-registration** — Writing down the metric and the expected effect *before* running the experiment.
Separates confirmatory from exploratory results. Without it, an agent evaluating its own change
will find some metric that moved and report that one.

**Risk–coverage curve** — Accuracy among the top fraction the method is most confident about.
The curve a lab actually plans against.

**Sealed split** — The encrypted test set. Only a human can unseal it, once per loop version, and every
unseal is logged. The only reliable defence against an agent overfitting its own benchmark.

**Selective accuracy @20% coverage** — The pre-registered primary metric:
how often the method is right about the 20% of targets it is most confident about.

**Time split** — Holding out *time* rather than proteins: train on pre-cutoff knowledge,
test on post-cutoff discoveries. Answers "would this have made the discovery?".
**⚠** Its weakness is survivorship bias — ligands that *were* found are not a random sample of ligands that exist.

## This project

**`DeorphBench`** — The retrospective time-split benchmark. The primary deliverable.

**Channel** — One independent evidence stream (literature, structure, chemistry, screening, genetics, homology).
Channels do not see each other. **⚠** Two channels deriving from the same structural template are
*one* channel; the `restatement` attack exists to detect this.

**Cutoff `C`** — The date before which all evidence must be dated.

**Dossier** — The researcher-facing artifact for one target: ranked hypotheses, calibrated probability,
full evidence graph, falsification record, and the mandatory *what would change our mind* section.

**Falsifier** — The adversarial agent whose only job is to destroy the loop's own hypotheses.
Read-only on them, and given the strongest model deliberately: if the adversary is weaker than the
proposer, everything survives.

**Guard** — A `PreToolUse` hook that refuses a tool call. **⚠** Structural, not advisory.
Every leakage control is a guard rather than a prompt instruction, because a prompt is a suggestion.

**`L0`–`L4`** — The loop hierarchy: benchmark, target, evaluation, improvement, watch.
See [03-LOOPS.md](03-LOOPS.md).

**Loopspec** — A loop version as declarative, versioned, hashed YAML.
**⚠** Anything that affects a result must live here, not in a prompt.

**Run record** — The immutable directory for one loop execution, keyed by a content hash of its manifest.
**⚠** A result not reproducible from its run record does not exist.

**`source_date` vs `retrieved`** — **⚠ The distinction that matters most.**
`retrieved` is when we fetched a record; `source_date` is the date of the *fact*
(earliest primary publication). The time split filters on `source_date`.
Conflating them is leak L1 and silently invalidates everything downstream.

---

*Written material in this repository is licensed CC BY 4.0.*
