# Journal

Append-only. Every result, decision, dead end and exchange, newest last, with dates and links to outputs.

Failures are recorded with the same care as results.
This file is the project's honesty record and the fastest way for a reader to find out what actually ran.

---

## 2026-11-07 — Project scaffolded; problem and evaluation specified

**Decided.** The primary deliverable is the benchmark, not the method.

Surveying current practice in ligand prediction, held-out-*target* splits exist
(hold out whole receptors, predict their ligands — the strongest current practice, and explicitly framed
as the deorphanization scenario), but we found **no retrospective time-split benchmark** for endogenous
ligand assignment. Reviews in the area call for scaffold and time-split evaluation as future work.

A held-out-target split asks "can you generalise across proteins?".
A time split asks "would this loop have made the discovery?" — which is the question a researcher
deciding whether to trust the output actually needs answered.
So `DeorphBench` became the project rather than a supporting artifact.

**Decided.** Abstention is a scored output, not an error state.
The dominant failure mode in this area is confident fabrication, so the loop is scored on a
false-confidence rate against negative controls, with a pre-registered gate of < 0.10,
and a loop version that never abstains cannot be promoted regardless of its ranking metrics.

**Recorded as a known, unsolvable problem.** A time split prevents *tools* from seeing the future.
It does nothing about the language model, whose training data contains the post-cutoff literature.
This cannot be eliminated, only measured. We therefore added:

- a closed-book contamination probe per benchmark item, with results binned `clean` / `partial` / `contaminated` and **every headline metric reported per bin**;
- a scored non-LLM pipeline path, so the language model's contribution is a measured number rather than an assumption;
- a schema-level requirement that a hypothesis cite ≥2 independent non-LLM channels, making recall alone insufficient to score.

Our probe measures *elicitable* recall, which is a lower bound on what the model knows.
The `clean` bin is therefore optimistic in an unknown direction. Stated in `docs/04-EVALUATION.md` §9.

**Decided.** All leakage controls are enforced at the tool boundary, not by prompt instruction.
A prompt is a suggestion; a tool that refuses is a guarantee.
This is why T-006 (date filter) is the highest-priority single task in `TASKS.md` —
without it, every subsequent number is uninterpretable.

**Flagged.** The framing numbers in the original problem brief — 20–35% uncharacterised,
$2.6B per drug, 90% wet-lab failure — are definition-dependent or contested.
They are kept as motivation and excluded from every metric.
T-001 recomputes the two we actually use, from primary sources, with query dates.
Recorded as a tracked failure mode rather than quietly fixed, because inflated framing numbers
are the easiest thing for a reader to check and the fastest way to lose their trust.

**Not done.** No code runs yet. No benchmark exists. No result has been produced.
Everything above is specification. The next entry should be T-001 or T-006.

Artifacts: `docs/00-PROBLEM.md`, `docs/02-ARCHITECTURE.md`, `docs/03-LOOPS.md`,
`docs/04-EVALUATION.md`, `docs/07-VERSIONING.md`, `.claude/agents/`, `TASKS.md`.

---

## 2026-11-07 — Licence verification changed the design

**Task.** Documentation of tools (`docs/05-TOOLS-SETUP.md`) and data sources (`docs/06-DATA-SOURCES.md`).
Every licence was checked against its official page rather than recalled.
That turned a documentation task into a design change, which is why it gets its own entry.

**Three findings that altered the loop, not just its documentation.**

*HMDB is CC BY-NC 4.0, with an explicit-permission clause.*
It is the natural human-metabolite reference set and we cannot use it.
`loops/v0.1.0-baseline.yaml` previously named `hmdb_endogenous_v1` as the candidate library;
it now names ChEBI + LIPID MAPS, both CC BY 4.0.
**This measurably weakens the search space** — if the true ligand falls outside that coverage,
the loop cannot find it and nothing errors.
Added as failure mode B13, bounded by a library-membership statistic on the benchmark,
and `T-033` will measure what the substitution actually costs.
We chose a worse library over an undonatable repository.

