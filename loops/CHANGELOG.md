# Loop changelog

Every loop version that was evaluated, **promoted or rejected**, with its numbers.

A changelog of rejections is the strongest available evidence that an evaluation is real.
A project whose every version was promoted did not have a gate.

Versioning policy and the promotion gate: [docs/07-VERSIONING.md](../docs/07-VERSIONING.md).

---

## v0.1.0-baseline — INCUMBENT (not yet evaluated)

`loops/v0.1.0-baseline.yaml`

Deliberately conservative starting point: five channels, classical docking with decoy-calibrated
z-scores, the full nine-attack battery, logistic fusion with isotonic calibration and
**no correlation discount** — the discount is absent by design, because it is the first proposed
change (`P-001`) and a baseline must not already contain the improvement it is meant to test.

Nothing here is tuned. A baseline tuned to look good makes every subsequent improvement unfalsifiable.

**Status:** no evaluation has been run. There is no number for this version yet.

---

<!-- Template. Record the outcome whether promoted or rejected.

## v<x.y.z>-<slug> — PROMOTED | REJECTED  (YYYY-MM-DD)

<one-line description of the change>

prereg: `sha256:...` · primary: `<metric>` · expected: <direction> <effect size>
run: `runs/<run-id>/` · split: sealed · unseal log entry: <n>

| Metric | Incumbent | Candidate | Δ (95% CI) |
|---|---|---|---|
| <primary> | | | |
| ece | | | |
| recall@10 | | | |
| false_confidence_rate | | | |

Controls: pass | FAIL (<which>)
Baselines beaten: popularity ✓ · nearest-neighbour ✓ · family prior ✓ · docking-only ✓ · co-folding ✓

**Decision.** <promoted or rejected, and against which gate criterion>

**What we learned.** <including what was real even if the version was rejected —
a rejected version often contains a genuine finding worth keeping>

**Kept / follow-up.** <what goes back into PROPOSALS.md>

-->
