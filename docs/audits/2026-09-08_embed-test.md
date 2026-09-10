# R-5 — Quarto `{{< embed >}}` from a `.qmd` source, tested on the fixture

**Date:** 2026-09-09 (fix round 1) · **Quarto version:** `1.9.37`

## RULING (confirmed, fix round 1)

**`{{< embed >}}` is CONFIRMED usable on Quarto 1.9.37 today — no future Quarto release is
needed — conditional on the embed source being resolvable without the render crossing a
directory boundary.** The original (2026-09-09, same-day) ruling below this section called this a
hard failure and recommended a permanent file-reference fallback. That ruling was wrong: it
correctly reproduced one failing case, but it was not the whole story, and a second round of
seven additional variations plus one further controller probe isolated the actual boundary
condition and a working pattern. The failing evidence from the first pass is kept below because
it is real and still diagnostic — it establishes exactly where the boundary sits — but it is no
longer the basis for the ruling.

### The working pattern

- `talks/` holds a **relative symlink** named after the declared manuscript, pointing at
  `../<manuscript>` (e.g. `talks/manuscript_fixture.qmd -> ../manuscript_fixture.qmd`). Relative,
  not absolute, so it survives a coauthor's clone.
- The talk embeds the symlink by its **bare filename**, not a `../`-relative path:
  `{{< embed manuscript_fixture.qmd#fig-trends >}}`. An embed of `../manuscript_fixture.qmd`
  (crossing into the parent directory in the shortcode itself) still fails — verified directly
  below.
- The symlink is not something `apply.sh` can create, because the manuscript's filename is
  per-project (`apply.sh` never reads the `CLAUDE.md` `manuscript:` declaration). Its owner is
  `/talk`: it resolves the manuscript via `python3 .claude/scripts/pipeline.py manuscript` and
  creates the link if absent, before rendering the talk.

### Root cause (stated once, so a later reader does not re-derive it)

