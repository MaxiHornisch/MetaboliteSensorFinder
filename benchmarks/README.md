# DeorphBench

The retrospective time-split benchmark for endogenous ligand assignment.
**The primary deliverable of this project** (see [ADR-0004](../docs/adr/0004-benchmark-is-the-deliverable.md)).

| File | Contents |
|---|---|
| [curation-protocol.md](curation-protocol.md) | How items are selected and dated. **Frozen** — changes need a MAJOR bump and a human decision |
| `curation-log.md` | A recorded decision for every candidate considered, including every exclusion and its reason. The audit trail |
| `deorphbench-<C>-<F>.parquet` | The items, for cutoff `C` and freeze date `F` |
| `splits/` | Cluster assignments. `dev` and `val` in the clear; `sealed` encrypted |
| `snapshot-manifest.yaml` | Every source release used, with SHA-256 and retrieval date |
| [UNSEAL-LOG.md](UNSEAL-LOG.md) | Appended to by `scripts/unseal.py`. Published, so test-set exposure is visible rather than trusted |

## Status

**Not built.** This directory currently holds the protocol only.
Building it is task `T-007`, blocked on the date-filter and snapshot machinery.

Whether strict inclusion criteria leave enough items to support any claim is **unknown**,
and is the project main open risk.

## The one thing to know

Items are dated by **earliest primary publication**, never by database release date.

A pairing first appearing in a later database release may have been published years earlier.
Dating by release lets proteins leak across the cutoff and inflates every downstream number —
in the direction of looking better, which is why it would never be caught by inspecting results.

## Using it

Reproduce the benchmark from the protocol:

```bash
python -m msf.curate --cutoff 2018-01-01 --freeze 2026-11-07
```

Verify a build someone else produced:

```bash
pytest -m controls -k "split or decoy or structure_cutoff"
```

## For people outside this project

The benchmark is CC BY 4.0 and is meant to be used by anyone, including people who think our method is wrong.
If you build a method against it, the splits and the curation protocol are the parts that matter;
our results are not a baseline you need to care about.

If a retrospective time-split deorphanization benchmark already exists and we missed it,
telling us is more valuable than anything in this directory.
