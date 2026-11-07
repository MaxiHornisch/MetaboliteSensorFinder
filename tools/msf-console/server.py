"""Deorphan console - a thin HTTP layer over the two sequence-based channels.

Each tool keeps its own virtualenv with its own incompatible torch pin, and is
invoked as a subprocess. Nothing is imported across the boundary. This mirrors
the msf-gateway shape in docs/02-ARCHITECTURE.md: the loop talks to tools, it
does not link them.

  bindPredict (torch 2.14.1+cpu) -> pocket channel, read from precomputed results
  PSICHIC     (torch 2.9.0+cpu)  -> interaction channel, run on demand

Run:  python3 server.py [port]
"""
import csv
import json
import random
import re
import statistics
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAB = ROOT.parent
BIND = LAB / "bindPredict-repo"
PSICHIC = LAB / "PSICHIC"

FASTA = BIND / "my_proteins.fasta"
POCKET_DIR = BIND / "results"
PSICHIC_PY = PSICHIC / ".venv" / "bin" / "python"
PSICHIC_WEIGHTS = "trained_weights/multitask_PSICHIC"

# Attached to every PSICHIC result. See PSICHIC/PROVENANCE.md.
PSICHIC_CONTAMINATION = {
    "contaminated": True,
    "leak": "L5c",
    "checkpoint": "multitask_PSICHIC",
    "training_cutoff": "2023-02-02",
    "driver": "Cortellis Drug Discovery pull of 2023-02-02",
    "note": "Training data postdates any 2015 or 2018 cutoff. Input filtering "
            "cannot repair this. Report outside the headline metric.",
}

POCKET_PROVENANCE = {
    "contaminated": None,
    "leak": "L5c unresolved",
    "model": "bindEmbed21DL (5-checkpoint ensemble)",
    "note": "Embeddings were generated on another machine and the ProtT5 "
            "revision is not pinned. Treat as dev-only until resolved.",
}

SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
AA = set("ACDEFGHIKLMNPQRSTVWY")


TRUTH_CSV = (LAB / "Metabolite_sensors_resources" / "results_human"
             / "human_chebi_interpro_domains.csv")
N_BACKGROUND = 30
_background = None


def background_panel():
    """Unrelated human domains, used to tell a high score from an ordinary one.

    Without this a raw affinity is unreadable: PSICHIC's mean for ATP across
    random proteins is ~6.4, so an ATP score of 5.97 is below average, not a hit.
    """
    global _background
    if _background is not None:
        return _background
    rows = list(csv.DictReader(TRUTH_CSV.open())) if TRUTH_CSV.exists() else []
    seen, pool = set(), []
    for r in rows:
        acc = r["uniprot_id"]
        seq = r["domain_sequence"].strip().upper()
        if acc in ("O15067", "O15247") or acc in seen:
            continue
        if not (60 <= len(seq) <= 400) or set(seq) - AA:
            continue
        seen.add(acc)
        pool.append(seq)
    random.Random(20261107).shuffle(pool)
    _background = pool[:N_BACKGROUND]
    return _background


def clean_sequence(raw):
    """Accept a bare sequence or a FASTA record; drop headers and whitespace."""
    lines = [l for l in raw.splitlines() if not l.startswith(">")]
    return re.sub(r"[^A-Za-z]", "", "".join(lines)).upper()


def read_fasta(path):
    seqs, name = {}, None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            name = line[1:].split()[0]
            seqs[name] = ""
        elif name:
            seqs[name] += line
    return seqs


def read_pocket(protein_id):
    """Parse one .bindPredict_out into per-residue reliability indices."""
    f = POCKET_DIR / f"{protein_id}.bindPredict_out"
    if not f.exists():
        return None
    rows = []
    with f.open() as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            rows.append({
                "pos": int(r["Position"]),
                "metal": float(r["Metal.RI"]),
                "nuc": float(r["Nuc.RI"]),
                "small": float(r["Small.RI"]),
                "metal_b": r["Metal.Class"].strip() == "b",
                "nuc_b": r["Nuc.Class"].strip() == "b",
                "small_b": r["Small.Class"].strip() == "b",
                "any_b": r["Any.Class"].strip() == "b",
            })
    return rows


