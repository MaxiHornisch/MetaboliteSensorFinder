# Tools and setup

Status: setup manual, v1.
Audience: a competent scientist-engineer on a fresh machine with one day.
Assumes Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

All facts below were checked on **2026-11-07**.
Anything we could not confirm is marked `UNVERIFIED — check before use`.
Do not treat an unmarked command as eternal: version-pin, and re-run `scripts/doctor.py` (§6) before believing a result.

This document says *how to install and connect things*.
[04-EVALUATION.md](04-EVALUATION.md) says *what the setup has to guarantee*, and it wins on any conflict.
The single most important thing this manual exists to enforce is the leakage taxonomy in [§2 of 04-EVALUATION.md](04-EVALUATION.md#2-the-leakage-taxonomy):

> **L1** — future literature must be rejected at the tool boundary, by a hard date filter in the retrieval layer, *not by prompt instruction*.
> **L2** — database tools must read pinned snapshots dated ≤ cutoff `C`; the loop may not query live endpoints during a benchmark run.

Everything in §2 of this document is organised around one question per resource: **can you close L1 and L2 with it, and how?**
A resource whose date filter you cannot enforce in code is a resource that does not belong in a benchmark run.

---

## Minimum viable stack

The eight tools we would keep if we could only have eight.
This is the set that lets `DeorphBench` exist and be scored honestly.
Everything else improves the *method*; these make the *benchmark* possible.

| # | Tool | Why it survives the cut | Tier |
|---|---|---|---|
| 1 | **`uv`** | Every other install goes through it; it is the only thing that makes the stack reproducible on a fresh machine in minutes | 0 |
| 2 | **Claude Code + Claude Agent SDK (Python)** | The loop itself: subagents, skills, hooks, MCP. The hook layer is also where L1/L2 enforcement physically lives | 0 |
| 3 | **DuckDB + Parquet** | Run records, snapshot serving, and *offline date filtering* for the ~20 resources whose APIs have no date filter. This is the workhorse of leakage control | 0 |
| 4 | **Europe PMC REST** | The only literature source with a true server-side index-time date filter (`FIRST_PDATE`, `CREATION_DATE`). Closes L1 for literature. Keyless | 0 |
| 5 | **RCSB PDB** — dated archive snapshots + Search API | Dated whole-archive snapshots back to 2005 *and* a server-side `initial_release_date` filter. Closes L1 and L2 for structures outright. Keyless, CC0 | 0 |
| 6 | **ChEMBL pinned release dump** (`chembl_24` for a 2018 cutoff) | The ground-truth ligand/activity substrate, and every release since `chembl_08` is retained on FTP. Closes L2 for chemistry | 1 |
| 7 | **RDKit** | Standardisation, scaffolds (Bemis–Murcko for the L4 split), descriptors (the L6 decoy-separability control), fingerprints. Nothing else does this | 0 |
| 8 | **Foldseek** | The *nearest-structural-neighbour* baseline in [§5.3](04-EVALUATION.md#53-baselines-that-must-be-beaten) is mandatory and hard to beat; Foldseek is also the highest-value primary signal for low-homology orphans | 1 |

Two deliberate near-misses, stated so the omission is not read as a judgement:

- **scikit-learn** carries the pre-registered headline metric (selective accuracy @20% coverage via `CalibratedClassifierCV`).
  It is excluded only because it is a one-line pip install that arrives with any Python stack — not because it is optional. It is not.
- **Boltz-2** is the ninth tool and the first thing to add once a GPU exists.
  It is MIT-licensed for code *and* weights, which makes it the only co-folding + affinity model with no licence negotiation.

---

## 0. Platform reality check

The host dev machine is Windows 10 + PowerShell + Git Bash.
A meaningful part of this stack does not run there.
Decide early which half of the table you are in, because it determines whether you need WSL2 on day one.

| Runs natively on Windows | Needs WSL2, Docker, or Linux |
|---|---|
| RDKit, Open Babel (CLI + Python), Meeko, AutoDock Vina **CLI**, smina (conda-forge), P2Rank, pyhmmer, PLIP, ProLIF, OpenMM (incl. CUDA), ParmEd (conda-forge), `openmmforcefields`, scikit-learn, DuckDB, Boltz-2 (plain `pip install boltz`), Claude Code, Claude Agent SDK, Claude Science | Vina **Python API**, gnina, DiffDock-L, Chai-1, ColabFold/localcolabfold, **Foldseek**, **HMMER binaries**, **fpocket**, AmberTools / `MMPBSA.py`, full `openff-toolkit`, DeepCoy, ESMFold2 fused backend, `boltz[cuda]` kernels, MGLTools/ADFRsuite |

**Recommended Windows setup.**
Install WSL2 with Ubuntu 24.04 once, up front, and treat it as the compute host.

```powershell
wsl --install -d Ubuntu-24.04
```

Keep the repo on the Windows filesystem and work on it from both sides, or clone twice — but do not run heavy I/O across `/mnt/c`, it is slow.
For GPU work under WSL2 you need a recent NVIDIA Windows driver; CUDA inside WSL2 then works without a separate Linux driver install.

**`uv` and `pixi` both work natively on Windows** and are the right entry point on either side.

---

## 1. Agent layer

### 1.1 Claude Code

The CLI that drives the loop interactively and in CI.
Install per Anthropic's current instructions for your platform.
Docs moved in 2026: `docs.claude.com/en/docs/claude-code/*` now 301-redirects to **`https://code.claude.com/docs/en/<page>`** — update any bookmarks and any link in a prompt.

Verify:

```bash
claude --version
claude mcp list
```

### 1.2 Claude Agent SDK (Python)

| Item | Value |
|---|---|
| PyPI package | **`claude-agent-sdk`** (imports as `claude_agent_sdk`) |
| Version at check | `0.2.179` (2026-11-07) — re-check before pinning |
| Python | `>=3.10`; we target 3.11+ |
| Docs | https://code.claude.com/docs/en/agent-sdk/python |

```bash
uv venv --python 3.11
uv pip install claude-agent-sdk
python -c "import claude_agent_sdk; print('ok')"
```

The docs note that system Python on Debian/Ubuntu/Homebrew fails with `error: externally-managed-environment`; use a venv, which `uv venv` gives you anyway.
Whether Node.js is a hard requirement is `UNVERIFIED` — the Python SDK docs reference a bundled CLI and a `cli_path` option but never state the dependency outright.
Install Node 20+ anyway: several MCP servers we use are `npx`-launched.

### 1.3 Subagents — `.claude/agents/<name>.md`

One file per agent, YAML frontmatter plus a system prompt.
The hypothesis-generating agent and the adversarial falsifier from [00-PROBLEM.md](00-PROBLEM.md) are both of these.

```markdown
---
name: falsifier
description: Receives one surviving ligand hypothesis and a budget to kill it. Invoke after any hypothesis reaches confidence > 0.3.
tools: Read, Grep, Glob, Bash
model: opus
permissionMode: default
effort: high
---

You are an adversarial reviewer. Your job is to destroy the hypothesis you are given,
not to evaluate it fairly. Report the strongest surviving objection and whether it is fatal.
```

| Field | Notes |
|---|---|
| `name` | **Required.** Max 256 chars, **cannot contain `:`** (reserved for plugin ids). Filename need not match |
| `description` | **Required.** When Claude should delegate |
| `tools` | Comma-separated string or YAML list. Omitted = inherits all |
| `disallowedTools` | Same format, subtractive |
| `model` | `sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit` |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`, `manual` |
| `effort` | `low` / `medium` / `high` / `xhigh` / `max` |
| Also documented | `maxTurns`, `autoCompactWindow`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `omitClaudeMd`, `isolation`, `color`, `initialPrompt` |

**Trap:** unrecognised frontmatter is *silently ignored*.
A typo'd field fails quietly and you get a subagent with different permissions than you think.
`disable-model-invocation` is a **skill** field, not a subagent field — putting it here does nothing.

### 1.4 Skills — `.claude/skills/<name>/SKILL.md`

Skills carry the procedural knowledge that would otherwise bloat every prompt: how to run a docking job, how to format a benchmark item, how to read the pre-registration.

```yaml
---
name: pin-check
description: Verify that every data access in the current run used a pinned snapshot and a date filter
when_to_use: Before writing any result to runs/, and before any promotion decision
allowed-tools: Read Grep Bash
disable-model-invocation: false
---
```

```text
.claude/skills/pin-check/
├── SKILL.md          # required — overview and navigation
├── reference.md      # loaded only when needed
└── scripts/
    └── verify_pins.py  # executed, not loaded into context
```

Locations: `.claude/skills/<name>/` (project, commit it) and `~/.claude/skills/<name>/` (personal).
`description` + `when_to_use` are truncated at **1,536 chars** combined in the skill listing; keep the SKILL.md body under ~500 lines and push detail into sibling files.

**Portability trap:** outside Claude Code — claude.ai uploads, the Skills API — only `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools` are accepted, and any other key is a **hard error**.
If a skill must work in both places, restrict it to that subset.

### 1.5 Hooks — `.claude/settings.json`

**This is where L1 and L2 are actually enforced.**
A prompt that says "do not read post-cutoff literature" is not a control.
A `PreToolUse` hook that inspects the tool input, finds no `max_date` parameter, and returns `permissionDecision: "deny"` is a control, because the model cannot talk its way past it.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/enforce_cutoff.py",
            "timeout": 30
          }
        ]
      },
      {
        "matcher": "WebFetch|WebSearch",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block_live_web.py"
          }
        ]
      }
    ]
  }
}
```

The hook writes this to stdout to block a call:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Benchmark run MSF-0042 is pinned to cutoff 2018-01-01; this call has no date filter."
  }
}
```

| Detail | Value |
|---|---|
| `permissionDecision` values | `"allow"`, `"deny"`, `"ask"`, `"defer"` |
| Multi-hook precedence | **deny > defer > ask > allow** |
| Exit-code alternative | **exit 2** blocks, stderr becomes the reason shown to Claude. Exit 1 is a *non-blocking* error — never use it for policy |
| `permissionDecisionReason` | Shown to Claude on deny; shown in the prompt on ask; debug log only on allow |
| `updatedInput` | Replaces the **whole** input object, not a merge |

**Matcher trap, and it is the one that will bite you.**
A matcher string containing only letters, digits, `_`, `-`, space, `,` or `|` is treated as an **exact** match.
Anything else is an unanchored JavaScript regex.
So `mcp__msf_europepmc` matches exactly that one tool, and **`mcp__msf` matches nothing at all**.
To cover a server's whole tool surface you must write `mcp__msf.*`.
A silently non-matching leakage hook is indistinguishable from a working one until the control test fails — which is exactly why `tests/controls/test_date_filter.py` exists.

The docs now list **33 hook events**, including `SessionStart`, `Setup`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `PreCompact`, `SessionEnd`.
For this project the load-bearing three are `PreToolUse` (block), `PostToolUse` (log every retrieved document's date into the run record), and `SessionEnd` (assert the egress log is clean).

**Settings precedence:** managed > command line > `.claude/settings.local.json` (personal, git-ignored) > `.claude/settings.json` (project, committed) > `~/.claude/settings.json` (user).
List fields such as `permissions.allow` **merge** across files; object fields do not.

### 1.6 MCP server registration

Two mechanisms: a committed `.mcp.json` at the project root (shared, reproducible — use this) and `claude mcp add` (interactive, for exploration).

`.mcp.json`, HTTP transport:

```json
{
  "mcpServers": {
    "rcsb-pdb": {
      "type": "http",
      "url": "https://mcp-beta.rcsb.org/mcp"
    },
    "msf-gateway": {
      "type": "http",
      "url": "${MSF_GATEWAY_URL:-http://127.0.0.1:8777}/mcp",
      "headers": {
        "X-MSF-Run-Id": "${MSF_RUN_ID}"
      }
    }
  }
}
```

`.mcp.json`, stdio transport:

```json
{
  "mcpServers": {
    "pdbe": {
      "command": "uvx",
      "args": ["pdbe-mcp-server==2.0.1", "--server-type", "all"]
    },
    "tooluniverse": {
      "command": "uvx",
      "args": ["--refresh", "tooluniverse"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

Environment expansion works in `command`, `args`, `env`, `url` and `headers`.
`${VAR}` expands; `${VAR:-default}` falls back.
**An empty string counts as set** and expands to `""` — to get the default you must *unset* the variable.
Credential-shaped names (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `AWS_BEARER_TOKEN_BEDROCK`, `HTTPS_PROXY`, `NPM_TOKEN`) are deliberately read as empty inside remote `url`/`headers`; names like `API_KEY` expand normally.

CLI equivalents:

```bash
# remote HTTP (recommended)
claude mcp add --transport http rcsb-pdb https://mcp-beta.rcsb.org/mcp
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"

# local stdio — everything after `--` is passed through unchanged
claude mcp add --env GTP_API_KEY=xxx --transport stdio gtopdb -- uvx msf-gtopdb-mcp

# project scope writes to .mcp.json
claude mcp add --transport http shared-server --scope project https://example.com/mcp

# raw JSON — pass only the object that goes inside mcpServers
claude mcp add-json example '{"command":"npx","args":["-y","@example/mcp-server"]}'

claude mcp list      # all servers + health
claude mcp get rcsb-pdb
claude mcp remove rcsb-pdb
claude mcp logout sentry   # clear stored OAuth creds BEFORE removing
```

Scopes: `local` (default, `~/.claude.json`, this project only), `project` (`.mcp.json`, committed), `user` (`~/.claude.json`, all projects).
Precedence local → project → user → plugin → claude.ai connectors, and **fields are not merged** — a name defined twice takes one definition wholesale.
`--transport sse` is deprecated; Claude Code v2.1.265+ falls back to SSE over HTTP automatically.
`add-json` gotcha: an entry with a `url` but no `type` is parsed as stdio and errors.

### 1.7 Claude Science (beta)

Anthropic's desktop research workbench.
Relevant here because its connector set overlaps ~18 of our 25 data resources, and because it can dispatch compute to Slurm and Modal — which is how a judge with no cluster reproduces a GPU result.

| Item | Value |
|---|---|
| Status | **Public beta**, launched 2026-06-30. No GA date, no waitlist, no invite gate published (`UNVERIFIED` whether a GA date exists internally) |
| What it is | A **locally installed desktop application**. Verbatim: *"Claude Science is a local application, not a website, so there's no public URL to visit."* Not claude.ai, not Claude Code, not the Claude desktop app |
| Platforms | macOS 13+, **Windows 11 x64** (added 0.1.47, Sept 2026), Linux x64 glibc (needs `socat` + `bubblewrap` ≥0.8.0 + unprivileged user namespaces). ~5 GB disk. Runs under WSL2 (Ubuntu 24.04+) and over an SSH tunnel to a remote Linux box |
| Auth | OAuth with a Claude account. **No API key required** |
| Plans | Pro, Max, Ultra, Team, Enterprise. **Not on Free.** Team/Enterprise: **off by default**, an Owner must enable it |
| Local execution | Python, R and shell (PowerShell on Windows) in a **persistent kernel** that holds variables across steps. Kernel dies after ~30 min idle. Two read-only starter conda envs; task envs on demand via micromamba from conda-forge/bioconda/pytorch, plus pip and CRAN/Bioconductor. No root, no apt. OS sandbox, deny-by-default network through a local proxy. **Host GPU on Linux with NVIDIA** |
| Slurm dispatch | Over SSH using your existing `~/.ssh/config`; installs nothing on the host. Submits via `sbatch` where present, detached processes otherwise. Default job timeout 30 min, 100 concurrent. **Verbatim: does not submit to PBS or LSF.** Remote jobs run *outside* the sandbox as your user |
| Modal dispatch | Your own Modal account and token. **Verbatim: "Modal bills you directly. Anthropic doesn't provide or bill compute."** Per-job approval card showing the machine spec; inputs ≤1 GiB per submit, outputs from `./out/` up to 5 GiB; default container timeout 12 h (max 23); 10 concurrent; **no spend ceiling** |
| AWS / GCP / Azure | **Storage only** — S3, S3-compatible, GCS via HMAC. No compute dispatch is documented. Treat any claim of "dispatches to AWS compute" as **false** |
| Relevant bundled skills | AlphaFold2, **Boltz-2**, **Chai-1**, ESMFold2, OpenFold3, ProteinMPNN, **DiffDock**, ESM-2, Evo 2, Borzoi, scGPT, scvi-tools |
| Custom connectors | MCP, remote URL or local command (admin-gated on Team/Enterprise) |

Docs: `https://claude.com/docs/claude-science/{overview, get-started, tools-and-environments, connectors-and-skills, remote-compute-clusters, compute-providers, the-reviewer, changelog}`.
Note the domain: Anthropic's science docs are on **`claude.com/docs`**, not `docs.claude.com`.

**Do not confuse it with Claude for Life Sciences** (Oct 2025), which was a bundle of connectors and skills layered on existing Claude surfaces, not an application.

**Caveat that matters for this project.**
Claude Science's Featured connectors are *in-product only* — they do not publish standalone MCP URLs, so you cannot point an arbitrary MCP client at them, and you cannot wrap them in our date-enforcing gateway.
Claude Science is therefore excellent for **exploration and for `true-orphan-hold` targets**, and **must not be used for a scored benchmark run**, because its connectors query live endpoints and nothing stops them seeing post-cutoff data.
Four of its connectors (PubMed, Clinical Trials, ChEMBL, bioRxiv) are Directory connectors usable from other Claude products; those *do* have URLs (§2.2).

---

## 2. Knowledge and data layer

### 2.1 The architecture that closes L1 and L2

**Only 6 of 26 resources can enforce a date cutoff server-side.**
Everything else must be served from a pinned, dated local snapshot.
That single fact determines the shape of the data layer:

```
   agent
     │  MCP (stdio or local HTTP)
     ▼
┌──────────────────────────────────────────────┐
│  msf-gateway   (one thin MCP server we own)  │
│  • injects cutoff C into every date-capable  │
│    query                                     │
│  • asserts filtered_count < unfiltered_count │
│  • refuses any call with no date discipline  │
│  • logs every retrieved record + its date    │
└───────┬──────────────────────┬───────────────┘
        │                      │
        ▼                      ▼
  live, date-filtered    DuckDB over pinned
  (6 resources)          Parquet snapshots
                         (everything else)
```

Three rules, and they are not negotiable during a benchmark run:

1. **Public MCP servers are for `dev` and for `true-orphan-hold` only.**
   None of them take a cutoff parameter, and none of them can be audited.
   During a scored run the egress allowlist (`tests/controls/test_snapshot_pinning.py`) blocks their hosts outright.
2. **Every pinned snapshot is recorded in the run record** as `(resource, release_id, url, sha256, download_date)`.
   A result whose snapshot hashes cannot be reproduced does not exist ([04-EVALUATION.md §0.2](04-EVALUATION.md#0-principles)).
3. **Any wrapper over an API that fails open must assert the filter worked.**
   See the ChEMBL trap below.

### 2.2 MCP server availability

Checked against the official MCP Registry, PyPI, npm, GitHub and the BioContextAI registry on 2026-11-07, with live `initialize` handshakes against every hosted endpoint listed as verified.

**Only seven data providers ship their own MCP server.**
There is no official server from UniProt, NCBI/NLM, EMBL-EBI for ChEMBL/ChEBI/Europe PMC, SIB (Rhea), Wishart Lab (HMDB), IUPHAR/BPS, LIPID MAPS, BindingDB, Broad/GTEx, HPA, MaayanLab (ARCHS4), NCATS (Pharos), OurResearch (OpenAlex) or CSHL (bioRxiv).

| Resource | MCP server status | Endpoint / command |
|---|---|---|
| InterPro / Pfam | ✅ **Official** (EBI Protein Families team) | `https://www.ebi.ac.uk/interpro/mcp` — verified live |
| RCSB PDB | ✅ **Official** (beta) | `https://mcp-beta.rcsb.org/mcp` — verified live; or `uvx rcsb-mcp==0.23.0` |
| PDBe | ✅ **Official** (best-engineered of the set) | `uvx pdbe-mcp-server --server-type all`; hosted beta `https://wwwdev.ebi.ac.uk/pdbe/mcp/all/` (dev host only — the production path 404s) |
| STRING | ✅ **Official** (von Mering lab) | `https://mcp.string-db.org/` — verified live |
| Reactome | ✅ **Official** — **from git, not npm** | `git clone https://github.com/reactome/reactome-mcp` then `claude mcp add reactome node /abs/path/dist/index.js` |
| Open Targets | ✅ **Official** (experimental) | `https://mcp.platform.opentargets.org/mcp` — verified live. GraphQL passthrough, 5 tools |
| GWAS Catalog | ✅ **Official** (EBI-hosted) | `https://www.ebi.ac.uk/gwas/mcp` — verified live. No local package |
| ChEMBL | Anthropic-hosted connector | `https://hcls.mcp.claude.com/chembl/mcp` — verified live (`ChEMBL v34`) |
| PubMed | Anthropic-hosted connector | `https://pubmed.mcp.claude.com/mcp` |
| bioRxiv / medRxiv | Anthropic-hosted connector | `https://hcls.mcp.claude.com/biorxiv/mcp` |
| UniProt | Community only | `npx -y @cyanheads/uniprot-mcp-server`; semi-official SIB SPARQL server `https://chat.expasy.org/mcp` |
| AlphaFold DB | Community only | `npx -y @cyanheads/protein-mcp-server` (federates PDB + AFDB + 3D-Beacons + UniProt + InterPro + Foldseek) |
| Europe PMC | Community only | `uvx pyeuropepmc mcp`, or `@cyanheads/pubmed-mcp-server` (has first-class Europe PMC tools) |
| OpenAlex | Community only | `npx -y @cyanheads/openalex-mcp-server` |
| BindingDB | Community only | `pwrose/mcp-bindingdb` — builds a local read-only DuckDB from the monthly dump. Early development |
| ChEBI, Rhea, GtoPdb, HMDB, LIPID MAPS | Thin community wrappers only | Prefer **ToolUniverse** (below) |
| GTEx | Community only, all ≤3★ | Self-host `berntpopp/gtex-link` (streamable HTTP only, no stdio) |
| Human Protein Atlas | Technically exists; every option 0–4★ and ~11 months stale | **Write a thin wrapper** — the API is `search_download.php?format=json&columns=…`, trivially wrappable |
| ARCHS4 | **None found** | **Write a thin wrapper** over `archs4py`. Partial coverage via `gget-mcp` → `gget_archs4` (stale ~13 months) |
| Pharos / TCRD | **None found** | **Write a thin wrapper.** The GraphQL API is keyless — a single `pharos_graphql_query` tool is ~50 lines of FastMCP |

**Aggregators worth knowing:**

| Aggregator | Install | Coverage | Caveat |
|---|---|---|---|
| **ToolUniverse** (Harvard, Zitnik lab, 1.8k★, active today) | `uvx --refresh tooluniverse`; `claude plugin marketplace add mims-harvard/ToolUniverse` | 2,700+ tools; the **only** thing covering all nine chem/pharma targets — ChEMBL, BindingDB, ChEBI, Rhea, Reactome, GtoPdb, LIPID MAPS, PubChem, HMDB | Huge tool surface — subset with `--categories` or it eats your context budget. stdio only |
| **BioMCP** (`genomoncology`, 673★) | `uv tool install biomcp-cli` then `biomcp serve` | 72 sources incl. UniProt, Reactome, STRING, GTEx, HPA, InterPro, PDB, AlphaFold, ChEMBL, Open Targets, GWAS Catalog, Europe PMC, bioRxiv | **Does not** cover ARCHS4, Pharos, OpenAlex, HMDB, LIPID MAPS, ChEBI, Rhea, BindingDB, GtoPdb. No hosted endpoint — self-host only |
| **BioContextAI Knowledgebase** | `uvx biocontext_kb@latest` (set `UV_PYTHON=3.12`) | Best one-shot for **HPA + AlphaFold + STRING + InterPro**; the only aggregator with Europe PMC *and* bioRxiv together | No UniProt or PDB/PDBe tools. Correct org slug is **`biocontext-ai`** — `BioContextAI` 404s |

**Name-collision traps.** These are the highest-risk lines to get wrong:

| Write this | Not this | Why |
|---|---|---|
| `pip install biomcp-cli` | `pip install biomcp` | PyPI `biomcp` is an **unrelated** package by a different author. `biomcp-python` is the legacy pre-Rust release |
| `git clone reactome/reactome-mcp` | `npx reactome-mcp` | The npm name belongs to a different community project; the official server is not published to npm |
| ToolUniverse for Rhea | `pip install rhea-mcp` | PyPI `rhea-mcp` is `chrisagrams/rhea`, a generic biomedical tool framework, **not** the Rhea reaction database |
| `@cyanheads/protein-mcp-server` | `protein-mcp-server` | An unrelated npm package of the same unscoped name exists |
| — | `@ncbijs/http-mcp` | Looks official, is not. Version `0.0.0` placeholder |
| — | `uniprot-mcp` / `uniprot-mcp-server` on PyPI | Three unrelated projects share these names. Do not guess |

Additional cautions: `github.com/modelcontextprotocol/servers` contains **zero** science entries — do not cite it.
Third-party hosted endpoints (`*.caseyjhand.com`, `gateway.pipeworx.io`, `*.workers.dev`) route your queries and any keys through someone else's infrastructure; prefer local stdio for anything sensitive.
`pyeuropepmc-mcp --transport streamable-http` is **unauthenticated by default** — bind it to `127.0.0.1`.
`openags/paper-search-mcp` ships a disabled Sci-Hub path; verify it stays disabled before documenting that server anywhere.
The `Augmented-Nature` family has the best star counts in the community set but every repo was last pushed 2025-12-21 and none publish an npm or PyPI package.

### 2.3 Resource reference — the leakage-control view

The column that matters is **L1 (date filter)** and **L2 (snapshot pin)**.
Auth is `none` unless stated.

#### Tier A — true server-side date filter (6 resources)

| Resource | Endpoint | L1 — date filter | L2 — snapshot pin | Rate limit | Licence |
|---|---|---|---|---|---|
| **Europe PMC** | `https://www.ebi.ac.uk/europepmc/webservices/rest/search` | ✅ **Best in set.** `FIRST_PDATE:[* TO 2018-12-31]` (publication), `CREATION_DATE` / `FIRST_IDATE` (index time — use for strict "knowable-at-the-time"), `PUB_YEAR`. **Fails closed**: an invalid field gives `hitCount: 0` | FTP mirror `https://ftp.ebi.ac.uk/pub/databases/pmc/` but **no dated releases** → download once + SHA256 | ~10 req/s (500/min) per IP, from EBI staff on the official forum — **semi-official, not in docs** | Per-article; exposed in the `LICENSE` search field — filter on it, don't assume |
| **RCSB PDB** | Search `https://search.rcsb.org/rcsbsearch/v2/query` (POST); Data `https://data.rcsb.org/rest/v1/` | ✅ `rcsb_accession_info.initial_release_date` (**use this** — public availability, not deposition), `deposit_date`, `revision_date`. Operators incl. `range`, date math (`now-12M`) | ✅ **Gold standard.** Dated whole-archive snapshots: `s3://pdbsnapshots/<YYYYMMDD>/pub/` (`--no-sign-request`) or `https://snapshots.pdbj.org/<YYYYMMDD>/pub/`. Snapshots exist for 20050106 … 20260415; **for a 2018 cutoff pin `20190101/`** | `UNVERIFIED` — none documented | CC0 (`UNVERIFIED` verbatim; long-standing wwPDB position) |
| **PDBe** | REST `https://www.ebi.ac.uk/pdbe/api/v2/`; **Solr** `https://www.ebi.ac.uk/pdbe/search/pdb/select` | ⚠️ **The REST API has NO date filter** (all 197 paths checked). Date filtering is Solr-only: `fq=deposition_date:[2018-01-01T00:00:00Z TO …]`. Fields: `deposition_date`, `release_date`, `revision_date`, `data_collection_date` | Use the RCSB snapshots | `UNVERIFIED` | Per-resource; see each PDBe-KB `README.txt` |
| **OpenAlex** | `https://api.openalex.org` | ⚠️ **Partially paywalled.** `from_publication_date` / `to_publication_date` / `publication_year` work free. **`from_created_date` returns HTTP 429 "Plan upgrade required"** (Member+/Partner). Publication date ≠ index date, so free-tier OpenAlex **cannot** give a true knowable-at-the-time cutoff. Fails closed | ✅ Quarterly S3 snapshot `s3://openalex/` (JSONL + Parquet, partitioned by `updated_date`). ⚠️ **The prefix is NOT dated** — `data/` is overwritten each quarter; record `manifest.json` + `RELEASE_NOTES.txt` at download | **USD budget, not request count.** $0.10/day keyless (shared per IP), $1/day with a free key. 10 / 30 / 50 req/s by tier. `mailto=` buys nothing now — the polite pool is gone | **CC0** for the data, even though access is metered |
| **bioRxiv / medRxiv** | `https://api.biorxiv.org` | ✅ **Cleanest boundary of any resource — the date range *is* the URL path.** `/details/[biorxiv\|medrxiv]/[YYYY-MM-DD]/[YYYY-MM-DD]/[cursor]` (30/page). **Critical companion:** `/pubs/[server]/[from]/[to]/[cursor]` maps a preprint to its later journal DOI — this is how you avoid leaking the published version | S3 requester-pays `s3://biorxiv-src-monthly/` (you pay egress) | `UNVERIFIED` — none documented | Per-preprint; the `license` field is returned in `/details` |
| **UniProt** | `https://rest.uniprot.org/uniprotkb/search` | ✅ `date_created:[2012-10-01 TO *]`, `date_modified:[… TO 2019-03-01] AND active:true`, `date_sequence_modified`. **No publication-date field** | ✅ **UniSave is the only per-entry API time machine**: `https://rest.uniprot.org/unisave/{acc}?versions=1,3-8` returns `firstReleaseDate` / `lastReleaseDate` per version. Release archive `…/previous_releases/release-YYYY_NN/` — ⚠️ **currently only reaches back to 2022_04**, so for a 2018 cutoff UniSave is your only option | No numeric limit published; `size` max 500/page | CC BY 4.0 |

#### Tier B — version-pinned endpoint (the API itself is time-travelable)

| Resource | Pin mechanism | For a 2018 cutoff | Notes |
|---|---|---|---|
| **STRING** | `https://version-<MAJOR>-<MINOR>.string-db.org/api/…` | **`https://version-10-5.string-db.org/`** (live 2017-05-14 → 2019-01-19) | Documented limit: *"wait one second between each call"*. CC BY 4.0, and the access page **explicitly permits RAG and model training** provided metadata names STRING *and its version* |
| **Human Protein Atlas** | `https://v<N>.proteinatlas.org/` — and **the API works on archive hosts** | **`https://v18.proteinatlas.org/`** | ⚠️ `v25.proteinatlas.org` **302-redirects to current** — pin v24 or lower, or hash the file. CC BY 4.0, but the dump embeds **AlphaFold 3 content under CC BY-NC-SA 4.0** — a real redistribution hazard |
| **GTEx** | `datasetId` ∈ `{gtex_v8, gtex_v10, gtex_v11, …}` on `https://gtexportal.org/api/v2/` | `datasetId=gtex_v8` | ⚠️ **Defaults differ per endpoint — always pass it explicitly.** `gtex_v11` now exists; don't assume v10 is latest. Open-access files follow NIH GDS policy; **no named CC licence — `UNVERIFIED`** |

#### Tier C — pin a dated archive, filter offline

These have **no date filter in the API**.
Download the release, load it into DuckDB, and filter there.

| Resource | Archive URL pattern | Pin for 2018 | Size / notes | Licence |
|---|---|---|---|---|
| **ChEMBL** | `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_<N>/` — **every release from `chembl_08` to `chembl_37` is retained** | **`chembl_24`** | `chembl_37_sqlite.tar.gz` 5.8 GB; `_mysql` 2.1 GB; `.sdf.gz` 931 MB. Current release is ChEMBL_37 (2026-05-01) | **CC BY-SA 3.0 — share-alike is viral.** A derived benchmark containing ChEMBL data must be released compatibly |
| **InterPro / Pfam** | `https://ftp.ebi.ac.uk/pub/databases/interpro/releases/<NN>.0/`; Pfam at `…/Pfam/releases/Pfam<VER>/` | nearest release ≤ C | `interpro.xml.gz` 43 MB; `protein2ipr.dat.gz` **12.8 GB**; `match_complete.xml.gz` **54.9 GB** | **CC0** |
| **ChEBI** | `https://ftp.ebi.ac.uk/pub/databases/chebi/archive/rel<NNN>/` (monthly) | nearest `rel` ≤ C | `chebi.owl` 65 MB; `chebi.sdf.gz` 140 MB. `compounds.tsv.gz` carries `modified_on` + `release_date` for offline filtering | CC BY 4.0 (the binding `LICENSE` file; the `flat_files/README` prose erroneously says ShareAlike). **Attribution must name the release number** |
| **Rhea** | `https://ftp.expasy.org/databases/rhea/old_releases/<NN>.tar.bz2` — **releases 100–143 all present** | nearest ≤ C | 104–404 MB. Current release 143 (2026-11-04) | CC BY 4.0, commercial use explicit. ⚠️ Cloudflare — set a real User-Agent, and Rhea asks for a contact email in it |
| **Reactome** | `https://download.reactome.org/<VERSION>/` | `UNVERIFIED` whether 2018-era version numbers are retained — Zenodo archives only ≥v89 | `biopax.zip` 157 MB; `reactome.graphdb.tgz` 433 MB. ⚠️ `…/current/…` returns **403** — always use the explicit number | **Data CC0** (cleanest of the set) |
| **AlphaFold DB** | `https://ftp.ebi.ac.uk/pub/databases/alphafold/v<N>/` | version ≤ C | `UP000005640_9606_HUMAN_v6.tar` 4.8 GB. ⚠️ **Per-entry web files are NOT version-archived** — `AF-P00520-F1-model_v4.cif` **404s**; only the FTP tars give history | CC BY 4.0 |
| **BindingDB** | ⚠️ `…/downloads/BindingDB_All_<YYYYMM>_tsv.zip` keeps only the **two most recent months**. Durable pinning is the **UC San Diego Library quarterly archive**, which BindingDB itself recommends for "documentably training an AI": `https://library.ucsd.edu/dc/collection/bb03870458`, DOI `10.6075/J0HD7VVF` | a UCSD-archived release ≤ C | TSV 567 MB. **The bulk TSV has `Date of publication` AND `Date in BindingDB`** — use the latter for a strict knowable-at-the-time split | Curated data CC BY 3.0; **ChEMBL-imported subset CC BY-SA 3.0** (viral) |
| **IUPHAR / GtoPdb** | `https://www.guidetopharmacology.org/DATA/public_iuphardb_v<YYYY>.<N>.zip` — **downloadable without login**; verified 2019.5 → 2026.3 | **`public_iuphardb_v2019.5.zip`** (earliest archived) | 34 MB. Flat CSVs also keyless: `…/DATA/{targets_and_families,interactions,ligands}.csv` | ⚠️ **ODbL + CC BY-SA 4.0**, and *"commercial organisations that use GtoPdb must pay access-fees"* |
| **LIPID MAPS** | ⚠️ **No server-side dated snapshot.** The page labels the file by date but the URL and filename are undated | Download once, record the displayed release date + SHA256 | `…/files/?file=LMSD&ext=sdf.zip` 20.9 MB | CC BY 4.0; the `lipidmaps_ids_cc0` TSV is CC0. Least restrictive here |
| **ARCHS4** | Pin an explicit version: `human_gene_v2.6.h5` (50.0 GB, 2026-06-14). Version→URL map in `archs4py/data/config.json` | an explicit `v2.x` ≤ C | ⚠️ **Never use `human_gene_v2.latest.h5`** — it moved on 2026-11-06 and is `archs4py`'s default. The download page is stale and disagrees with live S3 headers — hash it yourself | ⚠️ **CC BY-NC-SA 4.0** — non-commercial **and** share-alike |
| **Pharos / TCRD** | Pharos SQL `https://opendata.ncats.nih.gov/public/pharos/archive/pharos<NNN>.sql.gz`; TCRD MySQL `http://habanero.health.unm.edu/tcrd/download/old_versions/TCRDv<X>.sql.gz` | nearest TCRD version ≤ C | ⚠️ The live API serves a **rolling build** — self-host a dump or you are not reproducible. No TCRD dump newer than v6.13.4. Each dump's `.README` names the exact upstream releases loaded — **your best date provenance**. The UNM host is **HTTP only**; the `juniper` mirror is dead | ⚠️ **No single licence** — aggregates ChEMBL (CC BY-SA), DrugCentral, DTO. Per-source terms in `TCRDv6_DataSourcesLicenses.xlsx` |
| **Open Targets** | `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/<YY.MM>/output/<dataset>/`; also `gs://`, `s3://`, BigQuery | nearest ≤ C | ~44 GB across 60 datasets (26.09). ⚠️ **Schema break at 25.03** (snake_case, `output/etl/parquet/` dropped) and **Parquet-only from 25.03**. Integrity file `release_data_integrity` with per-file SHA1 | **CC0** overall; ⚠️ per-datasource caveats — ChEMBL and HPA enter as CC BY-SA 3.0 and can contaminate a redistributed derivative |
| **Open Targets Genetics** | **Merged into the Platform in release 25.03 (19 Mar 2025); UI deprecated 9 Jul 2025; the GraphQL API is dead** (`api.genetics.opentargets.org` fails to resolve) | ✅ `https://ftp.ebi.ac.uk/pub/databases/opentargets/genetics/22.09/` — the **frozen final release is itself a good pre-cutoff snapshot** | Releases `190303` … `22.09` | CC0 |
| **GWAS Catalog** | `https://ftp.ebi.ac.uk/pub/databases/gwas/releases/<YYYY>/<MM>/<DD>/` (biweekly, 2016→2026) | `2019/01/<DD>/` | 🔑 **The flat file solves the date problem.** `gwas-catalog-download-studies-v1.0.3.1.tsv` (124 MB) has three cutoff axes: `DATE` (publication), **`DATE ADDED TO CATALOG`** (curation — the correct one), `SUBMISSION DATE`. **Use this, not the API** | ⚠️ **Mixed.** Curated metadata is under EMBL-EBI general terms — **not CC0, not a named open licence**. Summary statistics **are CC0** "unless otherwise stated" |
| **HMDB** | ⚠️ **No versioned archive at all** — the path is literally `/system/downloads/current/` | Self-archive + SHA256, nothing else is possible | ⚠️ **No documented REST API.** Behind a Cloudflare managed challenge; every programmatic fetch returned 403 during research. A human must fetch it in a real browser | 🔴 **CC BY-NC 4.0 + explicit prohibition on commercial redistribution.** Ship HMDB IDs and a download script, **never the data** |

#### Notes on two specific resources

**ChEMBL has a date filter, and it fails open.**
This is the single most dangerous API behaviour in the whole set.

| Query | `total_count` | Verdict |
|---|---|---|
| `activity?format=json&limit=1` (baseline) | 24,527,044 | — |
| `activity?…&document_year__lte=2018` | 8,553,530 | ✅ works |
| `document?…&year__lte=2018` | 78,857 | ✅ works |
| `activity?…&chembl_release__chembl_release=CHEMBL_24` | 24,527,044 | ❌ **silently ignored** |
| `activity?…&bogusfield__lte=2018` | 24,527,044 | ❌ **silently ignored, HTTP 200** |

A typo in your cutoff filter silently disables it and returns the full, post-cutoff dataset with a 200.
**Every ChEMBL wrapper must assert `filtered_count < unfiltered_count` on every call** and raise otherwise.
Also: use `?format=json`, not the `.json` suffix — the suffix form returned HTTP 500 from EBI during testing.
Better still, do not use the live API for benchmark runs at all; load `chembl_24` locally.

**Metabolite QTLs do not exist as a product.**
Neither GWAS Catalog nor Open Targets has an mQTL type — `StudyTypeEnum` is `eqtl, gwas, pqtl, sceqtl, scpqtl, scsqtl, sqtl, tuqtl` with **no metabolite entry**.
Metabolite work enters as ordinary GWAS annotated with **`EFO_0004725` "metabolite measurement"**.
The cheapest path is the harmonised filename convention `<PMID>-<GCST>-<EFO_ID>.h.tsv.gz`: grep the 12.4 MB `harmonised_list.txt` for `EFO_0004725` and you get **294 metabolite-trait summary-statistics files with zero API calls**.
Do not depend on the GWAS Catalog REST API for this — v1 is **HTTP 410 Gone** (retired August 2026) and most v2 endpoints were returning **HTTP 500** on 2026-11-07 while FTP was 100% reliable.

#### Auth summary

| Needs a key or registration | Genuinely key-free |
|---|---|
| **IUPHAR/GtoPdb** — API key + registration required (`GTP-API-Key` header); the website itself now requires login. The **bulk dumps and flat CSVs do not** | UniProt, InterPro/Pfam, RCSB, PDBe, AlphaFold DB, ChEMBL, BindingDB REST, ChEBI, Rhea, Reactome, STRING, GTEx, HPA, Open Targets, GWAS Catalog, Europe PMC, bioRxiv/medRxiv, Pharos GraphQL, LIPID MAPS |
| **OpenAlex** — technically keyless but the keyless budget is $0.10/day shared per IP; get a free key ($1/day) | ARCHS4 (bulk H5 download, no key) |
| **GTEx controlled tier** — dbGaP `phs000424`, DUC required. The open tier needs nothing | HMDB (no key — but Cloudflare-blocked in practice, and NC-licensed) |

#### Documented rate limits (the rest are `UNVERIFIED`)

| Resource | Limit |
|---|---|
| Europe PMC | ~10 req/s (500/min) per IP — official forum, not a docs page |
| OpenAlex | 10 / 30 / 50 req/s by tier, plus a USD/day budget |
| GWAS Catalog | 100 req/min **and** 15 req/s per IP; above either → HTTP 429 |
| STRING | *"wait one second between each call"* (~1 req/s) |
| IUPHAR/GtoPdb | ~60 req/min |

Rate limits for InterPro, ChEBI, Rhea, Reactome, UniProt, PDBe, AlphaFold, BindingDB, LIPID MAPS, HPA, GTEx, ARCHS4, Pharos, Open Targets, RCSB, ChEMBL and bioRxiv are **`UNVERIFIED` — not published.**
Default every wrapper to 1 req/s with exponential backoff and you will not have to find out.

### 2.4 Known-dead and corrected URLs

Worth checking against any older guide you find.

| Dead | Use instead |
|---|---|
| `snapshots.rcsb.org` (NXDOMAIN) | `s3://pdbsnapshots/` or `https://snapshots.pdbj.org/` |
| `ftp.wwpdb.org` (unreachable); FTP protocol deprecated 2024-11-01 | `https://files.wwpdb.org/pub/pdb/` or rsync |
| `https://api.genetics.opentargets.org/graphql` | Merged into `https://api.platform.opentargets.org/api/v4/graphql` |
| `https://www.ebi.ac.uk/gwas/rest/api/studies` (v1) → **HTTP 410 Gone** | `https://www.ebi.ac.uk/gwas/rest/api/v2` — but prefer the FTP flat files |
| `https://download.reactome.org/current/…` → **403** | Explicit version number |
| `https://www.ebi.ac.uk/chembl/api/data/*.json?...` (suffix form) → intermittent 500 | `?format=json` |
| `http://juniper.health.unm.edu/tcrd/download/` | `http://habanero.health.unm.edu/tcrd/download/` (**HTTP only**, port 443 refused) |
| `https://maayanlab.cloud/custom/rooky` (ARCHS4 signature API) → 307 → 405 | Bulk H5 + `archs4py` |
| `europepmc.org/*` HTML → 403 to non-browser clients | The REST service at `www.ebi.ac.uk/europepmc/webservices/rest/` (bare `/rest/` is 404) |
| `dude.docking.org` — **unreachable from two network paths on 2026-11-07** (`UNVERIFIED` whether transient) | `dudez.docking.org` was fine. Do not plan around DUD-E being live |

`ftp.expasy.org`, `www.rhea-db.org`, `hmdb.ca` and `www.lipidmaps.org` sit behind Cloudflare and reject bare `curl` — send a browser User-Agent.

---

## 3. Scientific compute tools

Versions below were read from the live PyPI/anaconda.org/GitHub APIs on 2026-11-07, not recalled.

### 3.1 Master table

| Tool | Package (exact) | Version | Install | Native Win | GPU | Licence |
|---|---|---|---|---|---|---|
| RDKit | PyPI/cf `rdkit` | 2026.9.1 / cf 2026.09.2 | `uv pip install rdkit` | ✅ | CPU | BSD-3 |
| Open Babel | PyPI/cf `openbabel` | 3.2.1 | `uv pip install openbabel` | ✅ | CPU | **GPL-2.0-only** |
| AutoDock Vina CLI | GitHub binary | 1.2.7 | `vina_1.2.7_win.exe` | ✅ | CPU | Apache-2.0 |
| Vina Python API | PyPI `vina` | 1.2.7 | `uv pip install -U numpy vina` | ❌ | CPU | Apache-2.0 |
| Meeko (ligand prep) | PyPI `meeko` | 0.8.0 | `uv pip install meeko` | ✅ | CPU | LGPL-2.1 |
| smina | cf `smina` | 2020.12.10 | `conda install -c conda-forge smina` | ✅ | CPU | Apache code / **GPLv2 binary** |
| gnina | GitHub / Docker | v1.3.3 | binary or `gnina/gnina` image | ❌ | **CUDA ≥12.0** | **GPL** |
| DiffDock-L | none (Docker) | v1.1.3 (2024-09-04) | `docker pull rbgcsail/diffdock` | ❌ | GPU rec. | MIT |
| **Boltz-2** | PyPI **`boltz`** | 2.2.1 | `pip install boltz[cuda] -U` (Linux) | ✅ *without* `[cuda]` | 24 GB rec. | **MIT** ✅ |
| Chai-1 | PyPI `chai_lab` | 0.6.1 | `pip install chai_lab==0.6.1` | ❌ | A100/H100 80 GB rec. | **Apache-2.0** ✅ |
| ESMFold (HF route) | `transformers` | 5.22.2 | `pip install -U transformers accelerate` | likely, `UNVERIFIED` | 16–24 GB | MIT |
| ESMFold2 | PyPI `esm` | 3.4.2 | `pip install esm` | ❌ (fused=Linux) | **24 GB+** | **MIT** |
| ColabFold | PyPI `colabfold` | 1.6.3 | see §3.6 | ❌ | 16 GB → ~2000 res | MIT / AF2 weights CC BY 4.0 |
| **Foldseek** | **bioconda** `foldseek` | 10-941cd33 | `conda install -c conda-forge -c bioconda foldseek` | ❌ | CPU (opt. CUDA) | GPL-3.0 |
| HMMER | bioconda `hmmer` | 3.4 | `conda install -c bioconda hmmer` | ❌ | CPU | BSD-3 + SIMD sublicence |
| pyhmmer | PyPI `pyhmmer` | 0.12.3 | `uv pip install pyhmmer` | ✅ (experimental) | CPU | MIT/BSD |
| fpocket | **conda-forge** `fpocket` | 4.2.3 | `conda install -c conda-forge fpocket` | ❌ | CPU | MIT |
| P2Rank | GitHub tarball | **2.5.1** | tarball + **Java 17–23** | ✅ (`prank.bat`) | CPU, ~1 GB RAM | MIT |
| PLIP | PyPI/cf `plip` | 3.0.1 | `uv pip install plip` | ✅ (now) | CPU | **GPL-2.0-only** |
| ProLIF | `prolif` | 2.2.3 | `uv pip install rdkit prolif` | ✅ | CPU | Apache-2.0 |
| OpenMM | cf + PyPI `openmm` | 8.6.1 | `conda install -c conda-forge openmm` | ✅ **incl. CUDA** | CPU ok | LGPL-3.0+ |
| AmberTools (MM-GBSA) | cf `ambertools` | 26.0 | `conda install -c conda-forge ambertools=26` | ❌ **never** | CPU | GPL |
| DeepCoy | git only | — (2024) | clone + conda env | ❌ | TF 1.10 | BSD-3 |
| scikit-learn | `scikit-learn` | 1.9.1 | `pip install -U scikit-learn` | ✅ | CPU | BSD-3 |

### 3.2 Cheminformatics core

```bash
uv pip install rdkit openbabel meeko prolif scikit-learn
```

Verify:

```bash
python -c "import rdkit; from rdkit import Chem; print(rdkit.__version__, Chem.MolFromSmiles('CCO').GetNumAtoms())"
obabel -V
python -c "from openbabel import pybel; print(pybel.readstring('smi','CCO').write('can'))"
mk_prepare_ligand.py --help
python -c "import prolif; print(prolif.__version__)"
python -c "import sklearn; from sklearn.calibration import CalibratedClassifierCV; print(sklearn.__version__)"
```

Packaging notes that will cost you an hour each if you miss them:

- **`rdkit-pypi` is dead** (last real release 2022). The package is `rdkit`.
- **Open Babel's PyPI wheel now bundles the CLI** — `obabel.exe`, `obrms`, `obgen` and the format plugins all ship inside the wheel. `openbabel-wheel` is superseded; bioconda's `openbabel` is abandoned at 2.4.1. Open Babel's own docs still link to a GitHub Windows installer whose releases have **zero assets**.
- Open Babel **3.2.1 is a security release** fixing CVE-2026-54751. Pin `>=3.2.1` if you parse untrusted structure files — which, downloading from the PDB, you do.
- **`pip install prolif` alone is broken.** ProLIF imports RDKit at module load but RDKit is absent from its `dependencies`. The official command is literally `pip install rdkit prolif`.
- **scikit-learn ≥1.8 removed `cv="prefit"`** — not deprecated, *removed*, and ≥1.9 requires Python ≥3.11. Existing calibration code raises. The replacement:

  ```python
  from sklearn.calibration import CalibratedClassifierCV
  from sklearn.frozen import FrozenEstimator
  calibrated = CalibratedClassifierCV(FrozenEstimator(base_clf)).fit(X_calib, y_calib)
  ```

  When wrapping in `FrozenEstimator`, **all** provided data is used for calibration — keeping fit and calibration data disjoint is now your responsibility.
  `method` also gained a third option in 1.8: `'sigmoid'` (default), `'isotonic'` (overfits below ~1000 calibration samples), and **`'temperature'`** (natively multiclass, the only one with Array API support).

### 3.3 Docking

```bash
# CLI — works on Windows
curl -LO https://github.com/forlilab/AutoDock-Vina/releases/download/v1.2.7/vina_1.2.7_linux_x86_64
chmod +x vina_1.2.7_linux_x86_64 && ./vina_1.2.7_linux_x86_64 --version

# Python API — Linux/macOS only
uv pip install -U numpy vina
python -c "from vina import Vina; print('ok')"

conda install -c conda-forge smina && smina --version
```

The Vina repo **moved** from `ccsb-scripps/AutoDock-Vina` to **`forlilab/AutoDock-Vina`**.
The PyPI `vina` wheel ships only manylinux and musllinux — there is **no native-Windows Python binding** and none on conda-forge. Use WSL2.
`smina` is David Koes' Vina fork (not CCDC — CCDC makes GOLD); the conda-forge build is the only current route and *does* have a `win-64` package.

**gnina** (CNN rescoring, GPU):

```bash
curl -LO https://github.com/gnina/gnina/releases/download/v1.3.3/gnina.cuda12.8.static
chmod +x gnina.cuda12.8.static && ./gnina.cuda12.8.static --version
# or
docker run --rm --gpus all -v "$PWD:/data" -w /data gnina/gnina:latest gnina --version
```

v1.3.3 ships **exactly one asset**, `gnina.cuda12.8.static` (2.06 GB), and **dropped the older-CUDA compat binary** that v1.3.2 had — fall back to v1.3.2 if your driver predates CUDA 12.8.
The Docker image is **~24 GB**.
No native Windows; the README explicitly supports WSL2 and there is a documented WSL2 Ubuntu 22.04 build recipe.
**VRAM requirement is `UNVERIFIED` — not documented anywhere.** Measure it.

**DiffDock-L**: no PyPI package, last release **2024-09-04**, and the conda env is a 2023 fossil (`python=3.9.18`, `torch==1.13.1+cu117`, `fair-esm[esmfold]==2.0.0` → `deepspeed==0.5.9`) that will almost certainly not solve in 2026.
**Docker is the only practical route**: `docker pull rbgcsail/diffdock` (3.67 GB).
VRAM `UNVERIFIED`.

**Licensing chain to be aware of:** Open Babel is GPL-2.0, and smina, gnina and PLIP all link it.
Their distributed binaries are effectively **GPLv2**.
Shelling out to the CLI is safe; `import`ing them into a distributed product is not.
MGLTools/ADFRsuite were **re-licensed in 2026** under a "Sannerlab MIT-like Source-Available License v1.0": commercial use is now permitted, but it is **not OSI-approved**, **Schrödinger Inc. is excluded entirely** (including from benchmarking), and **MSMS remains non-commercial-only**.
Read https://sannerlab.github.io/software/license.html before any commercial deployment.
You can avoid the whole question by using Meeko instead of MGLTools for receptor and ligand prep.

### 3.4 Co-folding and affinity

**Boltz-2 — the one to install first.**
MIT for both code and weights, verbatim: *"can be freely used for both academic and commercial purposes."*
No other co-folding + affinity model has that.

```bash
pip install boltz -U            # Windows, CPU, or non-CUDA GPU
pip install boltz[cuda] -U      # Linux with CUDA — fast kernels
boltz predict --help
pip show boltz                  # version; boltz.__version__ is UNVERIFIED
```

⚠️ **`pip install boltz[cuda]` fails on native Windows** — `cuequivariance_ops_cu12` publishes manylinux wheels only, no `win_amd64`, no sdist.
On Windows use plain `pip install boltz` with a CUDA torch build, and accept the slower path, or move to WSL2.

VRAM, from UCSF ChimeraX's own measurements (the best figures available; the README publishes none):

| VRAM | Approximate capacity |
|---|---|
| 8 GB | ~300–700 residues |
| 12 GB | up to ~1000 residues |
| **24 GB** | **~1300 residues in ~4 minutes** |
| 24 GB + low-memory optimisations | 1300 → 2200; with chunking up to 2500 |

bfloat16 buys ~40% more.
OOM levers: lower `--diffusion_samples`, lower `--recycling_steps`.
Interestingly, **Windows degrades more gracefully than Linux** — it falls back to CPU memory (10–30× slower) where Linux simply OOMs and fails.

**There is no Boltz-3.** `boltz` 2.2.1 (2025-09-08) is still the newest open release, confirmed against the official news feed.
BoltzGen (binder design, MIT, `pip install boltzgen`) is the other open release.
BoltzMol-1 and BoltzProt-1 (June 2026) are **not** labelled open-source and appear to be hosted-API-only — `UNVERIFIED`.

**Chai-1**: `pip install chai_lab==0.6.1`. Linux required, A100/H100 80 GB or L40S 48 GB recommended; RTX 4090 (24 GB) reported working.
⚠️ **The non-commercial restriction is gone** — the current LICENSE is plain Apache-2.0 with no field-of-use clause.
Third-party sources still describing Chai-1 as non-commercial are quoting the original September-2024 terms.
Last release 0.6.1 (2025-03-18) but `main` is actively committed to, so the git install may be well ahead.
**Chai-2 is closed** — no open weights, no public API.

### 3.5 Structure prediction

**Do not use `fair-esm[esmfold]`** — the repo is archived, the `esmfold` extra pins `deepspeed==0.5.9` (Dec 2021) and Python ≤3.9.
It is also a **name-collision trap**: `fair-esm` imports as `esm`, the same top-level name as the current `esm` package. Never co-install them.

| Route | Install | VRAM |
|---|---|---|
| ESMFold via HuggingFace (the working legacy route) | `pip install -U transformers accelerate` | *"about 16-24GB… depending on protein length"* (HF notebook, verbatim). Levers: `model.esm.half()`, `model.trunk.set_chunk_size(64)` |
| ESMFold2 / ESMC (current generation) | `pip install esm` (PyPI `esm` 3.4.2, repo now `github.com/Biohub/esm`). ~5.6 GB install | *"a GPU with 24GB of memory or more"* (verbatim). 6.6B params. Default `num_diffusion_samples=32` exceeds most consumer GPUs; 8 samples fits a 24 GB card |

⚠️ **The ESM3 non-commercial trap is gone.** The LICENSE at `Biohub/esm` is MIT ("Copyright 2026 Chan Zuckerberg Biohub"); no Cambrian Open License anywhere.
ESMFold2's data cutoff is Sept 2021 — convenient for a 2018 benchmark, but note it is not zero.

### 3.6 ColabFold

LocalColabFold is now **pixi-based**, not the old `install_colabbatch_linux.sh`:

```bash
sudo apt -y install curl git wget
curl -fsSL https://pixi.sh/install.sh | sh
git clone https://github.com/YoshitakaMo/localcolabfold.git
cd localcolabfold && pixi install && pixi run setup
bash run_colabfoldbatch_sample.sh     # folds 1BJP_1.fasta
```

Upstream's own pip route:

```bash
conda create -n colabfold -c conda-forge -c bioconda python=3.13 mmseqs2=18.8cc5c
conda activate colabfold
pip install colabfold[alphafold,openmm] jax[cuda12] openmm[cuda12]
```

**No native Windows** — `pyproject.toml` declares `linux-64`, `linux-aarch64`, `osx-arm64` only; the README supports WSL2.
**WSL2 gotcha**, verbatim from the README: if install fails with symlink errors, run in *Windows PowerShell* (not WSL):

```powershell
fsutil file SetCaseSensitiveInfo path\to\localcolabfold\installation enable
```

GPU: *"For GPUs with ~16G the max length is ~2000."*
**No multi-GPU** — select with `CUDA_VISIBLE_DEVICES`.
Required exports: `TF_FORCE_UNIFIED_MEMORY=1`, `XLA_PYTHON_CLIENT_MEM_FRACTION=4.0`, `XLA_PYTHON_CLIENT_ALLOCATOR=platform`, `TF_FORCE_GPU_ALLOW_GROWTH=true`.

The public MMseqs2 MSA server has **no published numeric rate limit** (`UNVERIFIED`), only the statements *"queries [must be] serial from a single IP"* and *"large-scale structure predictions should not be done with the public MSA server"*.
For batches run local `colabfold_search` — which needs **940 GB disk** and ~128 GB RAM.

**AF2 weights are CC BY 4.0, not CC BY-NC** — including Multimer. There is no non-commercial trap here.

### 3.7 Homology — Foldseek and HMMER

**Foldseek** is the highest-value tool in §3 for this project: it supplies the mandatory nearest-structural-neighbour baseline and is the main structural signal for proteins with no sequence homologue.

```bash
conda install -c conda-forge -c bioconda foldseek
# or static binary:
wget https://mmseqs.com/foldseek/foldseek-linux-avx2.tar.gz
tar xvzf foldseek-linux-avx2.tar.gz && export PATH=$(pwd)/foldseek/bin/:$PATH

foldseek version
foldseek easy-search example/d1asha_ example/ aln.m8 tmp
```

⚠️ **There is no conda-forge `foldseek`** — it is **bioconda-only**; the `-c conda-forge` in the README only satisfies dependencies.
No `win-64` on any channel. WSL2 or Docker (`quay.io/biocontainers/foldseek`).

Database download — **the CLI names differ from the web-server names, and this trips everyone**:

```bash
foldseek databases                      # list valid names
foldseek databases --tsv 1              # same, tab-separated
foldseek databases PDB pdb tmp
foldseek databases Alphafold/Proteome afdb tmp
foldseek databases Alphafold/Swiss-Prot afsp tmp
```

Valid CLI names are `Alphafold/UniProt`, `Alphafold/UniProt50`, `Alphafold/Proteome`, `Alphafold/Swiss-Prot`, `ESMAtlas30`, `PDB`.
**`AFDB50`, `AFDB-Proteome` and `AFDB-SwissProt` are rejected** — those are web-server names.
`CATH50`, `BFVD`, `PDB100` are web-server-only; build them yourself with `foldseek createdb`.

**RAM, not VRAM, is the constraint**: `(6 B Cα + 1 B 3Di + 1 B AA) × database residues`.
AFDB50 (54M entries) needs **151 GB RAM** by default, **35 GB** with `--sort-by-structure-bits 0`, or use `--prefilter-mode 1` which is not memory-limited and is best for single queries.
GPU is optional (`--gpu 1`, needs a padded DB via `foldseek makepaddedseqdb`) and requires **Ampere or newer**; precompiled binaries will not run on Volta or Pascal.
GPU VRAM requirement is `UNVERIFIED`.

**L1/L2 note:** the hosted Foldseek server at `search.foldseek.com` has no date control.
For benchmark runs, build your own DB from the pinned PDB snapshot (`s3://pdbsnapshots/20190101/`) so the search space itself is date-correct.
This closes **L5** (structure leakage) at the same time.

**HMMER / pyhmmer.**
HMMER has **no native Windows** — explicitly unsupported upstream (pthreads, POSIX signals; `hmmpgmd` cannot work on Windows at all).

```bash
conda install -c bioconda hmmer        # Linux/macOS/WSL2
hmmsearch -h | head -3                  # "# HMMER 3.4 (Aug 2023)"

uv pip install pyhmmer                  # the native-Windows route
python -c "import pyhmmer; print(pyhmmer.__version__)"
```

**pyhmmer now ships `win_amd64` wheels** (x86-64 only, no Windows ARM64) and has supported Windows since v0.12.0 — this is the single biggest correction to the usual guidance.
It is marked *experimental*, tested only against pyhmmer's own suite, and there is a **documented deadlock risk** if file-like-object I/O runs on the main thread without releasing the GIL.
The pyhmmer install docs still say "use WSL instead"; the dedicated Windows guide and the wheel inventory are newer and authoritative.
For zero risk, WSL2 remains the conservative choice.
HMMER 3.4 (2023-08-15) is still the only release; HMMER4 is branch-only.

### 3.8 Pockets and interactions

```bash
conda install -c conda-forge fpocket     # NOT bioconda — bioconda 404s
fpocket -f 1uyd.pdb

wget https://github.com/rdk/p2rank/releases/download/2.5.1/p2rank_2.5.1.tar.gz
tar -xzf p2rank_2.5.1.tar.gz && cd p2rank_2.5.1
./prank predict -f test_data/1fbl.pdb    # or prank.bat on Windows

uv pip install plip && plip -h | head -2
```

| Tool | Gotcha |
|---|---|
| **fpocket** | conda-forge only (no bioconda, no `win-64`). **Has no `--version` and no `--help`** — and its usage banner is **hardcoded "fpocket 4.0"** even in 4.2.3. Read the version from `conda list fpocket`. Docker `fpocket/fpocket` is the upstream-recommended non-Linux route |
| **P2Rank** | **No conda package exists on any channel** — verified three ways. Tarball only. **Java 17–23** for 2.5.1 (`master` says 17+, tested to 26). **Native Windows works** — `prank.bat` ships in `distro/`; upstream suggests running from Git Bash. ⚠️ **2.6-alpha is listed first on the releases page but 2.5.1 is still flagged "Latest" — pin 2.5.1.** Use `prank predict -c alphafold` for predicted structures |
| **PLIP** | **No `--version` flag** — it is in the argparse description, or `plip.basic.config.__version__`. Historically painful on Windows because of Open Babel bindings; now workable since `openbabel` 3.2.1 ships `win_amd64` wheels. ⚠️ The README's Windows Docker command contains a bash-ism (`-u $(id -u ${USER})`) that will not expand in cmd/PowerShell |
| **ProLIF** | See §3.2 for the RDKit dependency bug. Apache-2.0, **but MDAnalysis is GPL-2.0+** and propagates if you bundle |

Pocket detection is load-bearing for the `sham-pocket` and `designed-void` negative controls in [04-EVALUATION.md §5.1](04-EVALUATION.md#51-negative-controls-must-fail-to-produce-confident-answers).
Run both fpocket and P2Rank: disagreement between a geometric and an ML pocket finder is itself a useful abstention signal on cryptic sites.

### 3.9 MD and MM-GBSA

```bash
conda install -c conda-forge openmm parmed openmmforcefields openff-toolkit-base openff-forcefields
python -m openmm.testInstallation      # detects GPU platforms and cross-checks consistency

# Linux/macOS ONLY
conda install -c conda-forge ambertools=26
```

**OpenMM runs natively on Windows including CUDA** — conda-forge has `win-64` 8.6.1 and PyPI publishes an `OpenMM-CUDA-12` `win_amd64` wheel.
`pip install openmm` gives OpenCL + CPU only; use `pip install openmm[cuda12]` or `conda install -c conda-forge openmm cuda-version=12`.

**The MM-GBSA half is a WSL2-only story.**
AmberTools has **never** had a `win-64` build, so `MMPBSA.py`, `gmx_MMPBSA` and the AmberTools-backed charge methods in the full `openff-toolkit` are all unavailable on Windows.

There is one native-Windows MM-GBSA path, and it is worth knowing:
`AmberPrmtopFile.createSystem(implicitSolvent=...)` accepts `HCT`, `OBC1`, `OBC2`, `GBn`, `GBn2` plus `implicitSolventSaltConc`.
A hand-rolled single-trajectory MM-GBSA (complex/receptor/ligand energies with GBn2) therefore needs **OpenMM + ParmEd only**.
The trade-off is that you reimplement the decomposition and entropy bookkeeping yourself.

Packaging notes: the package is **`openmmforcefields`, one word** — `openmm-forcefields` does not exist.
`parmed` on PyPI is **sdist-only** at 4.3.1 (no wheels, needs a C compiler) — install it from conda-forge on Windows.
`openmmforcefields` vendors the AMBER force-field files from AmberTools 24.8, so you do **not** need AmberTools installed just to use `ForceField('amber14-all.xml')`.

⚠️ **Amber ≠ AmberTools.**
AmberTools26 is free and mostly GPL.
**Amber26 is a separate paid product** — $0 academic, **$25,000 industrial**, $2,000 for not-for-profit computing centres — and the licence *"applies to commercial and non-commercial users alike"*.
`MMPBSA.py` and `gmx_MMPBSA` are both GPL-3.0.
Also note the conda-forge AmberTools build **lacks CPU-parallel and CUDA support** — upstream says so explicitly.

### 3.10 Decoys

Needed for **L6** — the decoy-separability control, where a logistic model on physicochemical descriptors alone must score near chance.

| Source | Status |
|---|---|
| **DeepCoy** (`oxpig/DeepCoy`, BSD-3) | Clone + conda env. Pretrained models are off-GitHub and **verified reachable**: `https://opig.stats.ox.ac.uk/data/downloads/DeepCoy_pretrained_models.tar.gz` (369 MB). ⚠️ The env hard-pins **TF 1.10, CUDA 9.2, cuDNN 7.2.1, Python 3.6** and the dead `rdkit` Anaconda channel — **it will very likely not solve in 2026.** Linux-only even then. Given it is BSD-3, **reimplementing the property-matching is probably cheaper than resurrecting the environment** |
| **DUD-E** (`dude.docking.org`) | ⚠️ **Unreachable from two independent network paths on 2026-11-07** (connection refused on :443). `UNVERIFIED` whether transient. Also carries documented analogue bias / data leakage — exactly the failure [00-PROBLEM.md](00-PROBLEM.md) names. **No licence published**, citation-only |
| **DUDE-Z** (`dudez.docking.org`) | ✅ Live. Both a static dataset and an on-demand generator at `https://tldr.docking.org/` (login required for the service). 43 targets; property-matched = 2,312 ligands + 69,994 decoys. ⚠️ Maintainer caveat: `DUDE-Z-benchmark-grids/` is deprecated (broken symlinks) — use `DOCKING_GRIDS_AND_POSES/`. **No licence stated**, citation-only, commercial terms `UNVERIFIED` |

**Recommendation for this project:** generate property-matched decoys in-house with RDKit from the human metabolome reference set, and use DUDE-Z only as an external cross-check.
That is the only route whose licence we can state, whose availability we control, and whose property matching we can prove passes the L6 test.

---

## 4. Infrastructure

### 4.1 Environments

**`uv` for the Python layer** — fast, lockfile-based, works identically on Windows and Linux.

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv venv --python 3.11
uv pip install -r requirements.txt
uv lock && uv sync          # reproducible
```

**`pixi` for the conda layer.**
Foldseek, fpocket, HMMER, smina, AmberTools and OpenMM-with-CUDA are conda packages, not wheels.
`pixi` gives a lockfile across conda-forge and bioconda, which `conda` does not.

```bash
# Linux / macOS
curl -fsSL https://pixi.sh/install.sh | sh
# Windows PowerShell
powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
```

```toml
# pixi.toml
[project]
channels = ["conda-forge", "bioconda"]
platforms = ["linux-64", "win-64", "osx-arm64"]

[dependencies]
python  = "3.11.*"
rdkit   = "*"
openmm  = "*"

[target.linux-64.dependencies]
foldseek = "*"
fpocket  = "*"
hmmer    = "*"
smina    = "*"
```

Note the `[target.linux-64]` split: this is how you keep one manifest that works on the Windows dev box *and* installs the Linux-only tools on the compute host, rather than two divergent environment files.

**Rule:** one `uv.lock` and one `pixi.lock`, both committed.
An environment that is not locked is not a reproducible run record.

### 4.2 Docker

Required, not optional, for gnina, DiffDock-L and the PDBe graph server; strongly preferred for fpocket and PLIP on Windows.

| Image | Size | Use |
|---|---|---|
| `rbgcsail/diffdock` | 3.67 GB | The only practical DiffDock route |
| `gnina/gnina:latest` | ~24 GB | CNN docking |
| `fpocket/fpocket` | small | Upstream-recommended non-Linux route |
| `pharmai/plip:latest` | small | PLIP without the Open Babel dance |
| `quay.io/biocontainers/foldseek` | — | bioconda auto-build; **no official image from the project** |

On Windows, Docker Desktop with the WSL2 backend and GPU passthrough.
`--gpus all` for gnina is the standard NVIDIA Container Toolkit flag but is **not in gnina's own docs** — `UNVERIFIED`.

### 4.3 Compute dispatch

**Modal** — serverless GPU, the right answer for a hackathon because a judge needs no cluster account.

```bash
uv pip install modal
modal setup          # or: python -m modal setup
```

Modal bills you directly; Anthropic does not provide or bill compute when dispatched from Claude Science.
From Claude Science the constraints are: inputs ≤1 GiB per submit, outputs from `./out/` up to 5 GiB, default container timeout 12 h (max 23), 10 concurrent jobs, and **no spend ceiling** — set one on the Modal side.

**Slurm** — over plain SSH, using your existing `~/.ssh/config`, no agent installed on the host.
Claude Science submits via `sbatch` where present and runs detached processes otherwise.
Default job timeout 30 min, 100 concurrent, outputs pulled back, files >~100 MB left on the host.
⚠️ **PBS and LSF are explicitly not supported**, and remote jobs run **outside the sandbox as your user** — the usual care applies.

For our own scripts, keep dispatch behind one interface (`src/msf/compute/`) with three backends — `local`, `modal`, `slurm` — so that a benchmark run is defined by its inputs and seed, not by where it happened to execute.

### 4.4 Artifacts: DVC vs git-lfs

| | git-lfs | DVC |
|---|---|---|
| Good for | A handful of files under ~100 MB: a Pfam HMM, a pinned CSV, reference poses | Multi-GB snapshots, pipeline stages with dependency tracking, remote storage on S3/GCS |
| Bad for | Anything multi-GB — it bloats clones and GitHub LFS quota | Slight ceremony overhead for small files |

**Use both.**
git-lfs for small committed reference data; DVC for the pinned database snapshots.

```bash
uv pip install "dvc[s3]"
dvc init
dvc remote add -d store s3://msf-artifacts
dvc add data/snapshots/chembl_24.sqlite
git add data/snapshots/chembl_24.sqlite.dvc .gitignore
```

The `.dvc` file carries the md5 and goes in git — which is exactly the snapshot-provenance guarantee [04-EVALUATION.md](04-EVALUATION.md#0-principles) requires.
Record the upstream URL and your own SHA256 alongside it in `data/snapshots/MANIFEST.yaml`, because DVC's hash proves *you have the same bytes*, not *where they came from*.

The sealed split is a separate mechanism: an age-encrypted blob committed to git, unsealed only by `scripts/unseal.py`.
Do **not** put the sealed split in DVC — a remote-store ACL is a weaker guarantee than encryption at rest.

### 4.5 DuckDB + Parquet for run records and snapshots

DuckDB does two jobs here, and both matter.

**Job 1 — run records.**
Every tool call, every retrieved document with its date, every score, every seed.
Append to Parquet; query with SQL; no server.

```bash
uv pip install duckdb
python -c "import duckdb; print(duckdb.__version__); print(duckdb.sql('SELECT 42').fetchone())"
```

```sql
-- the L1 audit query: did anything post-cutoff reach the agent?
SELECT run_id, tool, doc_id, doc_date
FROM read_parquet('runs/*/retrievals.parquet')
WHERE doc_date > (SELECT cutoff FROM read_parquet('runs/*/prereg.parquet'))
-- must return zero rows
```

**Job 2 — serving the Tier-C snapshots.**
DuckDB reads Parquet, CSV, JSON and SQLite directly, and `httpfs` lets it read Parquet over S3 and HTTPS without downloading.
Open Targets ships Parquet natively (~44 GB, 60 datasets); the GWAS Catalog flat file, the BindingDB TSV and the ChEMBL SQLite all load in one statement.
This is how the ~20 resources with no API date filter get one:

```sql
CREATE VIEW gwas_pre_cutoff AS
SELECT * FROM read_csv('data/snapshots/gwas_2019_01/studies.tsv', delim='\t')
WHERE "DATE ADDED TO CATALOG" <= DATE '2018-01-01';
```

The date filter is then a property of the *view the tool reads*, not of the prompt — which is the whole point.

### 4.6 Caching

Three layers, with different invalidation rules.

| Layer | Key | Invalidated by | Store |
|---|---|---|---|
| **HTTP response cache** | URL + full query string + cutoff date | Never within a run; manually between snapshot versions | `requests-cache` SQLite, or an on-disk keyed store |
| **Computation cache** | `sha256(tool_version + input_files + parameters + seed)` | Any component of the key | Content-addressed directory under `.cache/`, tracked by DVC if large |
| **Agent context** | Prompt prefix | Per Anthropic's prompt-caching rules | Handled by the SDK |

Two rules that stop the cache becoming a leak:

1. **The cutoff date is part of every cache key.**
   Otherwise a `dev`-split query with no cutoff poisons a `sealed`-split lookup with post-cutoff content, and you will never find it.
2. **During a benchmark run the HTTP cache is read-only and the network is blocked.**
   A cache miss should *fail the run*, not silently fetch.
   This is what `tests/controls/test_snapshot_pinning.py` asserts.

---

## 5. Tiered setup path

### Tier 0 — 15 minutes, no GPU, no API keys

The point of Tier 0 is that a judge can clone the repo and reproduce *something real* before losing interest.
What it must demonstrate: the loop runs, the leakage controls actually block things, and the benchmark scoring works on a bundled sample.

```bash
# 1. uv
curl -LsSf https://astral.sh/uv/install.sh | sh           # or the PowerShell line in §4.1

# 2. environment
git clone <repo> && cd MetaboliteSensorFinder
uv venv --python 3.11 && uv sync

# 3. agent layer
uv pip install claude-agent-sdk
claude --version

# 4. the doctor
uv run python scripts/doctor.py --tier 0
```

| Works at Tier 0 | Does not |
|---|---|
| Claude Code + Agent SDK, subagents, skills, hooks | Any docking, co-folding or MD |
| RDKit, scikit-learn, DuckDB | Foldseek (bundle precomputed hits instead) |
| Europe PMC, RCSB, UniProt, bioRxiv over keyless REST (date-filtered) | Anything needing a snapshot >1 GB |
| **All leakage control tests** (`tests/controls/`) — these are pure logic | GPU anything |
| **The `dev`-split sample benchmark**, shipped as ~50 MB of Parquet | The `sealed` split (encrypted, requires a human key) |
| Calibration, abstention, and the popularity baseline | |

Everything in `tests/controls/` must pass at Tier 0.
That is deliberate: the controls are the claim, and the claim should be checkable without a GPU.

### Tier 1 — full CPU stack (1–3 hours, mostly download time)

```bash
# conda layer
pixi install                           # foldseek, fpocket, hmmer, smina, openmm (see §4.1)

# python layer
uv pip install rdkit openbabel meeko prolif plip pyhmmer duckdb "dvc[s3]"

# P2Rank (needs Java 17-23)
wget https://github.com/rdk/p2rank/releases/download/2.5.1/p2rank_2.5.1.tar.gz
tar -xzf p2rank_2.5.1.tar.gz

# pinned snapshots — the big download
uv run python scripts/fetch_snapshot.py --cutoff 2018-01-01
```

Snapshot budget for a 2018 cutoff, approximately:

| Snapshot | Size |
|---|---|
| ChEMBL 24 SQLite | ~4 GB |
| GWAS Catalog 2019/01 flat files | ~212 MB (lean) |
| GtoPdb 2019.5 | 34 MB |
| ChEBI, Rhea, Reactome, InterPro (core files only) | ~1.5 GB |
| PDB snapshot 20190101 — **sequences and headers only**, not full coordinates | ~5 GB |
| AlphaFold human proteome | 4.8 GB |
| Open Targets Genetics 22.09 (subset) | ~10 GB |
| **Total** | **~25–30 GB** |

Full PDB coordinates and AFDB50 are Tier 2 — they are 100 GB+ and 151 GB of RAM respectively.

Windows users: Tier 1 is where you need WSL2, because Foldseek, fpocket and HMMER have no Windows builds.

### Tier 2 — GPU and cloud

| Add | Requirement |
|---|---|
| **Boltz-2** | 24 GB VRAM for useful protein sizes. `pip install boltz[cuda]` on Linux; plain `pip install boltz` on Windows |
| **gnina** | CUDA ≥12.0 driver; 2 GB binary or 24 GB Docker image |
| **DiffDock-L** | Docker + GPU |
| **Chai-1** | Linux, A100/H100 80 GB recommended |
| **ESMFold2 / ColabFold** | 24 GB VRAM; ColabFold local DB needs 940 GB disk |
| **Foldseek GPU** | Ampere or newer; padded DB via `makepaddedseqdb` |
| **Full AFDB50 Foldseek search** | 151 GB RAM, or 35 GB with `--sort-by-structure-bits 0` |
| **Modal** | An account and a token. No cluster needed |

Keep a Modal path for every Tier 2 tool.
A judge with a laptop should be able to run one GPU target end-to-end by supplying their own Modal token, and get back the same artifact a local GPU would produce.

---

## 6. `scripts/doctor.py` — verification script spec

**Purpose.** Answer one question in under 60 seconds: *what can this machine actually do right now?*
It is the first thing a new contributor runs and the first thing a judge runs.

**Invocation.**

```bash
uv run python scripts/doctor.py                      # all checks
uv run python scripts/doctor.py --tier 0             # only Tier-0 checks
uv run python scripts/doctor.py --json               # machine-readable, for CI
uv run python scripts/doctor.py --fix-hints          # print the install command for each failure
uv run python scripts/doctor.py --check foldseek     # one check
```

**Exit codes.**

| Code | Meaning |
|---|---|
| `0` | Every check in the requested tier passed |
| `1` | A required check for the requested tier failed |
| `2` | Only optional / higher-tier checks failed |
| `3` | The doctor itself could not run (bad Python, missing `scripts/`) |

**Check registry.**
Each check is a declarative record, not bespoke code, so adding a tool is one entry:

```python
Check(
    name="foldseek",
    tier=1,
    category="compute",
    probe=["foldseek", "version"],
    parse=r"(\d+[-.][\w]+)",
    expect_min=None,
    platform_note="no native Windows — use WSL2 or bioconda in Linux",
    fix="conda install -c conda-forge -c bioconda foldseek",
    license_flag="GPL-3.0",
)
```

**Categories, in report order.**

| Category | What it checks |
|---|---|
| `platform` | OS, Python version, `uv` / `pixi` presence, WSL2 availability, NVIDIA driver + CUDA version + VRAM, free disk |
| `agent` | `claude --version`, `claude_agent_sdk` importable, `.mcp.json` parses, every configured MCP server answers an `initialize` handshake, `.claude/agents/*.md` frontmatter validates, `.claude/settings.json` hooks parse **and their matchers are tested against a sample tool name** |
| `compute` | Each tool in §3: binary present, version parsed, and one smoke test that produces real output (not just `--help`) |
| `data` | Each snapshot in `data/snapshots/MANIFEST.yaml`: file present, **SHA256 matches**, release id recorded, download date recorded |
| `network` | For Tier 0/1 only: a HEAD against each keyless endpoint, reporting reachable / rate-limited / dead. **Skipped entirely under `--benchmark-mode`** |
| `secrets` | Which keys in `.env.example` are set — reporting **set / unset**, never the value |
| `leakage` | The controls that do not need data: hook matchers compile and match, the egress allowlist is loadable, the cutoff is present in every cache key, the sealed blob is encrypted |

**Output.**

```
MetaboliteSensorFinder — environment report          2026-11-07 14:22  tier=1

PLATFORM
  ✓ os                Windows 10.0.19045 (+ WSL2 Ubuntu-24.04)
  ✓ python            3.11.9
  ✓ uv                0.9.x
  ✗ gpu               no NVIDIA driver found          → Tier 2 unavailable

AGENT
  ✓ claude-code       2.1.x
  ✓ agent-sdk         claude-agent-sdk 0.2.179
  ✓ mcp:rcsb-pdb      http  initialize ok  (rcsb_mcp 0.23.0)
  ! mcp:gwas-catalog  http  503                        → upstream, retry
  ✗ hook:enforce_cutoff   matcher "mcp__msf" matches 0 tools
                                                       → use "mcp__msf.*"

COMPUTE
  ✓ rdkit             2026.09.2    smoke: CCO → 3 atoms
  ✓ foldseek          10-941cd33   smoke: easy-search 1 hit      [WSL2]
  ✗ fpocket           not found    → conda install -c conda-forge fpocket  [no native Windows]
  – boltz             tier 2, skipped

DATA
  ✓ chembl_24         sha256 ok    3.9 GB   pinned 2026-11-02
  ✗ gwas_2019_01      sha256 MISMATCH                  → re-fetch, DO NOT USE

SECRETS
  ✓ GTP_API_KEY       set
  – OPENALEX_API_KEY  unset        → keyless budget is $0.10/day/IP

LEAKAGE CONTROLS
  ✓ egress allowlist loadable (14 hosts)
  ✓ cutoff present in cache key
  ✓ sealed split is encrypted
  ✗ hook matcher test                                  → see AGENT

READY: tier 0 ✓   tier 1 ✗ (2 blockers)   tier 2 ✗ (no GPU)
```

**Design rules.**

- **Never print a secret value**, only `set` / `unset`.
- **Every failure prints its fix**, and the platform note if the fix differs on Windows.
- **Smoke tests must produce output, not just exit 0.** `fpocket` has no `--help` and `plip`/`fpocket` have no `--version`; parse what they actually emit, and read fpocket's version from `conda list` because its banner is hardcoded to "fpocket 4.0".
- **`--benchmark-mode` makes the network category a hard failure if anything is reachable** — that is the L2 egress assertion, reused.
- The doctor is itself tested (`tests/unit/test_doctor.py`) with faked subprocess output, so a parser that breaks on a new version release is caught in CI rather than during a demo.

---

## 7. Secrets

### 7.1 Mechanism

`.env` at the repo root, loaded by `python-dotenv`, **never committed**.
`.env.example` is committed with every key name present and every value empty.
`scripts/doctor.py` reads `.env.example` for the key list and reports set/unset from the environment.

```gitignore
.env
.env.*
!.env.example
*.key
secrets/
```

A `PreToolUse` hook rejects any tool call whose serialised arguments match a secret-shaped pattern, so a key cannot leave in a prompt or a logged tool input.
Run records redact by key name before writing Parquet.

### 7.2 Who needs a key

| Key | Needed for | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | Agent SDK programmatic runs | Yes for SDK. **Not** for Claude Code (OAuth) or Claude Science (OAuth) |
| `GTP_API_KEY` | IUPHAR/GtoPdb **REST API** | Yes for the API — registration required. **No** for the quarterly dumps and flat CSVs, which is why we pin those instead |
| `OPENALEX_API_KEY` | OpenAlex | Technically optional, practically required: keyless is **$0.10/day shared across your whole IP**. A free key gives $1/day |
| `NCBI_API_KEY` | E-utilities, if you use a PubMed MCP server | Optional; raises the E-utilities rate limit |
| `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` | Modal dispatch | Only for Tier 2 cloud. Written by `modal setup` |
| `AWS_*` | DVC remote, requester-pays bioRxiv bucket | Only if using those |
| `MSF_SEAL_KEY` | Unsealing the `sealed` split | **Human-supplied at the prompt, never in `.env`.** See [04-EVALUATION.md §1.4](04-EVALUATION.md#14-splits) |

### 7.3 Genuinely key-free

UniProt, InterPro/Pfam, RCSB PDB, PDBe, AlphaFold DB, ChEMBL, BindingDB, ChEBI, Rhea, Reactome, STRING, GTEx (open tier), Human Protein Atlas, Open Targets, GWAS Catalog, Europe PMC, bioRxiv/medRxiv, Pharos GraphQL, LIPID MAPS, ARCHS4 bulk, and every official MCP server in §2.2.

**That is the large majority of the stack, and it is not an accident — it is a design constraint.**
A benchmark that requires nineteen API keys is not reproducible by a third party, and [04-EVALUATION.md §1](04-EVALUATION.md#1-deorphbench-a-retrospective-time-split-benchmark) requires that `DeorphBench` be usable by others.
Where a key-free path and a key-gated path both exist (GtoPdb: dumps vs API), **take the key-free one**.

---

## 8. Licensing traps that change whether you can install or use a tool

A full treatment is in the data-licensing document.
These are only the ones that affect setup.

| Trap | Effect |
|---|---|
| **HMDB — CC BY-NC 4.0 + explicit commercial-redistribution prohibition** | 🔴 Ship HMDB IDs and a fetch script, never the data. Also Cloudflare-blocked to programmatic clients — a human must download it in a browser |
| **ARCHS4 — CC BY-NC-SA 4.0** | Non-commercial *and* share-alike. Distribute accession lists, not matrices |
| **GtoPdb — ODbL + CC BY-SA 4.0, and commercial organisations must pay access fees** | Affects whether a company can use the loop at all, not just redistribute |
| **ChEMBL — CC BY-SA 3.0 (viral)** | A derived benchmark containing ChEMBL data must be released share-alike. This propagates into **BindingDB's ChEMBL subset**, **Open Targets**, **Pharos/TCRD** and **HPA** |
| **HPA dump embeds AlphaFold 3 content under CC BY-NC-SA 4.0** | HPA itself is CC BY 4.0, but rebundling the full dump carries the NC-SA passenger |
| **Pharos/TCRD — no single licence** | Aggregates heterogeneous sources. Per-source terms in `TCRDv6_DataSourcesLicenses.xlsx` |
| **GWAS Catalog curated metadata — EMBL-EBI general terms, not an open licence** | Summary statistics *are* CC0. Prefer those; cite-and-link the curated metadata |
| **Open Babel GPL-2.0 → smina / gnina / PLIP binaries are effectively GPLv2** | Shell out to the CLI; do not `import` them into a distributed product |
| **Foldseek GPL-3.0; MDAnalysis GPL-2.0+ (propagates through ProLIF)** | Same shape of problem |
| **Amber26 — $25,000 industrial** | AmberTools26 is free/GPL. Know which one you installed |
| **MGLTools/ADFRsuite — Sannerlab source-available v1.0** | Not OSI-approved. **Schrödinger Inc. excluded entirely, including from benchmarking.** MSMS stays non-commercial-only. Avoid by using Meeko |
| **DUD-E and DUDE-Z publish no licence at all** | Citation-only; commercial terms `UNVERIFIED`. Generate decoys in-house |

Two **non-commercial traps that no longer exist** and are still widely repeated:
**Chai-1 is Apache-2.0** (LICENSE read directly, no field-of-use clause — third-party sources quoting "non-commercial" are reporting the superseded September-2024 terms), and **ESM3 / ESMFold2 is MIT** (no Cambrian Open License).
**Boltz-2 is genuinely MIT** for code and weights, and **AlphaFold 2 parameters are CC BY 4.0**, including Multimer.

---

## 9. `UNVERIFIED` register

Collected so that nothing here is mistaken for a checked fact.
Each should be resolved before the item it describes is relied on.

**Agent layer**

- Whether Node.js is a hard requirement for the Python Agent SDK, and whether the CLI is truly bundled.
- Claude Science GA status or date; whether Benchling and 10x Genomics are first-class Claude Science connectors.
- `claude.com/docs/claude-science/specialists` 404s despite the feature existing in Settings.
- Literal doc examples for `permissionDecision: "ask"`, for a `timeout`-bearing hook handler, for an SSE `.mcp.json` entry, and for a plain (non-plugin) stdio `.mcp.json` entry. The shapes above are inferred from the documented field sets.

**Data layer**

- Numeric rate limits for InterPro, ChEBI, Rhea, Reactome, UniProt, PDBe, AlphaFold, BindingDB, LIPID MAPS, HPA, GTEx, ARCHS4, Pharos, Open Targets, RCSB, ChEMBL and bioRxiv — **none are published**.
- Europe PMC's 10 req/s figure is from an official EBI developer forum, **not a docs page**; Europe PMC's own terms page returns 403 to non-browser clients.
- HMDB: **everything** except the licence. Cloudflare-blocked. A human must open `hmdb.ca/{citing,about,downloads}` in a browser and record the verbatim terms, filenames and sizes.
- wwPDB CC0 not confirmed verbatim from a fetchable page.
- GTEx open-access tier: no named CC licence found.
- BindingDB's UCSD Library per-release DOIs (the page is bot-gated).
- Whether OpenAlex's `from_updated_date` is likewise Member+-gated; total OpenAlex snapshot size.
- The CC0-exception list for specific GWAS Catalog summary statistics.
- Whether `download.reactome.org/<v>/` retains 2018-era version numbers.
- Whether the ARCHS4 H5 contains a GEO submission-date field.
- Per-datasource completeness of Open Targets `Evidence.publicationYear`.

**Compute layer**

- **VRAM minimums for gnina, DiffDock, Foldseek-GPU and Chai-1** — none published. Measure before sizing a cloud job.
- Boltz-2 VRAM figures above are UCSF ChimeraX measurements, which are reliable, plus vendor-blog estimates, which are not.
- ESMFold VRAM-vs-length beyond the blanket "16–24 GB".
- Exact ColabFold MMseqs2 public-API rate limits.
- ESMFold via HF `transformers` on native Windows; ESMFold2 / `esm` on native Windows.
- Whether BoltzMol-1 and BoltzProt-1 weights are open or API-only. "Chai-3" is a single low-quality third-party source — treat as rumour.
- `openmmforcefields` generator import path against current source; licences of its bundled AMBER/CHARMM parameter files.
- Whether ProLIF's `multiprocess` parallel strategies have Windows-specific issues.
- Whether `dude.docking.org` being down on 2026-11-07 is transient; DUD-E tarball URLs; DUD-E and DUDE-Z commercial terms.
- Whether DeepCoy runs on CPU-only TF 1.x.
- biocontainers image tags for `hmmer` and `foldseek` on quay.io.
- `docker run --gpus all` for gnina — the standard NVIDIA Container Toolkit flag, but absent from gnina's own docs.
- Existence of `boltz.__version__` and `chai_lab.__version__` attributes — use `pip show` instead.

---

*Written material in this repository is licensed CC BY 4.0. See [LICENSE-CC-BY-4.0](../LICENSE-CC-BY-4.0).*
