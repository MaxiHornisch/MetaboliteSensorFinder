---
description: Run loop L2 - controls, then ablations, then the benchmark, then the report.
argument-hint: "<loop-version> [--split dev|val|sealed]"
---

Run the evaluation loop (`L2`) for $ARGUMENTS. Default split: `dev`.

Follow [docs/03-LOOPS.md](../../docs/03-LOOPS.md) §L2. The ordering is not negotiable:

1. `scripts/doctor.py` green; snapshot manifest hashes verified.
2. **Physics regressions** (`pytest tests/physics`). Any failure → **abort**.
3. **Negative controls** (`pytest tests/controls`). Any control producing confident answers → **abort** and open a bug task in `TASKS.md`.
4. Contamination probe over all items; assign bins.
5. `L1` over every benchmark item, seeded from the run ID.
6. All five baselines on the identical item set.
7. Ablations.
8. `statistician` for metrics per stratum and per contamination bin, with bootstrap CIs and a paired comparison to the incumbent.
9. Render the report.

**Aborting at step 2 or 3 is this loop working correctly.** Never relax a control to get past it.

If the split is `sealed`: stop and tell the human. You cannot unseal it; `scripts/unseal.py` requires
an interactive human key and the attempt is logged.

Exit when `metrics/summary.json` validates, `controls_passed` is true, every pre-registered metric has
a CI, and the report contains the popularity baseline column.
