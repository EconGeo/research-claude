# Fixture project

This is a synthetic, committed fixture that every pipeline gate in research-claude is red-tested against; it has no research content of its own.
`tests/run_fixture.sh` copies this directory to a temp dir before linking the pipeline into it, so gates never run against the committed copy directly.
`data/raw/panel.csv` is generated data — regenerate it with `Rscript tests/make_fixture_data.R` (run from the repo root) rather than editing it by hand.
The empty `.here` file pins the R `here` package's project root to this directory; it is needed only for the literal in-place `cd tests/fixture-project && quarto render manuscript_fixture.qmd` (otherwise `here::here()` walks up and resolves to the research-claude worktree root instead) — it is not needed for the normal copy-to-temp-dir path, since that copy gets its own root another way.
