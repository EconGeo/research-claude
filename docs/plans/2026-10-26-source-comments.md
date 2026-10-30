# Source Comments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tagged outside-world claims in a paper's `.qmd` get their source paragraph, extracted from a local file and checked word for word, shown as a Word comment in an optional "sourced" Word build, with warn-only checks at render, commit and critic-inputs.

**Architecture:** One shipped Python module, `scripts/source_check.py`, does everything that touches sources: it scans `.src` tags and the design quote, extracts and cleans source text, finds the paragraph, computes each claim's state against an approvals file, and prints warnings or JSON. A shipped Lua filter, `scripts/source_comments.lua`, runs in every render but acts only when metadata `source-comments: true` is set; it calls `source_check.py --json` and turns each tag into a pandoc comment span. `pipeline.py` gains `sources approve` (author-token gated) and `sources docx`, and calls the check from `commit-check` and `critic-inputs`.

**Tech Stack:** Python 3 stdlib (csv, hashlib, html.parser, unicodedata, subprocess), `pdftotext` (poppler), Quarto 1.9 / pandoc 3 Lua filters, pytest (unittest-style classes, as in `tests/`).

**Spec:** `docs/superpowers/specs/2026-10-26-source-comments-design.md` — read it in full first; §8 records the author's decisions.

## Global Constraints

- Warn only: nothing in this feature makes a render or a commit fail, except the 100 MB staged-file check in Task 6. `source_check.py` exits 0 in every mode except an internal usage error.
- Never emit source text that did not come from the file: a FAILED or NOT ON THIS MACHINE claim gets a comment saying so, never a paragraph.
- The supporting sentence is **underlined** (`[...]{.underline}`), not bold.
- The plain build's output is unchanged: with `source-comments` unset, the filter returns the document untouched.
- The sourced build writes `<manuscript stem>_sourced.docx` and never overwrites the plain `.docx`.
- A session never approves on the author's behalf: `sources approve` requires a fresh author token from the line `approve sources: <id>[, <id>…]` in the author's own message.
- Nothing project-specific ships (`./scripts/check_fork.sh` exit 0 before each commit touching `scripts/`, `rules/`, `hooks/`, `skills/`).
- Comment author string: `Source check`.
- States, exactly: `APPROVED`, `UNREVIEWED`, `NEEDS REVIEW`, `FAILED`, `NOT ON THIS MACHINE`.
- Files under `data/raw/` are committed when each is under 100 MB (104,857,600 bytes); larger ones stay off GitHub.
- Never pass a timeout to a live `claude -p` run (repo CLAUDE.md).
- Run the unit suite as `python3 -m pytest tests/<file> -q`.

## Review Focus

1. A sentence that wraps across lines with a hyphen in the PDF ("com-\npensation") is expected to match the unhyphenated sentence → Task 1 `test_dehyphenated_match`.
2. A sentence that appears in two paragraphs (form boilerplate) must be FAILED "ambiguous: 2 paragraphs", not silently pick one → Task 1 `test_ambiguous_sentence_fails`.
3. Ligatures and typographic quotes from PDF extraction ("ﬁnal", "Firm’s") must match plain typing → Task 1 `test_nfkc_and_quotes`.
4. A claim span containing markdown and a citation (`[*NWMLS* rule [@nwmls2022]]{.src ref="x" id="c1"}`) must be found, and its claim hash must not change when only whitespace changes → Task 2 `test_tag_with_citation`, `test_claim_hash_whitespace_stable`.
5. A tagged manuscript rendered to PDF, or to plain docx, renders the claim text with no comment and no error → Task 4 `test_plain_docx_unchanged`, `test_pdf_render_ignores_tags`.

---

### Task 1: Source extraction and the verbatim paragraph match

**Files:**
- Create: `scripts/source_check.py`
- Create: `tests/test_source_check.py`
- Create: `tests/fixtures/sources/form_lines.txt`, `tests/fixtures/sources/page.html`, `tests/fixtures/sources/hyphen.txt`, `tests/fixtures/sources/boiler.txt`
- Modify: `scripts/SHIPPED` (add `source_check.py`)

