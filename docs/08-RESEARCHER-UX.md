# Researcher UX: making the output checkable

Status: design, v1.
Companions: [02-ARCHITECTURE.md](02-ARCHITECTURE.md) (data contracts), [03-LOOPS.md](03-LOOPS.md) (where artifacts come from), [04-EVALUATION.md](04-EVALUATION.md) (the metrics this surface is allowed to show).
The implementable web specification derived from this document is [../web/spec/README.md](../web/spec/README.md).

Accessions in wireframes are illustrative.
`Q9HC97` (GPR35) is the running example because [03-LOOPS.md §2](03-LOOPS.md) already uses it, and because its literature is genuinely contested — which is the interesting case, not the easy one.

## 1. Design stance

The user is a scientist deciding whether to spend money.
The decision is not "is this interesting" — it is "do I believe this enough to burn three weeks and $2,500 of consumables".

That decision is made by **trying to break the claim**, not by reading a summary.
So the interface is built for a sceptic:

1. **Every number on screen is a link to the thing that produced it.**
   A number that cannot be drilled is a bug, and renders as `unsourced` rather than rendering plainly.
2. **Absence of evidence is rendered, not omitted.**
   An empty channel is a card that says `no evidence` and why.
   A channel that did not run is a card that says `not run` and why.
   These are different facts and the UI never collapses them.
3. **Confidence is a quantity with a provenance, never an adjective.**
   No "high confidence", no stars, no gauge needle, no traffic light standing alone.
4. **We show what we tried to do to kill it.**
   The falsification record sits on the same screen as the hypothesis, at the same visual weight.
   A hypothesis that survived nine attacks and one that nobody challenged must not look alike.
5. **Nothing persuades.**
   No hero claim, no "breakthrough" copy, no animation implying momentum.
   The most prominent element on a dossier is the thing that would falsify it (§6).

The honest summary of this project's output is: *prioritised, falsified hypotheses with a stated confidence, none of them wet-lab validated* ([00-PROBLEM.md](00-PROBLEM.md) §Scope and non-goals).
The UI's job is to make that sentence legible at every zoom level.

## 2. Two delivery surfaces

| | (a) The dossier bundle | (b) The web application |
|---|---|---|
| Unit | one `TargetDossier`, one run | many runs × many targets |
| Lifetime | outlives the project | lives while someone pays for hosting |
| Network | zero | optional — static export mode has none either |
| Audience | reviewers, collaborators, future readers, a DOI | anyone exploring |
| Authority | **canonical** | a view over bundles |

The bundle is the primary artifact.
The web app is a convenience layer that must never be able to show something the bundle does not contain.
If the two disagree, the bundle is right and the app has a bug.

### 2.1 Bundle layout

A dossier bundle is a directory, distributed as `.tar.zst`, named `dossier-<acc>-<loop-version>-<run-id-short>`:

```
dossier-Q9HC97-v0.3.1-c8f2a1e/
├── README.md                      # what this is, how to read it, how to verify it, licence
├── CITATION.cff                   # machine-readable citation, incl. DOI once deposited
├── MANIFEST.sha256                # sha256 of every file below, including dossier.html
├── commands.sh                    # every command that produced this bundle, in order
│
├── dossier.json                   # the TargetDossier (02-ARCHITECTURE §4.3) — canonical
├── dossier.md                     # rendered Markdown, semantic line breaks, PR-reviewable
├── dossier.html                   # single-file offline render (§2.2)
│
├── manifest.yaml                  # verbatim copy of runs/<run-id>/manifest.yaml
├── prereg.yaml                    # the pre-registration in force, with its hash
├── snapshot.yaml                  # the pinned snapshot manifest: DB releases and their dates
│
├── schemas/
│   ├── target-dossier.v1.json     # vendored, so the bundle validates with no network
│   ├── hypothesis.v1.json
│   └── evidence-item.v1.json
│
├── hypotheses/
│   ├── hyp_4d91c2.json
│   └── hyp_9b07ae.json
├── falsification/
│   ├── hyp_4d91c2.attacks.json    # every attack, survived AND killed
│   └── hyp_9b07ae.attacks.json
│
├── evidence/
│   ├── index.jsonl                # one EvidenceItem envelope per line, all channels
│   ├── literature/ev_7f2a19.json
│   ├── structure/ev_0c4b81.json
│   ├── chemistry/ …
│   ├── screening/ …
│   ├── genetics/ …
│   └── homology/ …
│
├── artifacts/
│   ├── INDEX.tsv                  # sha256 ⇥ path ⇥ bytes ⇥ mime ⇥ produced_by ⇥ command
│   ├── OMITTED.tsv                # too large to ship: sha256 ⇥ bytes ⇥ retrieval URI
│   ├── structures/AF-Q9HC97-F1-model_v4.cif
│   ├── pockets/p2rank-Q9HC97.csv
│   ├── poses/hyp_4d91c2-top1.sdf
│   ├── decoys/hyp_4d91c2-decoy-scores.parquet
│   └── logs/screener-Q9HC97.log
│
├── metrics/
│   ├── target.json                # this target's calibration bin, contamination score and bin, strata
│   └── channel-contributions.json # after correlation adjustment (02-ARCHITECTURE §4.3)
│
└── audit/
    ├── findings.json              # auditor output: claim → evidence_id → verdict
    └── unsupported.json           # must be empty for a released dossier
```

