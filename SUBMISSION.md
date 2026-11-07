# MetaboliteSensorFinder

**A Claude Code agent that predicts which human metabolites a protein domain binds.**

## The team

| Name | Role |
| --- | --- |
| Maxi | Scientist — biological framing, domain/metabolite datasets, interpretation of hits |
| Silvia | Engineer |
| Richard | Engineer |
| Umair | Engineer |

## The problem

Engineering a biosensor for a given metabolite starts with a sensing element — a protein
domain that actually binds the molecule of interest. Finding candidate domains is a
needle-in-a-haystack search: thousands of candidate domains crossed with thousands of
endogenous human metabolites is millions of pairs, and the structural methods that give a
trustworthy answer are far too expensive to run across that whole space.

## What the agent does

`domain-metabolite-screener` is a Claude Code subagent that orchestrates a **three-stage
funnel**, ordered so that each stage is cheaper than the one after it. Every stage exists
to keep expensive compute off low-value candidates.

**Stage 1 — bindPredict** ([Rostlab/bindPredict](https://github.com/Rostlab/bindPredict))
Scores every input domain for ligand-binding likelihood from sequence alone, producing
per-residue scores. Only high-confidence domains advance.

**Stage 2 — PSICHIC** ([huankoh/PSICHIC](https://github.com/huankoh/PSICHIC))
Scores each surviving domain against the full metabolite ligand set, giving a score per
domain–ligand pair. Only high-confidence pairs advance.

**Stage 3 — DiffDock**
Runs docking and final structure prediction on the surviving pairs only. For each pair the
agent fetches the full-length structure from [AlphaFold DB](https://alphafold.ebi.ac.uk),
locates the input domain within the full-length sequence, and trims the structure to the
domain residues before docking.

### Design principles

The agent's definition encodes a few rules that matter more than the pipeline itself:

- **Record everything, filter only what advances.** Scores for *all* domains and *all*
  pairs evaluated are written to disk, not just the ones that pass. Filtering controls
  progression through the funnel — never what gets reported. Negative results are results.
- **State the thresholds.** Every report names the cutoffs used at each stage and the
  reasoning behind them, so a hit list can be re-derived or re-cut by someone else.
- **Be honest about uncertainty.** These are predictions. The agent is required to say so,
  and to flag hits that are borderline, that rest on a poorly-modelled AlphaFold structure
  (low pLDDT), or that depend on an ambiguous domain boundary.
- **Built to scale, and to fail safely.** The target is several thousand domains, so work
  runs in batches with a checkpoint to disk after each one, and resumes from the last
  checkpoint rather than restarting. The agent runs a small pilot, reports measured
  per-domain cost, and asks for sign-off before scaling up.
- **Budget discipline as a hard constraint.** Working against a fixed ~$100 compute budget,
  the agent prefers writing and running scripts over pulling data into its context, never
  reads sequence or score files wholesale, keeps output terse, and tracks spend as it goes.

## Outputs

1. Docked structures (PDB/SDF poses) for good hits.
2. A list of domains and their predicted ligands that pass DiffDock's confidence criteria.
3. A full table of bindPredict and PSICHIC scores for **every** domain and pair scored.

## What's in this repository

| File | Contents |
| --- | --- |
| [.claude/agents/domain-metabolite-screener.md](.claude/agents/domain-metabolite-screener.md) | The agent definition — the submission's core artefact |
| [Agent_v1](Agent_v1) | The earlier single-prompt version, kept to show how the design evolved |
| [Test_sequences.csv](Test_sequences.csv) | 413 InterPro-annotated domains across 100 human proteins, with sequences and domain boundaries — the pilot input set |
| [metabolite_binding_sequences_human.csv](metabolite_binding_sequences_human.csv) | 8,685 human domains with experimentally annotated binding sites and their ChEBI ligands, spanning 3,864 genes — ground truth for evaluating the screen |
| [Test_set_metabolite_SIMLES.xlsx](Test_set_metabolite_SIMLES.xlsx) | Metabolite names with canonical SMILES and ChEMBL IDs — the ligand side of the screen |

## Why we built it this way

The interesting part of this project is not any single model — bindPredict, PSICHIC and
DiffDock are all existing published tools. It's that running them as a coherent screen
normally means a scientist hand-stitching three environments, three input formats and a
structure-trimming step, then babysitting a job that dies at hour six. Handing that
orchestration to an agent turns a multi-day manual pipeline into one instruction, while the
rules above keep the output something a scientist can actually audit: every score kept,
every threshold stated, every weak hit flagged as weak.
