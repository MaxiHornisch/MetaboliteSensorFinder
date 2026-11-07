# Tests

Three tiers with different jobs.
All are written **before** the code they test —
a passing test is a condition a `/goal` can check without a human.

| Directory | Job | When it runs |
|---|---|---|
| `unit/` | Schemas, parsers, metric implementations, loopspec validation | Every commit |
| `physics/` | Does the scientific stack actually work? Redocking, affinity correlation, units, determinism | Every commit; gates `L2` |
| `controls/` | Negative controls and leakage controls. **A control that passes is a bug** | Gates `L2`; aborts the run on failure |

## The ordering rule

`L2` runs `physics/` and `controls/` **before** it computes a single benchmark metric,
and aborts if either fails.

A benchmark number computed on a broken pipeline is worse than no number, because it will be believed.

Aborting is the loop working correctly.
Modifying anything under `controls/` during an `L2` run is a hard error enforced by a guard hook,
not a judgement call.

## Expected failures are declared, not hidden

Some tests are marked `xfail` with a reason.
`test_chirality_sensitivity` is expected to fail for classical docking configurations,
and that matters for a metabolome full of stereoisomers.

Known limitations are encoded as expected failures so they stay visible in the test report
rather than being omitted and forgotten.
An `xfail` that starts passing is also a signal and should be investigated, not simply unmarked.

The stubs currently in this directory are `xfail` because they are **unimplemented**, not because they
are expected to fail scientifically. The two cases are distinguished by the `reason` string:
a task ID (`T-0NN not implemented`) versus a scientific explanation.

## Running

```bash
pytest                      # everything
pytest -m controls          # the controls that gate L2
pytest -m physics           # the scientific-stack regressions
pytest -m "not slow"        # skip anything needing GPU or network
```

## Fixtures

`tests/fixtures/` holds the fixed 30-complex redocking set and hand-written schema examples,
including deliberately malformed ones.
Fixtures are the only structure files committed to this repository — see
[docs/06-DATA-SOURCES.md](../docs/06-DATA-SOURCES.md) for why.
