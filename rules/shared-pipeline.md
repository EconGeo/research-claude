# Shared Pipeline — what a symlinked `.claude/` means

`.claude/{skills,agents,rules,hooks}` are symlinks into a checkout of
`EconGeo/research-claude`. They are **not this project's files.**

**Editing one changes every paper immediately.** The edit lands as an
uncommitted change in the research-claude working copy, which no session is
"in". It will not appear in this project's `git status`, and nothing will warn
you.

## The three cases

- **Improving the pipeline** — edit through the link, then run `/promote` to
  review the change and commit it upstream. That is the intended path; it is how
  a fix stops being stranded in one paper.

- **Needing something only this paper wants** — `rm` the symlink and write a real
  file in its place. `apply.sh --link` treats a real file as a deliberate
  override and will never overwrite it, on this run or any later one.

- **Never** copy the whole tree back into the project to "make it local." That is
  the drift this design exists to end: six copies, each diverging, none knowing
  what the others learned.

## Edits propagate; membership does not

A link points at a *file*, so an edit upstream is visible here instantly — that is
the whole design. But a link cannot point at "whatever this directory will contain
later." An item **added** upstream gets no link here until the linker runs again:

```bash
./bootstrap-pipeline.sh --tip     # re-link: adds new items, prunes deleted ones
```

Per-directory links would make membership automatic, but then a project could
never keep a real file of its own beside the shared ones, and the override case
above would be impossible. Membership is the price of that escape hatch, so it is
checked rather than assumed:

```bash
RC="$(cd .claude/rules && cd "$(dirname "$(readlink quality.md)")/.." && pwd -P)"
"$RC/scripts/check_install.sh"
```

It reports items never linked here, links that resolve to nothing, links pointing
at some other checkout, symlinks committed into this repo, and overrides that a
clone would not receive.

## Which checkout you are on

`.claude/pipeline.lock` records the repo and commit. Two bootstrap modes, and
they deliberately do not share a checkout:

| Command | Checkout | Use |
|---|---|---|
| `./bootstrap-pipeline.sh --tip` | shared, `$RESEARCH_CLAUDE_HOME` (default `~/Academic/research-claude`), on `main` | maintainer — one `git pull` updates every project |
| `./bootstrap-pipeline.sh` | project-local `.pipeline/research-claude`, detached at the locked SHA | coauthor, or reproducing an archived result |

If pinned mode were allowed to detach the shared checkout, it would silently pin
every project on the machine to one paper's locked commit. Separating them
removes that hazard structurally rather than by warning about it.

## For coauthors

The linked directories are gitignored, so a fresh clone has nothing dangling.
One command materializes the pipeline:

```bash
./bootstrap-pipeline.sh
```

`EconGeo/research-claude` is public — no access grant is needed, only a clone.
