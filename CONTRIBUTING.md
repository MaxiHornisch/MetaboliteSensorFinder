# Contributing

This project was built at [Claude Impact Lab Berlin 2026](https://github.com/xemantic/claude-impact-lab-2026)
and is donated as open source. Contributions are welcome, including ones that show our method is wrong.

## What is most useful

In descending order:

1. **Telling us a retrospective time-split deorphanization benchmark already exists.**
   We searched and did not find one. If we missed it, adopting it is worth more than our own build,
   and we would rather do that than duplicate work.
2. **Finding a leak.** If you can show that a post-cutoff fact reaches an evidence channel,
   that a homologue crosses a split, or that our decoys are separable on properties alone,
   that invalidates results and we want to know immediately. Open an issue labelled `leak`.
3. **Curation review.** The 10% audit sample needs a domain expert.
   Published ligand assignments are contestable and we inherit the field's errors.
4. **A method that beats the popularity baseline** on the low-homology strata.
5. **Verifying anything marked `verify` or `UNVERIFIED`** in [docs/01-RESEARCH-BRIEF.md](docs/01-RESEARCH-BRIEF.md)
   and [docs/06-DATA-SOURCES.md](docs/06-DATA-SOURCES.md). These are honest gaps, not oversights,
   and closing one is a real contribution.

## Ground rules

**Read [docs/04-EVALUATION.md](docs/04-EVALUATION.md) first.** It is normative.
A change that improves a score without satisfying the evaluation protocol will not be merged.

- **Write the failing test first.** It is what makes the change checkable, and it becomes a `/goal` condition.
- **Pre-register a loop change.** A change to the loop goes through [loops/PROPOSALS.md](loops/PROPOSALS.md)
  with a named metric and an expected effect size, written *before* it is run.
  See [docs/07-VERSIONING.md](docs/07-VERSIONING.md).
- **Do not modify `tests/controls/` to make something pass.** If you believe a control is wrong,
  say so in the issue. A control that passes is a bug; a control that was edited to pass is worse.
- **Do not add data to the repository** without checking [docs/06-DATA-SOURCES.md](docs/06-DATA-SOURCES.md).
  Several sources we use forbid redistribution. Commit identifiers and a fetch script instead.
- **Record rejections.** A rejected loop version goes in [loops/CHANGELOG.md](loops/CHANGELOG.md) with its numbers.
  That changelog is evidence the gate is real.

## Style

- Markdown uses [semantic line breaks](https://sembr.org/): break after a sentence, optionally at clause
  boundaries. **Never hard-wrap to a column width** and never reflow a paragraph.
- Python: `ruff` and `mypy --strict`, line length 100.
- Carry the hedge the data earned. If the source says "EC50 in the high micromolar range in an
  overexpression system", do not write "activates the receptor".
  This is the most frequent audit finding and it applies to prose as much as to code comments.

## Working with AI agents on this repo

[CLAUDE.md](CLAUDE.md) holds the non-obvious constraints and the anti-patterns we have hit.
Add an entry when something surprises you. Do not add codebase overviews —
they cost context and dilute signal.

Agents should leave changes in the working tree rather than committing, so a human reviews the diff first.

## Licensing of contributions

By contributing you agree that your contribution is licensed under
[Apache 2.0](LICENSE) for code and [CC BY 4.0](LICENSE-CC-BY-4.0) for written material,
matching the rest of the repository.

Do not contribute code copied from GPL or AGPL sources, or data from sources that forbid reuse —
it would make the repository undonatable, which is a condition of the event it was built for.
