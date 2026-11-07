# MetaboliteSensorFinder

**A research loop for assigning endogenous ligands to orphan human proteins — and an honest benchmark to tell whether it works.**

Built at [Claude Impact Lab Berlin 2026](https://github.com/xemantic/claude-impact-lab-2026)
with [Foresight Institute](https://foresight.org/).

---

## What this is

Thousands of human proteins have no known natural ligand.
Computational methods to guess those ligands exist, produce confident answers, and are very hard to trust —
because the field has no evaluation that answers the question a researcher actually has:

> **Restricted to what was knowable in year *Y*, would this method have found the ligand
> that the field published in year *Y+k*?**

Existing benchmarks hold out *proteins*. We hold out *time*.

So this repository contains two things, in order of importance:

1. **`DeorphBench`** — a retrospective, time-split benchmark for endogenous ligand assignment.
   Proteins that were genuine orphans at a cutoff date, whose ligands the field found afterwards.
   The ground truth arrived independently of us: nobody constructed it to be findable.
   *Surveying current practice, we found no benchmark of this kind.*
2. **A multi-agent research loop** that attempts the task and is measured against it —
   including an adversarial agent whose only job is to destroy the loop's own hypotheses,
   and a calibration layer whose output may be **"no confident ligand"**.

**The benchmark is the deliverable. An honest negative result for our own method is a success.**

## Why "no confident ligand" is the headline feature

Every component of the classical stack returns a best answer whether or not one exists.
Docking returns a ranked list. A language model returns a plausible name and a plausible story.
Nothing in the standard pipeline is built to abstain, and the cost of a confident wrong answer
is a wasted experiment.

So abstention is scored here, not tolerated:

- Negative controls — scrambled sequences, sham pockets, mirror-image proteins, true current orphans —
  have no correct answer. The loop is measured on whether it says so.
- The pre-registered gate is a **false-confidence rate below 0.10**.
- A loop version that never abstains cannot be promoted, whatever its ranking metrics say.

## How it works

```
L3  IMPROVEMENT LOOP     propose a change to the loop → evaluate → promote or reject
     └── L2  EVALUATION  controls → ablations → benchmark → report
          └── L1  TARGET one protein → one dossier
                  evidence (5 independent channels, in parallel)
                     → hypothesise  (≥2 independent channels + a mechanism, or nothing)
                     → falsify      (9-attack battery; survivors only)
                     → fuse         (correlation-discounted, calibrated, may abstain)
                     → audit        (every claim re-derived from its artifact)
L0  BENCHMARK LOOP       builds DeorphBench. Never shares a session with a scoring loop
L4  WATCH LOOP           new literature and structures → invalidate caches
```

Thirteen subagents, defined in [.claude/agents/](.claude/agents/).
The orchestrator plans and never computes; state lives in files, not in context.

## Start here

| If you are… | Read |
|---|---|
| **Assessing this project** | [docs/04-EVALUATION.md](docs/04-EVALUATION.md) — the normative spec — then [JOURNAL.md](JOURNAL.md) for what actually ran. §9 of the evaluation lists what is wrong with our own evaluation |
| A scientist with an orphan protein | [docs/08-RESEARCHER-UX.md](docs/08-RESEARCHER-UX.md) |
| Setting it up | [docs/05-TOOLS-SETUP.md](docs/05-TOOLS-SETUP.md) — there is a 15-minute, no-GPU, no-API-key tier |
| Here for the science | [docs/00-PROBLEM.md](docs/00-PROBLEM.md) |
| Here for the agent design | [docs/02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md), [docs/03-LOOPS.md](docs/03-LOOPS.md) |
| Wondering how iteration stays honest | [docs/07-VERSIONING.md](docs/07-VERSIONING.md) |

Full index: [docs/](docs/).

## Honest status

**Specification, scaffold, and a verified Tier 0 environment.
No benchmark has been built and no scientific result has been produced.**

Verified by running, on 2026-11-07 (Python 3.12.10):

| | |
|---|---|
| `python scripts/doctor.py --tier 0` | **Tier 0 ready**, exit 0 |
| `python -m msf.cli validate` | schemas and the incumbent loopspec validate, exit 0 |
| `pytest` | **43 passed, 31 xfailed**, exit 0 |
| `scripts/unseal.py` from a non-interactive caller | **refused**, exit 77 — the sealed-split guard is real, not documentation |

The 31 `xfail`s are unimplemented work, each naming its task; one (`test_chirality_sensitivity`)
is a declared scientific limitation kept visible rather than omitted.

The 43 passing tests are the **measuring instrument**:
the loopspec guarantees (no raw docking score as a ranking signal, fusion fittable only on `val`,
no `AVOID`-licensed library, no predicted structures at an early cutoff)
and every evaluation metric, each pinned to a hand-derived value.
Writing those tests first caught a real bug — ECE was depending on input row order
([failure mode A14](docs/09-FAILURE-MODES.md)).

What does not exist yet: `DeorphBench`, the evidence channels, and any scientific number.
A verified instrument with nothing yet to measure — deliberately in that order,
since a benchmark number from an unverified metric would be worse than none, because it would be believed.
[TASKS.md](TASKS.md) is the prioritised list; [JOURNAL.md](JOURNAL.md) records decisions and dead ends.

## Running it

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"   # or: uv sync
python scripts/doctor.py          # tool readiness per tier; Tier 0 needs no GPU and no keys
PYTHONPATH=src python -m msf.cli validate
PYTHONPATH=src pytest
```

Then, in Claude Code:

```
/goal continue the goal described in PROMPT.md
```

See [PROMPT.md](PROMPT.md) for the standing loop prompt and the constraints the guards enforce.

## The design commitments

Each of these exists because the opposite failure is easy, common, and invisible in the output.

| Commitment | Mechanism |
|---|---|
| Leakage controls are **structural, not prompted** | Date filters and snapshot pinning enforced at the tool boundary. A prompt is a suggestion; a tool that refuses is a guarantee |
| The loop **cannot tune on its own test set** | The test split is encrypted; a human unseals it, once per loop version, and the unseal log is published |
| **Controls run before metrics** | A control failure aborts the run. A number computed on a broken pipeline is worse than no number, because it will be believed |
| A **raw docking score is never a ranking signal** | Decoy-calibrated z-scores only. The schema rejects raw scores |
| Every hypothesis is **attacked before it is reported** | A nine-attack battery, run by an agent that cannot edit what it attacks |
| **Rejections are recorded** | `loops/CHANGELOG.md` keeps failed loop versions with their numbers. A project whose every version was promoted did not have a gate |
| **Contamination is measured, not assumed away** | A time split does not stop the model from already knowing the answer. We probe for it and report every metric per contamination bin |

## Known limitations

Stated here rather than buried, because a project in this area without this section should not be trusted.
The full list is [docs/09-FAILURE-MODES.md](docs/09-FAILURE-MODES.md) and
[docs/04-EVALUATION.md §9](docs/04-EVALUATION.md).

- **Small N.** Genuine post-cutoff deorphanizations meeting our criteria are plausibly tens, not thousands. Confidence intervals will be wide.
- **Contamination cannot be eliminated**, only measured — and our probe gives a lower bound on what the model knows.
- **Survivorship bias.** Ligands that *were* found are biased toward abundant, easily assayed metabolites in well-funded protein families. Performance on `DeorphBench` overestimates performance on the orphans that remain.
- **Ground truth is itself uncertain.** Published assignments are sometimes wrong or later revised. We inherit the field's errors.
- **At a 2018 cutoff there is no AlphaFold.** The predicted-structure databases postdate our cutoffs entirely, so an honest run has experimental and homology structures only — and most orphans have neither. A correct consequence of the time split, and a severe handicap we report rather than work around.
- **The benchmark's own licence is unresolved.** Our primary ground-truth source is copyleft (ODbL + CC BY-SA 4.0), so `DeorphBench` ships as identifiers plus a reproduction script rather than as redistributed data. This is a live obstacle to success criterion 1.
- **Nothing here is wet-lab validated.** Every number is retrospective. The output is prioritised, falsified hypotheses with stated confidence — nothing more.

## License

Dual-licensed, per the event default:

- **Code** — [Apache License 2.0](LICENSE)
- **Written material** — [CC BY 4.0](LICENSE-CC-BY-4.0)

Third-party data sources carry their own licences, several of which forbid redistribution.
See [docs/06-DATA-SOURCES.md](docs/06-DATA-SOURCES.md) for what may and may not live in this repository.
