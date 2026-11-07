# MetaboliteSensorFinder

A Claude Code agent that screens protein domain sequences against endogenous human
metabolites via a staged bindPredict → PSICHIC → DiffDock funnel, to find candidate
sensing elements for biosensor engineering.

Developed at Claude Impact Lab Berlin 2026 (co-hosted by Foresight Institute).
See **[SUBMISSION.md](SUBMISSION.md)** for the full submission description and
design rationale.

## The problem

Engineering a biosensor for a given metabolite starts with a sensing element: a protein
domain that actually binds the molecule of interest. For most metabolites there is no
textbook sensor, and finding a binding domain is a needle-in-a-haystack search —
thousands of candidate domains crossed with endogenous human metabolites is millions of
pairs, and the structural methods that give a trustworthy answer are far too expensive
to run across that whole space.

The problem is open, significant, and checkable by computation. This repository commits
8,685 annotated human domain–ligand pairs, so any screen can be scored against real
evidence rather than taken on faith.

## How the screen works

`domain-metabolite-screener` is a Claude Code subagent that orchestrates a
**three-stage funnel**, ordered so that each stage is cheaper than the one after it.
Every stage exists to keep expensive compute off low-value candidates.

1. **bindPredict** ([Rostlab/bindPredict](https://github.com/Rostlab/bindPredict)) —
   scores every input domain for ligand-binding likelihood from sequence alone, with
   per-residue scores. Only high-confidence domains advance.
2. **PSICHIC** ([huankoh/PSICHIC](https://github.com/huankoh/PSICHIC)) — scores each
   surviving domain against the metabolite ligand set. Only high-confidence pairs
   advance.
3. **DiffDock** — docking and final structure prediction on surviving pairs only. For
   each pair the agent fetches the full-length model from
   [AlphaFold DB](https://alphafold.ebi.ac.uk), locates the domain within the
   full-length sequence, and trims the structure to the domain residues before docking.

The rules around the pipeline matter as much as the pipeline itself:

- **Record everything, filter only what advances.** Scores for every domain and pair
  evaluated are written to disk, not just the ones that pass. Filtering controls
  progression through the funnel — never what gets reported. Negative results are
  results.
- **State the thresholds.** Every report names the cutoffs used at each stage and the
  reasoning behind them, so a hit list can be re-derived or re-cut by someone else.
- **Flag the known ways this misleads.** Borderline hits, hits resting on a
  low-pLDDT AlphaFold model, and ambiguous domain boundaries are called out
  explicitly — the three ways this pipeline most often misleads a reader.
- **Checkpoint and resume.** Work runs in batches with state kept to disk, so a
  failure resumes from the last checkpoint instead of restarting the screen.
- **Pilot before scaling.** A small run with measured per-domain cost comes before any
  large run, with sign-off in between.

Everything above is encoded in the agent definition; see
[Status](#status-two-stages-executed-no-result-yet) for what has actually been executed
so far.

## Repository contents

| Path | Contents |
| --- | --- |
| [.claude/agents/domain-metabolite-screener.md](.claude/agents/domain-metabolite-screener.md) | The agent definition — the core artifact |
| [Agent_v1](Agent_v1) | The earlier single-prompt version, kept to show how the design evolved |
| [Test_sequences.csv](Test_sequences.csv) | 413 InterPro-annotated domains across 100 human proteins, with sequences and domain boundaries — the pilot input set |
| [metabolite_binding_sequences_human.csv](metabolite_binding_sequences_human.csv) | 8,685 annotated human domain–ligand pairs across 3,864 genes — the yardstick for evaluating a screen |
| [Test_set_metabolite_SIMLES.xlsx](Test_set_metabolite_SIMLES.xlsx) | The ligand side of the pilot: metabolite names with canonical SMILES and ChEMBL IDs |
| [executive-deck/](executive-deck/index.html) | An 11-slide executive briefing of the problem, the funnel, the data and the decisions needed |
| [binding-explainer/](binding-explainer/index.html) | An interactive 3D explainer of how a protein holds a molecule, built on a real structure (RCSB 2DN2) |
| [SUBMISSION.md](SUBMISSION.md) | Full submission description, design rationale and team credits |

## About the data

Three committed tables carry the project. Read their limits before relying on them:

- **Test_sequences.csv** — 413 data rows, 100 distinct proteins, 284 distinct InterPro
  accessions, each with `domain_start`, `domain_end` and `domain_sequence`. Note that
  156 of the 413 rows are family-level entries rather than domains, and some of those
  spans cover the whole protein, so the "domain" set is coarser than the word suggests.
- **metabolite_binding_sequences_human.csv** — exactly 8,685 rows spanning 3,864
  distinct genes and 408 distinct ChEBI ligands, each row carrying binding-site
  residues and an evidence code. The evidence codes mix direct annotation with
  sequence-inference codes (for example `ECO:0000255`), so the table is a strong
  yardstick, not uniformly experimental ground truth.
- **Test_set_metabolite_SIMLES.xlsx** — two metabolites (ATP and β-D-glucose) with
  canonical SMILES and ChEMBL IDs. It is a pilot ligand set, not yet the
  metabolite-scale library the full screen calls for.

Provenance: the tables are derived from [UniProt](https://www.uniprot.org)
(CC BY 4.0) and [InterPro](https://www.ebi.ac.uk/interpro/) (CC0), and the ligand
identifiers reference ChEBI and ChEMBL (ChEMBL IDs, CC BY-SA 3.0). These sources are
named here so the committed derivatives carry the attribution their licenses require.

## Status: two stages executed, no result yet

**Executed.** On the `feature/sequence-channels-console` branch, the first two funnel
stages run as working, sequence-based channels — the same two stages the agent
definition specifies, in the same order:

- **bindPredict** — per-residue pocket reliability indices and class calls for a
  candidate protein sequence, read from local output files. The pocket channel
  currently covers five candidates with precomputed embeddings.
- **PSICHIC** — ligand affinity plus agonist/antagonist/non-binder classification for a
  sequence against ligand SMILES, scored on request (about nine seconds per call on
  CPU), with no limit on input sequences.

Each tool runs in its own pinned environment — their requirements are incompatible, so
they meet only at a subprocess boundary. `scripts/doctor.py` checks that everything a
tier needs is ready before anything downstream is trusted, and the Deorphan console
(`tools/msf-console/`) puts both channels behind a local web UI and API. Every response
carries its contamination warrant, so a score cannot be read without its provenance
block.

**The testing approach.** The channels are exercised with sequences and ligands whose
behaviour is already known: screen a candidate with known binding through the console
and compare the returned affinity and class call against what is already known, before
trusting either channel on an orphan. The benchmark design applies the same discipline
at scale — near-trivial homology pairs are recovered as a sanity check and reported
separately, never counted as an achievement.

**Not yet run.** The third stage — docking — has not been executed, the run ledger
(`runs/INDEX.md` on that branch) has no rows, and no score table has been committed
against the 8,685-pair yardstick with a baseline. This `main` branch still carries no
score tables, docked poses or run logs of its own — the outputs described in
SUBMISSION.md are *intended* outputs. Nothing has been experimentally validated;
everything here is a prioritised hypothesis, not evidence of a binding interaction.

What a first complete result needs, in order:

1. a metabolite library at the intended scale — the committed pilot has two ligands;
2. stage 3 (docking) pinned and running alongside the two channels that already work;
3. a committed pilot run: stage-1 scores for all 413 domains, stage-2 scores for the
   survivors, at least one docked pose, and the measured cost per domain;
4. a scored evaluation against the committed 8,685-pair table — recall at a stated
   cutoff, next to a baseline — so a reader can see what the funnel adds over chance;
5. a literature step: stage thresholds derived from the tool papers and recorded, which
   the current definition does not yet include.

One committed score table would change the evidence of this repository more than any
further design prose.

## Reproducibility

- **Presentation materials** — `executive-deck/index.html` and
  `binding-explainer/index.html` are self-contained single files: open either directly
  in a browser. Structure data is embedded; 3Dmol.js loads from its CDN, so the first
  load needs an internet connection. No build step.
- **The agent** — runs inside Claude Code: the definition in `.claude/agents/` is
  invoked in a session with the three data files as inputs.
- **The two executed channels** — on `feature/sequence-channels-console`, run
  `python3 tools/msf-console/server.py 8420` from the repository root and open
  `http://127.0.0.1:8420`. The console needs only the Python standard library; the
  channels need their own tool environments, and `scripts/doctor.py` reports which are
  ready.
- **The full screen** — not yet reproducible end to end: stage 3 and the benchmark have
  not been executed, and no run has been committed to reproduce. See
  [Status](#status-two-stages-executed-no-result-yet).

## Branches

- **`main`** — the submission branch: agent definition, input tables, presentation
  materials and license files.
- **`feature/sequence-channels-console`** — the executed-channels branch: the first two
  funnel stages, bindPredict and PSICHIC, running as sequence-based channels behind a
  local Deorphan console, with doctor checks for tool readiness.
- **`scaffold/initial-documentation`** — an extended parallel line of work: a Python
  package with a CLI and tests, an experiment journal, task and decision records,
  research of the data sources with per-source licensing, provenance and
  redistribution verdicts, and the license files. Its pipeline workers are simulated.

The two remote branches share a common scaffold root; neither has been merged into
`main`.

## License

Code in this repository is licensed under the **Apache License, Version 2.0** — see
[LICENSE](LICENSE). Written material (problem descriptions, documentation, results
summaries) is licensed under **Creative Commons Attribution 4.0 International
(CC BY 4.0)** — see [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0). [NOTICE](NOTICE) records
the attribution, the terms covering the committed third-party-derived tables, and the
scientific disclaimer.

## If it works

The distance to impact is mostly execution, not concept. A working funnel would change
who can start a biosensor project: picking a sensing element for a metabolite with no
textbook sensor currently means either a literature search that returns whatever was
already studied, or a structural campaign only a well-funded structural biology group
can afford. A funnel that spends sequence-level compute on thousands of domains and
structural compute on dozens would let a cell-biology or synthetic-biology lab produce a
ranked, auditable shortlist for an arbitrary endogenous metabolite in days — useful to
synthetic biologists building reporters, metabolic engineers tuning pathways, and
biosensor groups beyond the usual handful of reused binding proteins.

## Team

| Name | Role |
| --- | --- |
| Maxi | Scientist — biological framing, domain/metabolite datasets, interpretation of hits |
| Silvia | Engineer |
| Richard | Engineer |
| Umair | Engineer |
