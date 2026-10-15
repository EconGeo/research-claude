# Write the package-version record for a manuscript (.claude/rules/readable-code.md §3).
# Usage: Rscript .claude/scripts/package_versions.R manuscript_<project>.qmd package_versions.txt
# Run from the console, never from a chunk (INV-18). It lists the packages the file loads
# with library(); a package used only through pkg:: needs its own library() line.
args <- commandArgs(trailingOnly = TRUE)
stopifnot("usage: package_versions.R <file.qmd> <out.txt>" = length(args) == 2)

qmd_lines <- readLines(args[1], warn = FALSE)
library_lines <- grep("^\\s*library\\(", qmd_lines, value = TRUE)
packages <- unique(sub("^\\s*library\\(([A-Za-z0-9.]+)\\).*$", "\\1", library_lines))
stopifnot("no library() calls found" = length(packages) > 0)

# GitHub installs carry RemoteType/RemoteSha in DESCRIPTION; CRAN installs carry Repository.
describe_package <- function(package) {
  description <- packageDescription(package)
  source <- if (!is.null(description$RemoteSha)) {
    paste0(description$RemoteType, "@", description$RemoteSha)
  } else if (!is.null(description$Repository)) {
    description$Repository
  } else {
    "unknown"
  }
  paste(package, description$Version, source)
}

writeLines(c(R.version.string, vapply(packages, describe_package, character(1))), args[2])
message("Wrote ", length(packages), " packages to ", args[2])
