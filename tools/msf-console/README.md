# Deorphan console

A local UI over the two sequence-based evidence channels, `P-007` and `P-008`.

```bash
python3 msf-console/server.py 8420
```

Then open <http://127.0.0.1:8420>. Needs only the Python standard library — the heavy
dependencies live in the tool venvs, not here.

## How it connects

```
          browser
             │  fetch
             ▼
   server.py (stdlib http.server, 127.0.0.1 only)
             │
      ┌──────┴───────────────────┐
      │                          │ subprocess
      ▼                          ▼
 bindPredict-repo/          PSICHIC/.venv/bin/python
 results/*.bindPredict_out    screening.py --device cpu
 (read from disk)             (run per request, ~9 s)
   torch 2.14.1+cpu             torch 2.9.0+cpu
```

**Nothing is imported across the boundary.** Each tool is a subprocess in its own venv,
because their torch pins are mutually incompatible: PSICHIC needs `torch_scatter`, whose
wheels stop at torch 2.9.0, while bindPredict runs 2.14.1. This is also the shape the
`msf-gateway` MCP server wants, so these two handlers port over directly.

## API

| | |
|---|---|
| `GET /api/proteins` | candidates, lengths, sequences, provenance for both channels |
| `GET /api/pocket/<id>` | per-residue Metal/Nuc/Small reliability indices and class calls |
| `POST /api/screen` | `{ligands:[{name, smiles}], protein_id}` or `{ligands, sequence}` → affinity + agonist/antagonist/non-binder |

`POST /api/screen` takes **either** a candidate id **or** a raw sequence, because PSICHIC needs
no precomputed embedding. A bare sequence or a pasted FASTA record both work; headers and
whitespace are stripped and non-amino-acid letters are rejected. Every response carries the
contamination block, so a caller cannot read a score without its warrant.

## The asymmetry between the two channels

The pocket channel reads a precomputed ProtT5 embedding, so it only works for the five
candidates in `my_proteins.fasta`. The interaction channel has no such limit. The UI lets you
paste any sequence and says plainly that the binding map will be empty for it, rather than
hiding the second channel behind the first channel's constraint.

## What the interface refuses to do

These are deliberate, and follow `MetaboliteSensorFinder/docs/04-EVALUATION.md`.

- **No pass/fail badge against a fixed threshold.** The prior architecture gated on
  `affinity ≥ 7.5`; the evaluation doc rejects fixed thresholds because docking-like scores
  track molecular weight. The UI shows the number and the control, never a verdict.
- **Affinity bars span the run's own range, not zero.** A zero-anchored bar implies these raw
  scores carry ratio meaning and invites cross-molecule comparison, which is the anti-pattern
  named in `CLAUDE.md`.
- **The residue scale diverges rather than running on the index alone.** The reliability index
  measures confidence in the *call*, so a confidently non-binding residue scores as high as a
  confidently binding one. Colouring on the index would paint most of a protein dark and read as
  though it all binds. Saturated means binds, pale means does not, depth is confidence.
- **PSICHIC's training cutoff stays on screen** as `trained to 2023-02-02` beside the channel
  heading. The checkpoint postdates any 2015 or 2018 cutoff (leak `L5c`); the full reasoning is
  in `PSICHIC/PROVENANCE.md`.
- **Methane is seeded as a negative control and cannot be removed.** Every run reports whether
  it scored below all real ligands.

## Known gaps

- `GET /api/pocket` reads precomputed bindPredict output. Embedding a *new* protein needs a
  ProtT5 run, which is not wired in; only the 5 sequences in `my_proteins.fasta` resolve.
- A pasted sequence is not persisted. Reload and it is gone.
- No date filtering is enforced anywhere here, so the header reads `cutoff: none enforced`.
  This is a `dev` instrument. It must not serve a scored benchmark run.
- No run record is written. Results are not yet reproducible from the UI.
