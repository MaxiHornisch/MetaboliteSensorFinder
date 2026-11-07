# Architecture

Status: design, v1.
Read [04-EVALUATION.md](04-EVALUATION.md) first — the evaluation is the specification, and this document is how we satisfy it.

## 1. The shape of the problem, and what that forces

Three properties of endogenous ligand assignment determine the architecture.

**It is an evidence-fusion problem, not a scoring problem.**
No single signal is strong enough.
Docking is weakly informative; co-expression is circumstantial; genetics is sparse but near-causal;
structural homology is strong when available and absent otherwise.
The architecture is therefore a set of **independent evidence channels** that are computed separately,
can disagree, and are fused with weights fitted on held-out data — not a pipeline with one scoring step.

Independence is the point.
Channels that share a failure mode give false confidence when they agree.
We track channel correlation explicitly and discount agreement between correlated channels (§4.3).

**The failure mode is confident fabrication, not silence.**
Every component in the classical stack returns a best answer regardless of whether one exists.
So the architecture adds a component whose job is to destroy answers —
the falsifier — and a calibration layer whose output may be "no confident ligand".

**The language model is both the integrator and a contamination risk.**
It is the only component that can read a paper, notice that the pocket is lined with basic residues,
and connect that to a negatively charged metabolite in a pathway the protein is co-expressed with.
It is also capable of recalling the answer and rationalising backwards.
So the architecture keeps a **non-LLM pipeline path** that can be scored independently (see [04-EVALUATION.md §3.4](04-EVALUATION.md)),
and routes all factual claims through tools that return citable, dated artifacts.

## 2. System view

```
┌──────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR  (main Claude Code session — plans, never computes)    │
│  state: TASKS.md · JOURNAL.md · PROMPT.md · runs/<run-id>/           │
└───────────────┬──────────────────────────────────────────────────────┘
                │ dispatches atomic steps to subagents
   ┌────────────┴───────────────────────────────────────────┐
   │                                                        │
┌──▼───────────────── EVIDENCE CHANNELS (parallel) ─────────▼────────┐
│ librarian    structuralist   chemist    geneticist   comparativist │
│ literature   pocket+pose     library    mQTL/GWAS    homology      │
│              ensembles       +decoys    co-expression Foldseek/HMM │
└──┬─────────────┬──────────────┬───────────┬──────────────┬─────────┘
   │             │              │           │              │
   └─────────────┴──────┬───────┴───────────┴──────────────┘
                        │  EvidenceBundle  (typed, provenance-carrying)
                 ┌──────▼───────┐
                 │  HYPOTHESIZER│  ranked candidate ligands + rationale
                 └──────┬───────┘
                        │  Hypothesis[]
                 ┌──────▼───────┐
                 │  FALSIFIER   │◀── adversarial; budget to kill each one
                 └──────┬───────┘    survivors only
                        │
                 ┌──────▼───────┐
                 │  FUSION +    │  calibrated p(correct) · may abstain
                 │  CALIBRATOR  │
                 └──────┬───────┘
                        │  TargetDossier  (the artifact)
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
     statistician    auditor         scribe
     metrics/CIs   provenance      dossier + web app
                   re-check
```

Two rules make this tractable over long runs:

- **The orchestrator never computes.**
  It plans, dispatches, and reviews. All real work happens in subagents with their own context windows.
  This is what lets a run continue for hours without the main context filling with tool output.
- **State lives in files, not in context.**
  `TASKS.md`, `JOURNAL.md`, `PROMPT.md` and the run directory are the memory.
  Any session can be killed and resumed with `/goal continue the goal described in PROMPT.md`.

## 3. The agents

Each is a subagent definition in [.claude/agents/](../.claude/agents/) with a restricted tool set.
Tool restriction is a safety and correctness mechanism, not bureaucracy:
the `falsifier` must not be able to write results, and the `librarian` must not be able to reach a live
un-dated endpoint during a benchmark run.