Rules the bundle must satisfy, each a test in `tests/web/`:

- `MANIFEST.sha256` verifies with `sha256sum -c` on a machine with no network.
- Every `evidence_id` referenced by a hypothesis exists under `evidence/`.
- Every claim in `dossier.md` carries an `evidence_id` that resolves, i.e. `audit/unsupported.json == []`.
- Every file in `artifacts/INDEX.tsv` either exists or is listed in `OMITTED.tsv` with a hash and a retrieval URI — never silently dropped.
- Total size ≤ 50 MB; anything larger goes to `OMITTED.tsv`.
- `commands.sh` re-runs end to end given the snapshot manifest, or declares at the top which steps are non-deterministic and why — `manifest.yaml` records which tools cannot be made deterministic ([02-ARCHITECTURE.md §6](02-ARCHITECTURE.md)).

### 2.2 `dossier.html` — the single-file form

One file, no network, no build step, opens from a USB stick in 2035.

- All CSS, JS and data inlined.
  Data is embedded as `<script type="application/json" id="msf-dossier">`; no `fetch`, no `XMLHttpRequest`, no CDN, no web font.
- Enforced by a meta CSP of `default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'` and by `tests/web/test_dossier_html_offline.py`, which asserts zero `http(s)://` references in any attribute that can initiate a request.
- Works with JavaScript disabled.
  The full dossier is present as semantic HTML — `<details>` for each drill level, `<table>` for every chart.
  JavaScript adds only sorting, the coverage slider, and residue highlighting.
- 3D structure: the bundle ships a **static pose figure** (inline SVG, two orthogonal views, pocket residues labelled) plus the pose `.sdf` as a downloadable `data:` URI.
  It does **not** inline Mol* — a 3 MB viewer in every bundle is a bad trade, and the interactive viewer lives in the web app.
  The figure caption always carries the pocket-quality verdict; a pose is never shown without it.
- Chart twins: every chart is followed by its `<table>` twin inside a `<details>`, not gated behind JavaScript.
- Print stylesheet: expands all `<details>` and prints the evidence index and `MANIFEST.sha256` as appendices.

### 2.3 Why the bundle is reviewable in a PR

`dossier.md` and `dossier.json` are committed to the run's branch when a dossier is released.
`dossier.md` uses semantic line breaks, so a changed sentence is a one-line diff and a reviewer sees exactly which claim moved between loop versions.
`dossier.json` is written with sorted keys and two-space indentation for the same reason.
Large artifacts are not committed; `MANIFEST.sha256` is, so the diff shows *that* an artifact changed even when the artifact itself lives elsewhere.

## 3. Three user journeys

### 3.1 The biologist with one orphan protein

**Nadia** studies GPR35 and wants to know whether to order anything.
She has thirty minutes and no interest in machine learning.

1. She lands on `/target/Q9HC97`.
   The first screen states, in a sentence: *no confident ligand assignment; the top hypothesis is kynurenic acid at p = 0.41 (BCa 95% CI 0.22–0.58), calibrated on `val`, 61 hypotheses in the fitting set*.
   Below that: **the loop abstained from recommending a test at the pre-registered threshold** — stated as a result, with the threshold shown.
2. She reads the **What would change our mind** panel first, because it is pinned above the evidence (§6).
   It names one experiment, an estimated cost, and what the experiment will *not* settle.
   This is the only part of the page that is about her money.
3. She opens the top hypothesis.
   The mechanism text names specific pocket residues; each residue chip links to the structure view with that residue selected, and to the conservation evidence for it.
4. She goes to the evidence section, a six-row matrix, one row per channel.
   Two rows are empty-state cards: `genetics — no evidence (no metabolite-QTL within 500 kb at p < 5e-8 in the pinned GTEx snapshot)` and `homology — no evidence (nearest assigned structural neighbour at 18% identity in the binding region, below the transfer threshold)`.
   She now knows the hypothesis rests on literature, structure and screening only — the single most decision-relevant fact on the page, visible without clicking.
5. She clicks the `screening` row.
   It does not show a docking score.
   It shows the ligand's rank against 1,000 property-matched decoys, the decoy score distribution with the ligand's position marked, and the pocket verdict that allowed docking to run at all.
   The raw score is one level further down, labelled `not a ranking signal`.
6. She opens **Falsification**.
   Nine attacks: seven survived, one weakened, one unresolved at the round bound.
   The unresolved one — `promiscuity check: scores in the top 5% against 31 of 200 unrelated proteins` — is what she takes to her group meeting.
7. She clicks **Download bundle**, gets a 14 MB `.tar.zst`, and emails it to a collaborator who has never heard of this project.