*IUPHAR/BPS Guide to Pharmacology is ODbL + CC BY-SA 4.0.*
Our primary ground-truth source is copyleft, and ChEMBL (CC BY-SA 3.0) is too.
Whether a curated item list is an "adapted database" carrying share-alike, or a set of unprotectable
facts, is genuinely unsettled — and the EU *sui generis* database right makes it more so, not less.
`DeorphBench` therefore ships as identifiers plus a reproduction script, not as redistributed data.
**This is a live obstacle to success criterion 1** (the benchmark being usable by others) and is
recorded as failure mode A11 and task `T-032` rather than assumed away.
We are not qualified to settle it and have not pretended to.

*AlphaFold DB postdates both the 2015 and 2018 cutoffs entirely.*
Any predicted structure is future information at those dates.
Added as leak L5b with a schema-level `allowed_structure_sources` gate;
the baseline is now restricted to `[experimental, homologue]`.
The consequence is severe and we are not working around it:
most orphans have neither an experimental structure nor a close homologue,
so `DeorphBench` at `C=2018` partly measures *working without a structure* —
a harder and different question than the one we set out to ask.
Later cutoffs trade this against less post-cutoff time for discoveries to accumulate.
The same argument extends one layer down to model weights (L5c):
a co-folding model trained past the cutoff cannot respect it whatever we feed it,
which is now the gating condition on proposal `P-002`.

**One finding that makes the benchmark possible.**
GtoPdb publishes archived PostgreSQL dumps back to `v2016.1`, verified reachable.
Without a dated archive there is no way to establish *orphan status at `C`* —
querying today's database and filtering by date answers a different question.
Dated snapshots also confirmed for PDB, UniProt, ChEBI (a release dated exactly 2018-01-01),
GWAS Catalog, Open Targets, GTEx, HPA and TCRD.
No dated archive exists at all for PDBe-KB, GPCRdb, LIPID MAPS, PubChem, ZINC, ARCHS4,
or any literature index.
STRING v10.5, the release current at the cutoff, 404s at every path;
v11.0 is the closest pin and the ~12-month gap is declared as quantified residual L2 exposure
rather than ignored.

**A concrete proof of the dating hazard.**
A paper published 2017-12-31 carries a Europe PMC first-index date of 2019-03-26.
Date-filtering a *current* index is therefore provably not the same as querying the index as it stood
at `C`. Worked into the curation protocol as a numbered step and recorded as failure mode A12.

**Corrections to our own earlier assumptions**, all verified:
LIPID MAPS is CC BY 4.0, not NC. STRING is CC BY 4.0 with explicit commercial permission, not NC.
HPA is CC BY 4.0 only from v25.0 — a 2018-pinned HPA snapshot *is* copyleft.
Open Targets Genetics no longer exists separately.
Four priors wrong out of the handful we had; a useful reminder that recalled licences are not evidence.

**Honest gaps.** 25 items remain `UNVERIFIED — must confirm before release` (`T-035`),
including all of ZINC and HMDB verbatim terms, because those sites block automated access.
KEGG, DrugBank, ARCHS4 and ZINC are `AVOID`.
An unverified item is recorded as unverified rather than guessed.

**Confidence.** High on the licences checked against official pages; low on anything marked
`UNVERIFIED`; and no confidence at all on the share-alike propagation question, which needs a lawyer.

**Artifacts.** `docs/05-TOOLS-SETUP.md`, `docs/06-DATA-SOURCES.md`,
`loops/v0.1.0-baseline.yaml`, `loops/loopspec.schema.json`,
`docs/04-EVALUATION.md` §2 and §9, `docs/09-FAILURE-MODES.md` A11–A12 and B11–B13,
`benchmarks/curation-protocol.md`, `TASKS.md` T-032…T-035.

---