| Agent | Responsibility | Writes | Key restriction |
|---|---|---|---|
| `curator` | Builds and maintains `DeorphBench` from primary sources; dates assignments by earliest primary publication | `benchmarks/` | May read post-cutoff data. **Never runs in the same session as a scoring loop** |
| `librarian` | Date-filtered literature retrieval; extracts claims with citations | `runs/*/evidence/literature/` | Date filter enforced at the MCP boundary, not by prompt |
| `structuralist` | Structure acquisition, quality gating (pLDDT/PAE), pocket detection, conformational ensembles | `runs/*/evidence/structure/` | Must emit a pocket-quality verdict before any docking is allowed |
| `chemist` | Candidate library, property-matched decoys, scaffold analysis, protonation/tautomer prep | `runs/*/evidence/chemistry/` | — |
| `screener` | Executes docking / co-folding; returns poses and calibrated z-scores, never raw scores | `runs/*/evidence/screening/` | **Forbidden from emitting a raw docking score as a ranking signal** |
| `geneticist` | Metabolite-QTL, GWAS, co-expression, pathway context | `runs/*/evidence/genetics/` | — |
| `comparativist` | Structural and sequence homology; ligand transfer from neighbours; conservation of pocket residues | `runs/*/evidence/homology/` | Must report identity to nearest assigned protein — feeds the `easy` stratum flag |
| `hypothesizer` | Integrates the bundle into ranked candidate hypotheses with explicit reasoning | `runs/*/hypotheses/` | Each hypothesis must cite ≥2 independent non-LLM channels or be rejected by the schema validator |
| `falsifier` | Adversarial. Tries to kill each hypothesis. See §5 | `runs/*/falsification/` | **Read-only on hypotheses.** Cannot modify or create them |
| `fusion` | Fits/applies channel weights, produces calibrated probability, decides abstention | `runs/*/dossier/` | Weights fitted only on `val`; refuses to run if it detects `sealed` in scope |
| `statistician` | Metrics, bootstrap CIs, paired comparisons, baselines, ablation table | `runs/*/metrics/` | Refuses to emit a results table without the popularity baseline |
| `auditor` | Re-derives every claim in the dossier from artifacts; flags unsupported statements | `runs/*/audit/` | Read-only everywhere |
| `scribe` | Writes the dossier, JOURNAL entries, and web-app payloads | `JOURNAL.md`, `web/data/` | May not introduce facts not present in the audited dossier |

### Why `falsifier` and `auditor` are separate

They catch different errors.
The `falsifier` attacks the *science*: is this hypothesis actually wrong?
The `auditor` attacks the *bookkeeping*: does the artifact actually say what the dossier claims it says?
In practice the auditor catches more problems, because the most common failure in an agentic run
is not a bad hypothesis but a claim that drifted from its evidence three steps back.

## 4. Data contracts

Typed, versioned, validated at every boundary. Schemas in [src/msf/schemas/](../src/msf/).
Unvalidated data crossing an agent boundary is the mechanism by which agentic pipelines silently corrupt.

### 4.1 `EvidenceItem`

Every piece of evidence, from every channel, has the same envelope:

```yaml
evidence_id: ev_<content-hash>
channel: literature | structure | chemistry | screening | genetics | homology
target: UniProt accession
claim: machine-readable assertion (typed per channel)
direction: supports | refutes | neutral
strength: 0.0 - 1.0          # channel-local, calibrated separately per channel
provenance:
  source: database or tool name
  snapshot: snapshot manifest id      # ties to the pinned release
  retrieved: ISO-8601
  source_date: ISO-8601               # the date of the FACT, for the time split
  locator: DOI / PDB ID / accession / file path + line
  tool_version: semver
  command: exact invocation, reproducible
reproducible: bool                     # false forces manual review
```

`source_date` is distinct from `retrieved` and is what the time filter uses.
Conflating them is leak L1 and is the single easiest way to invalidate the whole benchmark.

### 4.2 `Hypothesis`

```yaml
hypothesis_id: hyp_<hash>
target: UniProt accession
ligand: { chebi: ..., inchikey: ..., name: ... }
mechanism: free text, required, must reference pocket residues
supporting_evidence: [evidence_id, ...]   # ≥2 distinct non-LLM channels, enforced
refuting_evidence: [evidence_id, ...]
falsification:
  attempts: [{attack: str, outcome: survived|weakened|killed, evidence: [...]}]
  survived: bool
prior_speculation: bool                   # was this pairing already speculated pre-cutoff?
```

### 4.3 `TargetDossier`

The researcher-facing artifact and the unit the web app renders. Contains the ranked hypotheses,
the full evidence graph, the calibrated probability, the abstention decision, per-channel contributions,
and — mandatory — a **"what would change our mind"** section naming the single cheapest experiment
that would falsify the top hypothesis.

Channel contributions are reported after correlation adjustment:
if `homology` and `screening` both derive from the same template structure, their agreement is discounted.
The correlation matrix is estimated on `val` and stored with the loop version.

## 5. The falsifier

The most important component, and the one that distinguishes this from a ranking pipeline.

For each surviving hypothesis, the falsifier is given a budget and a standing instruction to destroy it.
It runs a fixed attack battery, and may add target-specific attacks:

