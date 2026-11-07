# Web application specification

Status: specification, v1.
Derived from [../../docs/08-RESEARCHER-UX.md](../../docs/08-RESEARCHER-UX.md), which is the normative statement of *what* the surface must do and why.
This document is *how*.
Data contracts are fixed by [../../docs/02-ARCHITECTURE.md §4](../../docs/02-ARCHITECTURE.md); every metric named here comes from [../../docs/04-EVALUATION.md](../../docs/04-EVALUATION.md) and none are invented.

Every chart and colour decision in §7 was produced by following the `dataviz` skill procedure (form → colour job → run the validator → marks → interaction → accessibility pass), and the validator output is reproduced verbatim.

---

## 1. Architecture

### 1.1 Static-first, and why

**The deployed artifact is a directory of files.**
A backend is a development convenience and an optional deployment, never a requirement.

The reasoning is the project's own honesty commitment, not a hosting preference:

- **A claim that needs a live server to check is not checkable.**
  [08-RESEARCHER-UX.md §9](../../docs/08-RESEARCHER-UX.md) forbids requiring the network to verify a claim.
  If the explorer is static, the explorer *is* a bundle — the same guarantee as `dossier.html`, at run scale.
- **The project will die, and the evidence should not.**
  A hackathon-born service has a hosting lifetime measured in months.
  A `gh-pages` branch, a Zenodo deposit and a `.tar.zst` outlive it.
- **Reviewers want a URL within five minutes** ([§3.3](../../docs/08-RESEARCHER-UX.md)).
  GitHub Pages needs no credentials, no cold start, no rate limit, no secret.
- **Run records are immutable.**
  [02-ARCHITECTURE.md §6](../../docs/02-ARCHITECTURE.md) makes `runs/<run-id>/` write-once.
  Immutable inputs plus read-only queries is precisely the case where a server adds latency and no capability.
- **One write, and it degrades cleanly.**
  The only mutation in the whole design is `register this prediction`, which becomes a downloadable YAML stub in static mode.

What we give up, stated plainly: no server-side search over full text, no on-demand re-query, bundle size grows with the number of targets, and `/compare` must be pre-computed for the version pairs we care about rather than any arbitrary pair.
All acceptable; none of them touch the verification path.

### 1.2 Three modes, one codebase

```
                       runs/<run-id>/   (immutable, DVC/object store)
                              │
                     msf web ingest  ──────────────┐
                              │                    │
                   web/data/msf.duckdb             │  (Parquet views, zero copy)
                              │                    │
            ┌─────────────────┴─────────────────┐  │
            │                                   │  │
   MODE A: dev / local             MODE B: static export
   FastAPI (uvicorn)               msf web export → web/data/api/**/*.json
   DuckDB queries live             Next.js `output: "export"`
   HMR, full search                → web/out/  → GitHub Pages
            │                                   │
            └──────────── same React app, same fetch paths ─────────┘
                              │
                     MODE C: hosted read-only
                     the Mode A server behind a CDN, for teams with many runs
```

The React app never knows which mode it is in.
It fetches `/api/...`; in Mode B those paths resolve to files on disk, written by the exporter to match the API byte-for-byte.
`tests/web/test_export_parity.py` asserts exactly that: for every endpoint and every fixture run, `GET /api/x` and `web/data/api/x/index.json` are identical JSON.

### 1.3 Technology choices

| Choice | Reason | Rejected alternative |
|---|---|---|
| **DuckDB over Parquet** | Already the project's analytics substrate ([02-ARCHITECTURE.md §8](../../docs/02-ARCHITECTURE.md)); queries `runs/**/*.parquet` in place with no load step; single-file, no service | Postgres — an operational dependency for read-only immutable data |
| **FastAPI** | Thin typed read layer; Pydantic models generated from the same JSON Schemas the agents validate against, so the API cannot drift from the contracts; `/openapi.json` for free | Flask (no typing), writing DuckDB queries in the front end (couples UI to storage layout) |
| **Next.js (App Router) + React, `output: "export"`** | One codebase for all three modes; file-system routing matches the permalink ladder one-to-one; static export is a config flag, not a rewrite | Vite SPA — needs hand-rolled routing to produce real per-dossier URLs; SSR — contradicts static-first |
| **Mol\*** | The field's viewer; reads `.cif`/`.pdb`/`.sdf` directly; handles pLDDT colouring and selections; MIT licensed; works fully client-side | NGL (less maintained), a server-rendered image (kills residue selection, which is the point) |
| **Recharts + a thin SVG layer** | Recharts for line/bar/dot forms; hand-written SVG for the dumbbell and segmented bar, which are faster to write correctly than to coerce | D3 from scratch (slow for a hackathon), Plotly (bundle weight, its defaults violate half of §7) |
| **No client-side state library** | Every view is a function of the URL; the URL is the state | Redux/Zustand for a read-only app |
| **Parquet → JSON at export time, not at request time** | Export is the chance to enforce the refusals in §4.4 once, in one place | Shaping in the component |

---

## 2. Data loading

### 2.1 From run records to the app

`msf web ingest` reads `runs/<run-id>/` and registers DuckDB views.
It copies nothing it does not have to; Parquet is read in place.

| Run-record path | DuckDB view | Notes |
|---|---|---|
| `manifest.yaml` | `runs` | YAML → one row; `run_id` is the content hash |
| `inputs/targets.parquet` | `run_targets` | the resolved item set — what `/compare` pairs on |
| `evidence/<channel>/*.json` | `evidence` | normalised to `evidence.parquet` on first ingest, partitioned by `channel`; the envelope is flat, `claim` stays as a JSON column |
| `hypotheses/*.json` | `hypotheses` | `supporting_evidence` / `refuting_evidence` as `LIST(VARCHAR)` |
| `falsification/*.attacks.json` | `attacks` | one row per attack, including `killed` |
| `dossier/*.json` | `dossiers` | the full `TargetDossier`, plus extracted columns for `p`, CI, abstention |
| `metrics/*.json` | `metrics`, `controls`, `ablations`, `calibration_bins`, `risk_coverage` | one view per metric family; no pooling happens here |
| `audit/findings.json` | `audit` | claim → `evidence_id` → verdict |
| `trace.jsonl` | `trace` | cost and turn counts only; **not exposed by the read API** |
| `artifacts/INDEX.tsv` | `artifacts` | `sha256` is the primary key, globally, across runs |

Two derived tables are computed at ingest, not at request time:

- `evidence_edges` — the back-edges for [L5](../../docs/08-RESEARCHER-UX.md) (`evidence_id` → citing hypotheses, using attacks).
- `staleness` — current state per `(run_id, acc)`, written by the L4 watch loop into `runs/INDEX.md`'s sidecar and joined here.

Artifacts are content-addressed.
The same structure file referenced by four runs is stored once under `web/public/artifact/<sha256>/<filename>`, which is what makes a multi-run export tractable.

### 2.2 The static export pipeline

```
$ msf web ingest  --runs runs/ --out web/data/msf.duckdb
$ msf web export  --db web/data/msf.duckdb --out web/data/api --artifacts web/public/artifact
$ cd web && npm run build          # next build, output: "export"  → web/out/
$ msf web verify  --out web/out    # parity, dead links, size budget, a11y smoke
```

