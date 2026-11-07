# ADR-0002: Enforce every leakage control in a hook, not a prompt

Status: accepted
Date: 2026-11-07

## Context

The evaluation depends on a set of invariants that must hold across hours of autonomous work:
no post-cutoff source reaches an evidence channel; no live database is queried during a benchmark run;
the sealed split is never read; controls are never modified to make them pass;
the benchmark is never edited to improve a score.

The obvious way to establish these is to write them in the agent instructions.
That does not work over long runs. An instruction competes with every other instruction and with the
agent's drive to make progress, and the moment a blocker appears, routing around it looks like
problem-solving rather than cheating. None of these violations announces itself in the output —
and all of them make results look *better*.

## Decision

Every invariant is enforced by `scripts/guard.py`, wired as `PreToolUse` and `PostToolUse` hooks,
or by an MCP wrapper that refuses the call. The agent instructions describe the invariants so the
agent understands *why* a call failed, but the instructions are not the enforcement.

Correspondingly, tool access is restricted per agent: the `falsifier` cannot write hypotheses,
the `auditor` is read-only everywhere, and `scripts/unseal.py` is unreachable from inside any agent.

## Alternatives rejected

**Prompt-level instruction only.** The default, and the thing we are rejecting.
Cheap, readable, and unreliable in exactly the cases that matter.
It also leaves no audit trail: there is no record of a rule that was simply not followed.

**Post-hoc detection.** Run freely, then check the trace for violations.
Catches violations after the compute is spent, and cannot catch a violation that corrupted a cached
artifact reused by later runs. Useful as a second layer; insufficient as the first.

**Human review of every run.** Does not survive contact with an overnight loop, and the volume of
tool calls makes it theatre.

**Separate sandboxed environments per loop** (true network isolation for benchmark runs).
Strictly better than hooks and genuinely correct. Rejected for now on cost: it needs container
infrastructure we do not have in a day. **Recorded as the preferred eventual answer** —
hooks are the affordable approximation, not the ideal.

## Consequences

**Cost — guards can be wrong, and a wrong guard blocks real work.**
Mitigated by making every refusal explain which rule it hit, and by instructing agents to record a
disputed guard in `JOURNAL.md` rather than disabling it.

**Cost — the guards are themselves code that can have bugs**, and a guard that silently fails open is
worse than no guard, because it is trusted. `tests/controls/` tests the guards, not just the pipeline.

**Cost — some legitimate exploratory work is blocked** during benchmark mode and has to be done in a
separate session. This is the intended trade and it is also why `L0` and `L1`/`L2` are forbidden from
sharing a session.

**Benefit.** The invariants hold without discipline, and a reader can verify *that they hold* by reading
`scripts/guard.py` and `.claude/settings.json` — a few hundred lines — rather than by trusting that
thousands of agent turns each followed an instruction.
That auditability is the point.
