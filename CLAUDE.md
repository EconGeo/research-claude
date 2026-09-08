# Working on research-claude

This repo **is** the research pipeline. It is the single edit surface: every paper
project under `~/Research` links to this working copy per item, so a change here
reaches all of them immediately.

**Two consequences to keep in mind while working here.**

1. **An edit to `agents/`, `skills/`, `rules/` or `hooks/` is live in every paper the
   moment you save it** — before you commit, before you push. Nothing stages it. If a
   change is experimental, branch first.
2. **Nothing project-specific may ship.** No journal name, dataset name, project noun,
   or non-standard manuscript filename in `agents/`, `skills/`, `rules/`, `hooks/` or
   `templates/`. `scripts/check_fork.sh` enforces this — run it before any commit that
   touches those directories. (`references/` is exempt from the journal/vendor half of
   that scan: discipline cards and journal profiles exist precisely to name real
   journals and data sources.)

The repo is public; the six paper repos that link to it are private. That is what lets
a coauthor bootstrap the pipeline with a clone and no access grant.

## Checkpoint / session-report location

**`SESSION_REPORT.md` lives at `docs/SESSION_REPORT.md`, not the repo root.**

When running `/checkpoint` in this repo, append the session entry to
`docs/SESSION_REPORT.md` (create it if missing). Do **not** write `SESSION_REPORT.md`
to the repo root — this overrides the checkpoint skill's default root path. A root
`SESSION_REPORT.md` is gitignored as a backstop.

## Where things go (don't pollute the public template)

- `agents/`, `skills/`, `rules/`, `hooks/` and `references/` are **linked into every
  project** by `apply.sh --link`. Only put content here that every project should
  receive. Never put research-claude's own dev notes or machine-specific state in them.
- `templates/` holds files `apply.sh` installs directly into a project (e.g.
  `data_manifest.md` → `data/raw/`, `gitignore` → `.gitignore`). Generic, no machine-specifics.
- `root-skills/` was **removed** on 2026-09-08. `new-project` was superseded by
  `rules/quarto-empirical.md` and `skills/new-project-ztp/`; see
  `docs/decisions/2026-09-08_cut-the-orchestration-graph.md`.
- `submodules/` holds only `ai-audit` and `journal-digest`, both live. `clo-author` was
  removed on 2026-09-08 — its agents are vendored into `agents/` and maintained here.
- `zotpilot-skills/` is **vendored verbatim** from `EconGeo/ZotPilot` and is never edited
  in place. Changes go into a bridge skill under `skills/` (see `lit-position`,
  `new-project-ztp`, `ztp-data-tag`).
- Keep the template generic: never hardcode a machine-specific path (e.g. a personal
  `~/research/.claude/references` dir). Mechanism goes in the template; the path is supplied at
  runtime (e.g. `apply.sh --link-references <dir>`).
- Repo-development docs (plans, session reports) go under `docs/`.
- Plans: `docs/plans/YYYY-MM-DD-<name>.md`. Decisions: `docs/decisions/`.

## Before committing a change to the shipped tree

```bash
./scripts/check_fork.sh    # exit 0 required
```

If the change **adds or removes** a file under `agents/`, `skills/`, `rules/` or
`hooks/`, also re-link the projects and confirm they picked it up. Edits propagate
through the links on save; membership does not.

```bash
./scripts/check_install.sh --all    # exit 0 required after a re-link
```

It checks: no LaTeX/multi-file residue, no project identity or project nouns, the
structural deletions still hold, and that the merged `coder-critic` still carries both
halves it was built from.