`msf web export` walks a declarative route table — the same table the FastAPI router is generated from — and writes one `index.json` per endpoint:

```
web/data/api/
├── runs/index.json
├── runs/c8f2a1e/manifest/index.json
├── runs/c8f2a1e/leaderboard/index.json
├── runs/c8f2a1e/leaderboard/stratum/gpcr/index.json
├── runs/c8f2a1e/dossier/Q9HC97/index.json
├── runs/c8f2a1e/metrics/summary/index.json
├── runs/c8f2a1e/metrics/risk-coverage/index.json
├── runs/c8f2a1e/metrics/reliability/index.json
├── runs/c8f2a1e/metrics/controls/index.json
├── runs/c8f2a1e/metrics/ablations/index.json
├── hypotheses/hyp_4d91c2/index.json
├── evidence/ev_0c4b81/index.json
├── artifacts/4e07c2…/index.json          # metadata only; bytes live in web/public/artifact/
├── compare/v0.3.0..v0.3.1/index.json     # only pre-computed pairs
├── search/index.json                     # a flat index, see §4.3
└── staleness/index.json
```

`msf web verify` fails the build on any of:

- an `index.json` whose shape does not match the generated OpenAPI schema;
- a `locator` or artifact link that resolves to nothing (no dead ends — [L0–L6](../../docs/08-RESEARCHER-UX.md));
- a metric payload that violates a §4.4 refusal (pooled without strata, point estimate without CI, metrics present on a run with `controls_passed == false`);
- total `web/out/` size over the budget (default 500 MB; artifacts above the per-file cap go to `OMITTED.tsv` with a retrieval URI);
- an axe-core violation on the fixture pages.

### 2.3 Bundle generation

`msf dossier bundle --run c8f2a1e --target Q9HC97 --out dist/` emits the layout in [08-RESEARCHER-UX.md §2.1](../../docs/08-RESEARCHER-UX.md).
It shares the renderer with the web app: `dossier.html` is the same React tree rendered to a single file with `renderToStaticMarkup`, data inlined as a `<script type="application/json">`, CSS inlined, and a hydration script that only adds sorting, the coverage slider and residue highlighting.
`tests/web/test_dossier_html_offline.py` asserts zero request-initiating external references.

---

## 3. Pages

Routes map one-to-one onto the drill-down ladder.
Wireframes are at roughly 96 columns; accessions are illustrative.

### P0 · `/` — Run index (ladder L0)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Metabolite Sensor Finder            runs   method   abstentions (14)   compare      [☀/☾]    │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  Nothing in this repository is wet-lab validated. Every number below is retrospective.       │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  [ split: all ▾ ]  [ loop version: all ▾ ]  [ controls: all ▾ ]        ← one filter row      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  RUN        VERSION   SPLIT   DATE        TARGETS  CONTROLS      PREREG   DECISION           │
│  c8f2a1e    v0.3.1    val     2026-11-05       61  ✓ passed      9ab31f…  promoted           │
│  7d02b4c    v0.3.0    val     2026-10-28       61  ✓ passed      11c7ad…  rejected: baseline │
│  3fa9910    v0.2.4    dev     2026-10-21       34  ✗ FAILED      —        —                  │
│             └ metrics withheld — sham-pocket control produced confident answers  ▸ details   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

A failed-control run shows no metrics at all, only the reason and a link.

### P1 · `/leaderboard?run=<id>` — Targets (ladder L1)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ run c8f2a1e · v0.3.1 · val · controls ✓ · snapshot snap-2018-01-01-b7d4        [download ⤓]  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ [ family: all ▾ ] [ ligand class: all ▾ ] [ contamination: all ▾ ] [ date conf: ≥medium ▾ ]  │
│ sort: ⦿ accession  ○ p(correct)          ← accession is the default, deliberately            │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ TARGET            HYP  TOP p  95% CI        STATE        CONTAM  STRATUM      CHANNELS       │
│ Q9HC97  GPR35       4   0.41  0.22–0.58     ⊘ abstain    partial GPCR/org.ac. L─S─C─X─G─H    │
│ Q99679  GPR21       2   0.19  0.06–0.37     ⊘ abstain    clean   GPCR/lipid   L──C─X──H     │
│ O00270  GPR31       3   0.67  0.48–0.81     ▶ test       clean   GPCR/lipid   L─S─C─X─G─H    │
│                                                                                              │
│ CHANNELS  L literature · S structure · C chemistry · X screening · G genetics · H homology   │
│           a dash means the channel returned no evidence; hover or focus gives the reason     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ 61 targets · 14 abstentions (23%) · per-stratum metrics ▸ /method#strata                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

The `CHANNELS` column is six fixed labelled slots, letter plus filled/empty glyph — never six colours (§7.4).

