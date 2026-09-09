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

Take the research-claude path from the link target. Call it `$RC`. Confirm it
against `.claude/pipeline.lock` — if the lock names a commit but `$RC` is on
`main`, this project is on the shared (`--tip`) checkout, which is expected for
the maintainer and wrong for a coauthor.

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

Offer to re-run `apply.sh --link` so `.claude/pipeline.lock` records the new SHA.
Without this the lock still names the pre-promotion commit, and a coauthor
bootstrapping from it gets the pipeline as it was before the improvement.

A promotion that **adds** a file matters beyond the lock: no other project has a
link to it until each one re-links. Say so, and confirm the install here:

```bash
"$RC/scripts/check_install.sh"          # this project
"$RC/scripts/check_install.sh" --all    # every project on this machine
```

---

## What this skill does NOT do

- Does not push. Committing upstream is enough; the user decides when to publish.
- Does not resolve merge conflicts in the shared checkout — if `$RC` has diverged
  from `origin/main`, stop and report it.
- Does not edit anything under `zotpilot-skills/`, which is vendored verbatim.