def run_psichic(sequence, ligands, calibrate=False):
    """ligands: [{name, smiles}] -> [{name, smiles, affinity, agonist, ...}]

    With calibrate, each ligand is also scored against the background panel so
    the result can report a z-score and percentile alongside the raw number.
    """
    bg = background_panel() if calibrate else []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        infile = td / "screen.csv"
        outdir = td / "out"
        rows = [(f"row{i}", lig["smiles"], sequence) for i, lig in enumerate(ligands)]
        for i, lig in enumerate(ligands):
            for j, bseq in enumerate(bg):
                rows.append((f"bg{i}_{j}", lig["smiles"], bseq))
        with infile.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ID", "Ligand", "Protein"])
            w.writerows(rows)

        proc = subprocess.run(
            [str(PSICHIC_PY), "screening.py",
             "--device", "cpu",
             "--screenfile", str(infile),
             "--result_path", str(outdir),
             "--trained_model_path", PSICHIC_WEIGHTS,
             "--save_interpret", "False"],
            cwd=str(PSICHIC), capture_output=True, text=True, timeout=900,
        )
        result_csv = outdir / "screening.csv"
        if not result_csv.exists():
            tail = (proc.stderr or proc.stdout or "")[-1500:]
            raise RuntimeError(f"PSICHIC produced no output.\n{tail}")

        with result_csv.open() as fh:
            scored = list(csv.DictReader(fh))

        out = []
        for i, lig in enumerate(ligands):
            r = scored[i]
            rec = {
                "name": lig["name"],
                "smiles": lig["smiles"],
                "affinity": float(r["predicted_binding_affinity"]),
                "agonist": float(r["predicted_agonist"]),
                "antagonist": float(r["predicted_antagonist"]),
                "nonbinder": float(r["predicted_nonbinder"]),
            }
            if bg:
                base = len(ligands) + i * len(bg)
                vals = [float(scored[base + j]["predicted_binding_affinity"])
                        for j in range(len(bg))]
                mean = statistics.mean(vals)
                sd = statistics.pstdev(vals) or 1e-9
                below = sum(1 for v in vals if v < rec["affinity"])
                rec["background"] = {
                    "mean": mean, "sd": sd, "n": len(vals),
                    "z": (rec["affinity"] - mean) / sd,
                    "percentile": 100.0 * below / len(vals),
                }
            out.append(rec)
        return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "static"), **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/proteins":
            seqs = read_fasta(FASTA)
            return self._send({
                "proteins": [
                    {"id": k, "length": len(v), "sequence": v,
                     "has_pocket": (POCKET_DIR / f"{k}.bindPredict_out").exists()}
                    for k, v in seqs.items()
                ],
                "pocket_provenance": POCKET_PROVENANCE,
                "psichic_contamination": PSICHIC_CONTAMINATION,
            })

        if self.path.startswith("/api/pocket/"):
            pid = self.path.rsplit("/", 1)[-1]
            if not SAFE_ID.match(pid):
                return self._send({"error": "bad protein id"}, 400)
            rows = read_pocket(pid)
            if rows is None:
                return self._send({"error": f"no bindPredict result for {pid}"}, 404)
            seq = read_fasta(FASTA).get(pid, "")
            return self._send({
                "protein": pid, "sequence": seq, "residues": rows,
                "provenance": POCKET_PROVENANCE,
            })

        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/screen":
            return self._send({"error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")

            # Either a known candidate, or any sequence the user pastes. PSICHIC
            # needs no precomputed embedding, so it is not limited to the five
            # proteins the pocket channel can read.
            raw = (req.get("sequence") or "").strip()
            if raw:
                seq = clean_sequence(raw)
                bad = set(seq) - AA
                if bad:
                    return self._send(
                        {"error": "Not an amino acid sequence. Unexpected letters: "
                                  + ", ".join(sorted(bad))}, 400)
                if len(seq) < 20:
                    return self._send(
                        {"error": f"Sequence is {len(seq)} residues. PSICHIC needs at "
                                  "least 20."}, 400)
            else:
                seq = read_fasta(FASTA).get(req.get("protein_id", ""))
                if not seq:
                    return self._send({"error": "unknown protein"}, 400)
            ligands = [l for l in req.get("ligands", [])
                       if l.get("smiles", "").strip()]
            if not ligands:
                return self._send({"error": "no ligands given"}, 400)
            calibrate = bool(req.get("calibrate"))
            results = run_psichic(seq, ligands, calibrate=calibrate)
            return self._send({
                "protein": req.get("protein_id") or "pasted sequence",
                "length": len(seq),
                "results": results,
                "calibrated": calibrate,
                "background_n": len(background_panel()) if calibrate else 0,
                "contamination": PSICHIC_CONTAMINATION,
            })
        except Exception as e:  # surface the real reason to the UI
            return self._send({"error": str(e)}, 500)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8420
    for p, label in [(FASTA, "bindPredict FASTA"),
                     (POCKET_DIR, "bindPredict results"),
                     (PSICHIC_PY, "PSICHIC venv python")]:
        print(f"{'ok ' if p.exists() else 'MISSING'}  {label}: {p}")
    print(f"\nDeorphan console on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


main()