What she never had to do: trust a summary, ask what "confidence" means, or guess which channels were empty.

### 3.2 The computational chemist auditing the method

**Marco** does not care about GPR35.
He wants to know whether any output of this loop is worth reading.
He goes to `/method`, not to a target.

1. **Controls first.**
   The top of `/method` is the control board, because [03-LOOPS.md §L2](03-LOOPS.md) runs controls before metrics and the UI mirrors that ordering.
   Six negative controls, pass/fail, each with an icon and a word — never colour alone.
   `true-orphan-hold` shows two confidence distributions, genuine orphans against solved positives.
   If they overlap, the loop's confidence means nothing, and this is where he sees it in ten seconds.
2. **Physics regressions.**
   The seven tests from [04-EVALUATION.md §6](04-EVALUATION.md), with their assertions printed.
   `test_chirality_sensitivity` shows as `xfail (expected)` with its recorded reason, not hidden.
   `test_known_affinity_correlation` shows the pre-registered band with both floor and ceiling, because a suspiciously high correlation is a leak, not a win.
3. **Leakage.**
   L1–L8 as a table, each with its closing mechanism and a link to the test run and its exit status.
   L7 is marked `cannot be closed — measured`, linking to the contamination section.
4. **Contamination.**
   Three faceted panels — `clean`, `partial`, `contaminated` — each with its own n in the facet title.
   The headline metric is the `clean` panel.
   If `clean` has n < 10, the panel says so in words above the chart and the interval is rendered without a point-estimate glyph.
5. **Pipeline versus loop.**
   The `−LLM` comparison from [04-EVALUATION.md §3.4](04-EVALUATION.md), faceted by contamination bin.
   This is the chart that tells him whether the agent is reasoning or recalling, and he looks at it before anything else about performance.
6. **Ablations and baselines.**
   The contribution table, with the popularity baseline as a required column.
   A version of this table without that column cannot be rendered: the API refuses to serve it, mirroring the statistician's refusal in [02-ARCHITECTURE.md §3](02-ARCHITECTURE.md).
7. **Calibration.**
   Reliability diagram with per-bin counts printed, unsmoothed, ten equal-mass bins; the risk–coverage curve; and the pre-registered headline `selective accuracy @20% coverage` with its CI.
8. He clicks **Reproduce**.
   He gets `manifest.yaml`, the env lock hash, the git commit, the seeds, the snapshot manifest, and the exact `/goal` invocation.
   He runs it.
   If the result differs, `tests/controls/test_determinism.py` and the manifest's non-deterministic-tool list tell him whether that was expected.

Marco's verdict is formed almost entirely from controls, ablations and calibration.
Ranking metrics are the last thing he looks at, so they are the last thing the page shows.

### 3.3 The reviewer verifying one claim in under five minutes

This is how the project is assessed, so it is a designed path, not an emergent one.

Entry point: any URL ending in a `hypothesis_id` or `evidence_id` is a permalink, and every claim in every rendered document carries one, exposed as a `[verify]` affordance beside the sentence.

| Clock | Action | What the UI guarantees |
|---|---|---|
| 0:00 | Clicks `[verify]` beside "kynurenic acid is the top hypothesis for GPR35, p = 0.41" | Lands on `/target/Q9HC97/hypothesis/hyp_4d91c2` with the clicked sentence quoted at the top and highlighted in the dossier text |
| 0:20 | Reads the **claim ledger**: each claim, the evidence ids it rests on, the auditor's verdict per claim, and a one-line "what this does not say" | Every row links down. Any row the auditor could not re-derive is marked `unsupported`, and the hypothesis carries that flag at the top of the page |
| 1:00 | Clicks evidence `ev_0c4b81` (`structure`) | The full `EvidenceItem` envelope rendered field by field, with `source_date` **and** `retrieved` as separate labelled fields — the distinction the entire time split rests on ([02-ARCHITECTURE.md §4.1](02-ARCHITECTURE.md)) |
| 1:40 | Clicks the `locator` | The raw artifact `artifacts/pockets/p2rank-Q9HC97.csv`, rendered as a table, with the cited row highlighted and its line number in the URL fragment |
| 2:10 | Clicks **Command** | A copyable block: exact invocation, tool version, container digest, seed, sha256 of inputs and outputs, exit code, wall clock. One button copies `msf verify ev_0c4b81`, which re-runs that single step and diffs the output hash |
| 2:40 | Presses `u` twice, back to the hypothesis, then opens **Falsification** | All nine attacks with outcomes, including the ones that failed to kill it; the unresolved attack sorts to the top |
| 3:20 | Opens **Provenance** | Run id, loop version, prereg hash, snapshot manifest with each database release and its date, the unseal-log entry if `sealed` was involved, model ids, git commit, env lock hash |
| 4:00 | Clicks **Cite this finding** | A citation block naming the hypothesis, run, loop version and snapshot — and, if the dossier is stale, saying so inside the citation string (§8) |
| 4:30 | Clicks **Download bundle** | The self-contained bundle; `sha256sum -c MANIFEST.sha256` passes offline |

