---
name: new-project
description: Use when creating a NEW research project / article under the research root — scaffolds the project with research-claude's apply.sh, wires GitHub (asks org-vs-personal and which team, never assumes), wires the citation database, writes the per-paper CLAUDE.md stub, and creates + pushes the private repo. Trigger on "new project", "start a new article", "scaffold a paper", "set up a repo for a new paper".
---

# New Project

Bootstrap a new research project end to end. `apply.sh` does the file mechanics; this skill
runs the conversation and the GitHub/git steps. Mechanism lives in `apply.sh`; policy
(which org, which references source, which citation DB) lives here.

This is a **root-level** skill — install it once at your research root
(`<research-root>/.claude/skills/new-project/`), not per project. It creates projects; it
does not run inside one.

## Preconditions

- `gh` is authenticated — check `gh auth status`.
- The research-claude checkout is available (it holds `apply.sh`). Ask the user for its path
  if unknown; a common location is `~/Academic/research-claude`.
- You know the research root (where projects live) — commonly `~/research`. Its
  `CLAUDE.md` may carry standing GitHub/collaboration rules (org, teams); read it first and
  honor it.

## Steps

Create one todo per step and work them in order.

### 1. Name and location
Ask for the article/repo name (a slug, e.g. `affordable_housing_2026`). Local directory is
`<research-root>/<name>` unless the user says otherwise. If the directory already exists and
is non-empty, stop and ask whether to pick a new name or remove the existing one — never
overwrite silently.

### 2. GitHub destination — ASK, never assume
Per the research root's GitHub rules, ask **org vs. personal** for this repo. Do not default
to either.
- If an org: list teams with `gh api orgs/<org>/teams --jq '.[].slug'` and ask **which team**
  should get access (or none).
- Record the destination and team; you'll use them in step 7.

### 3. References wiring — ASK
Ask how to populate the `.claude/references/` voice/style files:
- **Shared (symlink):** the user keeps one set of profiles reused across projects. Run
  `apply.sh` with `--link-references <dir>` (commonly `<research-root>/.claude/references`).
  Then append `.claude/references/` to the project `.gitignore` — personal/symlinked profiles
  must not be committed (the symlinks would dangle for collaborators who clone the repo).
- **Per-project templates:** run `apply.sh` without the flag. clo-author's fill-in-the-blank
  templates install; the user populates them later via `/discover interview` (domain profile)
  and `/write style-guide` (personal voice).

### 4. Run apply.sh
`apply.sh` guards against a missing project dir (typo safety for the install-into-existing
path), so create it first:
```
mkdir -p <research-root>/<name>
<research-claude>/apply.sh --project-dir <research-root>/<name> [--link-references <dir>]
```
This installs agents, skills, rules, references, `.gitignore`, the data manifest, and the
`explorations/` skeleton. It does **not** create a manuscript — that comes at the writing
phase.

### 5. Citation database — ASK
Ask the citation source: **Zotero (ZotPilot)**, a **`.bib` file**, or **none for now**.
Record the answer in the project `CLAUDE.md` (a `## Citation Database` section). If Zotero,
note that the ZotPilot MCP must be registered in `.mcp.json` (README Step 7) — do not
auto-register it here.

### 6. Per-paper CLAUDE.md stub
Write `<dir>/CLAUDE.md` with: project name, field, **target journal (TODO)**, **core question
(TODO)**, **contribution (TODO)**, the GitHub remote + team, and the citation source. State
that it inherits shared conventions from the research-root `CLAUDE.md`; do not duplicate them.

### 7. git + repo
- `git -C <dir> init`, add, and make the initial commit.
- Create the private repo at the chosen destination and push:
  - org: `gh repo create <org>/<name> --private --source <dir> --push`
  - personal: `gh repo create <name> --private --source <dir> --push`
- If an org team was chosen, grant access:
  `gh api -X PUT orgs/<org>/teams/<team>/repos/<org>/<name> -f permission=push`

### 8. Verify and report
Run `git -C <dir> remote -v`; confirm the repo is **private** and the team has access. Report
next steps: ZotPilot env/MCP if applicable, then `/discover` to begin the discovery phase.

## Notes

- **Never commit secrets.** API keys live in `~/.secrets.env` and are referenced as `${NAME}`.
- The **manuscript** (`manuscript_<name>.qmd`) is not created here — it is a writing-phase
  artifact produced by `/write`. Scaffolding stops at the project shell + `explorations/`.
- `quality_reports/` (lit review, research spec, decisions) is created on demand by the phase
  skills, not at scaffold time.
