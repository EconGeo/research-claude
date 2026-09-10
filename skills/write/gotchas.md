# Write Skill -- Gotchas

Known failure points and edge cases for paper drafting.

- Writer produces generic academic voice if `.claude/references/personal-style-guide.md` hasn't been extracted first. Run `/write style-guide` before drafting.
- Writer will draft results from strategy memo predictions if no estimation chunk exists yet -- the hard gate catches this, but watch for it in partial drafts.
- `@key` vs `[@key]` confusion is the most common citation issue. `@key` for "Author (Year)" in prose, `[@key]` for "(Author, Year)" parenthetical.
- Writer sometimes invents citation keys not in `references.bib`. Always verify generated `@key` citations against the actual bib file.
- The cleanup pass catches AI patterns but can over-correct domain-specific hedging that's actually appropriate (e.g., "may" in describing potential mechanisms is fine).
- Section ordering varies by paper type. Don't force reduced-form structure on structural papers.
- Abstract word count (150 max per INV-5) is a hard constraint -- the writer sometimes produces 200+ word abstracts on first pass.
