# Reference: setup

No registry agent named `setup` — this stage bootstraps the project, not a creator/critic
pair. No component is recorded and there is no critic or escalation target.

## Driver sequence
```
python3 .claude/scripts/pipeline.py manuscript
```
If that exits non-zero (no `CLAUDE.md`, or no single `manuscript: <file>.qmd` line, or the
declared file does not exist): **stop** and tell the user to declare it — "declare
`manuscript: <file>.qmd` in CLAUDE.md".

Check whether ZotPilot is configured: is `mcp__zotpilot__get_index_stats` available? If not,
run the `new-project-ztp` skill (it walks `/ztp-setup`, then indexes the library) before
continuing — `/lit-position` needs it.

```
python3 .claude/scripts/pipeline.py state init
```
No-op with a message if `quality_reports/pipeline_state.json` already exists.

## Approval-gate summary
Report: the resolved manuscript path, ZotPilot status (configured / just configured / user
declined indexing), and whether `pipeline_state.json` was created or already existed. No
score — nothing has been produced yet.

## Escalation
None. A missing `manuscript:` declaration is a stop, not a three-strikes escalation — there
is no creator to strike.
