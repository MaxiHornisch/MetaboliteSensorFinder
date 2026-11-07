# Pipeline execution: bindPredict → PSICHIC → DiffDock

Status: plan, v1. No machines contacted, nothing installed.
Sources: `input/Agent_v1.txt`, `input/domain-metabolite-screener.md`, [02-ARCHITECTURE.md](02-ARCHITECTURE.md), [05-TOOLS-SETUP.md](05-TOOLS-SETUP.md), and the public README pages of the three tools (read 2026-11-07; not install-tested).
Where [04-EVALUATION.md](04-EVALUATION.md) conflicts with this document, it wins.

---

## 1. Decisions

| # | Decision | Reason |
|---|---|---|
| D1 | The LLM orchestrates; it does not compute. A Python runner executes stages 1–3. | Per-domain inference through an agent loop burns the token budget for no gain. |
| D2 | Each tool runs as a worker on its own host, behind one contract: `submit(manifest) → job_id`, `status(job_id)`, `fetch(job_id)`. | Lets each tool use its own environment (Python, torch, Docker) without conflicts. |
| D3 | Workers sit on a private network (Tailscale or WireGuard). No public ports. | Keeps inputs and checkpoints off the open internet. |
| D4 | Stage logic lives in this repo: `src/msf/channels/screening.py`, with the `screener` and `structuralist` agents. | Reuses the existing guards, schemas, and run-record layout. |
| D5 | Every score is stored. Filtering only sets an `advanced` flag. | Non-negotiable rule in both input files; prevents silent cherry-picking. |
| D6 | Nothing is committed unless asked. | [CLAUDE.md](../CLAUDE.md). |

---

## 2. What the tools actually do (from their public READMEs)

These facts change the plan. Each still needs verification on the host (phase 0).

**bindPredict** (`github.com/Rostlab/bindPredict`, the README calls the tool *bindEmbed21*)
- Predicts **per-residue** binding for three classes: metal ions, nucleic acids, and small molecules. It does **not** score a domain against a specific ligand.
- Inputs: protein sequences. ML path needs ProtT5 embeddings (generated with `bio_embeddings`, converted by a script in `utils/`). Homology path needs MMseqs2 and large pre-computed databases from an FTP server (sizes not stated).
- Dependencies: Python 3, numpy, scikit-learn, torch, pandas, h5py. Paths are set in `config.py`.
- Licence: MIT. No version tags on the page.
- **Consequence:** the input spec's "domain-level ligand-binding likelihood" is a *small-molecule binding-residue* signal. Stage 1 therefore filters domains by "binds small molecules at all", which is weaker than the spec assumes. The evaluation doc must state this, and the threshold must be calibrated, not assumed.

**PSICHIC** (`github.com/huankoh/PSICHIC`)
- Graph neural network scoring **protein sequence + ligand SMILES pairs**. Supports regression, binary, and three-class outputs. This matches Stage 2.
- Installs with conda or mamba. Environment files exist for macOS, Linux/Windows GPU, and Linux/Windows CPU. Then PyG wheels (torch 2.1.0, cu118 or cpu). Manual setup was tested on Python 3.8 with torch 2.0.0 and RDKit 2022.09.5.
- Pretrained weights in `trained_weights/` (`multitask_PSICHIC` referenced). A beta web server exists but is not officially associated with the paper, so do not use it for the pipeline.
- Licence: Apache-2.0. No version tags on the page.
- **Gap:** the page does not document the screening output columns. Phase 0 must read the output from a real run on the fixture pair before the contract is written.

**DiffDock** (`github.com/gcorso/DiffDock`; default model DiffDock-L)
- Inputs: protein `.pdb` (or sequence, folded with ESMFold), ligand SMILES or RDKit-readable file. Batch mode via CSV.
- Output: a confidence score for the top pose. Bands from the README: above 0 high, −1.5 to 0 moderate, below −1.5 low. Poses saved as `.sdf` only with `--save_visualisation`.
- Install: conda from `environment.yml`, or Docker (`rbgcsail/diffdock`). Docker is the practical route on Windows (see [05-TOOLS-SETUP.md](05-TOOLS-SETUP.md) §3.3).
- GPU recommended; CPU works for `.pdb` inputs. First run precomputes lookup tables (minutes). No VRAM figure published.
- Licence: MIT for code and weights. The original DiffDock paper version is at tag/commit `v1.0`.
- Does not predict affinity. Confidence is a pose-quality signal, not a binding measure.

---

## 3. Architecture

```
 orchestrator (Claude Code, Opus)     plans · dispatches · checks summaries · writes report
          │
 pipeline runner (Python, this repo)  batches · checkpoints runs/<id>/ · resumes · hashes
          │  HTTP over private network (D2, D3)
   ┌──────┼─────────────────┬──────────────────┐
   ▼      ▼                 ▼                  ▼
 bindPredict worker    PSICHIC worker     DiffDock worker
 (host A)              (host B, GPU)      (host C, GPU, Docker)
          │
 shared storage  (inputs, outputs, SHA-256 per file)
```

