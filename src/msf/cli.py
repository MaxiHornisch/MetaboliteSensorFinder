"""Command-line entry point. Declared as `msf` in pyproject.toml.

Thin by design: every subcommand delegates to a module that can also be driven directly
by an agent. The CLI exists so a human can reproduce anything an agent did, from a run
record, without going through Claude Code.

    msf doctor                        tool readiness per tier
    msf curate --cutoff 2018-01-01    build DeorphBench (loop L0)
    msf run --loop <spec> --target Q9HC97     one target  (loop L1)
    msf evaluate --loop <spec> --split dev    score a version (loop L2)
    msf compare <run-a> <run-b>       paired diff between two runs
    msf validate                      schema-check the repo

Unimplemented subcommands raise NotImplementedError naming the task that would implement
them. They are not silently no-ops: a command that appears to succeed while doing nothing
is the failure this project exists to avoid.
"""

from __future__ import annotations

import sys

try:
    import typer
except ImportError:  # keep `msf --help` honest on a bare machine
    print(
        "msf: typer is not installed. Run `uv sync`, then `python scripts/doctor.py`.",
        file=sys.stderr,
    )
    raise SystemExit(69)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="MetaboliteSensorFinder: endogenous ligand assignment, and the benchmark that scores it.",
)


@app.command()
def doctor(tier: int = typer.Option(0, help="Highest setup tier to check (0, 1 or 2).")) -> None:
    """Check tool readiness. Run this before believing any result."""
    from pathlib import Path
    import subprocess

    script = Path(__file__).resolve().parents[2] / "scripts" / "doctor.py"
    raise SystemExit(subprocess.call([sys.executable, str(script), "--tier", str(tier)]))


@app.command()
def curate(
    cutoff: str = typer.Option(..., help="Evidence cutoff date, ISO-8601, e.g. 2018-01-01."),
    freeze: str = typer.Option(..., help="Ground-truth freeze date."),
) -> None:
    """Build DeorphBench (loop L0).

    The only command permitted to read post-cutoff data. It must never run in a session
    that also scores a loop version.
    """
    from msf.curate import build_benchmark

    build_benchmark(cutoff=cutoff, freeze=freeze)


@app.command()
def run(
    loop: str = typer.Option(..., help="Path to a loopspec YAML."),
    target: str = typer.Option(..., help="UniProt accession."),
    cutoff: str = typer.Option(None, help="Benchmark mode. Omit for discovery mode."),
    run_id: str = typer.Option(None, help="Reuse a run id to reproduce a recorded result."),
) -> None:
    """Run the target loop on one protein (loop L1)."""
    from msf.run import run_target

    run_target(loop=loop, target=target, cutoff=cutoff, run_id=run_id)


@app.command()
def evaluate(
    loop: str = typer.Option(..., help="Path to a loopspec YAML."),
    split: str = typer.Option("dev", help="dev | val | sealed."),
) -> None:
    """Score a loop version against DeorphBench (loop L2).

    Runs physics regressions and negative controls FIRST and aborts if either fails.
    A benchmark number computed on a broken pipeline is worse than no number.
    """
    from msf.run import evaluate_loop

    evaluate_loop(loop=loop, split=split)


@app.command()
def compare(run_a: str, run_b: str) -> None:
    """Paired comparison between two runs on identical items."""
    from pathlib import Path
    import subprocess

    script = Path(__file__).resolve().parents[2] / "scripts" / "compare_runs.py"
    raise SystemExit(subprocess.call([sys.executable, str(script), run_a, run_b]))


@app.command()
def validate() -> None:
    """Schema-check loopspecs and any artifacts on disk. Cheap; run it often."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    failures = 0
    for schema in (root / "loops" / "loopspec.schema.json",
                   root / "src" / "msf" / "schemas" / "artifacts.schema.json"):
        try:
            json.loads(schema.read_text(encoding="utf-8"))
            typer.echo(f"  ok    {schema.relative_to(root)}")
        except (OSError, json.JSONDecodeError) as exc:
            typer.echo(f"  FAIL  {schema.relative_to(root)}: {exc}")
            failures += 1

    try:
        import jsonschema  # noqa: F401
        import yaml
    except ImportError:
        typer.echo("  skip  loopspec validation (jsonschema/pyyaml not installed)")
        raise SystemExit(1 if failures else 0)

    import jsonschema
    spec_schema = json.loads((root / "loops" / "loopspec.schema.json").read_text(encoding="utf-8"))
    for spec in sorted((root / "loops").glob("v*.yaml")):
        try:
            jsonschema.validate(yaml.safe_load(spec.read_text(encoding="utf-8")), spec_schema)
            typer.echo(f"  ok    {spec.relative_to(root)}")
        except Exception as exc:  # noqa: BLE001 - report every failure, do not stop at the first
            typer.echo(f"  FAIL  {spec.relative_to(root)}: {exc}")
            failures += 1

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    app()
