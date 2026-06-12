# Working on research-claude

This repo is both a **working project** (we develop the tooling here) and a **public
template** that others fork and install via `apply.sh`. Keep that dual nature in mind.

## Checkpoint / session-report location

**`SESSION_REPORT.md` lives at `docs/SESSION_REPORT.md`, not the repo root.**

When running `/checkpoint` in this repo, append the session entry to
`docs/SESSION_REPORT.md` (create it if missing). Do **not** write `SESSION_REPORT.md`
to the repo root — this overrides the checkpoint skill's default root path. A root
`SESSION_REPORT.md` is gitignored as a backstop.

## Where things go (don't pollute the public template)

- `rules/` and `skills/` are **distributed to users' projects** by `apply.sh`. Only put
  content here that a forking researcher should receive. Never put research-claude's own
  dev notes or machine-specific state in these dirs.
- Repo-development docs (plans, session reports) go under `docs/`.
- Plans: `docs/plans/YYYY-MM-DD-<name>.md`.
