# Fixture project

This is a synthetic, committed fixture that every pipeline gate in research-claude is red-tested against; it has no research content of its own.
`tests/run_fixture.sh` copies this directory to a temp dir before linking the pipeline into it, so gates never run against the committed copy directly.
`data/raw/panel.csv` is generated data — regenerate it with `Rscript tests/make_fixture_data.R` (run from the repo root) rather than editing it by hand.