Design requirements that make this five minutes rather than twenty:

- **No level of the ladder requires a search.** Every step is a visible link on the previous screen.
- **No modal dead-ends.** Every drill opens a URL, so any level can be pasted into a review.
- **The claim they clicked is quoted back at every level**, so the thread is never lost.
- **One keystroke up.** `u` goes up a level, `[` and `]` move between siblings, `v` opens the verify command, `?` shows the sheet.
- **The whole path works offline**, because the static export contains the same JSON at the same paths.

## 4. The drill-down ladder

Six levels plus one lateral rung.
Each level states the question it answers; nothing sits on a level that does not answer that level's question.

```
L0  Run index  ──►  L1  Leaderboard  ──►  L2  Target dossier  ──►  L3  Hypothesis
                                                                       │
                                                    ┌──────────────────┘
                                                    ▼
                           L4  Evidence channel  ──►  L5  EvidenceItem  ──►  L6  Artifact + command
                                                    │
                                                    └── lateral: Falsification record (from L3 and L5)
```

### L0 — Run index · `/`

*Question: which runs exist, and which of them am I allowed to believe?*

Shows one row per run: run id, loop version, split (`dev`/`val`/`sealed`), date, n targets, `controls_passed`, whether a pre-registration was in force, promotion decision.
A run with `controls_passed == false` is listed with its metrics **suppressed** rather than greyed: the cells read `withheld — controls failed` and link to the control board.
This follows [04-EVALUATION.md §0](04-EVALUATION.md) principle 3 and [03-LOOPS.md §L2](03-LOOPS.md): a benchmark number computed on a broken pipeline is worse than no number, because it will be believed.

Click next: a run → L1; a control status → `/method`; two runs → `/compare`.

### L1 — Leaderboard · `/leaderboard?run=<id>`

*Question: for this run, which targets produced something, and how is that distributed across strata?*

Shows one row per target: accession, gene symbol, hypothesis count, top-hypothesis `p` with CI, abstention flag, contamination bin, family and ligand-class stratum, `date_confidence`, and six labelled slots showing which channels returned evidence.

Default sort is **not** `p`.
Default sort is accession, with a visible control to sort by `p`, because a list sorted by confidence by default is a list that argues.

Hard rule: **the leaderboard is always stratified.**
A pooled ranking metric never appears here.
Selecting "all strata" renders per-stratum small multiples, not one pooled number ([04-EVALUATION.md §4.1](04-EVALUATION.md)).
Abstentions are rows, not omissions, and `/abstentions` is a first-class sibling view with its own count in the navigation.

Click next: a target → L2; a stratum chip → filtered L1; a contamination chip → `/method#contamination`.

### L2 — Target dossier · `/target/<acc>?run=<id>`

*Question: what does the loop think about this protein, and what is it resting on?*

Shows, top to bottom:

1. The one-sentence verdict, including the abstention decision and the threshold it was taken against.
2. **What would change our mind** (§6).
3. The calibrated probability with its CI, its fitting set, and the n in its calibration bin.
4. The evidence matrix: six channels × {item count, direction balance, empty-state reason}.
5. Ranked hypotheses, each with its falsification summary inline — `9 attacked · 7 survived · 1 weakened · 1 unresolved`.
6. Channel contributions **after correlation adjustment**, with the discount as its own number and the correlated pair named.
7. Provenance footer and citation block.

Click next: a hypothesis → L3; a channel row → L4; the structure → the Mol* view; the bundle download; `/compare` against another version of the same target.

### L3 — Hypothesis · `/target/<acc>/hypothesis/<hyp_id>`

*Question: what exactly is the claim, what would make it false, and did anyone try?*

Shows ligand identity (ChEBI, InChIKey, name, 2D depiction), the mechanism text with pocket residues as links, the claim ledger, supporting and refuting evidence as two explicit lists at equal weight, the `prior_speculation` flag with its source, and the full falsification record.

`prior_speculation: true` is rendered prominently: recovering only pre-speculated pairings is a much weaker result, and [04-EVALUATION.md §1.3](04-EVALUATION.md) requires it to be visible.

Click next: an evidence id → L5 directly, or a channel → L4; an attack → the artifacts that attack produced; a residue → the structure view.

### L4 — Evidence channel · `/target/<acc>/channel/<channel>`

*Question: what did this one channel actually find, and how much of the picture is it?*

Shows every `EvidenceItem` from this channel as a table — id, claim summary, direction, strength, `source_date`, locator, `reproducible` — plus the channel's gate verdict and its calibration note.
The calibration note is on the page, not in a footnote: `strength` is channel-local and calibrated separately per channel, so 0.7 in `genetics` is not comparable to 0.7 in `screening`.

For `screening`, the page leads with the pocket verdict and the decoy comparison, never with a score.
For `structure`, it leads with the pLDDT/PAE mask and the pocket-quality verdict, and the viewer is disabled with an explanation if the verdict was `no usable pocket`.