### P2 · `/target/<acc>?run=<id>` — Dossier (ladder L2)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ‹ leaderboard          Q9HC97 · GPR35 · orphan at 2018-01-01        [bundle ⤓] [cite] [u ↑]  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ ⚠ stale:literature since 2026-10-02 — doi:10.1234/xyz touches hyp_4d91c2.                    │
│   Numbers below are unchanged. Affected evidence: ev_7f2a19.            ▸ what this means     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  NO CONFIDENT LIGAND                                                                         │
│  Pre-registered threshold p ≥ 0.60 to recommend a test. Top hypothesis p = 0.41.             │
│  4 hypotheses generated · 3 killed in falsification · 1 survived below threshold             │
│  Reason: 3 of 6 channels returned evidence; the two strongest share template 6QZH            │
│          and are discounted by 0.31.                                                         │
│                                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ WHAT WOULD CHANGE OUR MIND ─────────────────────────────────────────────────────────────┐ │
│ │ … layout as specified in docs/08-RESEARCHER-UX.md §6 …                                   │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ CONFIDENCE                                 │ EVIDENCE MATRIX                                 │
│ p(correct) 0.41   95% BCa CI 0.22–0.58     │ literature   7 items   5 support  2 refute   ▸  │
│ isotonic on `val`, 61 in fitting set       │ structure    3 items   3 support  0 refute   ▸  │
│ calibration bin 5/10 (n = 7)               │ chemistry    2 items   2 support  0 refute   ▸  │
│ ≈ 4 of every 10 hypotheses scored like     │ screening    1 item    1 support  0 refute   ▸  │
│   this one turn out correct                │ genetics     — no evidence · no mQTL within    │
│                                            │                500 kb at p<5e-8 (GTEx v8)    ▸  │
│ ▸ risk–coverage curve for this run         │ homology     — no evidence · nearest assigned  │
│ ▸ reliability diagram                      │                neighbour 18% id in pocket    ▸  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ HYPOTHESES                                                                                   │
│ 1  kynurenic acid       CHEBI:18344   p 0.41 [0.22–0.58]  9 attacked · 7✓ 1~ 1?        ▸    │
│ 2  5-hydroxyindoleacetate CHEBI:27823 p 0.17 [0.05–0.34]  9 attacked · 6✓ 2~ 1✗        ▸    │
│ 3  2-oleoyl-LPA         CHEBI:52333   killed in falsification (abundance check)        ▸    │
│ 4  cromolyn             —             killed — not endogenous; out of scope            ▸    │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ CHANNEL CONTRIBUTION (after correlation adjustment)        ▸ table view                       │
│ literature  ████████████████████ 0.38                                                        │
│ structure   ███████████ 0.21                                                                 │
│ screening   ███████ 0.13   ← discounted 0.31 for shared template 6QZH with `structure`       │
│ chemistry   ████ 0.08                                                                        │
│ genetics    (no evidence)                                                                    │
│ homology    (no evidence)                                                                    │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ PROVENANCE  run c8f2a1e · v0.3.1 · prereg 9ab31f… · snapshot snap-2018-01-01-b7d4            │
│             dossier sha256 4e07c2… · auditor: 0 unsupported claims          ▸ full record     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### P3 · `/target/<acc>/hypothesis/<hyp_id>` — Hypothesis (ladder L3)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ‹ Q9HC97      hyp_4d91c2 · kynurenic acid · CHEBI:18344            [cite] [verify] [u ↑]     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ You arrived from: "kynurenic acid is the top hypothesis for GPR35, p = 0.41"                  │
│                   docs/… → dossier.md:41                                     ▸ in context     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  [2D depiction]   InChIKey HCZHHEIFKROPDY-UHFFFAOYSA-N                                        │
│                   prior_speculation: TRUE — speculated pre-cutoff in PMID … (2014) ▸         │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ MECHANISM                                                                                     │
│ The pocket is lined with [R6.58] and [K7.32]; a carboxylate-bearing aromatic acid is          │
│ geometrically and electrostatically complementary … (residue chips link to structure)         │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ CLAIM LEDGER                                                                                  │
│ CLAIM                                   RESTS ON               AUDITOR   WHAT THIS DOES NOT SAY│
│ pocket is cationic at pH 7.4            ev_0c4b81              ✓ re-derived  not that it binds│
│ ligand ranks 3/1000 vs matched decoys   ev_4ab912              ✓ re-derived  not an affinity  │
│ co-expressed in colonic epithelium      ev_7f2a19              ✓ re-derived  not causal       │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ SUPPORTING (9)                           │ REFUTING (2)                                       │
│ ev_0c4b81 structure  0.72  2017-06-02 ▸  │ ev_c19d40 literature 0.55 2016-04-11  reports      │
│ ev_4ab912 screening  0.61  2026-11-05 ▸  │           this pairing as negative             ▸   │
│ …                                        │ ev_ff2093 genetics   0.30 2015-01-20            ▸  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ FALSIFICATION  9 attacks · 7 survived · 1 weakened · 1 unresolved          ▸ full record       │
│ ? promiscuity-check   UNRESOLVED at round bound — top 5% against 31/200 unrelated proteins ▸  │
│ ~ template-dependence WEAKENED — score drops 0.41→0.26 without template 6QZH               ▸  │
│ ✓ decoy-substitution  survived — best matched decoy ranks 47/1000                          ▸  │
│ ✓ pocket-ablation     survived — R6.58A abolishes the pose                                 ▸  │
│ ✗ (none killed)                                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### P4 · `/target/<acc>/channel/<channel>` — Channel (ladder L4)

Leads with the gate verdict, then the channel's calibration note, then the item table.
For `screening` the first element is the decoy distribution; the raw score is not on this page at all.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ‹ Q9HC97      channel: screening                                                   [u ↑]     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ GATE  pocket verdict: USABLE — P2Rank score 0.61 ≥ 0.35; mean pLDDT in pocket 84.2           │
│       docking was permitted because this verdict passed                            ▸ ev_0c4b81│
│ NOTE  `strength` is channel-local and calibrated per channel. A 0.61 here is not              │
│       comparable to a 0.61 in `genetics`.                                                     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ RANK AGAINST 1,000 PROPERTY-MATCHED DECOYS            ▸ table view   ▸ decoy property match   │
│                                                                                               │
│  count  ▏                      ▃▆█▇▅▃▂                                                        │
│         ▏                   ▁▃█████████▅▃▁                     ◆ kynurenic acid               │
│         ▏ ◆             ▁▂▅███████████████▆▄▂▁                   rank 3 / 1000                │
│         └──┴────────────┴──────────────────────┴──────────────────────────────────            │
│            better                 decoy score distribution              worse                 │
│                                                                                               │
│  The x-axis is the scoring function's output. It is NOT an affinity and is NOT               │
│  comparable across targets.                                                                   │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ ITEMS                                                                                         │
│ ID         CLAIM                           DIR     STR   SOURCE DATE  REPRO  LOCATOR          │
│ ev_4ab912  ranks 3/1000 vs matched decoys   supports 0.61 2026-11-05   yes   poses/…sdf  ▸    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### P5 · `/evidence/<evidence_id>` — EvidenceItem (ladder L5)

Field-by-field render of the envelope, nothing summarised, `source_date` and `retrieved` adjacent and labelled, plus the back-edges.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ev_0c4b81   channel: structure   target: Q9HC97                        [cite] [verify] [u ↑] │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ claim        {"type":"pocket_charge","pocket_id":"p1","net_formal_charge":+2,                 │
│               "residues":["R6.58","K7.32"],"ph":7.4}                                          │
│              → "pocket p1 carries net +2 formal charge at pH 7.4"                             │
│ direction    supports            strength  0.72  (structure-local calibration)                │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ PROVENANCE                                                                                    │
│ source       P2Rank 2.4.1 over AlphaFold DB model AF-Q9HC97-F1-model_v4                       │
│ snapshot     snap-2018-01-01-b7d4        ▸ which releases, and their dates                    │
│ source_date  2017-06-02     ← the date of the FACT; this is what the time filter uses        │
│ retrieved    2026-11-05     ← when we fetched it; NOT used by the time filter                │
│ locator      artifacts/pockets/p2rank-Q9HC97.csv#L14                                   ▸     │
│ tool_version 2.4.1          container sha256:9f1c…                                            │
│ command      p2rank predict -f AF-Q9HC97-F1-model_v4.cif -o pockets/ --threads 4       [copy] │
│ reproducible true                                                                             │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ USED BY      hyp_4d91c2 (supporting) · hyp_9b07ae (supporting)                                │
│              attack pocket-ablation on hyp_4d91c2                                             │
│              ⚠ 2 of 4 hypotheses on this target rest on this one item                         │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### P6 · `/artifact/<sha256>` — Raw artifact and command (ladder L6)

The bytes, rendered where renderable, with the cited row highlighted and addressable at `#L14`.
Shows sha256, size, mime, producing agent, full command, input and output hashes, exit code, wall clock.
`[copy] msf verify ev_0c4b81` re-runs the step and diffs the output hash.
This page has no outbound drill links — it is the floor.

### P7 · `/method?run=<id>` — Is the method trustworthy

