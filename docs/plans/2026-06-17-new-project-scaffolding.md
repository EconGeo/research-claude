# Plan: new-project scaffolding (references fix + skill)

Date: 2026-06-17
Status: in progress
Branch: `feat/new-project-scaffolding`

## Problem

`apply.sh` installs clo-author's `agents/`, `skills/`, `rules/`, and `state/` — but
**not** its `.claude/references/` directory. clo-author ships fill-in-the-blank template
versions of all six reference files (`domain-profile.md`, `journal-profiles.md`,
`personal-style-guide.md`, `coding-standards-{julia,python,r}.md`), each populated by the
phase skills (`/discover interview` → domain-profile, `/write style-guide` →
personal-style-guide, journal-profiles ships pre-populated).

Because `apply.sh` skips them, a forking researcher ends up with agents that read
`.claude/references/domain-profile.md` and find nothing. The repo author's own projects
only work because each one was hand-symlinked to a shared `~/research/.claude/references/`.
The symlink was a private workaround for a missing install step, not a designed feature.

Separately, `apply.sh` produces no project `.gitignore`, no per-paper `CLAUDE.md`, and no
directory skeleton beyond `data/raw/` — so "new project" setup is a manual ritual.

## Principle

**The public template ships the mechanism; the user's setup supplies the path.** Nothing
machine-specific (e.g. `~/research/.claude/references`) is hardcoded into the distributed
template. Mechanism (file copying, optional symlinking) lives in `apply.sh`; policy and
conversation (which org, which references source, which citation DB) live in a skill.

## Design

### 1. `apply.sh` (mechanism) — two changes
- **Install clo-author references templates.** Copy `clo-author/.claude/references/*.md`
  into `<project>/.claude/references/`. Fixes the omission; every forker now gets working
  reference files by default. Does not overwrite files that already exist.
- **Add opt-in `--link-references <dir>`.** When passed, after copying, replace the
  reference files with symlinks into `<dir>` (the user's shared voice-profile folder).
  Default behavior (no flag) leaves the per-project template copies in place. The path is
  a runtime argument — never hardcoded.

### 2. `templates/gitignore` + install step
Ship a `.gitignore` template and install it to the project root (no clobber if one exists).
- **Keeps:** `*.qmd` (the single-source manuscript), `*.bib`, `data/raw/data_manifest.md`,
  `data/raw/MANIFEST.sha256`.
- **Ignores:** Quarto build (`.quarto/`, `*_files/`, `*_cache/`, rendered `*.pdf`/`*.html`),
  LaTeX aux (`*.aux`, `*.log`, `*.bbl`, …), `data/raw/**` (large raw inputs),
  `data/cleaned/`, R/Python artifacts, `.DS_Store`.

### 3. Directory skeleton at scaffold time
Create only `explorations/` (one-off models not yet wired into the manuscript) and
`data/raw/` (with the existing `data_manifest.md`). **No** `paper/`, `scripts/`, `output/`,
and **no** seeded manuscript. `quality_reports/` and `manuscript_<slug>.qmd` are created by
the phase skills when they run (`/discover` writes lit review + research spec to
`quality_reports/`; `/write` creates the manuscript). The manuscript is a writing-phase
artifact, not a scaffold artifact.

### 4. `new-project` skill (policy/conversation)
research-claude's own skill (distinct from the clo-author `new-project` that `apply.sh`
deliberately excludes). It:
1. Confirms project/repo name and local dir under the research root.
2. **GitHub:** asks org-vs-personal, then (if org) which team — per the GitHub/Collaboration
   rules. Creates the private repo and grants the team access. Never assumes.
3. **References:** asks "shared voice profiles (symlink to a dir) or per-project templates?"
   → calls `apply.sh` with or without `--link-references <dir>`.
4. **Citation DB:** asks Zotero/ZotPilot vs a `.bib` file vs none → records the choice in
   the project `CLAUDE.md`. (ZotPilot MCP registration noted as a follow-up, not auto-run.)
5. Writes the per-paper `CLAUDE.md` stub (name, target-journal TODO, GitHub remote + team),
   `git init`, initial commit, push.

### 5. README / `--list`
Update the install summary and `--list` output to reflect references install, the
`--link-references` flag, and the `.gitignore` template.

## Out of scope
- Auto-registering the ZotPilot MCP server (remains a documented manual step).
- Seeding the manuscript or `quality_reports/` (phase-skill responsibilities).

## Validation
- `bash -n apply.sh`; `apply.sh --list`.
- Fresh install into a temp dir: references templates present; `.gitignore` present and
  keeps `*.qmd`; `explorations/` present; no `paper/`/`scripts/`/`output/`.
- `--link-references <dir>`: reference files become symlinks into `<dir>`.
- Re-run is idempotent and does not clobber an existing `.gitignore` or `CLAUDE.md`.

## First real use
Recreate `~/research/affordable_housing_2026` through the new flow with
`--link-references ~/research/.claude/references`, create the private `udenver` repo, grant
the `affordable_housing` team, and verify.
