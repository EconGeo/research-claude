# research-claude: AI-Powered Research Workstation

A fully composed research pipeline for empirical academic work. Combines [clo-author](https://github.com/hugosantanna/clo-author)'s multi-agent research pipeline with ZotPilot (Zotero MCP server), ai-audit (prose quality tools), and journal-digest (weekly literature monitor).

**Audience:** Academic researchers who write empirical papers (economics, finance, social science) and want Claude Code as a research partner, not just a coding assistant.

> ## 🚀 Easiest way to install: let Claude do it
>
> You don't have to follow the steps below by hand. Open this repo in [Claude Code](https://claude.com/claude-code) and simply tell it:
>
> > *"Read the README and install everything for me."*
>
> Claude will work through this guide step by step — installing the tools, running `apply.sh`, configuring ZotPilot, and verifying each step as it goes. When a step needs **you** (entering an API key, approving an app install, picking your Zotero folder, or loading the Chrome extension), it will pause and walk you through it. The numbered steps below are the same instructions, written out for reference or if you'd rather do it yourself.

---

## What you get

| Submodule | What it provides |
|-----------|-----------------|
| `clo-author` | Research pipeline agents: strategist, writer, coder, referees, reviewer, data-engineer, theorist, and more |
| `EconGeo/ZotPilot` | Zotero MCP server — embeds your whole library into a local ChromaDB so Claude searches it semantically, ingests papers, and cross-references citations (our fork of [xunhe730/ZotPilot](https://github.com/xunhe730/ZotPilot)) |
| `EconGeo/ai-audit` | Prose audit skills: `/humanize` (AI-voice tells) + `/verify-claims` (hallucination check) |
| `EconGeo/journal-digest` | Weekly journal monitor: RSS/CrossRef fetch + Claude in-session synthesis |

---

## Prerequisites

Follow these steps in order. Each step has a verification check.

### Step 1 — Install micromamba

micromamba creates isolated Python environments. We use it to sandbox every tool so uninstalling leaves no traces.

**macOS:**
```bash
brew install micromamba
micromamba shell init --shell zsh   # adds micromamba to your .zshrc
source ~/.zshrc                      # reload shell
micromamba --version                 # verify: should print a version number
```

**Windows (PowerShell):**
```powershell
# Official installer — downloads micromamba.exe and runs `micromamba shell init` for you
Invoke-Expression ((Invoke-WebRequest -Uri https://micro.mamba.pm/install.ps1 -UseBasicParsing).Content)

# Close and reopen PowerShell, then verify:
micromamba --version                 # should print a version number
```
If `Invoke-WebRequest` is blocked by execution policy, run PowerShell as Administrator once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then re-run the installer.

**Why micromamba instead of pip?** Running `pip install zotpilot` would add ZotPilot to your system Python — and uninstalling it later might leave orphaned dependencies. micromamba creates a clean, deletable env per tool.

### Step 2 — Install Zotero + Better BibTeX

1. Download and install [Zotero 9](https://www.zotero.org/download/) (the current release)
2. Open Zotero and sync your library at least once (File → Sync Library)
3. Install the [Better BibTeX (BBT)](https://retorque.re/zotero-better-bibtex/) plugin:
   - Download the `.xpi` file from the BBT releases page
   - In Zotero: Tools → Add-ons → drag the `.xpi` into the window
   - Restart Zotero

**BBT 7+ note:** The EconGeo/ZotPilot fork handles the schema change in BBT version 7. If you're on BBT 6 or earlier, the upstream ZotPilot package also works.

### Step 3 — Install Quarto CLI

Download from [quarto.org](https://quarto.org/docs/get-started/) and run the installer.

```bash
quarto check   # verify: should report versions for knitr and jupyter
```

### Step 4 — Install XeLaTeX (MacTeX)

```bash
brew install --cask mactex-no-gui   # ~4GB; run this before bed
xelatex --version                    # verify: should print pdfTeX or XeTeX version
```

If you already have BasicTeX or another TeX distribution, XeLaTeX may already be available.

### Step 5 — Install R + core packages

Download R from [cran.r-project.org](https://cran.r-project.org/). Then in R:

```r
install.packages(c(
  "fixest",         # fast panel regression (DiD, IV, event study)
  "modelsummary",   # regression tables (LaTeX + Word)
  "flextable",      # Word tables
  "kableExtra",     # LaTeX tables
  "ggplot2",        # figures
  "here",           # project-relative paths
  "renv"            # package version management
))
```

---

## Install research-claude

### Step 6 — Clone this repo and run apply.sh

```bash
git clone --recurse-submodules https://github.com/EconGeo/research-claude.git
cd research-claude

# Install into your project directory
./apply.sh --project-dir ~/path/to/your-project

# Preview what would be installed without making changes
./apply.sh --list
```

`apply.sh` copies `.claude/` files from each submodule into `your-project/.claude/`. It does not touch your Python environments or register MCP servers — those require user judgment about paths (Steps 7–8).

### Rules installed into `.claude/rules/`

Beyond the submodule agents and skills, research-claude ships its own pipeline rules that Claude reads as standing project conventions:

| Rule | What it enforces |
|------|------------------|
| `quarto-empirical.md` | **The required pipeline for new projects.** A single `.qmd` is the source of truth for all analysis, tables, figures, and prose — no external R scripts, no results registry, no ground-truth CSV. The rendered PDF *is* the paper. |
| `data-manifest.md` | Every project keeps `data/raw/data_manifest.md` — a current table recording where each raw data file came from, how it was acquired, and which variables are used. The audit trail behind every reported number. |
| `quarto-pdf.md` | PDF output format reference for the single `manuscript.qmd`: the `pdf:` block plus kableExtra/figure/citation mechanics and LaTeX landmines (XeLaTeX + biblatex). |
| `quarto-word.md` | Word output format reference: the optional `docx:` block plus flextable/CSL mechanics, rendered from the *same* `manuscript.qmd`. Architecture and caching are governed by `quarto-empirical.md`, not redefined here. |
| `registry-verification-gate.md` | *Legacy.* Write-gate for older registry-pattern projects (e.g. `zoning2026`) that pre-date the `quarto-empirical` standard. New projects don't need it. |

---

## Set up ZotPilot (the trickiest step)

ZotPilot lets Claude search your Zotero library, ingest new papers with PDFs, and cross-reference your citations. Under the hood it embeds your **entire Zotero library into a local [ChromaDB](https://www.trychroma.com/) vector store** — so Claude can search across everything you've ever saved by *meaning*, not just keywords. That index is what powers `/ztp-review`, `/seed-papers`, and the literature-search seeding described later.

**Upstream + our fork.** ZotPilot is originally the work of [xunhe730](https://github.com/xunhe730/ZotPilot). The [`EconGeo/ZotPilot`](https://github.com/EconGeo/ZotPilot) fork that research-claude pins adds and fixes several things on top of upstream:

- **Ollama embeddings** — embed your library locally instead of via Gemini, so indexing a large library isn't throttled by Gemini's API rate limits (see below).
- **Better BibTeX 7+ schema compatibility** — handles the BBT 7 database change.
- **Group-library indexing** — index shared/group libraries, not just your personal one.
- **Bundled `ztp-*` Claude skills** — `/ztp-research`, `/ztp-review`, `/ztp-setup`, etc.

Everything below uses the fork.

> **Tip:** Once you've done this setup once, you can ask Claude to walk you through it interactively: open Claude Code in your project and say "help me set up ZotPilot."

### Embedding options

ZotPilot needs an embedding model to build the semantic index (the ChromaDB vector store). **Ollama is the recommended option** — it runs fully locally with no API key and no data leaving your machine. The fork added Ollama support specifically to escape Gemini's free-tier rate limit (100 req/min), which throttles the first full index of a large library; with Ollama the only limit is your own hardware.

| Option | Setup | Privacy | Cost |
|--------|-------|---------|------|
| **Ollama** *(recommended)* | Install Ollama + pull a model | Fully local | Free |
| Gemini API | API key from Google AI Studio | Cloud | Free tier: 100 req/min |

**Ollama setup (do this before Step 7):**
```bash
# Install Ollama
brew install ollama          # macOS
# or download from https://ollama.com

# Start the Ollama server (runs in background)
ollama serve &

# Pull an embedding model
ollama pull nomic-embed-text   # fast, 274MB, good general-purpose embeddings
# alternative: ollama pull mxbai-embed-large  (higher quality, 670MB)

# Verify
ollama list   # should show nomic-embed-text
```

**Gemini API key** (only needed if using Gemini instead of Ollama):
Get a key at [aistudio.google.com](https://aistudio.google.com/) → "Get API key".

**Zotero API key + user ID** (needed for write operations — ingesting papers, adding notes/tags):
Create at [zotero.org/settings/keys](https://www.zotero.org/settings/keys). Your user ID is shown on the same page.

API keys go in `~/.config/zotpilot/config.json` — **never commit them**.

### Step 7 — Install and configure ZotPilot

```bash
# Create sandboxed Python environment
micromamba create -n zotpilot python=3.12 -c conda-forge
micromamba activate zotpilot

# Install from EconGeo fork (BBT 7+ compat + group library indexing)
pip install git+https://github.com/EconGeo/ZotPilot.git

# Find the zotpilot binary path (you'll need this for .mcp.json)
which zotpilot
# → /Users/YOUR_USERNAME/micromamba/envs/zotpilot/bin/zotpilot
```

Configure with **Ollama** (recommended):
```bash
zotpilot config set zotero_data_dir /path/to/Zotero    # e.g. ~/Library/CloudStorage/.../Zotero
zotpilot config set embedding_provider ollama
zotpilot config set ollama_model nomic-embed-text
zotpilot config set ollama_base_url http://localhost:11434
zotpilot config set zotero_api_key YOUR_ZOTERO_KEY      # for write operations
zotpilot config set zotero_user_id YOUR_ZOTERO_USER_ID
```

Configure with **Gemini** (cloud alternative):
```bash
zotpilot config set zotero_data_dir /path/to/Zotero
zotpilot config set embedding_provider gemini
zotpilot config set gemini_api_key YOUR_GEMINI_KEY
zotpilot config set zotero_api_key YOUR_ZOTERO_KEY
zotpilot config set zotero_user_id YOUR_ZOTERO_USER_ID
```

Finding your Zotero data directory:
```bash
# macOS with OneDrive sync:
ls ~/Library/CloudStorage/ | grep Zotero

# macOS local storage:
ls ~/Zotero/
```

### Register the MCP server (project-scoped by default)

Create `.mcp.json` in your project root (this file is sandboxed — it only activates ZotPilot in this project and is deleted with the project):

```json
{
  "mcpServers": {
    "zotpilot": {
      "command": "/Users/YOUR_USERNAME/micromamba/envs/zotpilot/bin/zotpilot",
      "args": ["mcp", "serve"]
    }
  }
}
```

Replace the path with the output of `which zotpilot` above.

**Global opt-in:** If you want ZotPilot active in all Claude Code projects, copy the same snippet into `~/.claude.json`. This persists after project deletion — only do this intentionally.

Restart Claude Code. The `mcp__zotpilot__*` tools should appear in the tool list.

---

## Step 8 — Index your Zotero library

> **Do this immediately after the MCP server is confirmed working.** The semantic search that powers the literature review workflow only works after indexing — Claude cannot search papers that haven't been embedded yet. Index once, then keep Ollama running when you work.

```bash
# Make sure Ollama is running (if using Ollama embedding)
ollama serve &

# Index your personal library
micromamba run -n zotpilot zotpilot index

# With Ollama: speed depends on your machine; ~2–4 sec/paper is typical.
# With Gemini: free tier is 100 req/min; the indexer retries automatically.
# 200 papers ≈ 10–20 minutes either way.
```

Verify the index:
```bash
micromamba run -n zotpilot zotpilot status
# Should report: N papers indexed, embedding provider, index size
```

### Keeping the index current

The index does not auto-update. Re-run `zotpilot index` after adding a batch of new papers to Zotero, or set a weekly cron job:

```bash
# Add to crontab (runs every Sunday at 9am)
0 9 * * 0 /path/to/micromamba run -n zotpilot zotpilot index >> ~/.zotpilot-index.log 2>&1
```

### Group library indexing (advanced)

The CLI only indexes your personal library. Use this Python wrapper for group libraries:

```python
# Find your group ID: Zotero → right-click group → Group Settings → URL
# e.g. groups.zotero.org/2350352/... → GROUP_ID = 2350352

from zotpilot.indexer import Indexer
from zotpilot.zotero_client import ZoteroClient
from zotpilot.config import Config

config = Config.load()
GROUP_ID = 2350352   # replace with your group ID
group_lib_id = ZoteroClient.resolve_group_library_id(config.zotero_data_dir, GROUP_ID)
Indexer(config, library_id=group_lib_id).run()
```

---

## Auto-download papers from a literature search (the Connector bridge)

Indexing (Step 8) makes the papers you *already have* searchable. The **ZotPilot Connector** does the opposite direction: it lets Claude **pull new papers — with PDFs — straight into your Zotero library** from a literature search, no one-by-one downloading.

The key advantage: saves go through **your own logged-in Chrome session**, so **institutional / paywalled PDFs come along**. On a campus network or VPN, hand Claude a list of DOIs or arXiv IDs (or let `/ztp-research` find them) and it deposits the full PDFs into Zotero.

### How it works

```
You: "find recent papers on zoning supply elasticity and add the good ones"
        ↓  /ztp-research
1. Claude searches OpenAlex + your indexed library, shows a ranked candidate table
2. You confirm which papers to ingest (and approve any institutional-access prompts)
3. Claude calls ingest_by_identifiers →
        agent → local bridge (127.0.0.1:2619) → Chrome Connector → Zotero Desktop
4. The Connector saves each paper through your real browser session — PDF attached
5. Claude auto-tags, files into a collection, and writes a per-paper report
6. Re-index (Step 8) to make the new papers semantically searchable
```

> **The bridge starts itself — nothing to launch.** You never run a command to start the `127.0.0.1:2619` bridge. The first time Claude ingests a paper, ZotPilot checks whether the bridge is up and, if not, launches it as a background process from the Python environment where `zotpilot` is installed (Step 7). A manual `zotpilot bridge` command exists if you ever want to run it yourself, but normal use never needs it.

The Connector is a **fork of the official Zotero Connector** that adds an agent-driven save path on top of the normal one. The two coexist: the official extension still handles your manual one-click saves; the fork handles agent-driven saves via the local bridge.

### Install the Connector (Chrome)

> **What this is:** the Connector is a Chrome extension maintained by the upstream author ([xunhe730](https://github.com/xunhe730/ZotPilot)), not by research-claude — we just bundle its source so you understand the moving parts. Like any Chrome extension, it has to be loaded into your browser once; neither `pip install` nor cloning this repo does that for you. Below are two ways to get it loaded — **most people should use Option A.**

#### Option A — Download the prebuilt extension *(recommended — no programming needed)*

1. Open the [ZotPilot releases page](https://github.com/xunhe730/ZotPilot/releases/latest), download `zotpilot-connector-v*.zip`, and unzip it.
2. In Chrome, open `chrome://extensions/`.
3. Turn on **Developer mode** (toggle, top-right).
4. Click **Load unpacked** and select the unzipped folder (the one containing `manifest.json`).
5. Confirm the Zotero/ZotPilot icon appears in the toolbar — and keep **Zotero Desktop running** whenever you ingest papers.

> **To upgrade:** download the latest release zip again, unzip over the old folder, then click the refresh icon on the ZotPilot Connector entry in `chrome://extensions/`.

#### Option B — Build from the copy already in this repo *(advanced — needs Node.js)*

If you'd rather not download a separate file — the Connector source is already in your clone at `submodules/zotpilot/connector/`, pinned to the same commit as everything else. Building it requires [Node.js](https://nodejs.org/) installed. From the repo root:

```bash
cd submodules/zotpilot/connector
npm install        # one-time: fetch build dependencies
./build.sh -d      # builds the Chrome (MV3) extension into build/manifestv3/
```

Then in Chrome: `chrome://extensions/` → **Developer mode** on → **Load unpacked** → select the **`build/manifestv3/`** folder (load `build/`, *not* `src/` — `src/` won't work). Keep Zotero Desktop running during ingestion.

> If you don't already have Node.js and a build toolchain, Option A is much less hassle. Option B mainly helps if you want the extension to match the exact pinned commit, or you can't download the release zip.

**Without the Connector** (either option), ingestion degrades to *metadata-only* (no PDFs attached) and pure-URL ingests fail — search, citation lookup, and library organization are unaffected. Install it if you want Claude to actually fetch the papers, not just their bibliographic records.

---

## Step 9 — Set up journal-digest (optional)

```bash
# Install with --with-digest flag
./apply.sh --project-dir ~/path/to/your-project --with-digest

# Create the Python env
micromamba create -n journal-digest python=3.12 -c conda-forge
micromamba run -n journal-digest pip install -r your-project/journal-digest/requirements.txt

# Edit config.py with your journals, keywords, Zotero paths
nano your-project/journal-digest/config.py

# Test
micromamba run -n journal-digest python your-project/journal-digest/run_gather.py --dry-run
```

See [EconGeo/journal-digest](https://github.com/EconGeo/journal-digest) for full setup including LaunchAgent (weekly scheduling).

---

## Optional — Obsidian knowledge base (journal-digest + `/checkpoint`)

If you keep an [Obsidian](https://obsidian.md) vault, two parts of the pipeline can write into it, turning Claude's session output into a durable, cross-linked knowledge base instead of a pile of dated files:

1. **`/checkpoint` → project journal.** When you wrap a session, `/checkpoint` appends a journal entry to the matching Obsidian project note (plus a dashboard row and daily-journal entry), alongside its usual memory + `SESSION_REPORT.md` updates.
2. **journal-digest → literature knowledge base.** After journal-digest produces a weekly digest (Step 9), ask Claude — in-session, with the Obsidian MCP connected — to file the synthesized digest into your vault. Each notable paper becomes a note, `[[wikilink]]`-crosslinked to related papers, your prior work, and the project it bears on. Over weeks this compounds into a navigable map of your field.

Both are **opt-in and gated** — nothing touches your vault unless you configure it. If `.claude/state/obsidian-config.md` is absent or the Obsidian MCP isn't connected, `/checkpoint` silently skips the vault and only updates memory + scaffold files.

### Setup

1. Install [Obsidian](https://obsidian.md) and enable the **Local REST API** community plugin (Settings → Community plugins).
2. Connect an Obsidian MCP server so Claude can read/write vault notes — see [mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian). Register it in `.mcp.json` alongside ZotPilot.
3. Create the config from the template `apply.sh` installed to `.claude/state/obsidian-config.md.example`:
   ```text
   # In Claude Code, from your project:
   /checkpoint --setup-obsidian
   # → copies the .example to .claude/state/obsidian-config.md and walks you
   #   through vault path + working-dir → project-note mapping
   ```
   The real `obsidian-config.md` is gitignored by design — your vault paths and mappings stay local.

### The digest → crosslinked knowledge base loop

```
journal-digest (Tier 1, automated)  →  digests/YYYY-MM-DD_raw.md
        ↓  open in Claude Code (Tier 2), Obsidian MCP connected
Claude synthesizes and files into the vault:
   • one note per notable paper (abstract, why it matters, connections)
   • [[wikilinks]] to related papers and your MY_PUBLICATIONS
   • linked from the relevant Obsidian project note
        ↓  repeat each week
A cumulative, navigable literature map — not a stack of dated digests
```

Because the notes are crosslinked, value compounds: a new paper on, say, zoning supply elasticity automatically connects to everything you've already filed on the topic. This is a Claude-in-session workflow enabled by the Obsidian MCP — journal-digest writes plain markdown; Claude does the synthesis and filing.

---

## Step 10 — Verify the full stack

After all steps, check:

- [ ] Claude Code opens in your project
- [ ] `mcp__zotpilot__*` tools appear in tool list (Settings → Tools or type `/tools`)
- [ ] `zotpilot status` shows papers indexed
- [ ] `/ztp-research` skill invocable (type `/ztp` in Claude Code)
- [ ] Connector (for paper download): ZotPilot Connector loaded in `chrome://extensions/`, Zotero Desktop running
- [ ] `/humanize` and `/verify-claims` skills available
- [ ] `quarto render` produces output from a test `.qmd` file
- [ ] `xelatex` compiles a test `.tex` file
- [ ] `journal-digest` (if installed): `python run_gather.py --dry-run` completes without errors
- [ ] Obsidian (if used): `.claude/state/obsidian-config.md` exists and the Obsidian MCP tools appear in `/tools`

---

## Using the research pipeline

Once installed, the main entry points are:

| Skill | When to use |
|-------|------------|
| `/ztp-research` | Find and ingest new papers into your Zotero library |
| `/ztp-review` | Synthesize papers already in your library |
| `/seed-papers` | Pre-search your Zotero library to seed a bibliography before `/discover lit` |
| `/strategize` | Design your identification strategy |
| `/write` | Draft paper sections |
| `/review-paper` | Manuscript review (single-pass, adversarial, or simulated peer review) |
| `/verify-claims` | Hallucination check on a draft |
| `/humanize` | Detect AI-voice tells before submission |
| `/analyze` | End-to-end data analysis (R / Python / Julia) |

See [clo-author](https://github.com/hugosantanna/clo-author) for the full skill and agent reference.

---

## How your Zotero library feeds the research pipeline

> **Once the ZotPilot MCP server is confirmed working, the first thing to do is index your Zotero library with Ollama** (Step 8). The semantic search that powers every literature review only works after indexing. Papers added to Zotero after the last index run won't be searchable until you re-index.

Once indexed, your library becomes the *starting point* for every literature search — not an afterthought.

### At project start (`/new-project`)

When you kick off a new project, Claude will ask:

> *"Do you want to set up ZotPilot to make your Zotero library searchable? This embeds your papers into a local ChromaDB vector store so I can search them semantically before running any web-based literature search."*

If ZotPilot is already indexed, Claude records the status in your project `CLAUDE.md` and moves on. If not, it walks you through `/ztp-setup` before starting the Discovery phase.

### At literature search (`/discover lit`)

Before dispatching the librarian agent to search the web, Claude will ask:

> *"Do you want me to search your Zotero library first for papers you already have on this topic? This seeds the bibliography with your existing anchors and tells the librarian what's already covered."*

If yes, the workflow is:

```
1. Claude searches ChromaDB via ZotPilot MCP for the core topic
2. Shows you a ranked candidate table — title, year, journal, relevance
3. You confirm which papers to include
4. Claude exports BibTeX entries → bibliography_base.bib
5. Claude writes annotation summaries → quality_reports/literature/{project}/zotero_seed.md
6. Librarian agent reads those files, sees what's covered, extends outward via web search
```

**No PDFs are copied.** Papers stay indexed in ChromaDB/Zotero. The `bibliography_base.bib` file is the handoff — it tells the librarian what anchor papers already exist so it fills genuine gaps rather than re-discovering what you already have.

### Why the librarian can't query ChromaDB directly

The librarian agent's tools are `Read, Write, Grep, Glob, WebSearch, WebFetch` — it has no MCP access and cannot query ChromaDB. Only the main Claude session (the one you're talking to) can hit ZotPilot. The `bibliography_base.bib` + `zotero_seed.md` files are the bridge:

```
ChromaDB / Ollama embeddings
    ↓  main session queries via ZotPilot MCP
bibliography_base.bib  +  zotero_seed.md   ← written before librarian runs
    ↓  librarian reads via Read tool
Web search extends outward from known anchors
    ↓
quality_reports/literature/{project}/annotated_bibliography.md
```

### What `master_supporting_docs/` is for

The `master_supporting_docs/` folder exists for papers **not in your Zotero library** — manually downloaded PDFs, unpublished working papers, draft manuscripts a colleague sent you. The librarian can read these as full text. For anything already indexed in ChromaDB, `bibliography_base.bib` is the right path and no files need to move.

---

## Updating

```bash
cd research-claude
git submodule update --remote            # pull latest from all upstreams
./apply.sh --update --project-dir ~/path/to/your-project
```

`apply.sh --update` runs `git submodule update --remote` before installing, so you always get the latest version of each submodule.

---

## Uninstall

**Remove Claude Code skills/agents/rules:**
```bash
rm -rf ~/path/to/your-project/.claude/
```

**Remove ZotPilot:**
```bash
micromamba env remove -n zotpilot          # removes Python env
rm ~/path/to/your-project/.mcp.json                 # removes MCP registration
rm -rf ~/.config/zotpilot/                 # removes config + API keys
rm -rf ~/.local/share/zotpilot/            # removes ChromaDB index
```
Also remove the **ZotPilot Connector** from Chrome: open `chrome://extensions/` and click **Remove** on the ZotPilot Connector entry.

**Remove journal-digest:**
```bash
micromamba env remove -n journal-digest
rm -rf ~/path/to/your-project/journal-digest/
launchctl unload ~/Library/LaunchAgents/com.YOUR_USERNAME.journal-digest.plist  # if scheduled
```

No global state remains after these steps.

---

## Architecture

```
Layer 0 — Upstream (not owned; tracked via git remote)
├── hugosantanna/clo-author        research pipeline + agents  ← primary base
└── xunhe730/ZotPilot              Zotero MCP server (upstream)

Layer 1 — Custom tools (each repo owns its versioning)
├── EconGeo/ZotPilot               fork: BBT 7+ + group library + Ollama + claude-skills
├── EconGeo/ai-audit               /humanize + /verify-claims + ai-disclosure
└── EconGeo/journal-digest         weekly journal monitor (RSS + CrossRef)

Layer 2 — This repo (compose via apply.sh)
└── EconGeo/research-claude        ← you are here
```

### Why submodules + apply.sh?

`research-claude` pins each Layer 1 tool to a tested commit via git submodules — you always know exactly which ZotPilot version you're running. `apply.sh` does the actual file installation. Users need only:

```bash
git clone --recurse-submodules EconGeo/research-claude
cd research-claude && ./apply.sh --project-dir ~/my-project
```

Upgrading: `git submodule update --remote && ./apply.sh --update --project-dir ~/my-project`