## 2026-11-07 — Tooling verification; two findings that break things quietly

**Task.** `docs/05-TOOLS-SETUP.md`. Facts checked live, including real MCP `initialize` handshakes
against every hosted endpoint cited rather than trusting that advertised servers exist.

**The finding that threatens the primary metric.**
**scikit-learn 1.8 removed `CalibratedClassifierCV(cv="prefit")`.**
That is exactly how we calibrate a fused score fitted separately on `val`.
Calibration is this project's primary metric ([ADR-0003](docs/adr/0003-calibration-is-the-primary-metric.md)),
so an unpinned dependency bump would break the headline number rather than a peripheral feature —
and would do it at install time, in a fresh environment, with no code change to point at.
`pyproject.toml` now pins `scikit-learn>=1.5,<1.8` with the reason in a comment,
because a bare version bound gets raised by the next person who sees it.

**The finding that would silently invalidate a benchmark run.**
**The ChEMBL REST API fails open on a malformed filter**: it ignores the bad parameter and returns the
full unfiltered result set with HTTP 200.
A typo in a date filter therefore returns everything, including post-cutoff records,
and the failure signature is indistinguishable from success.
Every other leak in our taxonomy requires someone to do something wrong; this one requires a typo.
Generalised into a rule — **no retrieval wrapper may trust that a filter was applied, it must verify it** —
asserted as `filtered_count < unfiltered_count` with both counts recorded in provenance.
Recorded as failure mode A13 with two new control tests.

**Also acted on.** Claude Science is barred from scored runs: its connectors cannot be wrapped by our
date gateway, so it cannot close L1. Useful for exploration, not for anything that produces a number.

**Scope reality.** Only **7 of 26** data resources ship an official MCP server, and only
**6 of 26** have a server-side date filter — so most of L1/L2 enforcement is offline filtering over
pinned snapshots in DuckDB, not a feature we get from upstream. That is more work than assumed.

**Corrections worth keeping.** Chai-1 is now Apache-2.0 and ESM3/ESMFold is now MIT —
both are still widely described as non-commercial. `rdkit-pypi` is dead,
`openmm-forcefields` is actually `openmmforcefields`, and `pip install prolif` alone is broken.
Packaging guidance for this stack is stale almost everywhere, which is why the doc records
verify-it-works one-liners rather than just install commands.

**Gaps.** ~35 items `UNVERIFIED`, including VRAM minimums for four GPU tools (published nowhere)
and rate limits for 17 resources. HMDB is unverifiable programmatically at all — Cloudflare blocks it —
so a human must read its terms in a browser before release.

---

## 2026-11-07 — Scaffold complete; still no result

**State.** 77 files, ~8,500 lines of documentation, all internal links resolving,
all JSON schemas validating. Thirteen subagents, four slash commands, five loop contracts,
the versioning and pre-registration machinery, guard hooks, and a test skeleton
whose every case is `xfail` because nothing is implemented.

**Not done, and worth being blunt about.**
No code has been executed. `DeorphBench` does not exist.
There is no number anywhere in this repository, and the one loop version on disk has never been run.
Everything above is specification.

**Blockers found by trying.**
There is no working Python runtime on the development machine — only the Windows Store stub —
and no `uv`. `scripts/doctor.py` was written to check exactly this class of problem and
**could not itself be run**, which is the most on-the-nose result of the day.
Recorded in `SUBMISSION.md` under "where it got stuck" rather than left implicit.

**One input we never obtained.**
The research link supplied with the brief was a Google AI-mode share behind a consent wall
and could not be retrieved at any redirect.
`docs/01-RESEARCH-BRIEF.md` was rebuilt from primary searches instead,
and every claim in it is marked `verify` because no human has checked it against a primary source.
If the original research contained something we have now contradicted, we would not know.

