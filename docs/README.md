# Documentation index

[04-EVALUATION.md](04-EVALUATION.md) is **normative**.
If any other document, comment, prompt or instruction in this repository contradicts it, the evaluation doc wins.

## Reading orders

**Assessing the project (≈20 minutes).**
[04-EVALUATION.md](04-EVALUATION.md) — especially §9, what is wrong with our own evaluation —
then [09-FAILURE-MODES.md](09-FAILURE-MODES.md),
then [../JOURNAL.md](../JOURNAL.md) for what actually ran rather than what was designed.
Then verify a specific claim using the five-minute path in [08-RESEARCHER-UX.md](08-RESEARCHER-UX.md).

**Understanding the science.**
[00-PROBLEM.md](00-PROBLEM.md) → [01-RESEARCH-BRIEF.md](01-RESEARCH-BRIEF.md) → [04-EVALUATION.md](04-EVALUATION.md).

**Understanding the agent system.**
[02-ARCHITECTURE.md](02-ARCHITECTURE.md) → [03-LOOPS.md](03-LOOPS.md) → [../.claude/agents/](../.claude/agents/) → [07-VERSIONING.md](07-VERSIONING.md).

**Running it.**
[05-TOOLS-SETUP.md](05-TOOLS-SETUP.md) → [06-DATA-SOURCES.md](06-DATA-SOURCES.md) → [../PROMPT.md](../PROMPT.md).

## The documents

| | Document | What it is |
|---|---|---|
| 00 | [The open problem](00-PROBLEM.md) | Endogenous ligand assignment for orphan human proteins. Scope, non-goals, and a confidence column on every framing number |
| 01 | [Research brief](01-RESEARCH-BRIEF.md) | Prior art, what is wrong with how it is evaluated, and the gap we target. Claims marked `verify` are unconfirmed |
| 02 | [Architecture](02-ARCHITECTURE.md) | The thirteen agents, the data contracts, the falsifier, and a map of where the language model is and is not |
| 03 | [The loops](03-LOOPS.md) | `L0`–`L4` as contracts, each with a machine-checkable exit condition |
| 04 | [**Evaluation**](04-EVALUATION.md) | **Normative.** `DeorphBench`, the leakage taxonomy, contamination, metrics, controls, statistics, the promotion gate — and §9, what is wrong with it |
| 05 | [Tools and setup](05-TOOLS-SETUP.md) | Every external tool, how to connect it, and a tiered setup path starting with a no-GPU, no-key tier |
| 06 | [Data sources](06-DATA-SOURCES.md) | Per-source licence, redistribution verdict, and whether a historical snapshot can be obtained at all |
| 07 | [Versioning](07-VERSIONING.md) | The loopspec, pre-registration, the sealed split, the guards, and how iteration stays honest |
| 08 | [Researcher UX](08-RESEARCHER-UX.md) | The drill-down ladder, how uncertainty is rendered, and the five-minute claim-verification path |
| 09 | [Failure modes](09-FAILURE-MODES.md) | Every specific way this project produces a wrong answer that looks right, with detection and whether it is actually closed |
| 10 | [Glossary](10-GLOSSARY.md) | Terms, for readers from either side of the biology/engineering line |
| 11 | [The prior architecture](11-PRIOR-ARCHITECTURE.md) | The *Orphan-Catch* three-loop funnel this project was asked to improve: what we adopted, what we changed and why, and what it contributes that we had missed |
| — | [Decision records](adr/) | Architectural decisions, with what was rejected and why |

## Related files outside `docs/`

| File | What it is |
|---|---|
| [../README.md](../README.md) | Entry point and honest status |
| [../SUBMISSION.md](../SUBMISSION.md) | Draft submission answers, kept beside the evidence |
| [../CLAUDE.md](../CLAUDE.md) | Non-obvious constraints and AI anti-patterns |
| [../PROMPT.md](../PROMPT.md) | The standing loop prompt; resume with `/goal continue the goal described in PROMPT.md` |
| [../TASKS.md](../TASKS.md) · [../JOURNAL.md](../JOURNAL.md) | Loop state: what is next, and what happened |
| [../loops/](../loops/) | Loopspec schema, the incumbent version, proposals, and the changelog of promotions **and rejections** |
| [../benchmarks/curation-protocol.md](../benchmarks/curation-protocol.md) | How `DeorphBench` is built, frozen |
| [../tests/](../tests/) | Unit, physics and control tests. A control that passes is a bug |
| [../web/spec/](../web/spec/) | The web application specification |

## Conventions

Markdown uses [semantic line breaks](https://sembr.org/): a break after each sentence,
and optionally at clause boundaries, so diffs stay reviewable.
No column width limit — never reflow a paragraph to fit a character count.

Written material is CC BY 4.0; code is Apache 2.0.