Ordered to mirror [03-LOOPS.md §L2](../../docs/03-LOOPS.md): controls, then physics, then leakage, then contamination, then pipeline-vs-loop, then ablations, then calibration, then — last — ranking.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ #controls  #physics  #leakage  #contamination  #ablations  #calibration  #strata  #ranking    │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ NEGATIVE CONTROLS — run before any metric below is believed                                   │
│ ✓ pass  scrambled-sequence    no confident hypothesis (0/12 at p>0.5)                    ▸    │
│ ✓ pass  shuffled-pairs        recovery at chance (recall@10 0.02, CI 0.00–0.07)          ▸    │
│ ✓ pass  sham-pocket           indistinguishable from random molecules (KS p = 0.41)      ▸    │
│ ✓ pass  mirror-protein        scores differ from native (known failure NOT triggered)    ▸    │
│ ✓ pass  designed-void         abstained on 8/8                                           ▸    │
│ ✓ pass  true-orphan-hold      confidence distribution resembles controls, not positives  ▸    │
│                                                                                               │
│   true-orphan-hold is the informative one: if the loop is as confident on genuine orphans      │
│   as on solved cases, its confidence is meaningless.         ▸ overlaid distributions          │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ FALSE-CONFIDENCE RATE  0.04  (CI 0.01–0.11)   pre-registered target < 0.10   ✓               │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ CONTAMINATION — faceted, never pooled                                                         │
│   clean (n=23)           partial (n=27)          contaminated (n=11)                          │
│   [ recall@10 panel ]    [ recall@10 panel ]     [ recall@10 panel ]                          │
│   ← HEADLINE                                                                                  │
│                                                                                               │
│ PIPELINE vs LOOP, by bin — is it reasoning or recalling?                      ▸ table view     │
│   clean:        pipeline 0.21 [0.08–0.37]   loop 0.26 [0.12–0.43]   Δ +0.05 (CI −0.09–0.19)  │
│   partial:      pipeline 0.23 [0.10–0.39]   loop 0.44 [0.27–0.61]   Δ +0.21 (CI  0.04–0.38)  │
│   contaminated: pipeline 0.18 [0.03–0.41]   loop 0.73 [0.47–0.91]   Δ +0.55 (CI  0.28–0.77)  │
│   ⚠ the gap grows with contamination. Read the `clean` column only.                           │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ CALIBRATION  ECE 0.08 [0.04–0.14] · Brier 0.19 [0.15–0.24]                                    │
│              selective accuracy @20% coverage  0.58 [0.39–0.74]   ← pre-registered headline   │
│              [ reliability diagram, bin n printed ]  [ risk–coverage curve + popularity ]      │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### P8 · `/compare?a=<v>&b=<v>&split=<s>` — Version diff

Guard first, then the promotion-gate checklist, then the dumbbell, then per-stratum rank movement, then the dossier-level diff, then the changelog including rejections.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ v0.3.0 → v0.3.1 on val · 61 items shared · paired bootstrap, 10,000 resamples                 │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ PROMOTION GATE                                                     ▸ 04-EVALUATION.md §8      │
│ ✓ all negative controls pass            ✓ all physics regressions pass                        │
│ ✓ false-confidence rate 0.04 < 0.10     ✓ beats popularity (Δ +0.14, CI 0.03–0.26)            │
│ ✓ beats nearest-neighbour · family-prior · docking-only · co-folding-only                     │
│ ✓ primary metric improves: sel.acc@20% +0.07 (paired CI 0.01–0.13, excludes zero)             │
│ ──────────────────────────────────────────────────────────────────────────────                │
│ PROMOTED                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ PER-TARGET MOVEMENT   44 unchanged · 11 improved · 6 worsened          ▸ table view            │
│ O00270  0.48 ●───────────────▶● 0.67                                                          │
│ Q9HC97  0.33 ●─────────▶● 0.41                                                                │
│ Q99679  0.31 ●◀──────● 0.19                                                                   │
│ … 44 targets unchanged (|Δp| < 0.02)  ▾                                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ DOSSIER DIFF  Q9HC97 ▾                                                                        │
│ + claims added (1)     − claims removed (0)                                                   │
│ ! claims whose evidence changed but whose text did not (1)  ← inspect this one                │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

If the item sets differ, the body is replaced by the symmetric difference and a refusal, and `/api/diff` returns `409`.

### P9 · `/abstentions?run=<id>` — Where the loop said no

Same table as P1, filtered to abstentions, with the reason column expanded and grouped by reason class (`channels empty`, `below threshold`, `all hypotheses killed`, `no usable pocket`).
Linked from the primary navigation with its count, because an abstention view behind a filter is an abstention view nobody opens.

### P10 · `/provenance/<run_id>` — The full record

`manifest.yaml` rendered: loop version, prereg hash and content, snapshot manifest with every database release and its date, seeds, model ids, tool versions, container digests, git commit, env lock hash, the `/goal` invocation, the unseal-log entry if `sealed` was in scope, and `tests/controls/test_determinism.py`'s verdict plus the list of tools the manifest records as non-deterministic.

### P11 · `/structure/<acc>?run=<id>` — Mol\* viewer

Not a separate destination so much as a focusable panel reachable from P2/P3/P4.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ POCKET VERDICT: USABLE — P2Rank 0.61 ≥ 0.35 · mean pocket pLDDT 84.2 · PAE max 6.1 Å     ▸    │
│ This model is a prediction, not a structure. Pose shown is a docking result, not a measurement.│
├─────────────────────────────────────────────┬────────────────────────────────────────────────┤
│                                             │ REPRESENTATION                                 │
│            [ Mol* canvas ]                  │ ⦿ pLDDT (AlphaFold convention)                 │
│                                             │ ○ pocket residues    ○ conservation            │
│        pose hyp_4d91c2-top1.sdf             │ ☐ show PAE-masked regions as translucent       │
│                                             │ RESIDUES  [R6.58] [K7.32] [Y3.33]              │
│                                             │ ⤓ pose .sdf   ⤓ model .cif   ▸ ev_0c4b81       │
└─────────────────────────────────────────────┴────────────────────────────────────────────────┘
```

The verdict banner is rendered by the same component as the viewer and cannot be dismissed: a pose is never shown without its pocket verdict.
If the verdict was `no usable pocket`, the canvas is replaced by the reason and the pose controls are absent, not disabled.

---

## 4. The read API

Generated from the JSON Schemas in `src/msf/schemas/`, so the API cannot drift from the contracts in [02-ARCHITECTURE.md §4](../../docs/02-ARCHITECTURE.md).
All responses are `application/json`, immutable, `Cache-Control: public, max-age=31536000, immutable` (every path is content- or run-addressed).

### 4.1 Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/runs` | run ledger; metrics suppressed where `controls_passed == false` |
| `GET` | `/api/runs/{run_id}/manifest` | the full provenance record |
| `GET` | `/api/runs/{run_id}/leaderboard` | per-target rows; `?family=&ligand_class=&contamination=&date_confidence=&abstained=` |
| `GET` | `/api/runs/{run_id}/dossier/{acc}` | the complete `TargetDossier` |
| `GET` | `/api/runs/{run_id}/dossier/{acc}/bundle` | `302` to the `.tar.zst` |
| `GET` | `/api/hypotheses/{hypothesis_id}` | `Hypothesis` + claim ledger + falsification record |
| `GET` | `/api/hypotheses/{hypothesis_id}/falsification` | the attack battery, including killed and not-attempted |
| `GET` | `/api/evidence/{evidence_id}` | `EvidenceItem` envelope + back-edges |
| `GET` | `/api/runs/{run_id}/targets/{acc}/channels/{channel}` | channel items, gate verdict, calibration note, empty-state reason |
| `GET` | `/api/artifacts/{sha256}` | artifact metadata + command record |
| `GET` | `/artifact/{sha256}/{filename}` | the bytes (static file, not JSON) |
| `GET` | `/api/runs/{run_id}/metrics/summary` | pre-registered metrics, per stratum, with CIs |
| `GET` | `/api/runs/{run_id}/metrics/risk-coverage` | the curve plus the popularity baseline curve |
| `GET` | `/api/runs/{run_id}/metrics/reliability` | 10 equal-mass bins with counts, ECE, Brier |
| `GET` | `/api/runs/{run_id}/metrics/controls` | negative controls and physics regressions |
| `GET` | `/api/runs/{run_id}/metrics/ablations` | contribution table incl. the required popularity column |
| `GET` | `/api/runs/{run_id}/metrics/contamination` | per-bin metrics, never pooled |
| `GET` | `/api/diff?a=<run|version>&b=<run|version>&split=<s>` | paired comparison, or `409` |
| `GET` | `/api/staleness` | state per `(run_id, acc)` |
| `GET` | `/api/citation/{run_id}/{acc}[?hypothesis=&evidence=]` | citation strings + BibTeX + `CITATION.cff` |
| `GET` | `/api/search?q=` | flat index (Mode A full-text; Mode B prefix over a pre-built index) |
| `POST` | `/api/predictions` | register a prediction — the only write; **absent in Mode B** |

