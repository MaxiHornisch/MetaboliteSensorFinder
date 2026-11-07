# Run ledger

One line per run. Artifacts live in object storage / DVC; this file carries the hashes
so a result can always be traced back to the exact configuration that produced it.

Append-only. Never edit a row.

| run_id | date | loop_version | split | primary metric (CI) | controls | commit |
|---|---|---|---|---|---|---|
| *(no runs yet)* | | | | | | |

**Columns.**
`primary metric` is whatever the run's pre-registration named — always with its confidence interval,
never a bare point estimate.
`controls` is `pass` / `FAIL`; a run whose controls failed has no valid metrics and the metric column
must read `n/a`, not a number.

Reproduce any row with:

```bash
git checkout <commit>
uv sync --locked
python scripts/fetch_snapshot.py --manifest <from manifest.yaml>
python -m msf.run --loop loops/<loop_version>.yaml --split <split> --run-id <run_id>
python scripts/compare_runs.py <run_id> runs/INDEX.md
```
