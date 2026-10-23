# tests/r/test_claims_helpers.R — run: Rscript tests/r/test_claims_helpers.R <repo-root>
repo_root <- commandArgs(trailingOnly = TRUE)[[1]]
eval(parse(file.path(repo_root, "templates", "claims-helpers.R.txt")))  # test harness only; manuscripts paste
repo_root <- normalizePath(repo_root)
project_root <- tempfile("rc_project_"); dir.create(file.path(project_root, "paper"), recursive = TRUE)
project_root <- normalizePath(project_root)
writeLines("manuscript: paper/manuscript.qmd", file.path(project_root, "CLAUDE.md"))
setwd(project_root)
design_qmd <- tempfile(fileext = ".qmd")
writeLines(c("---", "title: t", "design:", "  hypotheses:", "    H1: {outcome: mpg, spec: m_h1}", "---", "x"), design_qmd)
design <- rc_design(design_qmd)
expect_error_matching <- function(expr, pattern) {
  message_seen <- tryCatch({ expr; NULL }, error = function(e) conditionMessage(e))
  if (is.null(message_seen) || !grepl(pattern, message_seen)) stop("expected error /", pattern, "/, got: ", message_seen)
}
stopifnot("1% level" = rc_sig(0.004) == "statistically significant at the 1% level",
          "5% boundary is inclusive" = rc_sig(0.05) == "statistically significant at the 5% level",
          "10% boundary is inclusive" = rc_sig(0.10) == "statistically significant at the 10% level",
          "above 10%" = rc_sig(0.11) == "not statistically significant",
          "stars" = identical(c(rc_stars(0.01), rc_stars(0.05), rc_stars(0.1), rc_stars(0.2)), c("***", "**", "*", "")),
          "direction" = rc_dir(-1, "rose", "fell") == "fell" && rc_dir(2, "rose", "fell") == "rose",
          "comparison" = rc_cmp(3, 2, "larger", "smaller") == "larger",
          "comparison tie" = rc_cmp(2, 2.0001, "larger", "smaller", same = "the same", tol = 0.01) == "the same",
          "numbers" = rc_num(1234.567) == "1,234.57" && rc_pct(0.0312) == "3.1%")
expect_error_matching(rc_num(NA_real_), "not one finite number")
expect_error_matching(rc_sig(NaN), "not one finite number")
expect_error_matching(rc_sig(1.2), "not a probability")
expect_error_matching(rc_dir(0, "u", "d"), "exactly 0")
expect_error_matching(rc_num(c(1, 2)), "not one finite number")
fingerprint_path <- tempfile(fileext = ".json")
expect_error_matching(rc_fingerprint(path = fingerprint_path), "m_h1")          # missing spec object
m_h1 <- lm(mpg ~ wt, data = mtcars)
rc_fingerprint(path = fingerprint_path); fp_main <- readLines(fingerprint_path)
m_robust <- lm(mpg ~ wt + hp, data = mtcars)                                    # named in no hypothesis
rc_fingerprint(path = fingerprint_path); fp_with_robust <- readLines(fingerprint_path)
m_robust <- lm(mpg ~ wt + hp + qsec, data = mtcars)
rc_fingerprint(path = fingerprint_path); fp_robust_changed <- readLines(fingerprint_path)
stopifnot("an added model changes the fingerprint" = !identical(fp_main, fp_with_robust),
          "a re-estimated robustness model changes the fingerprint" = !identical(fp_with_robust, fp_robust_changed),
          "models are listed" = any(grepl('"models": \\["m_h1", "m_robust"\\]', fp_robust_changed)))
m_h1 <- "not a model"
expect_error_matching(rc_fingerprint(path = fingerprint_path), "not a fitted model")
if (requireNamespace("fixest", quietly = TRUE)) {
  m_h1 <- fixest::feols(mpg ~ wt | cyl, data = mtcars)
  m_multi <- fixest::feols(c(mpg, hp) ~ wt, data = mtcars)
  rc_fingerprint(path = fingerprint_path)
  stopifnot("fixest_multi is fingerprinted" = any(grepl("m_multi", readLines(fingerprint_path))))
}
hash_before <- rc_design_hash(design); design$hypotheses$H1$outcome <- "hp"
stopifnot("design hash moves with the design" = hash_before != rc_design_hash(design))
data_dir <- tempfile(); dir.create(data_dir); writeLines("a,b\n1,2", file.path(data_dir, "x.csv"))
hash_data <- rc_data_hash(data_dir); writeLines("a,b\n1,3", file.path(data_dir, "x.csv"))
stopifnot("data hash moves with the data" = hash_data != rc_data_hash(data_dir))
expect_error_matching(rc_design(tempfile()), "")

# Quarto runs chunks in the manuscript's directory: defaults resolve under the CLAUDE.md root.
dir.create(file.path(project_root, "data", "raw"), recursive = TRUE)
writeLines("a,b\n1,2", file.path(project_root, "data", "raw", "x.csv"))
setwd(file.path(project_root, "paper"))
stopifnot("rc_root walks up to CLAUDE.md" = identical(rc_root(), project_root))
hash_from_paper <- rc_data_hash()
setwd(project_root)
stopifnot("data hash is the same from the root and from a subdirectory" = identical(hash_from_paper, rc_data_hash()),
          "data hash covers <root>/data/raw" = hash_from_paper != rc_data_hash("no/such/dir"))
writeLines("a,b\n1,9", file.path(project_root, "data", "raw", "x.csv"))
stopifnot("data hash moves when <root>/data/raw changes" = hash_from_paper != rc_data_hash())
hash_raw_only <- rc_data_hash()
dir.create(file.path(project_root, "data", "derived"), recursive = TRUE)
writeLines("rebuilt by the render", file.path(project_root, "data", "derived", "panel.csv"))
stopifnot("data/derived (rewritten by the render) is not in the cache key" = identical(hash_raw_only, rc_data_hash()),
          "the pasted block carries its version" = is.character(rc_helpers_version))
setwd(file.path(project_root, "paper"))
written <- rc_fingerprint()
stopifnot("fingerprint lands at <root>/quality_reports" =
            identical(normalizePath(written), file.path(project_root, "quality_reports", "render_fingerprint.json")),
          "no stray quality_reports beside the manuscript" = !dir.exists(file.path(project_root, "paper", "quality_reports")))
rc_fingerprint(path = "quality_reports/other.json")
stopifnot("a relative path argument resolves under the root" =
            file.exists(file.path(project_root, "quality_reports", "other.json")))
setwd(tempdir())
lonely_dir <- tempfile("rc_no_root_"); dir.create(lonely_dir); setwd(lonely_dir)
if (!file.exists(file.path(dirname(lonely_dir), "CLAUDE.md"))) expect_error_matching(rc_root(), "no CLAUDE.md")
setwd(project_root)
B_model <- lm(mpg ~ wt, data = mtcars); a_model <- lm(mpg ~ hp, data = mtcars)
rc_fingerprint(path = fingerprint_path)
stopifnot("model names sort by radix (locale-independent)" =
            any(grepl('"models": \\["B_model", "a_model", "m_h1"', readLines(fingerprint_path))))
cat("claims-helpers: OK\n")