An empty channel renders a full-size card: `no evidence`, the reason, the query that returned nothing, and the snapshot it queried.
A channel that did not run renders `not run` and names the gate that blocked it.

Click next: an `EvidenceItem` → L5.

### L5 — `EvidenceItem` · `/evidence/<evidence_id>`

*Question: is this specific fact real, dated correctly, and reproducible?*

Shows the envelope from [02-ARCHITECTURE.md §4.1](02-ARCHITECTURE.md) field by field, nothing summarised: `channel`, `target`, `claim` as typed JSON and as prose, `direction`, `strength`, and the whole `provenance` block — `source`, `snapshot`, `retrieved`, `source_date`, `locator`, `tool_version`, `command`.
`reproducible: false` puts a banner at the top stating the item is held for manual review and naming who reviewed it.

Also shown: which hypotheses cite this item and which falsification attacks used it.
Evidence is a graph node, and the back-edges are part of checking it — an item cited by three hypotheses is a single point of failure, and that must be visible.

Click next: the locator → L6; the snapshot id → `/provenance`; a citing hypothesis → L3.

### L6 — Raw artifact and command · `/artifact/<sha256>`

*Question: can I see the actual bytes, and run the thing that made them?*

Shows the file itself — rendered for `.csv`, `.tsv`, `.json`, `.log`, `.sdf`, `.cif`, `.pdb`, downloadable otherwise — with its sha256, size, mime type, the agent that produced it, and the exact command: tool version, container digest, seed, input hashes, output hash, wall clock, exit code.
The cited line or record is highlighted and addressable in the URL fragment.
A copy button yields `msf verify <evidence_id>`, which re-runs that one step and diffs the output hash.

This is the floor.
There is nothing below it, and every path through the app reaches it in at most six clicks.

### Lateral — Falsification record · `/target/<acc>/hypothesis/<hyp_id>/falsification`

*Question: what was tried, what survived, and what is still open?*

Shows the nine standard attacks from [02-ARCHITECTURE.md §5](02-ARCHITECTURE.md) plus any target-specific ones, each with the attack, its outcome (`survived` / `weakened` / `killed`), the evidence it produced, and the artifacts it generated.
Attacks that hit the three-round bound in [03-LOOPS.md §L1.3](03-LOOPS.md) sort to the top labelled `unresolved at round bound`, never dropped.
Attacks that were not run are listed as `not attempted`, with a reason.

## 5. Showing uncertainty honestly

### 5.1 A calibrated probability

Rendered as four things together, always:

```
p(correct) = 0.41        95% BCa CI  0.22 – 0.58
             calibrated on `val` (isotonic), 61 hypotheses in the fitting set
             this hypothesis falls in calibration bin 5/10 (n = 7 in bin)
             ≈ 4 of every 10 hypotheses the loop scores like this one turn out correct
```

- **Never a bare point estimate.** [04-EVALUATION.md §7](04-EVALUATION.md) forbids it; the renderer drops the glyph entirely if the CI is absent rather than printing the point alone.
- **Two decimal places, never three.** Three implies a resolution the fitting set cannot support.
- **The natural-frequency gloss is computed from the calibration bin's own empirical rate**, not from `p`.
  So if the bin is miscalibrated, the gloss and the number visibly disagree — which is the correct behaviour, not a bug.
- **Bin n is always shown.** A probability from a bin with n = 3 is a different object from one with n = 40.
- **No adjectives.** The string "high confidence" does not exist in this UI.

### 5.2 The risk–coverage curve

The chart a lab actually plans against, so it leads both the dossier and the method page.

Selective accuracy on y, coverage on x, with a bootstrap band, plus a **coverage slider** whose output is a sentence:

```
At 20% coverage you would test 12 of these 61 hypotheses,
and 7 ± 2 of those 12 would be correct on the val split.
This does not mean 7 would validate in your lab.
```

The slider defaults to the pre-registered headline, 20% coverage ([04-EVALUATION.md §4.2](04-EVALUATION.md)).
The last clause is not optional copy; it is the difference between a decision aid and a sales pitch.
The curve is always drawn with the **popularity baseline** on the same axes, because a curve without its baseline overstates the method ([04-EVALUATION.md §5.3](04-EVALUATION.md)).

### 5.3 The reliability diagram

Ten equal-mass bins, per-bin n printed above each bin, the identity line as a recessive hairline, **no smoothing and no interpolation between bins**.
Bins with n < 5 are drawn with hollow markers labelled `n<5`.
ECE and Brier are printed beside it with their CIs.
A reliability diagram without bin counts is a picture, not a measurement, and this app does not render one.

### 5.4 Abstention

Abstention is content.
An abstaining dossier gets the same layout as a confident one, with the verdict replaced by:

```
NO CONFIDENT LIGAND
Pre-registered threshold: p ≥ 0.60 to recommend a test. Top hypothesis: p = 0.41.
4 hypotheses generated · 3 killed in falsification · 1 survived below threshold
Reason: only 3 of 6 evidence channels returned anything, and the two strongest
        are correlated (shared template 6QZH), discounted by 0.31.
```