### 4.2 Example responses

`GET /api/evidence/ev_0c4b81` — the envelope exactly as [02-ARCHITECTURE.md §4.1](../../docs/02-ARCHITECTURE.md) defines it, plus back-edges:

```json
{
  "evidence_id": "ev_0c4b81",
  "channel": "structure",
  "target": "Q9HC97",
  "claim": {
    "type": "pocket_charge",
    "pocket_id": "p1",
    "net_formal_charge": 2,
    "residues": ["R6.58", "K7.32"],
    "ph": 7.4
  },
  "claim_prose": "pocket p1 carries net +2 formal charge at pH 7.4",
  "direction": "supports",
  "strength": 0.72,
  "strength_scope": "structure-local; not comparable across channels",
  "provenance": {
    "source": "P2Rank over AlphaFold DB AF-Q9HC97-F1-model_v4",
    "snapshot": "snap-2018-01-01-b7d4",
    "retrieved": "2026-11-05T09:14:02Z",
    "source_date": "2017-06-02",
    "locator": "artifacts/pockets/p2rank-Q9HC97.csv#L14",
    "tool_version": "2.4.1",
    "command": "p2rank predict -f AF-Q9HC97-F1-model_v4.cif -o pockets/ --threads 4"
  },
  "reproducible": true,
  "artifact_sha256": "4e07c2a1b93f55d0e7c2118a44fe9a6b3c0d81f27ab5e4d9c6071fa2b8e3d415",
  "used_by": {
    "hypotheses": [
      {"hypothesis_id": "hyp_4d91c2", "role": "supporting"},
      {"hypothesis_id": "hyp_9b07ae", "role": "supporting"}
    ],
    "attacks": [{"hypothesis_id": "hyp_4d91c2", "attack": "pocket-ablation"}]
  },
  "verify_command": "msf verify ev_0c4b81"
}
```

`GET /api/hypotheses/hyp_4d91c2`:

```json
{
  "hypothesis_id": "hyp_4d91c2",
  "target": "Q9HC97",
  "ligand": {"chebi": "CHEBI:18344", "inchikey": "HCZHHEIFKROPDY-UHFFFAOYSA-N", "name": "kynurenic acid"},
  "mechanism": "The orthosteric pocket is lined with R6.58 and K7.32; a carboxylate-bearing aromatic acid is complementary in both geometry and electrostatics.",
  "mechanism_residues": ["R6.58", "K7.32", "Y3.33"],
  "supporting_evidence": ["ev_0c4b81", "ev_4ab912", "ev_7f2a19"],
  "refuting_evidence": ["ev_c19d40", "ev_ff2093"],
  "independent_non_llm_channels": ["structure", "screening", "literature"],
  "prior_speculation": true,
  "prior_speculation_source": {"pmid": "25…", "year": 2014},
  "calibrated": {
    "p_correct": 0.41,
    "ci": [0.22, 0.58],
    "ci_method": "BCa bootstrap, 10000 resamples",
    "calibrator": "isotonic",
    "fitted_on": "val",
    "fitting_set_n": 61,
    "calibration_bin": {"index": 5, "of": 10, "n": 7, "empirical_rate": 0.43}
  },
  "abstained": true,
  "abstention_threshold": 0.60,
  "falsification": {
    "attempts": [
      {"attack": "promiscuity-check", "outcome": "weakened", "resolved": false,
       "round_bound_hit": true,
       "detail": "top 5% against 31/200 unrelated proteins",
       "evidence": ["ev_2b77e1"], "artifacts": ["9c13…"]},
      {"attack": "template-dependence", "outcome": "weakened", "resolved": true,
       "detail": "p drops 0.41 to 0.26 when template 6QZH is removed",
       "evidence": ["ev_58aa02"], "artifacts": ["aa41…"]},
      {"attack": "decoy-substitution", "outcome": "survived",
       "detail": "best property-matched decoy ranks 47/1000",
       "evidence": ["ev_4ab912"], "artifacts": ["7f90…"]}
    ],
    "attempted": 9, "survived": 7, "weakened": 1, "killed": 0, "unresolved": 1,
    "not_attempted": []
  },
  "claim_ledger": [
    {"claim": "pocket is cationic at pH 7.4", "rests_on": ["ev_0c4b81"],
     "auditor": "re-derived", "does_not_say": "that the ligand binds"},
    {"claim": "ligand ranks 3/1000 against property-matched decoys", "rests_on": ["ev_4ab912"],
     "auditor": "re-derived", "does_not_say": "an affinity, or a cross-target comparison"}
  ]
}
```

`GET /api/runs/c8f2a1e/metrics/risk-coverage`:

```json
{
  "run_id": "c8f2a1e",
  "split": "val",
  "controls_passed": true,
  "headline": {"metric": "selective_accuracy@20%_coverage", "value": 0.58, "ci": [0.39, 0.74],
               "preregistered": true, "prereg_sha256": "9ab31f…"},
  "n_hypotheses": 61,
  "series": [
    {"name": "loop v0.3.1", "points": [
      {"coverage": 0.10, "n_selected": 6,  "selective_accuracy": 0.67, "ci": [0.30, 0.93]},
      {"coverage": 0.20, "n_selected": 12, "selective_accuracy": 0.58, "ci": [0.39, 0.74]},
      {"coverage": 0.50, "n_selected": 31, "selective_accuracy": 0.35, "ci": [0.24, 0.48]},
      {"coverage": 1.00, "n_selected": 61, "selective_accuracy": 0.26, "ci": [0.18, 0.36]}
    ]},
    {"name": "popularity baseline", "required": true, "points": [
      {"coverage": 0.10, "n_selected": 6,  "selective_accuracy": 0.33, "ci": [0.08, 0.70]},
      {"coverage": 0.20, "n_selected": 12, "selective_accuracy": 0.25, "ci": [0.09, 0.49]},
      {"coverage": 0.50, "n_selected": 31, "selective_accuracy": 0.19, "ci": [0.10, 0.32]},
      {"coverage": 1.00, "n_selected": 61, "selective_accuracy": 0.16, "ci": [0.09, 0.26]}
    ]}
  ],
  "strata": {"by": ["family", "ligand_class", "contamination_bin"], "href": "/api/runs/c8f2a1e/metrics/summary"},
  "caveat": "Retrospective. Selective accuracy on val is not a prediction about your assay."
}
```

