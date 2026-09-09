# make_fixture_data.R — deterministic synthetic panel for tests/fixture-project.
# Run from the repo root: Rscript tests/make_fixture_data.R
set.seed(20260908L)
n_units <- 40L; n_years <- 10L
panel_fixture <- expand.grid(unit = seq_len(n_units), year = 2011L + seq_len(n_years) - 1L)
treat_year <- ifelse(panel_fixture$unit <= 20L, 2016L, 9999L)
panel_fixture$treated <- as.integer(panel_fixture$year >= treat_year[match(panel_fixture$unit, panel_fixture$unit)])
unit_fe <- rnorm(n_units, 0, 0.5)[panel_fixture$unit]
year_fe <- seq(0, 0.45, length.out = n_years)[panel_fixture$year - 2010L]
panel_fixture$outcome <- round(2 + unit_fe + year_fe + 0.30 * panel_fixture$treated + rnorm(nrow(panel_fixture), 0, 0.3), 4)
dir.create("tests/fixture-project/data/raw", recursive = TRUE, showWarnings = FALSE)
write.csv(panel_fixture, "tests/fixture-project/data/raw/panel.csv", row.names = FALSE)
message("wrote ", nrow(panel_fixture), " rows")
