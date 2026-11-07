# Submission

Draft answers for the [project submission issue](https://github.com/xemantic/claude-impact-lab-2026/issues/new?template=project-submission.yml)
at Claude Impact Lab Berlin 2026.

Kept in the repository so the claims stay next to the evidence and can be diffed as the project changes.
**Fields marked `TODO` must be filled with real numbers before submitting — do not submit a claim this
repository does not support.** The assessment explicitly checks every claim in the issue against the repo.

---

**Team name**
`TODO`

**Team members**
`TODO` — one per line, GitHub handle and role, e.g. `Jane Doe (@janedoe), scientist, problem owner`

**Field**
Protein / molecular design

**Repository**
`TODO`

**License**
Apache 2.0 for code, CC BY 4.0 for text

---

## Open problem

Thousands of human proteins have no known endogenous ligand.
Computational methods to predict those ligands exist and return confident answers,
but the field cannot tell whether to trust them, because the evaluation does not answer the researcher's
actual question: *restricted to what was knowable in year Y, would this method have found the ligand
the field published in year Y+k?*

Existing practice holds out **proteins** (the strongest current split, and explicitly framed as the
deorphanization scenario). We found **no benchmark that holds out time**.
A 2025 review in the area calls for scaffold and time-split evaluation as future work.

Why it is still open:

- Docking scores rank poses adequately and rank different molecules poorly, yet are routinely used for cross-ligand ranking.
- Standard decoy sets are separable on physicochemical properties alone, so good enrichment numbers can mean nothing.
- Homology leakage is pervasive, and deorphanization is by definition the low-homology regime.
- Small N and the difficulty of dating a published fact make a time split genuinely hard to build.

**How results can be checked computationally:** retrospective recovery of post-cutoff assignments
(recall@k, MRR, BEDROC); physics regressions (redocking within 2 Å); negative controls that must *fail*
to produce confident answers; calibration (Brier, ECE, risk–coverage); and a contamination probe that
reports every metric net of what the language model already knows.

Full statement: [docs/00-PROBLEM.md](docs/00-PROBLEM.md). Prior art: [docs/01-RESEARCH-BRIEF.md](docs/01-RESEARCH-BRIEF.md).

## The research loop

Five nested loops; contracts in [docs/03-LOOPS.md](docs/03-LOOPS.md), agents in [.claude/agents/](.claude/agents/).

**L0 — benchmark loop** ([`curator`](.claude/agents/curator.md), [protocol](benchmarks/curation-protocol.md)).
Builds `DeorphBench`: proteins that were genuine orphans at cutoff `C` whose ligands were reported after it.
**Dates every assignment by earliest primary publication, never by database release** — the one step that
determines whether the benchmark is valid. The only agent allowed to read post-cutoff data, and it never
shares a session with a scoring loop.

**L1 — target loop.** One protein to one audited dossier:

- *reads literature* — [`librarian`](.claude/agents/librarian.md), date-filtered **at the tool boundary**, with a verbatim quote required on every claim;
- *writes and runs code* — [`structuralist`](.claude/agents/structuralist.md) (pocket detection and a quality gate that can block docking entirely), [`chemist`](.claude/agents/chemist.md) (library, protonation, property-matched decoys), [`screener`](.claude/agents/screener.md) (docking; **forbidden from emitting a raw score as a ranking signal**), [`geneticist`](.claude/agents/geneticist.md), [`comparativist`](.claude/agents/comparativist.md) (Foldseek);
- *checks its own results* — [`falsifier`](.claude/agents/falsifier.md) runs a nine-attack battery against every hypothesis and is read-only on them, then [`auditor`](.claude/agents/auditor.md) re-derives every claim from its artifact;
- *keeps state in files* — [`TASKS.md`](TASKS.md), [`JOURNAL.md`](JOURNAL.md), [`PROMPT.md`](PROMPT.md), immutable run records.

**L2 — evaluation loop.** Controls and physics regressions run **before** any benchmark metric, and abort the run on failure.

**L3 — improvement loop.** Proposes a change as a [loopspec](loops/loopspec.schema.json) diff, pre-registers the metric and expected effect *before* running, and records promote-or-reject in [`loops/CHANGELOG.md`](loops/CHANGELOG.md) either way.

**L4 — watch loop.** `/loop 6h` for new structures and literature; writes to the task list, never into a running evidence channel.

## What the loop found

**`TODO` — nothing yet. No benchmark has been built and no scientific result has been produced.**

What exists today is specification and scaffold: the problem analysis, the evaluation protocol,
thirteen agent definitions, the loop contracts, the versioning and pre-registration machinery,
the guard hooks, the test skeleton, and the tool and data documentation.

We would rather say this than imply more. See [JOURNAL.md](JOURNAL.md) for what actually ran.

When results exist, report here: recovery per contamination bin with bootstrap CIs, calibration,
false-confidence rate on negative controls, and the comparison against all five baselines —
**including the popularity baseline**, which is the hardest to beat and the most informative.

## Where it got stuck

- **The development machine had no Python at all** (Windows Store stub only, no `py` launcher), so for most of the build nothing could be executed and every file was unverified. Resolved by installing Python 3.12.10 and a project-local venv. Tier 0 is now green, `pytest` runs (16 passed, 31 xfailed), the loopspec validates, and `scripts/unseal.py` demonstrably refuses a non-interactive caller. **Running the tooling immediately found a bug in the tooling**: `doctor.py` checked `pytest` as a PATH executable, which misses a venv install — exactly the kind of defect that reading the file would never surface.
- **A completeness audit found ten referenced-but-absent files**, including the `msf.cli` entry point declared in `pyproject.toml` and `scripts/unseal.py` — the latter being the only documented path to the sealed split, and a control that the guard hooks explicitly deny access to. A security control pointing at a nonexistent file is not a control. All ten now exist; most raise `NotImplementedError` naming the task that would implement them. The markdown link checker had been passing throughout, which is a reminder that it validates links and not prose.
- **We built most of the repository before reading the research we were asked to build on.** The supplied link was behind an EU consent gate that no automated client can pass (three attempts, three URL forms), so we proceeded without it and documented the gap. It was later supplied as a saved page and is now reconciled in [docs/11-PRIOR-ARCHITECTURE.md](docs/11-PRIOR-ARCHITECTURE.md). **The honest move, in hindsight, was to block on the missing input rather than work around it.** The cost was concrete: the prior design blinds its executing agent with masked decoy batches, a good contamination control we missed and have now queued as `P-009`. It also named two sequence-based tools — **bindPredict** and **PSICHIC** — that directly address the early-cutoff structure gap we had written down as unavoidable (`P-007`, `P-008`).
- **We did not build the benchmark.** `DeorphBench` is a protocol, not a dataset. Its feasibility — specifically whether strict criteria leave enough items to support any claim — is **unknown and is the project's main open risk**.
- **Contamination cannot be solved**, only measured, and our probe measures *elicitable* recall, a lower bound on what the model knows. The `clean` bin is optimistic in an unknown direction. This is our largest unresolved threat to validity.
- **Survivorship bias is uncorrectable.** Ligands that were found are biased toward abundant, easily assayed metabolites in well-funded families, so `DeorphBench` will overestimate performance on the orphans that remain.
- **Database licensing bites harder than expected**, and verifying it changed the design. Every licence was checked against its official page rather than from memory ([docs/06-DATA-SOURCES.md](docs/06-DATA-SOURCES.md)):
  - **HMDB is CC BY-NC 4.0**, so the natural human-metabolite library is unusable. We substituted ChEBI + LIPID MAPS (both CC BY 4.0) and accepted worse coverage.
  - **Our primary ground truth, IUPHAR/BPS Guide to Pharmacology, is ODbL + CC BY-SA 4.0** — copyleft. Whether a curated item list is an "adapted database" carrying share-alike is genuinely unsettled, and the EU *sui generis* right makes it more so. `DeorphBench` therefore ships as identifiers plus a reproduction script, not as data. **This is a live obstacle to our primary deliverable being reusable, which is success criterion 1.**
  - KEGG, DrugBank, ARCHS4 and ZINC are all `AVOID`. ChEMBL and Pharos are share-alike, so derived facts only.
  - 25 items remain `UNVERIFIED` and must be confirmed before release.
- **At a 2018 cutoff, AlphaFold DB does not exist.** Any predicted model is future information, so the structure channel runs on experimental and homology structures only — and most orphans have neither. A correct consequence of the time split that partly turns `DeorphBench` into "can you work without a structure", which is a harder and different question.
- **A time split cannot constrain a model whose weights already crossed the cutoff** — the same problem as contamination, one layer down. Proposal `P-002` (co-folding) is gated on checking this first.
- **Some historical snapshots simply do not exist.** STRING v10.5 — the release current at 2018-01-01 — 404s at every path, so the closest pin is v11.0 and the ~12-month gap is declared as quantified residual leakage in the manifest. PDBe-KB, GPCRdb, LIPID MAPS, PubChem and the literature indexes have no dated archive at all.

## What it would need next

1. **Build the benchmark.** Everything depends on `N`. If strict criteria leave too few items, the honest responses are an earlier cutoff, more families, or orthologues as a separate stratum — **never relaxing the criteria**.
2. **A working environment** and the Tier 1 scientific stack; GPU for the co-folding channel.
3. **A domain curator** to check the 10% audit sample. Ground truth is contestable and we inherit the field's errors.
4. **A second sealed split held by someone outside the development loop** — once a developer has seen sealed numbers, they cannot unsee them.
5. **If a retrospective time-split deorphanization benchmark already exists, we would rather adopt it than duplicate it.** Finding one is worth more to us than our own build.

## How to run it

```shell
git clone <repo> && cd MetaboliteSensorFinder
uv sync
python scripts/doctor.py          # tool readiness per tier; Tier 0 needs no GPU and no keys but Anthropic
cp .env.example .env              # add ANTHROPIC_API_KEY

# then, in Claude Code:
#   /goal continue the goal described in PROMPT.md
# or a single target:
#   /target Q9HC97

pytest -m controls                # the controls that gate every evaluation run
```

Setup detail per tier: [docs/05-TOOLS-SETUP.md](docs/05-TOOLS-SETUP.md).
**Caveat: these commands have not been executed end to end — see "where it got stuck".**

## Data and sources

Public databases only; no private or patient data. Per-source licences, redistribution verdicts and
archive availability: [docs/06-DATA-SOURCES.md](docs/06-DATA-SOURCES.md).

Several sources (HMDB and KEGG among them) restrict redistribution, so the repository commits
identifiers and fetch scripts rather than data. Anything marked `UNVERIFIED` must be confirmed before release.
Ground truth for `DeorphBench` derives primarily from IUPHAR/BPS Guide to Pharmacology, corroborated
against UniProt and ChEMBL, with dates resolved via Europe PMC and Crossref.

## How Claude was used

Claude Code with subagents, skills, slash commands and `PreToolUse` hooks; Claude Agent SDK for the
programmatic loop; MCP servers for date-filtered data access.

Models per role are declared in the loopspec and hashed into every run record —
a model change is always at least a MINOR version bump, because it changes results even when nothing else does.
The `falsifier` is deliberately given the strongest model: if the adversary is weaker than the proposer,
everything survives and the battery is theatre.

Claude drives literature retrieval, hypothesis formation, falsification design, and report writing.
Claude does **not** drive pocket detection, docking, fusion weights or calibration — those are
deterministic tools and fitted statistics. The `−LLM` ablation exists so the language model's
contribution is a measured number rather than an assumption.
See [docs/02-ARCHITECTURE.md §7](docs/02-ARCHITECTURE.md) for the full map of where the model is and is not.

## Demo materials

`TODO`

## Confirmations

- [ ] The repository is public and has an open-source license.
- [ ] The submission contains no secrets, API keys or non-anonymized private data.
- [ ] We agree that this submission text is published under CC BY 4.0.