`GET /api/runs/3fa9910/metrics/summary` — a run whose controls failed:

```json
{
  "run_id": "3fa9910",
  "controls_passed": false,
  "metrics": null,
  "withheld_reason": "sham-pocket control produced confident answers (4/8 at p>0.5)",
  "withheld_policy": "04-EVALUATION.md §0 principle 3; 03-LOOPS.md L2 step 3",
  "controls_href": "/api/runs/3fa9910/metrics/controls"
}
```

`GET /api/diff?a=v0.3.1&b=v0.2.4&split=val` — item sets differ:

```json
{
  "error": "unpaired_comparison_refused",
  "status": 409,
  "reason": "Paired bootstrap requires an identical item set (04-EVALUATION.md §7).",
  "a_only": ["Q8NGZ5", "P0DMS8"],
  "b_only": [],
  "shared": 34,
  "remedy": "Re-run v0.2.4 over the v0.3.1 item set, or compare on the 34 shared items explicitly via &items=shared"
}
```

### 4.3 Search

Mode A: DuckDB full-text over gene symbols, accessions, ligand names, ChEBI ids, mechanism text.
Mode B: a pre-built flat index (`search/index.json`, one row per target and per ligand, ~200 KB for 10³ targets) with client-side prefix matching.
Search never ranks by confidence.

### 4.4 Refusals the API enforces

The API is where the honesty commitments become mechanical.
Each returns an error rather than a degraded payload, and `msf web verify` fails the build if an exported file violates one.

| Refusal | Status |
|---|---|
| A metric requested from a run with `controls_passed == false` | `200` with `metrics: null` and a reason (above) |
| A pooled ranking metric with no strata breakdown | `422` — the shape does not exist |
| A point estimate requested without a CI | `422` |
| An unpaired version comparison | `409` |
| An ablation table without the popularity baseline column | `500` — it is a server bug, not a client error |
| A raw docking score requested as a ranking field | `422`; it is available only on the artifact endpoint, flagged `ranking_signal: false` |
| A `sealed`-split metric with no unseal-log entry | `409` |
| `POST /api/predictions` in static mode | `405` with the YAML stub in the body |

---

## 5. Component inventory

Real names, grouped by layer.
Primitives are presentational; containers fetch.

### 5.1 Verification primitives

| Component | Responsibility |
|---|---|
| `<ProvenanceChip id= kind= />` | renders any `run_id` / `evidence_id` / `hypothesis_id` / `sha256` as a monospace link to its level |
| `<VerifyButton evidenceId= />` | opens the command drawer; copies `msf verify <id>` |
| `<CommandBlock command= toolVersion= digest= seed= inputs= outputs= exit= />` | the reproducibility block, copyable |
| `<ClaimLedger rows= />` | claim → evidence → auditor verdict → "what this does not say" |
| `<SourceDateField source= retrieved= />` | renders the two dates adjacently and labelled; never one without the other |
| `<CitationBlock scope= />` | citation string + BibTeX + `CITATION.cff`, staleness folded in |
| `<ArtifactViewer sha= highlight= />` | mime-dispatched render with line anchors |
| `<BundleDownload runId= acc= size= />` | the `.tar.zst` plus its `MANIFEST.sha256` |

### 5.2 Uncertainty primitives

| Component | Responsibility |
|---|---|
| `<CalibratedProbability p= ci= calibrator= fittedOn= bin= />` | the four-part render ([§5.1](../../docs/08-RESEARCHER-UX.md)); throws in dev if `ci` is missing |
| `<IntervalText value= ci= digits={2} />` | the only way a number with an interval is printed |
| `<AbstentionCard threshold= reason= counts= />` | abstention as content |
| `<EmptyChannelCard reason= query= snapshot= />` | `no evidence` |
| `<GateBlockedCard gate= verdict= />` | `not run` |
| `<StrataBanner pooled= perStratum= />` | the standing pooled warning |
| `<ContaminationFacets bins= headline="clean" />` | three panels, n in each title, small-n sentence |
| `<SmallNNotice n= threshold={10} />` | writes the sentence instead of implying a measurement |
| `<DenominatorPercent num= den= />` | `31% (19/61)` |

### 5.3 Charts (specs in §7)