**The main open risk, unchanged since this morning.**
Whether strict inclusion criteria leave enough items for `DeorphBench` to support any claim at all.
Plausibly tens, not thousands. We will not know until `L0` runs, and
if the answer is "too few", the honest responses are an earlier cutoff, more families,
or orthologues as a separate stratum — never relaxing the criteria.

**Next.** `T-001` (recompute the framing numbers) or `T-006` (date filter at the tool boundary).
`T-006` is the higher-value one: until the filter is structural, no subsequent number means anything.

---

## 2026-11-07 — Audit: the docs referenced ten files that did not exist

**What prompted it.** A completeness check on the scaffold, rather than on the prose.
The markdown link checker had been passing all along, which was misleading:
it validates markdown link syntax and says nothing about paths named in prose, in command
examples, in `pyproject.toml` entry points, or in agent instructions.

**What it found.** Ten referenced-but-absent paths, including `msf.cli` — declared as the
package entry point in `pyproject.toml`, so `uv sync` would have installed a console script
pointing at nothing. Also `scripts/unseal.py`, which the guard hooks and
`.claude/settings.json` both explicitly deny access to, and which several documents describe
as the only path to the sealed split. **A security control referencing a file that does not
exist is not a control.**

Two were false positives: `msf.channels` resolves as a package, and `msf.duckdb` is a
filename in the web spec rather than a module.

**Fixed.** All ten now exist. `src/msf/cli.py` is a working Typer CLI whose `validate`
subcommand genuinely runs. `scripts/unseal.py` is substantively implemented — it refuses a
non-interactive terminal, refuses to run inside a Claude Code session, requires a
pre-registration file, and detects a repeat unseal — and then stops short at the decryption
step with a non-zero exit, because there is no sealed split yet and a script that appears to
succeed against nothing is worse than one that refuses. The rest raise `NotImplementedError`
naming the task that would implement them, rather than returning silently.

Also normalised `fetch_snapshots.py` to `fetch_snapshot.py` (the tooling doc had the plural),
and added the `date-a-claim` skill, which packages the dating procedure that `L0`, `L1` and
the auditor all need and that is the easiest thing in this project to get quietly wrong.

**Lesson, worth generalising.** A link checker that only reads markdown links gives a false
sense of completeness. The referenced-path audit is now part of the verification pass:

```bash
grep -rhoE '(scripts/[a-z_]+\.py|src/msf/[a-z_/]+\.py)' --include='*.md' --include='*.toml' . \
  | sort -u | while read -r r; do [ -e "$r" ] || echo "MISSING $r"; done
```

**Still not run.** Confirmed there is no Python interpreter on this machine beyond the Windows
Store stub, and no `py` launcher. The new files are therefore **syntax-unverified** — they are
written carefully but nothing has parsed them. Installing a runtime is a change to the
developer's machine and is their call, not ours.

**Artifacts.** `src/msf/cli.py`, `src/msf/run.py`, `src/msf/curate.py`,
`src/msf/channels/screening.py`, `scripts/unseal.py`, `scripts/fetch_snapshot.py`,
`scripts/compare_runs.py`, `scripts/verify_licenses.py`,
`.claude/skills/date-a-claim/SKILL.md`.

---

## 2026-11-07 — Environment built; running the code found a bug in the code

**What changed.** Installed Python 3.12.10 and a project-local venv with the Tier 0 dependencies.
Until now nothing in this repository had ever been executed.

**Verified by running, not by reading:**

| Command | Result |
|---|---|
| syntax-check all 20 Python files | 0 failures |
| `scripts/doctor.py --tier 0` | **Tier 0 ready**, exit 0 |
| `python -m msf.cli validate` | schemas + incumbent loopspec validate, exit 0 |
| `pytest` | **16 passed, 31 xfailed**, exit 0 |
| `scripts/unseal.py` piped from a non-TTY | **refused**, exit 77 |

That last line matters more than the others.
The sealed-split guard is the mechanism the whole versioning story rests on,
and it is now demonstrated rather than asserted: an automated caller gets refused with a message
telling it to ask a human.