Structure step (AlphaFold DB fetch, domain location, trim, pLDDT and PAE within the pocket): runs on the runner or host C. It is a `structuralist` task, so it writes its verdict before any docking is allowed.

### Worker contract (all three)
- `GET /health` → tool name, pinned version, weights hash, GPU present.
- `POST /jobs` with a manifest: list of input items, each with `item_id` and `sha256`. Returns `job_id`.
- `GET /jobs/{id}` → `queued | running | done | failed`, with progress counts.
- `GET /jobs/{id}/results` → output table plus a checksum per file. The runner rejects any result whose checksum does not match.
- Idempotent: resubmitting the same manifest returns the same `job_id` and does not recompute.
- Fail closed: a malformed input is rejected with an error, never silently dropped.

---

## 4. Data contracts

- **Domain input:** `domain_id, uniprot, start, end, sequence_sha256`. `start`/`end` are 1-based, inclusive, in UniProt coordinates.
- **Ligand input:** `hmdb_id, inchikey, smiles`. HMDB data is CC BY-NC: ship IDs and a download script, not the data.
- **bindPredict out:** `domain_id, binds_small_molecule_score, per_residue_path, model_version, input_sha256`.
- **PSICHIC out:** `domain_id, hmdb_id, score, model_version, input_sha256`. Exact column names fixed in phase 0.
- **DiffDock out:** `domain_id, hmdb_id, confidence, confidence_band, rank, pose_path, trimmed_structure_sha256, plddt_domain, pae_pocket`.
- **Thresholds:** one config file, one line per stage, each with its cutoff, its calibration source, and the reason. Every report reproduces it.

---

## 5. Evaluation rules that apply here

- Report a score for every domain and pair. The `advanced` flag is the only filter.
- Calibrate stage thresholds on a held-out set of known binders and non-binders. Do not pick cutoffs by eye.
- Report the **recall** each stage keeps on the known positives. A funnel that drops true positives at stage 1 is invisible without this.
- DiffDock bands are a pose-quality signal, not affinity. Say so in every hit list.
- Flag borderline hits and any structure with low pLDDT or an ambiguous domain boundary.
- Negative control: shuffled ligand–domain pairs must not advance at the rate real pairs do.

---

## 6. Phases

Each phase ends with a written result in `JOURNAL.md`. No phase starts until the previous one passes.

**Phase 0: verify (no compute).** Read each tool's installation and output files from the repo, not the README alone. Pin the versions and record weight hashes. Confirm the PSICHIC output columns and the bindPredict output format. Confirm HMDB licence terms for the pipeline outputs.
Exit: a written verification note with the pinned versions and the three output schemas.

**Phase 1: workers.** One Dockerfile per tool with the FastAPI wrapper that implements the contract in §3. Test on a machine you choose; this plan does not pick one.
Exit: each worker passes `/health` and a fixture run.

**Phase 2: contract tests.** Fixtures: one known binding pair, one decoy pair, one malformed input. Assert the schema, repeat-run determinism, and fail-closed behaviour. Write these tests before the wrapper code (repo working style: failing test first).
Exit: all tests green on all three workers.

**Phase 3: pilot.** About 20 domains against a small ligand set. Record wall time and GPU-hours per domain.
Exit: a cost estimate and a recall figure for each stage on the known positives. **Sign-off required before scaling.**

**Phase 4: scale.** Batches of a few hundred. Checkpoint after each batch; retry a failed batch from its manifest; never recompute completed items.
Exit: full score table covering all domains and pairs.

**Phase 5: DiffDock on survivors.** Fetch AlphaFold DB model, locate domain, trim, dock, write the three deliverables: docked poses for good hits, the list of domain–ligand pairs in good DiffDock bands, and the full score table.
Exit: deliverables plus the threshold report.

---

## 7. Budget

- The $100 covers LLM tokens only. GPU host time is a separate cost and is not yet funded.
- Token rules: the orchestrator reads counts and summaries, never score tables or FASTA.
- Estimate GPU-hours from phase 3, not before.

---

## 8. Open items (blocking, need the user)

1. Which machines host workers A, B, C, and their GPUs and VRAM. Without this, phases 1 and 3 cannot be sized.
2. Whether cloud GPU hours are in scope.
3. Whether the pipeline runs as Claude Code subagents (recommended, matches the repo's guards and hooks) or as the Managed Agents config in `Agent_v1.txt`.
4. The known-positive and known-negative calibration set. The plan assumes the data is provided; the file and its schema are needed for phase 2.

---

## 9. Known uncertainties

- bindPredict's small-molecule signal is coarser than the input spec assumes (§2). Stage 1 may pass most domains; its value is unproven until calibrated.
- PSICHIC's screening output format is not documented on its page.
- DiffDock VRAM is unpublished.
- Windows vs WSL2 for each worker is unresolved. [05-TOOLS-SETUP.md](05-TOOLS-SETUP.md) §0 recommends WSL2 as the compute host.
