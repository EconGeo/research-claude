---
name: promote
description: >
  Review pipeline changes made from a project session and land them upstream in
  research-claude. Use after improving a shared skill, agent, or rule from inside a
  paper project, or when a project override looks like it should be shared. Reports
  uncommitted edits to the linked tree and real files shadowing a canonical item.
allowed-tools: Read,Grep,Glob,Bash,Edit
---

# Promote

Under symlinks there are no forks to reconcile, because there is nothing to fork.
What remains is still real: an improvement made through a link is an **uncommitted
change in a repository no session is in**, and it will sit there indefinitely
unless something surfaces it. That is this skill's job.

---

## Step 1: Resolve the checkout

```bash
readlink .claude/skills/write
```

Take the research-claude path from the link target. Call it `$RC`. Then read the
lock's last line — `apply.sh` writes `commit=<sha>` in **both** install modes, so
the commit line cannot tell them apart; the discriminator is
`# installed via: tip (shared checkout)` versus `# installed via: pinned`:

```bash
grep '^# installed via' .claude/pipeline.lock
```

`tip` means this project is on the shared checkout — expected for the maintainer,
wrong for a coauthor. `pinned` means a project-local checkout detached at the lock
SHA, where a promotion lands in the wrong place; stop and say so.

## Step 2: Uncommitted upstream edits

```bash
git -C "$RC" status --porcelain -- agents skills rules references hooks templates seeds scripts
```

Every entry is an improvement made from some paper session that has not been
committed. For each one:

1. Show the diff.
2. Ask whether to keep it.
3. Commit it with a message naming the project it came from — that provenance is
   the only record of *why* the change was made, and it will not be recoverable
   later.

Do not batch unrelated edits into one commit. They came from different sessions
for different reasons.

## Step 2.5: Vendored trees

`zotpilot-skills/` and `ai-audit/` are vendored verbatim (each has its own `VENDORED.md`) and
are never edited in place — Step 2's pathspec deliberately excludes both, because an edit made
there through a project's link is not "an improvement to land," it is a fork of upstream. Left
unreported, the next `"$RC/scripts/sync-zotpilot-skills.sh"` / `"$RC/scripts/sync-ai-audit.sh"`
refresh `rm -rf`s the vendored directory and destroys it with no warning at all (Phase 3.2).

```bash
git -C "$RC" status --porcelain -- zotpilot-skills ai-audit
```

Any output here is a change Step 2 will never surface. **Report it before doing anything else in
this skill.** The fix belongs upstream (the `EconGeo/ZotPilot` fork or `EconGeo/ai-audit`) or in
the bridge skill that mediates it (`.claude/skills/lit-position`, `.claude/skills/new-project-ztp`,
etc. for ZotPilot); it is never committed here as-is.

## Step 3: Project overrides

Every non-symlink in `.claude/{skills,agents,rules}` whose name also exists in the
canonical tree:

```bash
for d in skills agents rules; do
  for f in .claude/$d/*; do
    [[ -L "$f" ]] && continue
    [[ -e "$RC/$d/$(basename "$f")" ]] && echo "override: $d/$(basename "$f")"
  done
done
```

For each, diff against canonical and decide:

- **Genuinely local** — leave it, and record one line saying why. An override with
  no recorded reason becomes indistinguishable from an accident.
- **Generally useful** — upstream it, then replace the real file with a link.

## Step 3.5: Divergence register

`docs/decisions/clo-author-divergences.md` exists because a divergence litigated once, on the day
it happens, costs one paragraph; the same divergence found three months later by an audit costs a
priority finding (D-2, D-3 and D-18 were exactly that — a mechanism correctly retired or
correctly introduced whose *purpose* nobody re-homed, found only because a 2026-09-23 audit went
looking). This is the point to catch the next one, not the audit that finds it later.

Ask, for every change from Step 2 and Step 3 about to be committed upstream:

- Does it **retire, replace, or newly diverge from** something clo-author did — a safeguard, a
  mechanism, a default? If clo-author is not the origin of what's changing, this does not apply.
- If yes: does an entry already cover it? If not, add one before committing — class it
  (`INHERITED` / `DELIBERATE DIVERGENCE` / `GAP` / `OBSOLETE`), name the purpose the old mechanism
  served, and say where that purpose lives now (a gate, a rule, or explicitly nowhere, with a
  reason). An entry with no recorded reason is indistinguishable from an oversight to the next
  reader — that is the register's own founding complaint about itself.

Skip this for changes with no clo-author lineage at all (most project overrides in Step 3 are
purely local additions, not divergences from anything upstream).

## Step 4: De-projectification check

Before any upstream commit, run the D5 scan from the gate:

```bash
"$RC/scripts/check_fork.sh"
```

**Refuse to commit a file naming a project, journal, or dataset.** A project noun
in the canonical tree is how the next project scaffolds wrong. If the change is
worth keeping but carries a project name, generalize it first — replace the name
with `<project>` and the specific dataset with a description of its role.

## Step 5: Refresh the lock

Offer to re-link so `.claude/pipeline.lock` records the new SHA — from the project,
`./bootstrap-pipeline.sh --tip` (`.claude/rules/shared-pipeline.md`), or from the
checkout, `"$RC/apply.sh" --project-dir "$PWD" --link --tip` (`--project-dir` is
required; `apply.sh` exits 1 without it). Without this the lock still names the
pre-promotion commit, and a coauthor bootstrapping from it gets the pipeline as it
was before the improvement.

A promotion that **adds a new top-level item** — a new skill directory, agent, rule
or hook — matters beyond the lock: no other project has a link to it until each one
re-links. A file added *inside* an existing skill directory needs no re-link, because
the link is to the directory and propagates on save. Say which case this is, and
confirm the install here:

```bash
"$RC/scripts/check_install.sh"          # this project
"$RC/scripts/check_install.sh" --all    # every project on this machine
```

---

## What this skill does NOT do

- Does not push. Committing upstream is enough; the user decides when to publish.
- Does not resolve merge conflicts in the shared checkout — if `$RC` has diverged
  from `origin/main`, stop and report it.
- Does not edit anything under `zotpilot-skills/` or `ai-audit/`, both vendored verbatim — see
  Step 2.5.