**Running `doctor.py` immediately found a bug in `doctor.py`.**
It checked `pytest` as a PATH executable via `shutil.which`, which misses a perfectly good install
inside an unactivated venv — so it reported a missing tool that was present.
Now checked as an importable module.
This is exactly the class of defect that reading the file would never surface,
and it is a small, concrete argument for the project's own rule that controls must be run,
not reviewed.

**T-002 converted from stub to real.**
`msf validate` was already validating the baseline, which meant the `xfail`s in
`tests/unit/test_loopspec.py` were stale — they would have passed if implemented.
Rewrote them as 16 real assertions, and deliberately made them assert the *guarantees* rather than
mere schema conformance: that no raw docking score can be configured as a ranking signal,
that fusion can be fitted only on `val`, that fewer than two independent channels is unwritable,
that refinement is bounded, that the candidate library is not an `AVOID`-licensed source,
and that predicted structures are excluded at an early cutoff.

Those last two are new and worth noting: they pin yesterday's licensing and anachronism findings
into the test suite, so a future edit cannot quietly reintroduce HMDB or AlphaFold models.
**A limitation that is only written down will eventually be undone; one with a test will not.**

**Still true.** No benchmark, no evidence channels, no scientific number.
The 31 `xfail`s are the honest map of what remains.

**Artifacts.** `tests/unit/test_loopspec.py` (16 passing), `scripts/doctor.py` (fixed),
`TASKS.md` (T-002, T-004 closed), `.gitignore`, `README.md` status table.

---

## 2026-11-07 — Metrics implemented; test-first caught a metric that depended on row order

**Task.** `T-036`. Implemented `src/msf/eval/metrics.py` for real:
recall@k, MRR, enrichment factor, BEDROC, Brier, ECE, risk–coverage, selective accuracy
at coverage, false-confidence rate, decision utility, BCa bootstrap and paired bootstrap.

These were chosen as the next thing to build because they need **no external data,
no licence, and no GPU** — so they could be finished and genuinely verified rather than
stubbed. They are also the part of the project the evaluation rests on:
if a metric is wrong, every number computed later is wrong in a way nothing downstream detects.

**27 tests, each pinned to a hand-derived answer** where a closed form exists
(MRR of ranks 1,2,4 is exactly 1.75/3; Brier of [0.2,0.9,0.3] against [T,T,F] is 0.74/3;
BEDROC of a perfect ranking is 1 and of the worst is 0), and to analytic bounds or
orderings where it does not.

**The bug that justifies the whole approach.**
`test_ece_detects_systematic_overconfidence` asserted 0.4 — a model claiming 0.9 and being
right half the time. The implementation returned **0.5**.

The implementation was wrong, not the test.
Equal-mass ECE binning cuts by count, so a thousand tied 0.9 predictions were being
scattered across ten bins, and the score became a function of **how the rows happened to be
sorted** rather than of the data. Sorted outcomes gave 0.5; interleaved gave 0.4.
A metric that changes when you shuffle the input is not a metric.

Fixed by pushing bin boundaries past tie groups so identical claims always share a bin.
Pinned by a regression test across three orderings plus a general permutation-invariance
test on a realistic mixture of tied and untied predictions.
Recorded as failure mode **A14**.

Worth stating plainly: this would never have been caught by reading the code.
It looks obviously correct, it returns a plausible number, and no pipeline would flag it.
It was caught because the expected value was derived by hand *before* the code ran.
That is the project's own rule, and this is the first time it has paid out.

**Suite now: 43 passed, 31 xfailed, exit 0.**

**Still true, and unchanged.** No benchmark, no evidence channels, no scientific result.
What exists is a verified measuring instrument with nothing yet to measure.
That ordering is deliberate — a benchmark number produced by an unverified metric
would be worse than no number, because it would be believed.