**Interfaces:**
- Produces:
  - `extract_text(path: Path) -> str` — `.pdf` via `pdftotext <path> -` (no `-layout`); `.html`/`.htm` via `html.parser` (block tags `p, div, li, br, h1-h6, tr` end a paragraph with a blank line); anything else read as UTF-8.
  - `clean(text: str, rules: list[str]) -> str` — rule `trailing-line-numbers` deletes a trailing ` \d{1,4}` on each line and drops lines that are only digits; unknown rule names raise `ValueError`.
  - `normalise(s: str) -> str` — NFKC, curly quotes/apostrophes to straight, all whitespace runs to one space, stripped.
  - `find_paragraph(text: str, sentence: str) -> tuple[str, str | None, str]` — returns `(status, paragraph, reason)` with status `"ok"`, `"not-found"` or `"ambiguous"`. Paragraphs split on blank lines. Match on `normalise`d text; if no match, retry on text with `-\n` line-end hyphenation joined. `paragraph` is the normalised paragraph with the sentence wrapped as `[<sentence>]{.underline}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_source_check.py` (class `ExtractMatch(unittest.TestCase)`):
  - `test_trailing_line_numbers`: `clean(form_lines.txt, ["trailing-line-numbers"])` contains `"listing or compensation agreement"` and no `" 206"`, and `find_paragraph(...)` for the Form 21 ¶u sentence returns `"ok"` with a paragraph that does not end in a digit (the spike's stray `216`).
  - `test_not_found_never_returns_text`: `find_paragraph(text, "NWMLS stopped posting compensation offers.")` → `("not-found", None, <reason naming the sentence>)`.
  - `test_ambiguous_sentence_fails`: `boiler.txt` has the same sentence in two paragraphs → `("ambiguous", None, "ambiguous: 2 paragraphs")`.
  - `test_dehyphenated_match`: `hyphen.txt` wraps "com-\npensation" → `"ok"`.
  - `test_nfkc_and_quotes`: source "the ﬁnal Firm’s fee" matches typed "the final Firm's fee".
  - `test_html_paragraphs`: `page.html` `<p>` blocks are separate paragraphs; a sentence in the second `<p>` returns only that paragraph.
  - `test_underline_markup`: returned paragraph contains `"[" + normalised sentence + "]{.underline}"` exactly once.
  - `test_unknown_cleanup_rule`: `clean("x", ["nope"])` raises `ValueError`.
- [ ] **Step 2:** `python3 -m pytest tests/test_source_check.py -q` → FAIL (module missing).
- [ ] **Step 3:** Implement the four functions in `scripts/source_check.py`. Fixture `form_lines.txt` is the Form 21 ¶u block as `pdftotext` emits it (line numbers at line ends, a lone `216` line): generate it once with `pdftotext ~/Research/paper-D/data/raw/legal/2023-07_nwmls_form21_rev7-23_hosted_spokanerealtors.pdf - | sed -n 684,700p` and check it starts at `205` / `u.` and ends after `216`. `tests/` is not scanned by `check_fork.sh`; nothing from it may move into `scripts/`.
- [ ] **Step 4:** Same command → PASS.
- [ ] **Step 5:** Add `source_check.py` to `scripts/SHIPPED`; `./scripts/check_fork.sh` exit 0; commit `"source_check: extraction, cleanup and verbatim paragraph match"`.

### Task 2: Registry, tags, design quote, approvals and states

**Files:**
- Modify: `scripts/source_check.py`
- Modify: `tests/test_source_check.py`

**Interfaces:**
- Consumes: Task 1 functions; `design_block.design_block(text)` from `scripts/design_block.py`.
- Produces:
  - Registry `quality_reports/sources.csv`, columns exactly `id,file,label,page,sentence,cleanup,ocr` (`cleanup` is `;`-separated rule names; `ocr` is `true`/`false`).
  - Approvals `quality_reports/source_approvals.csv`, columns exactly `tag_id,ref,claim_sha256,file_sha256,approved_at`.
  - `Tag = NamedTuple(tag_id: str, ref: str, claim: str)`.
  - `scan_tags(qmd_text: str) -> list[Tag]` — `[claim]{.src ref="R" id="I"}` with balanced brackets inside the claim; attribute order free. Plus, when the design block has `treatment.source` with `cite` and `quote`, one `Tag("design", "design:<cite>", <quote>)`.
  - `claim_sha256(claim: str) -> str` — sha256 of `normalise(claim)`.
  - `Result = NamedTuple(tag: Tag, state: str, paragraph: str | None, reason: str, label: str, page: str, ocr: bool)`.
  - `check(root: Path, qmd_text: str) -> list[Result]` — state rules: ref not in registry → FAILED "no registry entry"; file missing → NOT ON THIS MACHINE; match not ok → FAILED with the match reason; no approval row for `tag_id` → UNREVIEWED; approval's `claim_sha256` or `file_sha256` differs from now → NEEDS REVIEW (reason names which); else APPROVED.
  - `warning_lines(results: list[Result]) -> list[str]` — one `source-check: FAILED <tag_id> (<ref>): <reason>` / `NEEDS REVIEW` line each; then at most one `source-check: <n> claims not yet reviewed` and one `source-check: <n> sources not on this machine`; nothing when all are APPROVED.

- [ ] **Step 1: Failing tests** (class `States`, each builds a temp project with `CLAUDE.md`, a `.qmd`, the two CSVs and a source file):
  - `test_each_state` — one tag per state, asserts the exact state string for each.
  - `test_claim_change_needs_review` — approve `c1`, edit only its claim text → NEEDS REVIEW, reason mentions "claim"; a second tag on the same ref stays APPROVED (author decision §8.1).
  - `test_file_change_needs_review` — approve, append a byte to the source file → NEEDS REVIEW, reason mentions "file".
  - `test_tag_with_citation` — `[*NWMLS* rule [@nwmls2022]]{.src ref="x" id="c1"}` yields `Tag("c1","x","*NWMLS* rule [@nwmls2022]")`.
  - `test_claim_hash_whitespace_stable` — reflowing the claim across two lines leaves `claim_sha256` unchanged.
  - `test_design_quote_tag` — a `design:` block with `source: {cite: key2024, page: 12, quote: "the rule took effect"}` yields `Tag("design","design:key2024","the rule took effect")`; no design block → no such tag.
  - `test_warning_lines_summarise` — 3 UNREVIEWED + 2 NOT ON THIS MACHINE + 1 FAILED → exactly 3 lines, the two summaries carry `3` and `2`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Read the design quote with a regex over `design_block(text)` for `source:\s*\{[^}]*cite:\s*([^,}\s]+)[^}]*quote:\s*"([^"]*)"`; do not add a YAML dependency.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `"source_check: registry, tags, design quote, approval states"`.

### Task 3: Command line — warnings, JSON and the post-render hook

**Files:**
- Modify: `scripts/source_check.py`
- Modify: `tests/test_source_check.py`

**Interfaces:**
- Produces CLI: `python3 .claude/scripts/source_check.py [MANUSCRIPT] [--root DIR] [--json]`.
  - No `MANUSCRIPT`: resolve the single `manuscript: <file>.qmd` line in `<root>/CLAUDE.md`; none → print nothing, exit 0 (not a paper project).
  - Default output: `warning_lines`, exit 0.
  - `--json`: `{"<tag_id>": {"state", "label", "page", "ocr", "paragraph", "reason"}}` on stdout, exit 0.
  - Run as a Quarto `post-render` step (env `QUARTO_PROJECT_OUTPUT_FILES` set) it behaves as the default mode for the declared manuscript.
  - Any internal exception → one line `source-check: internal error: <msg>` and exit 0 (fail open; a FAILED match is never an internal error).

- [ ] **Step 1: Failing tests** (class `Cli`, subprocess against a temp project): `test_default_prints_warnings_exit0`, `test_json_shape` (keys exactly as above), `test_no_manuscript_silent`, `test_internal_error_fails_open` (unreadable `sources.csv` → exit 0 and the internal-error line).
- [ ] **Step 2:** run → FAIL. **Step 3:** implement `main(argv: list[str]) -> int`. **Step 4:** run → PASS.
- [ ] **Step 5:** commit `"source_check: CLI, JSON and post-render mode"`.

### Task 4: Lua filter and the sourced Word build

**Files:**
- Create: `scripts/source_comments.lua`
- Modify: `scripts/SHIPPED` (add `source_comments.lua`)
- Modify: `seeds/_quarto.yml`
- Modify: `scripts/pipeline.py` (new subcommand `sources docx`)
- Create: `tests/test_source_comments_render.py`

**Interfaces:**
- Consumes: `source_check.py --json` (Task 3).
- Produces:
  - `seeds/_quarto.yml`: `filters: [.claude/scripts/source_comments.lua]`; `post-render:` becomes a list: `python3 .claude/scripts/fix_docx_floats.py`, `python3 .claude/scripts/source_check.py`.
  - Filter behaviour: if `meta["source-comments"]` is not true, return the document unchanged. Otherwise call `pandoc.pipe("python3", {".claude/scripts/source_check.py", "--json"}, "")` once, and replace each `Span` with class `src` by: a `comment-start` Span (`id` = running integer, `author="Source check"`) whose content is `pandoc.read(header .. paragraph).blocks[1].content`, the claim inlines, then a `comment-end` Span. Header: `<label>, p. <page>. ` plus `[OCR] ` when `ocr`, plus `<STATE>: ` unless APPROVED. FAILED / NOT ON THIS MACHINE: content is `SOURCE CHECK <STATE>: <reason>` with no paragraph. The design quote's comment anchors on the first Span with class `src-design` if the manuscript has one, else is skipped (a manuscript marks where it states the treatment with `[...]{.src-design}`).
  - `pipeline.py sources docx` → runs `quarto render <ms> --to docx -M source-comments:true --output <stem>_sourced.docx` from the root, then prints the `warning_lines` and the output path; returns quarto's exit code.

- [ ] **Step 1: Verify two Quarto facts before writing the filter** (record each as `tested:` in the filter's header comment): (a) a project-level `filters:` in `_quarto.yml` applies to a `quarto render x.qmd --to docx`; (b) `quarto render x.qmd --to docx --output y.docx -M source-comments:true` writes `y.docx` and leaves `x.docx` alone. If either fails, stop and report (core rule 8) — the fallback is passing `--lua-filter` and renaming after render, which changes this task's interface.
- [ ] **Step 2: Failing tests** (skip the class when `quarto` or `pdftotext` is missing; the fixture project is a temp copy with `_quarto.yml` from the seed, `.claude/scripts` symlinked to `scripts/`, a `word-reference.docx`-free docx block):
  - `test_sourced_docx_has_comment` — `comments.xml` exists, `w:author="Source check"`, the comment text contains the paragraph, the sentence run carries `<w:u w:val="single"/>`, and `document.xml` has `commentRangeStart`/`commentRangeEnd` around the claim.
  - `test_failed_claim_comment_has_no_source_text` — a tag whose sentence is absent yields a comment starting `SOURCE CHECK FAILED` and containing no source-file text.
  - `test_plain_docx_unchanged` — plain render has no `word/comments.xml` and the claim text is present.
  - `test_pdf_render_ignores_tags` — `--to pdf` exits 0 and `pdftotext` of the output contains the claim text.
  - `test_sourced_does_not_overwrite_plain` — after `sources docx`, `<stem>.docx` mtime is unchanged.
- [ ] **Step 3:** run → FAIL. **Step 4:** implement filter, seed edit and `sources docx`. **Step 5:** run → PASS; `./scripts/check_fork.sh` exit 0.
- [ ] **Step 6:** commit `"Source comments: Lua filter, seed wiring, pipeline.py sources docx"`.

### Task 5: Author approval — `approve sources:` token and `sources approve`

**Files:**
- Modify: `scripts/author_token.py`, `hooks/design-token.py`, `hooks/design-guard.py`, `scripts/pipeline.py`
- Modify: `tests/test_design_token.py`, `tests/test_design_guard.py`
- Create: `tests/test_sources_approve.py`

**Interfaces:**
- Consumes: `source_check.check`, `claim_sha256`, approvals CSV (Task 2).
- Produces:
  - `author_token.approval()` also accepts the whole line `approve sources: <id>[, <id>…]` (same trimming, case, fence, `>` and one-per-message rules as rule 13) → `("sources", "<comma-joined ids>")`. `approve sources` with no ids → None.
  - `design-token.py` issues a `sources` token with `design_hash=None` and the ids as `reason`; its `additionalContext` names the ids.
  - `design-guard.py` refuses a Bash `claude` command containing `approve sources`, exactly as it does `approve design`.
  - `pipeline.py sources approve <id>…` → requires a fresh `sources` token whose ids equal the arguments (set equality), consumes it, and appends one approvals row per id with the current `claim_sha256` and `file_sha256` and a UTC ISO timestamp. Refuses (exit 1, no rows written) when: no fresh token, ids differ, or any id is FAILED or NOT ON THIS MACHINE.

- [ ] **Step 1: Failing tests:** `test_approval_sources_line` (parses; ids preserved in order), `test_sources_needs_ids`, `test_guard_refuses_nested_approve_sources`, `test_approve_writes_rows`, `test_approve_without_token_refused`, `test_approve_mismatched_ids_refused`, `test_approve_failed_claim_refused`, `test_token_single_use`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run those files plus `tests/test_design_token.py tests/test_design_guard.py tests/test_design_lock.py` → PASS (design behaviour unchanged).
- [ ] **Step 5:** commit `"sources approve: author-token gated approvals"`.

### Task 6: Warnings at commit and critic-inputs; the 100 MB staged-file check

**Files:**
- Modify: `scripts/pipeline.py` (`_commit_check_staged`, `critic_inputs`)
- Modify: `tests/test_commit_check.py`, `tests/test_writer_critic_inputs.py`

**Interfaces:**
- Consumes: `source_check.py` CLI via `run_script(root, "source_check.py", tmp_rel)`.
- Produces:
  - `commit-check` prints each source-check line prefixed `WARN ` and never adds to `probs` for them. It **does** add a problem for any staged file ≥ 104,857,600 bytes: `staged file <path> is <n> MB — GitHub refuses files over 100 MB; unstage it and keep it off GitHub`.
  - `critic-inputs` log gains a section `## source_check.py <ms> — exit <rc>` with the output, and the summary gains `source-check <n> warnings`.

- [ ] **Step 1: Failing tests:** `test_commit_check_warns_on_failed_source` (exit 0, output has `WARN source-check: FAILED`), `test_commit_check_refuses_101mb_staged_file` (sparse file via `truncate`), `test_commit_check_allows_99mb_staged_file`, `test_critic_inputs_has_source_section`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run plus the whole of `tests/test_commit_check.py` → PASS.
- [ ] **Step 5:** commit `"commit-check and critic-inputs: source warnings; refuse staged files over 100 MB"`.

### Task 7: Rules and the plain-or-sourced offer

**Files:**
- Modify: `rules/quarto-word.md` (§Build: new subsection "Source comments")
- Modify: `rules/core.md` rule 3 tag → `[hook: read-gate for edits; script: source_check for tagged claims; judgment for the rest]`
- Modify: `rules/quarto-empirical.md` (design block: the treatment quote is checked against a `design:<cite>` registry entry)
- Modify: `seeds/gitignore`
- Modify: `tests/test_rule_reads.py` only if its fixture lists rule text it asserts on

**Content to pin:**
- quarto-word.md "Source comments": the tag syntax; registry and approvals paths and columns; the five states; "Before building a Word draft for the author, ask once: plain, or with source comments (`python3 .claude/scripts/pipeline.py sources docx`)"; approval only via the author's `approve sources: <ids>` line; tag every claim about the outside world, tag when unsure, and list in the final message any untagged outside-world claim noticed.
- seeds/gitignore: replace the `data/raw/**` block with a comment "Committed when each file is under 100 MB; list larger files below" and no blanket ignore.

- [ ] **Step 1:** edit. **Step 2:** `python3 -m pytest tests -q -x --ignore=tests/evals` → PASS; `./scripts/check_fork.sh` exit 0.
- [ ] **Step 3:** commit `"Rules: source comments, plain-or-sourced offer, data/raw under 100 MB"`.

### Task 8: Roll out to the seven papers

**Files (in each of `~/Research/{paper-B,paper-G,paper-H,paper-D,paper-A,paper-F,paper-C}`):**
- Modify: `_quarto.yml` (add the `filters:` line; `post-render:` list as in the seed)
- Modify: `.gitignore` (drop the blanket `data/raw/**`; add each file under `data/raw/` ≥ 100 MB by path)

- [ ] **Step 1:** In each paper, list `find data/raw -type f -size +102400k`; add those paths to `.gitignore`; then confirm `git status --short data/raw | head` shows only files under 100 MB (do not stage them in this task).
- [ ] **Step 2:** Edit `_quarto.yml`. Run `./apply.sh --project-dir <paper> --link` (new shipped scripts are new link members), then `./scripts/check_install.sh --all` → exit 0.
- [ ] **Step 3:** In each paper, `quarto render <ms> --to docx` → exit 0 and the `.docx` has no `word/comments.xml`.
- [ ] **Step 4:** One local commit per paper, staging only `_quarto.yml` and `.gitignore`, message `"Wire source comments (research-claude <sha>)"`. Do not push.
- [ ] **Step 5:** End-to-end in paper-D on a scratch branch: one registry row for Form 21 ¶u (`data/raw/legal/2023-07_nwmls_form21_rev7-23_hosted_spokanerealtors.pdf`, cleanup `trailing-line-numbers`), one tagged sentence, `pipeline.py sources docx` → the comment shows the ¶u paragraph with the sentence underlined. Open it in Word for the author to look at; then delete the scratch branch unless the author keeps it.