Quarto's notebook-embed path re-renders the entire source `.qmd` beside wherever that source
*file* actually resides on disk, producing `<source>_files/mediabag` next to it. Its post-render
cleanup (`safeRemoveDirSync`, called from `renderCleanup`/`onPostProcess`) then compares that
freshly-created `mediabag` directory's location against the **rendering file's own directory**
(the talk's directory, e.g. `talks/`) and throws `safeRemoveDirSync: refusing to remove a
directory that isn't a subdirectory of <rendering dir>` whenever the two differ. A symlink placed
directly inside the talk's own directory makes the source *resolve* to a path inside that
directory (Quarto follows the file's own containing directory, not the link target's real path,
for this comparison), so the boundary condition is never triggered. A `../`-relative reference —
symlinked or not — always resolves to a path one level up, outside the talk's directory, and
always triggers it.

### Second-pass evidence (fix round 1) — eight variations, one boundary condition isolated

Run by the reviewer (seven variations) and the controller (an eighth, the working probe) against
this same fixture:

| Variation | Result |
|---|---|
| Talk in `talks/` embedding `../manuscript_fixture.qmd` | exit 1, no HTML (the original finding below) |
| Same, with `manuscript_fixture_files/` deleted first | exit 1 — same failure; the mediabag is created by the embed's own re-render, not inherited from a stale build |
| Manuscript rendered to HTML instead of PDF, same layout | exit 1 — output format is irrelevant |
| Talk at the project root (same directory as the manuscript) | **exit 0** — real PNG, real table |
| Talk co-located with the manuscript in a subdirectory (both moved down together) | **exit 0** — confirms the condition is *same directory*, not "project root" specifically |
| Talk in `talks/`, embed path written as an absolute path to the manuscript | exit 1 — same failure; the trigger is directory containment, not path syntax |
| Talk in `talks/`, embedding `../manuscript_fixture.qmd`, rendered with `--no-clean` | exit 1 — fails via a different code path, still fails |
| **Controller's probe: a relative symlink to the manuscript placed inside `talks/`, embedded by bare filename** | **exit 0** — 23,565-byte HTML, a real 31,347-byte PNG, and a table carrying genuine model output (`treated 0.258`, `Num.Obs. 400`); reproduced from a clean tree, same output size both times |

### This fixture, converted to the working pattern and re-verified

`tests/fixture-project/talks/manuscript_fixture.qmd` is now a relative symlink
(`-> ../manuscript_fixture.qmd`, git mode `120000`, tracked), and
`tests/fixture-project/talks/seminar_talk.qmd`'s two embeds were changed from
`../manuscript_fixture.qmd#<label>` to the bare `manuscript_fixture.qmd#<label>`.

```bash
cd tests/fixture-project
quarto render manuscript_fixture.qmd    # exit=0
quarto render talks/seminar_talk.qmd    # exit=0
```

Result: `talks/seminar_talk.html`, 23,715 bytes. `<img data-src="seminar_talk_files/figure-revealjs/
manuscript_fixture-fig-trends-output-1.png">` — the referenced file exists on disk at
`talks/seminar_talk_files/figure-revealjs/manuscript_fixture-fig-trends-output-1.png`, 31,347
bytes (matching the controller's probe size exactly). The rendered `<table>` contains genuine
model output, not placeholder text:

```
TWFE  treated 0.258*** (0.049)  Num.Obs. 400  R2 0.800  R2 Adj. 0.772  ...
FE: unit X  FE: year X  * p < 0.1, ** p < 0.05, *** p < 0.01
Standard errors clustered by unit in parentheses. Synthetic data.
```

Re-verified from a fully clean tree (all render artifacts deleted, both files re-rendered from
scratch): exit 0 again, identical 23,715-byte HTML and identical 31,347-byte PNG — reproducible,
not a cached-artifact fluke.

### Instruction for Tasks 3b.4 and 3b.5

- The storyteller rewrite (Task 3b.4) uses `{{< embed <manuscript>#<label> >}}` with the
  **bare filename**, never a `../`-relative path.
- Task 3b.5 (or whichever task owns `/talk`) must have `/talk` resolve the declared manuscript
  (`python3 .claude/scripts/pipeline.py manuscript`) and create the relative symlink
  `talks/<manuscript filename> -> ../<manuscript filename>` if it does not already exist, before
  rendering any talk. `apply.sh` does not own this — it has no access to the per-project
  `CLAUDE.md` manuscript declaration.
- The file-reference fallback (`manuscript_<project>_files/figure-pdf/<label>-1.pdf`) is **not**
  the path forward; it was correctly identified as a working alternative in the original pass but
  is no longer needed and depends on three fragile assumptions (render-target extension, the
  manuscript's own output-artifact naming, and staying in sync with the manuscript's `format:`)
  that the confirmed embed path avoids entirely.

---

## Original finding (2026-09-09, first pass — kept for its diagnostic boundary-establishing value)

**What was tested:** whether a `revealjs` talk in `tests/fixture-project/talks/` can pull a
figure (`fig-trends`) and a table (`tbl-main`) out of the declared manuscript
(`manuscript_fixture.qmd`, `format: pdf`) via `{{< embed ../manuscript_fixture.qmd#<label> >}}` —
i.e. a `../`-relative reference, no symlink.

**Commands and exit codes:**

```bash
cd tests/fixture-project
quarto render manuscript_fixture.qmd      # exit=0
quarto render talks/seminar_talk.qmd      # exit=1 (this specific case only — see ruling above)
```

The manuscript rendered cleanly to `manuscript_fixture.pdf` (xelatex, biblatex/biber, two-pass
compile, `Output created: manuscript_fixture.pdf`, exit 0).

The talk render failed with exit code 1. Full captured output:

```
Rendering qmd embeds
[1/1] ../manuscript_fixture.qmd

processing file: manuscript_fixture.qmd
1/11
2/11 [setup]
3/11
4/11 [build-panel]
5/11
6/11 [estimate-main]
7/11
8/11 [tbl-main]
9/11
10/11 [fig-trends]
11/11
output file: manuscript_fixture.knit.md

ERROR: Rendering of qmd notebook produced an unexpected result
ERROR: Refusing to remove directory /Users/andrew.mueller/Academic/research-claude/.claude/worktrees/pipeline-repair/tests/fixture-project/manuscript_fixture_files/mediabag that isn't a subdirectory of /Users/andrew.mueller/Academic/research-claude/.claude/worktrees/pipeline-repair/tests/fixture-project/talks

Stack trace:
    at safeRemoveDirSync (file:///Applications/quarto/bin/quarto.js:3249:11)
    at file:///Applications/quarto/bin/quarto.js:130159:9
    at Array.forEach (<anonymous>)
    at renderCleanup (file:///Applications/quarto/bin/quarto.js:130157:22)
    at file:///Applications/quarto/bin/quarto.js:131050:44
    at withTiming (file:///Applications/quarto/bin/quarto.js:15969:21)
    at Object.complete (file:///Applications/quarto/bin/quarto.js:131050:9)
    at eventLoopTick (ext:core/01_core.js:179:7)
    at async Object.onPostProcess (file:///Applications/quarto/bin/quarto.js:136879:28)
    at async renderFileInternal (file:///Applications/quarto/bin/quarto.js:136863:3)
    at async renderFile (file:///Applications/quarto/bin/quarto.js:136627:7)
    at async Object.renderOutputNotebook2 [as render] (file:///Applications/quarto/bin/quarto.js:141834:20)
    at async Object.render (file:///Applications/quarto/bin/quarto.js:142068:28)
    at async ensureNotebookContext (file:///Applications/quarto/bin/quarto.js:130325:5)
    at async renderFileInternal (file:///Applications/quarto/bin/quarto.js:136845:9)
    at async renderFiles (file:///Applications/quarto/bin/quarto.js:136582:9)
    at async render (file:///Applications/quarto/bin/quarto.js:142236:19)
    at async _Command.actionHandler (file:///Applications/quarto/bin/quarto.js:142481:24)
    at async _Command.execute (file:///Applications/quarto/bin/quarto.js:102102:7)
    at async _Command.parseCommand (file:///Applications/quarto/bin/quarto.js:101979:14)
    at async quarto4 (file:///Applications/quarto/bin/quarto.js:187653:5)
    at async file:///Applications/quarto/bin/quarto.js:187681:5
    at async file:///Applications/quarto/bin/quarto.js:187536:14
    at async mainRunner (file:///Applications/quarto/bin/quarto.js:187538:5)
    at async file:///Applications/quarto/bin/quarto.js:187674:3
```

`{{< embed >}}` re-renders the *entire source document* into an intermediate notebook
(`manuscript_fixture.embed.ipynb`) so it can pull the tagged cell out by label — it does not read
the manuscript's own render artifacts. That re-render ran the full R pipeline (`setup` →
`build-panel` → `estimate-main` → `tbl-main` → `fig-trends`, all 11 execution steps completed) and
produced `manuscript_fixture_files/mediabag`. Quarto's post-render cleanup then threw on that
directory for the reason established above (directory-containment check against the *rendering*
file's directory, not the source's). No `talks/seminar_talk.html` (or any `talks/*_files/`) was
produced at all — the failure occurs after every embed source has been executed but before the
revealjs HTML is written out. This is not a partial/empty-slide false pass — it is a hard failure
(exit 1) with no output file at all, and it was correctly diagnosed as such. What was wrong was
generalizing from this one case (a `../`-relative reference) to "embed does not work for this
project layout" — the boundary is directory containment of the *resolved source path*, not the
project layout in general, and a same-directory symlink resolves inside the boundary.

## Cleanup verification

All render artifacts (`manuscript_fixture.pdf`, `manuscript_fixture_files/`,
`manuscript_fixture_cache/`, `manuscript_fixture.embed.ipynb`, `talks/.quarto/`,
`talks/seminar_talk.html`, `talks/seminar_talk_files/`, `talks/manuscript_fixture_files/`,
`talks/manuscript_fixture_cache/`) were removed before committing, including after the fix-round-1
clean re-render. `manuscript_fixture.pdf`, `manuscript_fixture_files/`, and
`manuscript_fixture_cache/` are covered by the fixture's own `.gitignore` (`manuscript_*.pdf` and
the generic `*_files/`/`*_cache/` patterns); `manuscript_fixture.embed.ipynb` and `talks/.quarto/`
are not covered by any existing pattern and were removed manually. `git status --porcelain` after
cleanup shows only the intended additions: the new `talks/manuscript_fixture.qmd` symlink and the
modified `talks/seminar_talk.qmd`.
