# DeorphBench curation protocol

Status: frozen for cutoff `C = 2018-01-01`. Changes require a MAJOR version bump and a human decision.

This protocol is the benchmark.
If it is not followed exactly and reproducibly, the numbers computed against `DeorphBench` mean nothing —
and they will mean nothing in the direction of looking *better*, which is why the protocol is frozen
rather than left to judgement.

Executed by the `curator` agent in loop `L0`. Normative reference: [docs/04-EVALUATION.md](../docs/04-EVALUATION.md) §1.

## Definitions

| Term | Meaning |
|---|---|
| **Cutoff `C`** | The date before which all evidence must be dated. The loop may see nothing after it |
| **Freeze date `F`** | The date at which ground truth was harvested. Assignments after `F` are not in this benchmark |
| **Orphan at `C`** | No agreed endogenous small-molecule ligand in GtoPdb, UniProt or ChEMBL as of `C` |
| **Assignment** | A reported endogenous ligand supported by ≥1 direct binding or activity measurement |

## Step 1 — Enumerate candidates

From snapshots dated ≤ `C`, list human proteins with no agreed endogenous small-molecule ligand.
Primary source: IUPHAR/BPS Guide to Pharmacology orphan lists.

**This step is only possible because GtoPdb publishes archived PostgreSQL dumps**
at `https://www.guidetopharmacology.org/DATA/public_iuphardb_v<YYYY.N>.zip`, verified to exist back to
`v2016.1`. Use the archived dump for the release current at `C`, never the live site —
querying today's GtoPdb and filtering by date is not the same as querying the 2018 database,
and the difference is exactly the orphan-status question we are asking.

**Licence note:** GtoPdb is ODbL + CC BY-SA 4.0 and ChEMBL is CC BY-SA 3.0, so the ground truth is
copyleft. Whether the curated item list inherits share-alike is unsettled.
`DeorphBench` therefore ships as identifiers plus this protocol, not as redistributed data.
See [../docs/06-DATA-SOURCES.md](../docs/06-DATA-SOURCES.md) §4.
Corroborating sources: UniProt (absence of a ligand-binding annotation), ChEMBL (absence of endogenous
ligand activity), Pharos development level.

Record the snapshot release of each source in the manifest.
A candidate that is an orphan in one source and assigned in another is **excluded** and the
disagreement recorded — we require agreement across sources for orphan status, because
a disputed starting point produces a disputed item.

## Step 2 — Find post-cutoff assignments

For each candidate, search for an endogenous ligand reported after `C` and recorded in a curated
resource at `F`.

## Step 3 — Date the assignment

**This is the step that determines whether the benchmark is valid.**

Date by **earliest primary publication reporting the binding**. Never by database release date.

A pairing first appearing in ChEMBL v30 may have been published years before v30 shipped.
Dating by release lets proteins leak across the cutoff and inflates every result.
Prior work on pseudo-time-splits has flagged exactly this, and it would not be caught by
inspecting the output.

Procedure:

1. Find the database record asserting the pairing.
2. Follow it to its **primary reference**.
3. Resolve that reference's date via Europe PMC or Crossref.
4. Check for an **earlier preprint** of the same work. Record both dates; use the earlier.
5. Check for an **earlier independent report**. Databases frequently cite a review rather than the original.
6. **Do not use an index date as a publication date.** A literature index records when *it* indexed the
   paper. A verified real example: a paper published 2017-12-31 carries a Europe PMC first-index date of
   2019-03-26. Date-filtering today's index is therefore provably not the same as querying the index as it
   stood at `C`. Resolve the publication date from Crossref and treat an index-only date as `low`.
7. Assign `date_confidence`:

| Value | Criteria |
|---|---|
| `high` | Primary paper found, date unambiguous, no earlier report located after searching |
| `medium` | Primary paper found, some ambiguity about priority |
| `low` | Only a secondary source, or conflicting dates |

Headline metrics use `medium` and above. `low` items are retained and reported separately —
we do not discard evidence, we label it.

## Step 4 — Apply inclusion criteria

All of I1–I5 must hold. Record the outcome for **every** candidate, including exclusions.

| # | Criterion |
|---|---|
| I1 | Orphan at `C`, agreed across sources (step 1) |
| I2 | Endogenous ligand reported after `C`, in a curated resource at `F` |
| I3 | Supported by ≥1 direct binding or activity measurement, not inference alone |
| I4 | Ligand is a small molecule or lipid present in a human metabolite reference set |
| I5 | Not retracted or substantively contested at `F` |

## Step 5 — Flags and strata

| Flag | Meaning | Why it matters |
|---|---|---|
| `prior_speculation` | A pre-cutoff source speculated about this ligand without showing binding | Recovering a pairing the field had already guessed is a much weaker result than recovering a surprise. Recovery must be reported split by this flag |
| `easy` | Binding-region identity >60% to a pre-cutoff assigned protein | The assignment is close to a trivial consequence of homology. Recovering it is a sanity check, not an achievement. Not deleted — reported separately |
| `disputed` | Contested at `F` | Scored, reported apart |
| `structure_available` | Any structure of the target with any ligand exists ≤ `C` | Leak L5. Results reported with and without these |

## Step 6 — Splits

Cluster by **sequence identity (30%)** and **Bemis–Murcko scaffold**, jointly.
Assign **clusters**, never individual proteins, to `dev` / `val` / `sealed`.

A protein in `dev` whose 80%-identical homologue sits in `sealed` is leakage L3,
and it is the easiest mistake in this area to make by accident.

Stratify by protein family (GPCR / SLC / NR / enzyme / other), ligand class
(amino-acid-like, lipid, nucleotide, organic acid, other), and `date_confidence`,
so per-stratum metrics are reportable and no single family can dominate the headline.

Encrypt `sealed`. Write the snapshot manifest.

## Step 7 — Independent audit

The `auditor` re-derives a **10% random sample** from primary sources, independently,
without seeing the curator's reasoning.
Disagreement rate is reported with the benchmark, not hidden.
A disagreement rate above 10% invalidates the pass and the protocol must be re-run.

## What the curator may not do

**Relaxing I1–I5 to increase N is forbidden.**

The benchmark will be small — plausibly tens of items, not thousands.
The obvious fix is to loosen the criteria, and it invalidates everything.

If N is too small, the permitted responses are:

- an **earlier cutoff** (2015), giving a nested benchmark with more post-cutoff time;
- **additional protein families**;
- **non-human orthologues** as a separate, separately-reported stratum.

Any relaxation of an inclusion criterion requires a human decision recorded in `curation-log.md`.
This is the single most tempting corner to cut in the whole project.

## Outputs

| File | Contents |
|---|---|
| `deorphbench-<C>-<F>.parquet` | The items |
| `curation-log.md` | A decision for every candidate considered, with the reason. The audit trail |
| `splits/` | Cluster assignments; `sealed` encrypted |
| `snapshot-manifest.yaml` | Every source release used, with SHA-256 and retrieval date |
| `UNSEAL-LOG.md` | Appended to by `scripts/unseal.py` |

The curator finishes by reporting: item count by stratum, the `easy`/`disputed` breakdown,
the `date_confidence` distribution, and **an honest assessment of how many items are genuinely solid**.

If the benchmark is too small to support the claims the project wants to make,
that is the most important thing the curator can report, and it goes in `JOURNAL.md`
before anyone computes a metric against it.
