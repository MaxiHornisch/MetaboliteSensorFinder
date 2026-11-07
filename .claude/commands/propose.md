---
description: Run loop L3 - take the top loop-change proposal, pre-register it, evaluate, promote or reject.
argument-hint: "[proposal-id]"
---

Run the improvement loop (`L3`) on $ARGUMENTS, or on the top-ranked proposal in `loops/PROPOSALS.md`.

Follow [docs/03-LOOPS.md](../../docs/03-LOOPS.md) §L3:

1. Express the proposal as a **loopspec diff** — a concrete change to the YAML, not a prose intention.
2. **Write `prereg/<version>.yaml` naming the metric and the expected effect size, before running anything.** Without this, you will find some metric that moved and report that one. Hash it into the run manifest.
3. `/evaluate <version> --split dev`. **If the effect is absent (CI includes zero), stop.** Record it and move on. Most proposals die here, cheaply, and that is what preserves the sealed split.
4. Only if it survives `dev`: `--split val` to fit weights, thresholds and calibration.
5. Only if it still looks good: stop and ask the human to unseal. You cannot do this yourself.
6. Apply the promotion gate ([docs/04-EVALUATION.md](../../docs/04-EVALUATION.md) §8).
7. Record the outcome in `loops/CHANGELOG.md` **whether promoted or rejected**, with the numbers and the pre-registration hash.

You may not write to `benchmarks/`. Improving a score by changing the benchmark rather than the method
is failure mode A6; the guard will refuse the write.

Exit when the proposal has a recorded decision in `loops/CHANGELOG.md` with its metric delta and CI.