`/abstentions` is a top-level view with its own count in the navigation.
On negative controls the abstention *is* the result, and the false-confidence rate ([04-EVALUATION.md §4.3](04-EVALUATION.md)) is shown beside it with its pre-registered target of < 0.10.
A loop version that never abstains is marked `not promotable` in the run index regardless of its ranking metrics.

### 5.5 Contamination bins

Never pooled, never a single number, never a colour gradient on a leaderboard row.

Always three faceted panels — `clean`, `partial`, `contaminated` — each with its own n in the facet title, and the `clean` panel marked as the headline.
When `clean` is empty or small, the UI writes the sentence rather than letting a wide interval imply a measurement:

```
clean bin: n = 6. Too small to support the headline metric.
Reported for completeness; the interval below is not informative.
```

Per item, the contamination score and the probe variant that elicited it (`direct` / `multiple-choice` / `masked`) are shown on the target page, so a reviewer can see *how* the model knew.

### 5.6 Strata

Per-stratum is the default view everywhere.
Pooled numbers are reachable behind one click and carry a standing banner:

```
POOLED — hides between-stratum variation.
Per stratum: GPCR 0.31 · SLC 0.08 · NR 0.44 · enzyme 0.12 · other 0.05
```

A pooled metric with no strata beside it is not renderable: the API does not serve that shape.

### 5.7 Absence of evidence

Three distinct states, three distinct renders, never conflated:

| State | Render | Example |
|---|---|---|
| `no evidence` | full card: reason, the query, the snapshot queried | `no mQTL within 500 kb at p < 5e-8 in the GTEx v8 snapshot` |
| `not run` | full card: which gate blocked it | `docking skipped — pocket verdict "no usable pocket" (best P2Rank score 0.21 < 0.35 gate)` |
| `refutes` | an evidence item with `direction: refutes`, in the same list as supporting evidence, at the same weight | `pre-cutoff source reports this pairing as negative (PMID …, 2016-04-11)` |

Refuting evidence is never in a collapsed section.
A UI that collapses the disconfirming half is arguing.

### 5.8 What must never be rendered

Each of these is a known way to mislead, and each is blocked at the API or the renderer rather than by reviewer discipline.

1. **A bare docking score anywhere a ranking is implied.**
   Docking scores rank poses adequately and molecules poorly ([00-PROBLEM.md](00-PROBLEM.md)).
   They appear only at L6, labelled `not a ranking signal` — never on a leaderboard, never in a tooltip, never as a sort key.
2. **A pooled metric without its strata.**
3. **AUC-ROC as a headline.** Reported, never used for a decision, never above the fold ([04-EVALUATION.md §4.1](04-EVALUATION.md)).
4. **A point estimate without an interval.**
5. **A reliability diagram without per-bin counts, or with a smoothed curve.**
6. **A confidence gauge, needle, speedometer, star rating, letter grade or "AI confidence" badge.**
7. **A colour gradient as the only encoding of confidence.** See [../web/spec/README.md §7](../web/spec/README.md).
8. **A docking-score heatmap over a candidate library.** A picture of a weakly informative quantity that reads as a result.
9. **A pose render without the pocket-quality verdict in the same frame.**
10. **A percentage without a denominator.** `recall@10 = 31%` renders as `recall@10 = 31% (19/61)`.
11. **Any metric from a run with `controls_passed == false`.** Withheld, with a link to the failure.
12. **An unpaired comparison between loop versions.** Forbidden by [04-EVALUATION.md §7](04-EVALUATION.md), refused by `/api/diff`.
13. **A result from `sealed` without its unseal-log entry beside it.**
14. **Any framing number from the contested rows of [00-PROBLEM.md](00-PROBLEM.md).**
    The $2.6B figure and the ~90% failure rate never appear in the product UI — only in the problem statement, with their confidence column attached.
15. **A count of hypotheses as a measure of productivity.** Generating hypotheses is cheap.
16. **An animated transition on a value change.** Motion implies progress. The value either changed or it did not.

## 6. The "what would change our mind" panel

Mandated by [02-ARCHITECTURE.md §4.3](02-ARCHITECTURE.md) and by the L1 exit condition in [03-LOOPS.md](03-LOOPS.md).
In the UI it is not a section at the bottom.
It is the second element on every dossier, above the evidence, at the same type size as the verdict, and it is present on abstaining dossiers too — where the question becomes *what would make us confident*.

It is derived from the falsifier's **unresolved and weakened** attacks, not invented by the writer: the cheapest falsifying experiment is the one that would resolve the attack still open.

