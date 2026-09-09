# R-5 — Quarto `{{< embed >}}` from a `.qmd` source, tested on the fixture

**Date:** 2026-09-09
**Quarto version:** `1.9.37`

## What was tested

Whether a `revealjs` talk can pull a figure (`fig-trends`) and a table (`tbl-main`)
out of the declared manuscript (`manuscript_fixture.qmd`, `format: pdf`) via
Quarto's `{{< embed >}}` shortcode, per D-20's preferred path.

`tests/fixture-project/talks/seminar_talk.qmd` was created exactly as the brief
specifies:

```markdown
---
title: "Fixture talk"
format:
  revealjs:
    slide-number: true
bibliography: ../references.bib
---

## Trends

{{< embed ../manuscript_fixture.qmd#fig-trends >}}

## Estimate

{{< embed ../manuscript_fixture.qmd#tbl-main >}}
```

## Commands and exit codes

```bash
cd tests/fixture-project
quarto render manuscript_fixture.qmd      # exit=0
quarto render talks/seminar_talk.qmd      # exit=1
```

The manuscript rendered cleanly to `manuscript_fixture.pdf` (xelatex, biblatex/biber,
two-pass compile, `Output created: manuscript_fixture.pdf`, exit 0).

The talk render then failed with exit code 1. Full captured output:

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

## What actually happened

`{{< embed >}}` re-renders the *entire source document* (`manuscript_fixture.qmd`)
into an intermediate notebook (`manuscript_fixture.embed.ipynb`) so it can pull the
tagged cell out by label — it does not read the manuscript's own render artifacts.
That re-render ran the full R pipeline (`setup` → `build-panel` → `estimate-main` →
`tbl-main` → `fig-trends`, all 11 execution steps completed) and produced
`manuscript_fixture_files/mediabag`. Quarto's post-render cleanup then tried to
remove that directory under the assumption it was a subdirectory of the *caller's*
output tree (`talks/`), but the manuscript lives one level up from `talks/`, so the
path is not a subdirectory of `talks/` and the cleanup step throws and aborts the
whole render. No `talks/seminar_talk.html` (or any `talks/*_files/`) was produced at
all — the failure occurs after every embed source has been executed but before the
revealjs HTML is written out.

Because no HTML was produced, there is nothing to grep for `fig-trends`/`tbl-main`
content — the check the brief specifies
(`grep -c 'fig-trends\|tbl-main' talks/seminar_talk.html`) cannot even run:
`talks/seminar_talk.html` does not exist. `ls talks/*.html` returned no matches.
There is no `<img>`/`<svg>` for the figure and no `<table>` for the table anywhere,
because the render never reached HTML output.

This is not a partial/empty-slide false pass — it is a hard failure (exit 1) with no
output file at all.

## Ruling

**Fallback.** `{{< embed <manuscript>#<label> >}}` from a talk one directory below
the manuscript does not work with Quarto 1.9.37 for this project's layout (manuscript
at project root, `format: pdf`, talk under `talks/`). The failure is Quarto's own
notebook-embed cleanup logic, not a mistake in the fixture's shortcode syntax — the
embed source is correctly re-executed (all 5 R chunks run, right dependency order)
and only the post-render directory cleanup throws.

The manuscript therefore keeps `manuscript_<project>_files/` as the artifact source,
and the talk must reference the pre-rendered figure directly rather than embedding
the source `.qmd`:

```markdown
![](../manuscript_fixture_files/figure-pdf/fig-trends-1.pdf)
```

(Path/extension depend on the manuscript's actual render target — for this PDF-format
manuscript that is `figure-pdf/fig-trends-1.pdf`; a project rendering to `figure-ipynb/`
would need `.png` instead, as observed during this test.) `Task 3b.4` (the storyteller
rewrite) and the talk scaffold task should use this file-reference fallback, not
`{{< embed >}}`, until/unless a later Quarto release fixes the cross-directory
cleanup bug (the stack trace points at `safeRemoveDirSync` in
`renderCleanup`/`onPostProcess`, i.e. this looks like a Quarto defect, not
something the fixture triggered by using the shortcode incorrectly).

## Cleanup verification

All render artifacts (`manuscript_fixture.pdf`, `manuscript_fixture_files/`,
`manuscript_fixture_cache/`, `manuscript_fixture.embed.ipynb`, `talks/.quarto/`) were
removed before committing. `manuscript_fixture.pdf`, `manuscript_fixture_files/`, and
`manuscript_fixture_cache/` are already covered by the fixture's own
`tests/fixture-project/.gitignore` (`manuscript_*.pdf` and the generic `*_files/` /
`*_cache/` patterns); `manuscript_fixture.embed.ipynb` and `talks/.quarto/` are not
covered by any existing pattern and were removed manually. `git status --porcelain`
after cleanup shows only `tests/fixture-project/talks/` (new, containing exactly
`seminar_talk.qmd`) as an addition relevant to this task.
