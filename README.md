# research-claude: AI-Powered Research Workstation

A fully composed research pipeline for empirical academic work. Combines [clo-author](https://github.com/hugosantanna/clo-author)'s multi-agent research pipeline with ZotPilot (Zotero MCP server), ai-audit (prose quality tools), and journal-digest (weekly literature monitor).

**Audience:** Academic researchers who write empirical papers (economics, finance, social science) and want Claude Code as a research partner, not just a coding assistant.

---

## What you get

| Submodule | What it provides |
|-----------|-----------------|
| `clo-author` | Research pipeline agents: strategist, writer, coder, referees, reviewer, data-engineer, theorist, and more |
| `EconGeo/ZotPilot` | Zotero MCP server — Claude searches your library, ingests papers, cross-references citations |
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

**Why micromamba instead of pip?** Running `pip install zotpilot` would add ZotPilot to your system Python — and uninstalling it later might leave orphaned dependencies. micromamba creates a clean, deletable env per tool.

### Step 2 — Install Zotero + Better BibTeX

1. Download and install [Zotero 8](https://www.zotero.org/download/)
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

ZotPilot lets Claude search your Zotero library, ingest new papers with PDFs, and cross-reference your citations.

> **Tip:** Once you've done this setup once, you can ask Claude to walk you through it interactively: open Claude Code in your project and say "help me set up ZotPilot."

### Embedding options

ZotPilot needs an embedding model to build the semantic index. **Ollama is the recommended option** — it runs fully locally with no API key and no data leaving your machine.

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
micromamba run -n zotpilot zotpilot stats
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

## Step 10 — Verify the full stack

After all steps, check:

- [ ] Claude Code opens in your project
- [ ] `mcp__zotpilot__*` tools appear in tool list (Settings → Tools or type `/tools`)
- [ ] `zotpilot stats` shows papers indexed
- [ ] `/ztp-research` skill invocable (type `/ztp` in Claude Code)
- [ ] `/humanize` and `/verify-claims` skills available
- [ ] `quarto render` produces output from a test `.qmd` file
- [ ] `xelatex` compiles a test `.tex` file
- [ ] `journal-digest` (if installed): `python run_gather.py --dry-run` completes without errors

---

## Using the research pipeline

Once installed, the main entry points are:

| Skill | When to use |
|-------|------------|
| `/ztp-research` | Find and ingest new papers into your Zotero library |
| `/ztp-review` | Synthesize papers already in your library |
| `/strategize` | Design your identification strategy |
| `/write` | Draft paper sections |
| `/review-paper` | Manuscript review (single-pass, adversarial, or simulated peer review) |
| `/verify-claims` | Hallucination check on a draft |
| `/humanize` | Detect AI-voice tells before submission |
| `/data-analysis` | End-to-end R analysis |

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
rm -rf /your-project/.claude/
```

**Remove ZotPilot:**
```bash
micromamba env remove -n zotpilot          # removes Python env
rm /your-project/.mcp.json                 # removes MCP registration
rm -rf ~/.config/zotpilot/                 # removes config + API keys
rm -rf ~/.local/share/zotpilot/            # removes ChromaDB index
```

**Remove journal-digest:**
```bash
micromamba env remove -n journal-digest
rm -rf /your-project/journal-digest/
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
