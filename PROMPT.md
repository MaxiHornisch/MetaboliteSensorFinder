# Session prompt

Any new session can resume this project with:

```
/goal continue the goal described in PROMPT.md
```

---

## The goal

Build and evaluate `DeorphBench` — a retrospective, time-split benchmark for endogenous ligand assignment
to orphan human proteins — together with a multi-agent research loop measured against it.

The benchmark is the primary deliverable.
**An honest negative result for our own method, on a benchmark others can use, is a success.**
A good-looking number we cannot defend is a failure.

## Current state

Read in this order before doing anything:

1. `TASKS.md` — the prioritised task list. Take the top unblocked task.
2. `JOURNAL.md` — what has happened, what failed, and why. Read the last 5 entries at minimum.
3. `docs/04-EVALUATION.md` — the normative specification. If anything contradicts it, it wins.
4. `loops/CHANGELOG.md` — which loop versions were promoted and rejected, with numbers.

## How to work

- **Take the top unblocked task from `TASKS.md`.** Do it. Update the list. Then take the next.
- **Run every atomic step in its own subagent.** Agents are defined in `.claude/agents/`. Keep the main session for planning and review — do not let tool output fill it.
- **Write a failing test before implementing anything.** Then make it pass. The test is what makes the next `/goal` checkable.
- **Append every result, decision and exchange to `JOURNAL.md`** with the date and links to outputs. Including failures. Especially failures.
- **Keep this file current** so the next session can resume without you.
- **Leave changes in the working tree.** Do not commit unless explicitly asked.

## Standing constraints

These are not negotiable and the guards enforce them:

| | |
|---|---|
| **Controls before metrics** | Negative controls and physics regressions run first. A control failure aborts the run. Never relax a control to get past it |
| **Never tune on `sealed`** | It is encrypted. A human unseals it, once per loop version, logged |
| **Date filter is structural** | Enforced at the tool boundary, not by instruction. Any post-cutoff source reaching an agent is leak L1 and is a critical bug |
| **No raw docking score as a ranking signal** | Decoy-calibrated z-scores or percentiles only |
| **Two independent channels per hypothesis** | And check for `restatement` — channels sharing a template are one channel |
| **Abstention is a valid result** | `no evidence`, `no hypothesis` and `abstain` are first-class outputs, not failures |
| **Record rejections** | A rejected loop version goes in `loops/CHANGELOG.md` with its numbers |
| **`L0` never shares a session with `L1`/`L2`** | The curator may read post-cutoff data. Nothing that scores may |

## When you are stuck

Write it in `JOURNAL.md` and in the submission's "where it got stuck" section.
Dead ends are part of the deliverable — the event asks for them explicitly,
and the assessment rewards stating failures and limits.

Do not work around a blocker by weakening the evaluation.
If the honest path is blocked, record that the honest path is blocked.
