# Pre-Submission Checklist

## Quality Gates
- [ ] Overall score >= 95
- [ ] All component scores >= 80
- [ ] Verifier pass (0 or 100)

## Manuscript
- [ ] Abstract <= 150 words (INV-5)
- [ ] JEL codes and keywords present (INV-6)
- [ ] All tables have notes (INV-1)
- [ ] All figures have notes (INV-2)
- [ ] No `\hline` -- booktabs only (INV-3)
- [ ] Notation consistent throughout (INV-7)
- [ ] Numbers in text match tables (INV-11)
- [ ] Compiles cleanly with no warnings
- [ ] pandoc `@key` citations; `cite-method: biblatex` on the PDF path; no top-level `csl:` (INV-9)
- [ ] When a preamble is supplied, hyperref second-to-last, cleveref after (INV-10)
- [ ] No hardcoded figure/table numbers -- use `@fig-`/`@tbl-` cross-references throughout

## Replication Package
- [ ] README follows AEA template
- [ ] `scripts/acquire/*` run from a clean state
- [ ] Data dictionary included
- [ ] Computational requirements documented
- [ ] License specified
- [ ] `quarto render <manuscript>` runs end-to-end

## Submission Materials
- [ ] Cover letter drafted
- [ ] Target journal selected (from journal profiles)
- [ ] Formatting matches journal requirements
- [ ] Author information complete
- [ ] Significance stars match journal convention (INV-4)