```
┌─ WHAT WOULD CHANGE OUR MIND ─────────────────────────────────────────────────┐
│                                                                              │
│  The cheapest experiment that would falsify hyp_4d91c2                       │
│                                                                              │
│  Assay      nanoDSF thermal shift, purified GPR35 in nanodisc                │
│  Readout    ΔTm across a 0–1 mM kynurenic acid titration                     │
│                                                                              │
│  If TRUE    ΔTm ≥ +1.5 °C, dose-dependent, abolished in the R6.58A mutant    │
│  If FALSE   ΔTm within ±0.5 °C at every concentration                        │
│                                                                              │
│  Attacks    promiscuity-check · unresolved at round bound · ▸ ev_0c4b81      │
│  Cost       ~$2,500 · ~3 weeks · needs purified receptor + ligand            │
│             cost confidence: LOW — published protocol, not a facility quote  │
│                                                                              │
│  This will NOT resolve                                                       │
│    · whether binding occurs at physiological tissue concentrations           │
│    · selectivity against the other 3 surviving candidates                    │
│    · whether binding produces signalling                                     │
│                                                                              │
│  ▸ Cheaper alternatives considered and rejected (1)                          │
│                                                                              │
│  [ copy protocol stub ]   [ register this prediction ]                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

JSON shape, carried in `dossier.json` and served at `/api/runs/{run_id}/dossier/{acc}`:

```json
{
  "what_would_change_our_mind": {
    "experiment_id": "exp_1d3f77",
    "falsifies": "hyp_4d91c2",
    "derived_from_attack": {"attack": "promiscuity-check", "outcome": "weakened", "resolved": false},
    "assay": "nanoDSF thermal shift, purified GPR35 in nanodisc",
    "readout": "delta-Tm across a 0-1 mM kynurenic acid titration",
    "predicted_if_true": "delta-Tm >= +1.5 C, dose-dependent, abolished in the R6.58A pocket mutant",
    "predicted_if_false": "delta-Tm within +/-0.5 C at every concentration",
    "attacks_evidence": ["ev_0c4b81", "ev_7f2a19"],
    "cost": {
      "usd": 2500,
      "weeks": 3,
      "requires": ["purified receptor in nanodisc", "kynurenic acid"],
      "confidence": "low",
      "basis": "published protocol, not a facility quote"
    },
    "does_not_resolve": [
      "whether binding occurs at physiological tissue concentrations",
      "selectivity against the other 3 surviving candidates",
      "whether binding produces signalling"
    ],
    "discriminating_power": {
      "p_prior": 0.41,
      "p_if_positive": 0.78,
      "p_if_negative": 0.09,
      "estimated_on": "val",
      "n": 61
    },
    "alternatives_rejected": [
      {
        "assay": "cellular BRET recruitment",
        "usd": 900,
        "rejected_because": "a positive result is consistent with an indirect effect; it does not falsify"
      }
    ]
  }
}
```

Rules:

- **If `discriminating_power` cannot be estimated, the panel prints `not estimated` and why.**
  It never guesses a posterior.
- **`does_not_resolve` is required and non-empty.**
  An experiment described as resolving everything has been described dishonestly.
- **`cost.confidence` is required and rendered next to the number**, because our cost estimates are weak.
- **`register this prediction`** writes the predicted outcome, today's date and the dossier hash into the run's prediction log.
  When [03-LOOPS.md §L4](03-LOOPS.md) later observes a publication touching this pairing, the prediction log is what turns a stale flag into a scored prediction.
  This is the only write the web app performs; in static export mode it degrades to a downloadable YAML stub.

## 7. Comparing loop versions

Iteration is only visible if two versions can be put side by side on the *same* items.

`/compare?a=v0.3.0&b=v0.3.1&split=val` renders:

1. **A guard, first.**
   If the two runs do not share an item set, the page refuses to compute a delta and names the items that differ.
   Unpaired comparison across versions is forbidden by [04-EVALUATION.md §7](04-EVALUATION.md); the API returns `409` with the symmetric difference.
2. **The promotion gate as a checklist**, rendered from [04-EVALUATION.md §8](04-EVALUATION.md): controls, physics, false-confidence rate < 0.10, primary-metric improvement with a paired bootstrap CI excluding zero, and every baseline in §5.3 beaten.
   Each line is pass/fail with an icon and a word, and links to its evidence.
   The verdict reads `PROMOTED` or `REJECTED`, and when rejected it names the failing line.
3. **Per-target movement** as a dumbbell chart, one row per target, old `p` → new `p`, sorted by magnitude of change, with unmoved targets collapsed into a count.
   Churn is its own number: *of 61 targets, 44 unchanged, 11 improved, 6 worsened*.
4. **Rank movement** for the primary metric, per stratum, never pooled.
5. **A dossier-level diff.**
   For any target, `diff` the two `dossier.md` files.
   Semantic line breaks make this sentence-level, so a reader sees exactly which claim changed.
   The diff view separates three classes: *claims added*, *claims removed*, and *claims whose evidence changed but whose text did not* — the last being the dangerous one.
6. **The changelog, including rejections.**
   `loops/CHANGELOG.md` renders with rejected versions at equal weight to promoted ones, each with its pre-registration hash, metric delta and CI.
   The list of what failed is part of the evidence that the evaluation is real ([03-LOOPS.md §3](03-LOOPS.md), rule 8), so it is not behind a filter.

What the compare view must not do: compute a delta the pre-registration did not name, or describe a difference inside the CI as an improvement.
The renderer emits `no detectable difference (Δ 0.02, CI −0.05 to 0.09)` and refuses the word "improved" in that case, mirroring the report generator.

## 8. Provenance and citation

### 8.1 Citing a finding

Three granularities, each with a stable permalink and a copyable citation.

| Granularity | Permalink | Citation adds |
|---|---|---|
| Dossier | `/target/Q9HC97?run=c8f2a1e` | bundle DOI, run id, loop version, snapshot, dossier hash |
| Hypothesis | `/target/Q9HC97/hypothesis/hyp_4d91c2` | the above plus `hyp_4d91c2` and its `p` with CI |
| Evidence item | `/evidence/ev_0c4b81` | the above plus `ev_0c4b81` and the underlying primary source |

```
Metabolite Sensor Finder, loop v0.3.1. Target dossier for Q9HC97 (GPR35),
hypothesis hyp_4d91c2 (kynurenic acid, p = 0.41, 95% CI 0.22-0.58).
Run c8f2a1e; snapshot manifest snap-2018-01-01-b7d4; prereg sha256 9ab31f…;
dossier sha256 4e07c2…. Generated 2026-11-07. Not experimentally validated.
CC BY 4.0. DOI: 10.5281/zenodo.XXXXXXX
```

Notes on each field, because a citation that cannot be resolved is decoration:

- **`dossier sha256`** is the hash of `dossier.json` with sorted keys, so the citation pins exact content, not just a run.
- **`Not experimentally validated`** is part of the citation string, not a footnote.
  Anyone quoting us quotes that clause too.
- **The underlying primary source is cited alongside, never instead.**
  A reviewer should cite the 2016 paper for the fact and cite us for the inference.
- **DOI.** Bundles are deposited to Zenodo on release; `CITATION.cff` carries the concept DOI and the version DOI separately.
  Before deposition the field reads `DOI: not yet deposited` rather than being omitted.

### 8.2 Staleness, driven by L4

[03-LOOPS.md §L4](03-LOOPS.md) watches for new structures, new publications and new curated releases.
It may not inject anything into a run.
What it may do is mark a dossier stale — and staleness is a visible state on every surface, including the citation string.

| State | Meaning | Render |
|---|---|---|
| `current` | no upstream change since the snapshot | nothing |
| `stale:snapshot` | a pinned database released a newer version | banner naming the database, old and new release, and the affected `evidence_id`s |
| `stale:literature` | a publication matching an open hypothesis appeared after the run | banner naming the DOI and date, and which hypothesis it touches |
| `superseded` | a newer run exists for this target | banner with a link to it and a `diff` link |
| `withdrawn` | the dossier was retracted | the dossier stays reachable, stamped, with the reason and retraction date |

Rules:

- **Nothing is silently updated.**
  A stale dossier keeps its numbers; recomputing produces a new run with a new id.
- **The banner names the affected evidence ids**, so a reader can judge whether the change touches the claim they care about.
  "This dossier may be out of date" without the list is useless.
- **Staleness propagates into the citation string** — `Status at retrieval: stale:literature since 2026-10-02` — so a stale finding cannot be quoted as current.
- **Withdrawn dossiers are never deleted.**
  Deleting them breaks every citation that pointed at them, which is worse than the error being visible.
- **The bundle carries its staleness as of export** in `README.md`, plus a `check-staleness` URL so an offline reader knows where to look.

## 9. Anti-patterns

A dashboard for this problem must never:

1. **Sort by confidence by default.** The first thing the user sees should not be an argument.
2. **Show a score without what it was compared against.** A screening score with no decoy distribution is not a result.
3. **Hide empty channels.** The most decision-relevant fact is often what returned nothing.
4. **Collapse refuting evidence** into a secondary tab, an accordion or a smaller type size.
5. **Round a probability to a word.** "Likely" is not a number and cannot be calibrated.
6. **Encode confidence in colour alone.** A deuteranope must read every claim at full fidelity.
7. **Render a metric from a run whose controls failed.** A control that passes is a bug; a control that failed and still produced a published number is a scandal.
8. **Let the user reach a claim they cannot drill.** Every number links down, or it does not render.
9. **Use the words "discovery", "breakthrough" or "validated"** anywhere in the product surface. Nothing here is wet-lab validated.
10. **Count hypotheses, runs, tokens or targets as a success metric** in the UI chrome. Volume is not progress.
11. **Animate a number changing.** It implies momentum where there is only a recomputation.
12. **Make the falsification record optional, collapsed or below the fold.**
13. **Require the network to check a claim.** The bundle is the answer to "the site is down".
14. **Normalise across strata to make a chart tidier.**
15. **Make a 3D pose the hero image.** A rendered pose is the most persuasive and least informative object in the whole system.

---

*Written material in this repository is licensed CC BY 4.0. See [LICENSE-CC-BY-4.0](../LICENSE-CC-BY-4.0).*