| Attack | Kills the hypothesis if |
|---|---|
| Decoy substitution | Property-matched decoys score as well as the proposed ligand |
| Pocket ablation | The score survives mutating the pocket residues the mechanism depends on |
| Abundance check | The ligand is not present in the tissue where the protein is expressed, at a plausible concentration |
| Pathway coherence | No metabolic route puts ligand and protein in the same compartment |
| Promiscuity check | The ligand scores equally well against many unrelated proteins — it is a sticky molecule, not a match |
| Template dependence | The result disappears when the single structural template is removed |
| Literature contradiction | A dated, pre-cutoff source already reports this pairing as negative |
| Conservation | The pocket residues the mechanism relies on are not conserved across orthologues |
| Restatement | The "evidence" is the same fact arriving through three channels |

Outcomes are recorded whether or not the hypothesis survives.
**The record of failed attacks is part of the dossier** — a researcher needs to know what was tried,
and a hypothesis that survived nine serious attacks is a different object from one nobody challenged.

The falsifier is deliberately denied write access to hypotheses.
An agent that can both attack and edit will, over a long run, quietly soften the thing it is attacking.

## 6. Run records and reproducibility

Every loop execution produces an immutable directory:

```
runs/<run-id>/
├── manifest.yaml        # loop version, prereg hash, snapshot manifest, seeds,
│                        # model ids, tool versions, git commit, env lock hash
├── inputs/              # exact resolved inputs
├── evidence/            # per channel, typed EvidenceItems
├── hypotheses/
├── falsification/
├── dossier/             # the artifact
├── metrics/             # scores, CIs, ablations, control results
├── audit/               # auditor findings
└── trace.jsonl          # every agent turn, tool call and cost
```

`run-id` is a content hash of `manifest.yaml`.
Two runs with the same manifest must produce the same result;
`tests/controls/test_determinism.py` enforces it where the underlying tools allow determinism,
and the manifest records which tools do not.

`runs/` is git-ignored except `runs/INDEX.md`, which is a committed one-line-per-run ledger.
Artifacts go to DVC or object storage; the index carries the hashes.

## 7. Where the LLM is and is not in the loop

An explicit map, because "we used AI" is not an architecture.

| Step | LLM role | Non-LLM fallback exists? |
|---|---|---|
| Benchmark curation | Extracts dates and claims from papers; **every extraction is schema-validated and a 10% sample is human-checked** | No — but errors are visible in the sample |
| Literature evidence | Reads and summarises with citations | No |
| Pocket detection | None — fpocket/P2Rank | n/a |
| Docking / co-folding | None | n/a |
| Candidate generation | Proposes classes of metabolite to prioritise | Yes — full-library screen |
| Hypothesis formation | Primary | Yes — pipeline-only ranker (§1) |
| Falsification | Designs attacks; attacks themselves are computational | Partly |
| Fusion weights | None — fitted statistically | n/a |
| Calibration | None — isotonic/Platt on `val` | n/a |
| Report writing | Primary, then audited | No |

The scored pipeline path (`−LLM` ablation) exists precisely so the contribution of the language model
is a measured number rather than an assumption.

## 8. Technology choices and their reasons

| Choice | Reason | Alternative rejected |
|---|---|---|
| Claude Code + Agent SDK subagents | Context isolation per step; skills and hooks give deterministic enforcement points | Single long-context agent — fills context, loses state |
| Enforcement in hooks and MCP wrappers, not prompts | A prompt instruction is a suggestion; a tool that refuses is a guarantee. All leakage controls are tool-level | Prompt-only guardrails |
| Typed schemas at every boundary | Catches drift between agents, which is the dominant long-run failure | Free-text handoffs |
| Files as state | Survives session death; reviewable in git; is the evidence | Agent memory |
| DuckDB + Parquet run records | Zero-infrastructure analytics over runs; the web app queries it directly | A database service |
| Co-folding affinity head alongside classical docking | Two methods with different failure modes; disagreement is informative | Docking alone |
| Sealed, encrypted test split | The only reliable defence against an agent overfitting its own benchmark | Discipline |

## 9. Open architectural questions

Recorded rather than resolved; see [docs/adr/](adr/).

- **Fusion model.** Logistic regression on channel strengths is interpretable and fits in small data; a learned model is better in principle and we do not have the N. Starting with regularised logistic regression plus isotonic calibration, and revisiting if the benchmark grows.
- **How to credit a partially-correct answer.** Predicting "a short-chain fatty acid" when the answer is butyrate is substantially right. Current plan is a chemical-similarity-graded recovery metric reported alongside exact recovery, but the similarity threshold is arbitrary and we have not justified one.
- **Whether `--blind-targets` should be the default.** It is the strongest contamination control and badly degrades retrieval. Currently a reported configuration, not the headline.
- **Multi-ligand targets.** Many proteins bind several endogenous ligands. The benchmark currently treats one as correct, which under-credits a correct alternative. Needs a set-valued ground truth.

---

*Written material in this repository is licensed CC BY 4.0.*
