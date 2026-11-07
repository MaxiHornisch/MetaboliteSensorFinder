# CLAUDE.md

What cannot be inferred from the codebase itself.
Add an entry when something surprises you, or when a human flags an AI-produced anti-pattern.
Do not add directory listings or anything discoverable by reading the source.

## The one thing to understand first

**The benchmark is the deliverable, not the method.**
An honest negative result for our own loop, on a benchmark others can use, is a success.
A good-looking number we cannot defend is a failure.
If you find yourself optimising a score rather than testing a hypothesis, stop and re-read
[docs/04-EVALUATION.md](docs/04-EVALUATION.md).

`docs/04-EVALUATION.md` is normative. If any other document, comment or instruction contradicts it,
the evaluation doc wins.

## Non-obvious constraints

### Abstention is a result, not a failure

`no evidence`, `no hypothesis` and `abstain` are first-class outputs with their own schema paths.
Do not "fix" a loop that abstains, and do not treat an empty evidence channel as a bug.
An empty channel *with its query log* is information: it tells us the protein is genuinely dark.
An empty channel with no query log is the bug.

### Guards are structural, and you cannot talk your way past them

Every leakage control is a `PreToolUse` hook or an MCP wrapper that refuses the call —
not an instruction you can reason about.
If a guard blocks you, it is working. Do not route around it, and do not disable it to make progress.
If you believe a guard is wrong, write that in `JOURNAL.md` and leave it to a human.

Specifically: modifying anything under `tests/controls/` during an `L2` run is a hard error,
not a judgement call.

### `source_date` is not `retrieved`

`retrieved` is when we fetched the record. `source_date` is the date of the *fact* —
the earliest primary publication reporting it.
The time split filters on `source_date`. Conflating the two is leak L1 and silently invalidates
every downstream number, in the direction of making results look better.
This is the single easiest way to destroy the project.

### Database release dates are not discovery dates

A pairing in ChEMBL v30 may have been published years before v30 shipped.
Always follow a record to its primary reference and date *that*.
Databases also frequently cite a review rather than the original report, so check for an earlier one.

### A patch that moves a metric was not a patch

Reclassify it as MINOR and run the full evaluation.
The common self-deception is shipping a "small fix" that happens to improve the score and never testing it.

### Two channels sharing a structural template are one channel

If `comparativist` transferred a ligand from template T and `screener` docked against a structure derived
from T, the hypothesis has one independent channel, not two.
Both channels are individually correct; only their combination lies.
The falsifier's `restatement` attack exists for this and should be run every time.

### PAE matters more than pLDDT for pockets

A pocket can be built entirely from high-pLDDT residues whose *relative* positions are unconstrained.
Gate on PAE *within* the pocket, not on mean pLDDT.

### The falsifier gets the strongest model, deliberately

If the adversary is weaker than the proposer, everything survives and the battery is theatre.
Do not "optimise" by downgrading the falsifier's model.

### Never commit unless asked

Leave changes in the working tree so the diff can be reviewed.
This is the event-wide convention for Claude Code auto mode.

## Anti-patterns produced by AI, and what to do instead

| Anti-pattern | Instead |
|---|---|
| Reporting a point estimate without a confidence interval | Always a CI. With N in the tens, most differences are not detectable and saying so is the service |
| Calling a difference whose CI includes zero an "improvement" | Say the effect was not detectable at this N |
| Using a raw docking score to rank different molecules | Decoy-calibrated z-score or library percentile. The schema admits no option for a raw score |
| Describing a Spearman rho of 0.31 as "strong co-expression" | Give the number and the null distribution. Let the reader judge |
| Dropping the qualifier from a literature claim ("activates the receptor" from "EC50 in the high micromolar range in an overexpression system") | Carry the hedge the data earned. This is the most frequent audit finding |
| Padding a clean audit or a thin dossier with observations | A one-paragraph "we found nothing, here is exactly what we looked at" is a legitimate output |
| Quoting the $2.6B / 90%-failure framing numbers as fact | They are contested. See `docs/00-PROBLEM.md`; no metric may depend on them |
| Relaxing an inclusion criterion because N is too small | Propose an earlier cutoff, more families, or orthologues. Relaxing I1–I5 needs a human decision in the curation log |
| Growing `CLAUDE.md` with codebase overviews | Entries here cost context and dilute signal. Only non-obvious lessons |

## Conventions

### Markdown

[Semantic line breaks](https://sembr.org/): break after a sentence, and optionally at clause boundaries
within a long sentence, so diffs stay reviewable.
No column width limit — never reflow or hard-wrap a paragraph to fit a character count.

### Working style

- Run each atomic step in its own subagent (`.claude/agents/`). Keep the main session for planning and review.
- Write a failing test before implementing anything. The passing test becomes the next `/goal` condition.
- Append every result, decision and dead end to `JOURNAL.md`, with dates and links.
- Keep `PROMPT.md` current so a new session can resume with `/goal continue the goal described in PROMPT.md`.