`<RiskCoverageCurve>` · `<ReliabilityDiagram>` · `<DecoyDistribution>` · `<ChannelContributionBars>` · `<VersionDumbbell>` · `<ConfidenceOverlay>` · `<PipelineVsLoopFacets>` · `<ContaminationCompositionBar>` · `<EvidenceHeatGrid>` · `<StatTile>` · `<HeroFigure>` · `<ChartFrame>` (title, subtitle, legend, table-twin toggle, texture toggle, caption) · `<TableTwin>` (every chart's WCAG-clean equivalent).

### 5.4 Structure

`<MolstarViewer>` · `<PocketVerdictBanner>` (non-dismissable; the viewer will not mount without it) · `<ResidueChip>` · `<RepresentationControls>` · `<PoseDownload>` · `<Static2DDepiction>` (RDKit-rendered SVG, used in bundles and as the `<noscript>` fallback).

### 5.5 Navigation and chrome

`<LadderBreadcrumb>` · `<UpOneLevel>` (binds `u`) · `<SiblingPager>` (binds `[`/`]`) · `<KeyboardSheet>` (binds `?`) · `<FilterRow>` (one row, above everything it scopes) · `<StalenessBanner>` · `<NotValidatedNotice>` (site-wide, in the header, not the footer) · `<ThemeToggle>` · `<A11ySettings>` (texture, reduced motion, table-first).

### 5.6 What deliberately does not exist

`<ConfidenceGauge>`, `<ScoreBadge>`, `<StarRating>`, `<TrendArrow>`, `<DockingScoreHeatmap>`, `<HeroPoseRender>`, `<AnimatedCounter>`.
Named here so that a future contributor reads the refusal rather than inventing the component.

---

## 6. Accessibility

Target: **WCAG 2.2 AA**, verified by `axe-core` in `msf web verify` and by manual keyboard and screen-reader passes on P2, P3 and P5 — the verification path.

- **Keyboard.** The whole ladder is reachable and operable without a pointer. `u`, `[`, `]`, `v`, `?` are documented in `<KeyboardSheet>` and do not shadow browser defaults. Visible focus rings everywhere, 3:1 against the surface. Skip-to-content on every page.
- **Screen readers.** Every chart carries an accessible name, a one-sentence `aria-describedby` summary of what it shows, and a `<TableTwin>` with real `<th scope>`. Charts are `role="img"` with the summary; the table is the data. Live regions are used only for the coverage slider's sentence output.
- **No colour-alone encoding, anywhere** (§7.4). This is the critical one: confidence is the thing being communicated.
- **Motion.** `prefers-reduced-motion: reduce` disables the only two transitions in the app (drawer open, tooltip fade). No value ever animates.
- **Forced colours.** `forced-colors: active` switches every chart to the texture channel plus `CanvasText`/`Canvas`; no chart loses information.
- **Zoom and reflow.** 400% zoom with no horizontal scroll at 320 CSS px; wireframe tables collapse to stacked definition lists.
- **Text.** Minimum 14px for data tables, 16px body; `tabular-nums` in table columns and axis ticks only, proportional figures on stat tiles and the hero figure.
- **JavaScript off.** P2 and P3 render fully from the server/exported HTML. Only sorting, the slider and Mol\* require JS, and each degrades to a stated fallback rather than an empty box.
- **The bundle is the final accessibility fallback.** Anyone who cannot use the app at all can read `dossier.md`.

---

## 7. Charts and colour

Produced by following the `dataviz` skill procedure in order.
Colour was chosen **last**, and the palette was **validated with the script, not by eye**.

The palette below is the skill's brand-neutral reference instance (`references/palette.md`).
It is a placeholder: substitute project hues and **re-run the validator against the project's own surfaces** before changing a single hex.

### 7.1 Form, chosen before colour

| What the reader must do | Form | Colour job | Component |
|---|---|---|---|
| Plan a testing budget against accuracy | line, 2 series (loop, popularity baseline), crosshair tooltip | categorical, 2 slots | `<RiskCoverageCurve>` |
| See whether stated probabilities match outcomes | dot plot vs an identity hairline, per-bin n printed | 1 series → **no legend box** | `<ReliabilityDiagram>` |
| See how a ligand ranks against its decoys | histogram with **emphasis**: one accent mark for the ligand, the distribution in de-emphasis gray | 1 hue + gray | `<DecoyDistribution>` |
| Compare channel contributions | ranked horizontal bars, largest first, **one hue** | sequential, single slot | `<ChannelContributionBars>` |
| See before → after per target | dumbbell, one hue in two shades | 1 hue, 2 shades | `<VersionDumbbell>` |
| Compare two confidence distributions | 2 overlaid density lines, both direct-labelled | categorical, 2 slots | `<ConfidenceOverlay>` |
| Compare pipeline vs loop across bins | **small multiples**, 3 facets, 2 bars each | categorical, 2 slots | `<PipelineVsLoopFacets>` |
| See how the benchmark splits across contamination bins | **tall segmented bar**, 3 ordered parts, legend of names | ordinal ramp | `<ContaminationCompositionBar>` |
| Scan which channels fired across many targets | heat grid, cells encode item **count** | sequential, 1 hue, with scale legend | `<EvidenceHeatGrid>` |
| Read one headline number | **hero figure** (one per view) and a KPI row of stat tiles | none | `<HeroFigure>`, `<StatTile>` |

Deliberately **not** charts:

- The per-target channel strip on the leaderboard is six labelled letter slots with filled/empty glyphs, not six colours and not a heat strip. Nominal categories do not get a value ramp.
- Falsification outcomes are a glyph plus a word in text ink. See §7.5.
- Anything from [08-RESEARCHER-UX.md §5.8](../../docs/08-RESEARCHER-UX.md) — no docking-score heatmap, no gauge, no smoothed reliability curve.

### 7.2 The validated palette

Categorical use never exceeds **three** concurrent series anywhere in this app, which is exactly the all-pairs-safe cap.
Slots are assigned in fixed order and **follow the entity, never its rank** — filtering a series never repaints the survivors.

| Slot | Role in this app | Light | Dark |
|---|---|---|---|
| 1 | the loop / the current version / the measured series | `#2a78d6` | `#3987e5` |
| 2 | the baseline / the incumbent version / the comparison | `#eb6834` | `#d95926` |
| 3 | a third series, used only in `<ConfidenceOverlay>` | `#1baf7a` | `#199e70` |

Sequential (magnitude: channel contribution, evidence counts), single hue, light → dark, `#cde2fb` → `#0d366b`.
Ordinal (ordered bins: `clean` / `partial` / `contaminated`), light `#86b6ef` · `#2a78d6` · `#104281`; dark `#cde2fb` · `#3987e5` · `#184f95`.
Diverging (only in `<VersionDumbbell>`'s Δ column): blue ↔ red with a **gray** midpoint — light `#f0efec`, dark `#383835`.
De-emphasis gray: `#898781` in both modes.

Status (fixed, never themed, always with an icon **and** a word): good `#0ca30c` · warning `#fab219` · serious `#ec835a` · critical `#d03b3b`.

Surfaces and ink, from the same reference instance:

| Role | Light | Dark |
|---|---|---|
| Chart surface | `#fcfcfb` | `#1a1a19` |
| Page plane | `#f9f9f7` | `#0d0d0d` |
| Primary ink | `#0b0b0b` | `#f0efec` |
| Secondary ink | `#52514e` | `#c3c2b7` |
| Muted (axis, labels) | `#898781` | `#898781` |
| Gridline (hairline, solid) | `#e1e0d9` | `#2c2c2a` |
| Baseline / axis | `#c3c2b7` | `#383835` |
| Label inside a fill | `#ffffff`, `#0b0b0b` on yellow/warning | `#ffffff`, `#0b0b0b` on warning |

Dark mode is **selected**, not an inverted light mode: the dark steps are stepped for the dark surface and validated as their own set.
Declare both scopes, so an explicit theme toggle beats the OS setting in both directions:

```css
.viz-root {
  color-scheme: light;
  --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e;
  --muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7;
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a;
  --deemph: #898781;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --surface-1: #1a1a19; --text-primary: #f0efec; --text-secondary: #c3c2b7;
    --grid: #2c2c2a; --axis: #383835;
    --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70;
  }
}
:root[data-theme="dark"] .viz-root { /* same dark block, so the toggle wins */ }
```

### 7.3 Validator output

Run from the skill's base directory, with the project's surfaces:

```
$ node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a" --mode light --pairs all
Palette (light, surface #fcfcfb, categorical): 3 slots
  [PASS] Lightness band         all 3 inside L 0.43–0.77
  [PASS] Chroma floor           all 3 >= 0.1
  [PASS] CVD separation         worst all-pairs #1baf7a↔#eb6834 ΔE 9.2 (deutan) · tritan 9.6
  [PASS] Normal-vision floor    worst all-pairs #1baf7a↔#2a78d6 ΔE 24.0 (normal)
  [WARN] Contrast vs surface    below 3:1 — relief required: [["#1baf7a",2.74]]
  → ALL CHECKS PASS

$ node scripts/validate_palette.js "#3987e5,#d95926,#199e70" --mode dark --pairs all
  [PASS] Lightness band · [PASS] Chroma floor
  [PASS] CVD separation         worst all-pairs #199e70↔#d95926 ΔE 9.4 (deutan) · tritan 4.0
  [PASS] Normal-vision floor    worst all-pairs #199e70↔#3987e5 ΔE 20.9 (normal)
  [PASS] Contrast vs surface    all 3 >= 3:1
  → ALL CHECKS PASS

$ node scripts/validate_palette.js "#86b6ef,#2a78d6,#104281" --mode light --ordinal
  [PASS] Lightness monotone · [PASS] Adjacent ΔL · [PASS] Light-end contrast 2.06:1 · [PASS] Single hue (3°)
$ node scripts/validate_palette.js "#cde2fb,#3987e5,#184f95" --mode dark --ordinal
  [PASS] Lightness monotone · [PASS] Adjacent ΔL · [PASS] Light-end contrast 2.15:1 · [PASS] Single hue (4°)
```

Two consequences we are obliged to honour:

- The **light-mode aqua contrast WARN** is not dismissable. Slot 3 appears only in `<ConfidenceOverlay>`, which always ships direct labels on both lines and a table twin. That is the relief.
- The **dark tritan ΔE of 4.0** between slots 2 and 3 means those two must never be the only distinction. They co-occur only in `<ConfidenceOverlay>`, which is direct-labelled — secondary encoding is present by construction.

Re-run all four commands in CI (`tests/web/test_palette.py` shells out) so a future palette edit cannot land unvalidated.

### 7.4 Redundant encoding — the non-negotiable

Confidence is what this app communicates, so colour is never the carrier.

1. **Every series is direct-labelled or legend-keyed, and for two or more series a legend is always present.** A single-series chart has no legend box; its title names it.
2. **Every chart has a `<TableTwin>`**, reachable from the chart frame and present in the exported HTML without JavaScript.
3. **Every probability is a number with an interval**, never a bar length alone, never a colour alone.
4. **Status is icon + word + colour**, in that order of reliability. `✓ passed` / `✗ FAILED`, not a green or red dot.
5. **The channel strip uses letters and glyphs**, not hue.
6. **Texture** (one hand-drawn Lines fill at 45° and its 135° mirror, tone-on-tone, ordered on value scales) is available from `<A11ySettings>` and auto-engages under `forced-colors` and in print. Off by default; never decorative.
7. **Greyscale print is a supported output.** `msf web verify` renders the fixture charts to greyscale PNG and asserts every series is still distinguishable.

### 7.5 Why falsification outcomes are not status-coloured

`killed` is a **successful** falsification: the falsifier did its job and the project is better off.
Painting it red implies failure and would train readers to see the most valuable output of the system as bad news.
So attack outcomes use a glyph and a word in text ink — `✓ survived`, `~ weakened`, `✗ killed`, `? unresolved` — and the status palette is reserved for cases where good and bad are unambiguous: control pass/fail, gate verdicts, promotion-gate lines, staleness.

### 7.6 The pLDDT exception, recorded

Mol\*'s AlphaFold pLDDT colouring is a multi-hue ramp and therefore violates the sequential rule.
We keep it anyway, because it is the field's convention and a structural biologist reads it instantly; overriding it would be a different kind of dishonesty.
Conditions: it is used **only** inside `<MolstarViewer>`, it always ships its scale legend, the numeric pocket pLDDT and max PAE are printed in the banner above it, and those four hues are not reused anywhere else in the app.
Recorded here so it reads as a considered exception rather than an oversight.

### 7.7 Mark and interaction specs

Straight from the skill, applied without deviation: bars ≤ 24px with a 4px rounded data-end square at the baseline; lines 2px, round joins; markers ≥ 8px with a 2px surface ring; area fills at ~10% opacity; gridlines and axes solid hairlines one step off surface, never dashed; a 2px surface gap between touching fills.

Interaction: crosshair plus one tooltip listing every series on line charts; per-mark tooltips on bars, cells and dots; hit targets ≥ 24px, with a nearest-point layer on `<DecoyDistribution>`; values lead and labels follow inside tooltips; series names inserted with `textContent` (ligand and gene names come from tool output and are untrusted); keyboard focus shows exactly what hover shows; **one filter row above everything it scopes**, never inside a chart card; on refetch the previous render is held at reduced opacity rather than flashing a skeleton.

One axis, always. No chart in this app plots two scales.

---

## 8. Staged build plan

### v0 — hackathon day: a static dossier renderer, and nothing else

Realistic scope for one day. No React, no API, no DuckDB, no Mol\*.

```
msf render dossier --run <id> --target <acc>
  → dist/dossier-<acc>-<ver>-<run>/{dossier.md, dossier.html, dossier.json, …}
msf render index --runs runs/ → dist/index.html   # a flat list of dossiers
```

- A Jinja2 template plus hand-written CSS produces `dossier.html` as a single offline file.
- Charts in v0 are **tables only**, plus `<ChannelContributionBars>` as inline SVG — a ranked single-hue bar chart is 40 lines of SVG and is the one chart worth the day's time.
- 2D ligand depiction from RDKit; **no 3D**.
- The `what would change our mind` panel, the abstention card, the empty-channel cards, the claim ledger and the full provenance footer are all in v0. They are the point.
- `dist/` is published to GitHub Pages directly. No build toolchain.

**v0 acceptance:** for one real target, a judge can open `index.html`, reach a raw artifact and its exact command in under five minutes with the network disabled after the first load, and `sha256sum -c MANIFEST.sha256` passes.
Nothing else in v0 matters.

### v1 — the explorer

- `msf web ingest` and the DuckDB views; `evidence.parquet` normalisation.
- FastAPI read API, generated from the schemas, with §4.4's refusals implemented and tested.
- Next.js app with P0, P1, P2, P3, P4, P5, P6 — the whole ladder.
- `<RiskCoverageCurve>`, `<ReliabilityDiagram>`, `<DecoyDistribution>`, `<ChannelContributionBars>`, each with its `<TableTwin>`.
- `msf web export` and the Mode A/Mode B parity test.
- GitHub Pages deployment from `web/out/`; `msf web verify` wired into CI.
- Keyboard ladder and the axe-core gate.

**v1 acceptance:** export parity passes for every fixture run; zero dead links; the five-minute reviewer journey works against the static export with no server running.

### v2 — the auditor's surface

- P7 `/method` in full: controls, physics, leakage table, contamination facets, pipeline-vs-loop, ablations.
- P8 `/compare` with the guard, the promotion-gate checklist and `<VersionDumbbell>`; the sentence-level `dossier.md` diff.
- P11 Mol\* viewer with `<PocketVerdictBanner>`, residue selection and pose overlay.
- Staleness from L4: banners, citation-string propagation, `superseded` and `withdrawn` states.
- `POST /api/predictions` in Mode A; the YAML stub in Mode B.
- Zenodo deposition for bundles; `CITATION.cff` with concept and version DOIs.
- Search, and the texture/print accessibility channel.

**v2 acceptance:** a loop version can be promoted or rejected entirely from `/compare`, with every gate line linking to its evidence; a stale dossier cannot be cited as current.

### Out of scope at every stage

Authentication, multi-tenancy, writing anything but a prediction, server-side rendering of poses, a mobile-first layout (responsive down to 320px, but the audience is on a laptop), and any view that ranks targets by confidence by default.

---

## 9. Open questions

- **Export size at 10³ targets.** Artifact dedup by hash should hold it, but we have not measured it. If it breaks the budget, the first thing to drop is bundled decoy Parquet, replaced by `OMITTED.tsv` pointers.
- **Pre-computed `/compare` pairs.** Static mode can only serve pairs the exporter was told about. Current plan: every adjacent version pair plus every pair against the incumbent. An arbitrary pair returns a message explaining how to generate it locally.
- **Full-text search in static mode.** The flat index is fine for identifiers and ligand names; mechanism-text search needs either a Lunr index (bundle weight) or Mode C.
- **Whether `<EvidenceHeatGrid>` earns its place.** It is the one chart in this spec whose job could be done by a table, and the dataviz heuristic says that past ~7 meaningful classes a table is the answer. Build it last; drop it if the table reads better.

---

*Written material in this repository is licensed CC BY 4.0. See [../../LICENSE-CC-BY-4.0](../../LICENSE-CC-BY-4.0).*
