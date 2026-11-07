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
    import subprocess
    from pathlib import Path

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
    import subprocess
    from pathlib import Path

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
        import jsonschema
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


screen_app = typer.Typer(no_args_is_help=True, help="Domain-vs-ligand screen (docs/12, docs/13).")
app.add_typer(screen_app, name="screen")
_RUN_ROOT = "runs"


@screen_app.command("ingest")
def screen_ingest(
    input: str = typer.Option(..., help="Domain CSV, e.g. input/Test_sequences.csv."),
    run_root: str = typer.Option(_RUN_ROOT, help="Where run directories are written."),
) -> None:
    """Validate the CSV, write a manifest. Count-in equals count-out, nothing dropped."""
    from pathlib import Path

    from msf.screen.pipeline import cmd_ingest

    run_dir = cmd_ingest(Path(input), Path(run_root))
    typer.echo(f"manifest: {run_dir / 'manifest.json'}")


@screen_app.command("simulate")
def screen_simulate(
    input: str = typer.Option(..., help="Domain CSV. Truth is planted; scores are not evidence."),
    run_root: str = typer.Option(_RUN_ROOT, help="Where run directories are written."),
) -> None:
    """Loop S1: run the simulation suite on the ingested domains. No network."""
    from pathlib import Path

    from msf.screen.pipeline import cmd_simulate

    run_dir, results = cmd_simulate(Path(input), Path(run_root))
    for r in results:
        typer.echo(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['scenario']}: {r['detail']}")
    typer.echo(f"summary: {run_dir / 'simulation' / 'summary.json'}")
    raise SystemExit(0 if all(r["passed"] for r in results) else 1)


@screen_app.command("chain")
def screen_chain(
    input: str = typer.Option(..., help="Domain CSV. Simulated end to end; not evidence."),
    run_root: str = typer.Option(_RUN_ROOT, help="Where run directories are written."),
) -> None:
    """Simulated full chain: bindPredict, PSICHIC, DiffDock, evidence, hypotheses, dossiers."""
    import json
    from pathlib import Path

    from msf.screen.chain import run_chain
    from msf.screen.ingest import ingest
    from msf.screen.validate import validate_run

    result = ingest(Path(input))
    body = {"schema": "msf.screen.chain/v1", "input_sha256": result.file_sha256,
            "counts": result.counts, "label": "SIMULATION"}
    import hashlib
    run_id = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    run_dir = Path(run_root) / f"chain-{run_id}"
    # The run id covers the input only, so an old directory would be resumed and its stale
    # batches reused. This is a regenerable simulation directory, so rebuild it from scratch.
    import shutil

    # Rebuild only what the chain generates. Keep the agent outputs (metrics, falsification,
    # audit, report). Their inputs are deterministic, and the auditor re-checks them each run.
    keep = {"metrics", "falsification", "audit", "report.md"}
    if run_dir.exists():
        for child in run_dir.iterdir():
            if child.name in keep:
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    summary = run_chain(result.screened, run_dir)
    problems = validate_run(run_dir)
    typer.echo(json.dumps(summary["counts"], indent=2))
    typer.echo(f"calibration: {summary['calibration']}")
    typer.echo(f"controls: {summary['controls']}")
    typer.echo(f"validation problems: {len(problems)}")
    for p in problems[:20]:
        typer.echo(f"  {p}")
    typer.echo(f"run: {run_dir}")
    raise SystemExit(1 if problems else 0)


@screen_app.command("labels")
def screen_labels(
    input: str = typer.Option(..., help="Domain CSV to screen (Test_sequences.csv)."),
    binding: str = typer.Option(..., help="Binding table (metabolite_binding_sequences_human.csv)."),
    smiles: str = typer.Option(None, help="SMILES workbook (.xlsx). Needs the `data` extra."),
    run_root: str = typer.Option(_RUN_ROOT, help="Where the labelled set is written."),
) -> None:
    """Match known binders to screened domains (exact span only). Labels are undated."""
    import json
    from pathlib import Path

    from msf.screen.ingest import ingest
    from msf.screen.labels import load_labels, smiles_coverage, write_labels

    result = ingest(Path(input))
    report = load_labels(Path(binding), result.screened)
    out = write_labels(report, Path(run_root) / "labels")
    typer.echo(f"labelled domains: {report.matched_domains}  pairs: {len(report.labels)}  "
               f"ligands: {report.ligands}  protein-only rows (no exact span): {report.protein_only}")
    typer.echo(f"labels: {out}")
    if smiles:
        names = {x["chebi"]: x["ligand_name"] for x in report.labels}
        cov = smiles_coverage(Path(smiles), names)
        typer.echo(json.dumps(cov, indent=2))


@screen_app.command("run")
def screen_run(
    input: str = typer.Option(..., help="Domain CSV."),
    run_root: str = typer.Option(_RUN_ROOT, help="Where run directories are written."),
) -> None:
    """Real workers. Not configured: raises NotImplementedError naming the blocker."""
    from pathlib import Path

    from msf.screen.pipeline import cmd_run

    cmd_run(Path(input), Path(run_root))


if __name__ == "__main__":
    app()