**Artifacts.** `src/msf/eval/metrics.py`, `tests/unit/test_metrics.py` (27 passing),
`docs/09-FAILURE-MODES.md` A14, `TASKS.md` T-036.

---

## 2026-11-07 — Read the source research at last; reconciled against it

**What happened.** The research we were commissioned to improve — unreachable all day behind an EU
consent gate — was supplied directly as a saved page: a seventeen-turn conversation that develops the
**Orphan-Catch Agentic Harness**, a three-loop filtering funnel.

**Process failure, stated plainly.** We built most of this repository before reading it.
The correct move was to block on the missing input and ask for it, not to work around it and
document the gap. We did the latter. This entry exists so the cost is on the record.

**What the prior design is.**
`bindPredict` (sequence → binding residues) → `PSICHIC` (GNN affinity screen) → `AutoDock Vina`
(geometric calibration), with a TDD Architect writing an immutable manifest, a deliberately *blind*
Builder, a Validator checking artifact integrity, and a two-member adversarial Judge Panel.

**Convergence, and why it is only weak evidence.**
We independently arrived at specialised agents, TDD-for-biology, negative controls, an adversarial
step, a separate validator-vs-critic split, bounded retries and file-based state.
Agreement is mildly reassuring about those choices. It is not vindication:
we would have got to a better architecture faster by reading first.

**What we had missed, now adopted.**
The **blinded Builder** — 49 masked decoys and 1 candidate, so the executing agent cannot know which
answer it is meant to reach. We had decoys for metric purposes but never blinded the executor.
Queued as `P-009`. Also the methane negative control, which is nearly free.

**What the research gives us that solves a problem we had called unavoidable.**
`bindPredict` and `PSICHIC` are **sequence-based**: they need no structural database.
We had independently found that AlphaFold DB postdates the 2015 and 2018 cutoffs (leak L5b),
leaving the structure channel nearly empty at an early cutoff, and recorded that in
`04-EVALUATION.md` §9 as a severe handicap we would simply have to report.
A sequence-based pocket predictor is not subject to it. Queued as `P-007` and `P-008`,
the latter gated on checking its training cutoff (L5c).

**The one thing we would change hardest.**
The prior design gates on `PSICHIC ≥ 7.5` and `Vina energy < −8.0 kcal/mol`.
Fixed score thresholds are the raw-score failure (B1): a Vina score is not an affinity,
−8.0 has no fixed meaning across targets, and it correlates strongly with molecular weight —
so across a 100k library that threshold selects for heavy molecules.
Replaced with decoy-calibrated z-scores. This is about what the numbers mean when compared across
molecules, not about the tools, which are the right tools.

**The gap that became this whole project.**
The prior architecture specifies gates but has no way to know whether the pipeline works:
the thresholds are stated, not derived; nothing calibrates confidence, nothing compares against a
baseline, nothing stops a confident answer for a protein that binds nothing.
A funnel with invented thresholds and no benchmark is the apparatus that produces the
"digital hallucinations and costly real-world failures" the research set out to solve.

**Action recorded, not taken.** The three-loop funnel should be **benchmarked as a baseline** on
`DeorphBench`, not treated as superseded. It is a serious method.
If it beats the evidence-fusion design, it is right and we should say so.

**Artifacts.** `docs/11-PRIOR-ARCHITECTURE.md`, `loops/PROPOSALS.md` (P-007, P-008, P-009),
`docs/01-RESEARCH-BRIEF.md` appendix, `docs/README.md`, `SUBMISSION.md`.

---

<!-- Append new entries below. Template:

## YYYY-MM-DD — <one-line summary>

**Task.** T-0NN
**Run.** `runs/<run-id>/` · loop `v<x.y.z>` · commit `<hash>`

**What happened.**

**What the numbers were.** (with CIs, per stratum; never a bare point estimate)

**What failed, and what we concluded from the failure.**

**Confidence.** <how much we believe this, and why>

**Artifacts.** <links>

-->
