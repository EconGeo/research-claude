# Prose-Number Gate Holes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the six holes in `scripts/prose_number_check.py` (INV-11's gate) that a project audit found on 2026-09-23 and that no research-claude plan ever picked up.

**Architecture:** All changes are in the one shared scanner. The scanner splits the manuscript into prose lines and (new) caption strings in a single pass, which also fixes fence matching. It then runs three passes. The existing literal pass now also covers captions. A new sign-glue pass is a hard fail and cannot be allowlisted. A new verdict-word pass is advisory unless the project declares a ceiling. Each hole gets a failing test first.

**Tech Stack:** Python 3 stdlib (`re`, `csv`, `os`); tests are `unittest.TestCase` classes run by `python3 -m pytest tests/ -q`.

**Spec:** `~/Research/POGM4/quality_reports/2026-09-23_pipeline_gate_audit.md`. This plan implements its §D1 (sign glue), §D2 (verdict words), §D3 (captions) and §D6 (fence desync), plus two smaller holes from §A: the `` `{r}` `` inline syntax and the trailing-comma key. §D4/§D5 already landed (`quarto_structure_check.py`, `chunk_labels()`). §D7 is project-local, and §D8 landed as repair-plan item 1.6. The executor reads §A and §D of that audit in full before Task 1.

## Why this plan exists

The repair plan (`docs/plans/2026-09-23_pipeline-repair.md`) Phase 5 says the number-gate holes are "either Phase 1 above or genuinely project-local". Neither is true. Phase 1 has no item for them, and the audit calls them research-wide. The closeout handoff's §4 does not list them either, so `CLAUDE.md` came to say "Nothing is open in this repo" while they were open. Re-tested on 2026-09-28 against `main` at `efe9e70`:

- a sign typed beside an inline value passes with 0 literals;
- everything after an unclosed fence is skipped and the gate passes;
- a `#| fig-cap:` caption is not scanned. A Markdown `![…]` caption *is* scanned.

## Global Constraints

- **Edits in the main working copy go live in six papers on save** (`CLAUDE.md`). All work happens on branch `prose-gate-holes` in a worktree. Use `superpowers:using-git-worktrees` or `EnterWorktree`. Nothing merges to `main` before Task 7's fleet gate.
- **No project nouns in `scripts/`**: no journal, dataset, project or paper name in code or comments. `./scripts/check_fork.sh` must exit 0 before every commit.
- Exit codes are unchanged in meaning: 0 clean, 1 findings, 2 usage/structural error. `pipeline.py`'s `prose-check` predicate treats any non-zero code as fail (`scripts/pipeline.py:389-393`).
- Read-before-asserting applies. Read `scripts/prose_number_check.py` and `tests/test_prose_number_check.py` in full before Task 1.
- Chat output: one line per task started. Put findings in the final report only.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File map

| File | Change |
|---|---|
| `scripts/prose_number_check.py` | Replace `load_prose` with `load_manuscript` (prose + captions, fence matching, `FenceError`). Widen `INLINE` and tighten `NUM`. Add `SIGN_GLUE`, `verdict_rx`, `paragraphs`, `verdict_hits`, `declared`. Restructure `main` output. Update the docstring. |
| `tests/test_prose_number_holes.py` | **Create.** One `TestCase` class per hole. |
| `tests/test_prose_number_check.py` | Change the fixture `ALLOW` row `"2024,"` to `2024` and fix the comment above it (Task 2). |
| `rules/content-invariants.md` | INV-11 enforcement row: state the new coverage. |
| `rules/quarto-empirical.md` | Document `prose-verdict-words:` / `prose-verdict-ceiling:` wherever `prose-number-nouns:` is documented, or after write-gate item 3. |
| `CLAUDE.md`, `docs/plans/2026-09-23_pipeline-repair.md`, `docs/SESSION_REPORT.md`, `docs/improvement-ledger.md` | Close-out corrections (Task 8). |

---

### Task 0: Worktree and baseline

- [ ] **Step 1:** Create branch `prose-gate-holes` in a worktree off `main`.
- [ ] **Step 2:** Baseline the suite: `python3 -m pytest tests/ -q > "$SCRATCH/baseline.log" 2>&1; echo $?`. The expected exit is 0. If it isn't, stop and report the failing tests.
- [ ] **Step 3:** Record the fleet baseline with the **main** copy. All five exited 0 on 2026-09-28:

```bash
for m in ESG/manuscript.qmd NAR_settlement/manuscript_NAR_settlement.qmd POGM4/manuscript_quarto_word.qmd affordable_housing_2026/manuscript_affordable_housing_2026.qmd zoning2026/paper/manuscript.qmd; do
  python3 /Users/andrew.mueller/Academic/research-claude/scripts/prose_number_check.py "/Users/andrew.mueller/Research/$m" >/dev/null 2>&1; echo "$m $?"
done
```

(BRI has no manuscript yet.)

---

### Task 1: Fence matching and the unclosed-fence fail-open (§D6)

**Files:** Modify `scripts/prose_number_check.py` (`load_prose`, `main`). Create `tests/test_prose_number_holes.py`.

**Interfaces — produces:** `load_manuscript(qmd) -> (prose: list[(int, str)], captions: list[(int, str)])`; `class FenceError(Exception)` with `args[0]` = the line number of the unclosed opener. `load_prose(qmd)` is kept as a thin wrapper returning `load_manuscript(qmd)[0]`. In this task `captions` is always `[]`; Task 4 fills it.

- [ ] **Step 1: Create the test file with the helper and the fence tests**

```python
"""prose_number_check.py — the holes a 2026-09-23 project audit found.

Each class is one hole. Every test here failed on main at efe9e70.
"""
import pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "prose_number_check.py"


class Case(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / ".claude").mkdir()

    def tearDown(self):
        shutil.rmtree(self.t)

    def check(self, body, allow="literal,reason\n", claude=None):
        qmd = self.t / "manuscript_fixture.qmd"
        qmd.write_text('---\ntitle: "x"\n---\n\n' + body)
        a = self.t / "quality_reports" / "prose_number_allowlist.csv"
        a.parent.mkdir(exist_ok=True)
        a.write_text(allow)
        if claude is not None:
            (self.t / "CLAUDE.md").write_text(claude)
        p = subprocess.run([sys.executable, str(CHECK), str(qmd)],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr


class TestFences(Case):
    def test_unclosed_fence_is_a_structural_error(self):
        rc, out = self.check("Intro.\n\n```\nstray\n\nThe elasticity is 0.634.\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("never closed", out)
        self.assertIn("line 7", out)          # 4 header lines + blank + "Intro." + blank

    def test_longer_fence_contains_a_shorter_one(self):
        body = "````markdown\n```{r}\nx <- 1\n```\n````\n\nThe elasticity is 0.634.\n"
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'0.634'", out)          # prose after the outer fence is scanned

    def test_fence_with_info_string_does_not_close(self):
        body = "```{r}\nx <- 1\n```{r}\n```\n\nShare is 0.25.\n"
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'0.25'", out)

    def test_balanced_chunks_still_pass(self):
        rc, out = self.check("```{r}\nx <- 1.5\n```\n\nNo numbers.\n")
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
```

**Line numbering:** the helper writes 4 header lines. Body line k is file line 4 + k, so the stray fence in the first test is body line 3, which is file line 7.

- [ ] **Step 2: Run the tests and confirm the failure**

Run: `python3 -m pytest tests/test_prose_number_holes.py -q`
Expected: `test_unclosed_fence_is_a_structural_error` FAILs (exit 0 instead of 2). `test_fence_with_info_string_does_not_close` FAILs: `` ```{r} `` currently toggles the fence shut, so `` ``` `` reopens it and `0.25` is skipped. The other two pass.

- [ ] **Step 3: Implement.** Replace `load_prose` with:

```python
FENCE = re.compile(r"^(`{3,})(.*?)\s*$")


class FenceError(Exception):
    """A code fence was opened and never closed; args[0] is its line number."""


def load_manuscript(qmd):
    """Split the manuscript into prose lines and caption strings, in one pass.

    Prose = outside fenced chunks, YAML front matter and HTML comments. HTML
    comments are excluded because they do not appear in the rendered document:
    a number inside one cannot make a false claim to a reader.

    Fences follow CommonMark: a fence closes only on a line of at least as many
    backticks with no info string. The old toggle-on-any-``` let a ```{r} line
    close a chunk and let a nested display block desynchronise the scan.

    An unclosed fence raises FenceError. Before, one stray fence silenced the rest
    of the file while the gate still exited on whatever came before it -- a
    partial scan that read as a complete one.
    """
    prose, captions = [], []
    fence, opened = None, 0
    in_yaml = in_comment = False
    for i, line in enumerate(open(qmd, encoding="utf-8"), 1):
        if fence is not None:
            m = FENCE.match(line)
            if m and len(m.group(1)) >= len(fence) and not m.group(2):
                fence = None
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        s = line.strip()
        if s.startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue
        if i == 1 and s == "---":
            in_yaml = True
            continue
        if in_yaml:
            if s == "---":
                in_yaml = False
            continue
        m = FENCE.match(line)
        if m:
            fence, opened = m.group(1), i
            continue
        prose.append((i, line))
    if fence is not None:
        raise FenceError(opened)
    return prose, captions


def load_prose(qmd):
    """Prose lines only."""
    return load_manuscript(qmd)[0]
```

In `main`, replace `for lineno, line in load_prose(qmd):` with a load that runs first, after the allowlist is resolved:

```python
    try:
        prose, captions = load_manuscript(qmd)
    except FenceError as e:
        print(f"error: the code fence opened at line {e.args[0]} of {qmd} is never closed.")
        print("       Nothing after that line could be scanned, so no verdict is given.")
        return 2
```

Then iterate `for lineno, line in prose:`.

- [ ] **Step 4:** Run `python3 -m pytest tests/test_prose_number_holes.py tests/test_prose_number_check.py -q`. Expected: all PASS.
- [ ] **Step 5:** `./scripts/check_fork.sh` exits 0. Commit `fix(prose-check): CommonMark fence matching; an unclosed fence is exit 2, not a silent partial scan`.

---

### Task 2: `` `{r}` `` inline syntax and the trailing-comma key (§A)

**Files:** Modify `scripts/prose_number_check.py` (`INLINE`, `NUM`), `tests/test_prose_number_holes.py` and `tests/test_prose_number_check.py`.

- [ ] **Step 1: Add tests**

```python
class TestTokenisation(Case):
    def test_quarto_inline_syntax_is_recognised(self):
        rc, out = self.check("The coefficient is `{r} round(b, 3)` here.\n")
        self.assertEqual(rc, 0, out)

    def test_trailing_comma_is_not_part_of_the_key(self):
        rc, out = self.check("In 2024, prices fell.\n", allow="literal,reason\n2024,Calendar year.\n")
        self.assertEqual(rc, 0, out)

    def test_thousands_separator_is_kept(self):
        rc, out = self.check("We observe 1,234 sales.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("'1,234'", out)
```

- [ ] **Step 2:** Run them. The first two FAIL: the `'3'` false hit, and `'2024,'` keyed separately.
- [ ] **Step 3: Implement**

```python
# `r expr` (knitr) and `{r} expr` (Quarto's native form). Matching only the first
# made the modern syntax a false positive: `{r} round(b, 3)` reported '3'.
INLINE = re.compile(r"`(?:r|\{r\})\s[^`]*`")
# A literal ends on a digit, so "Table 4," and "Table 4." key as '4'. The old
# \d[\d,]* swallowed a trailing comma, so an allowlist needed a twin row ("4" and
# "4,") for every literal that ever preceded a comma.
NUM = re.compile(r"(?<![\w`])(\d(?:[\d,]*\d)?(?:\.\d+)?)")
```

- [ ] **Step 4:** In `tests/test_prose_number_check.py`, change `ALLOW`'s row `"2024,",Calendar year followed by a comma.` to `2024,Calendar year.`. Replace the two comment lines above `ALLOW` with `# A trailing comma is not part of the key: "2024," in prose matches a 2024 row.` Run both test files; expected all PASS.
- [ ] **Step 5:** `check_fork.sh`, then commit `fix(prose-check): recognise {r} inline syntax; a trailing comma is not part of a literal`.

---

### Task 3: A sign typed beside a live value (§D1)

**Interfaces — produces:** `SIGN_GLUE` (compiled regex). `main` collects `glued = [(lineno, ctx)]` and fails (exit 1) when it is non-empty. The allowlist is never consulted for it.

- [ ] **Step 1: Add tests**

```python
class TestSignGlue(Case):
    def test_plus_before_inline_fails(self):
        rc, out = self.check("The coefficient = +`r b` points.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("SIGN TYPED BESIDE A LIVE VALUE", out)

    def test_minus_and_unicode_minus_and_quarto_form_fail(self):
        for body in ("It is -`r b`.\n", "It is −`r b`.\n", "It is (-`{r} b`).\n"):
            with self.subTest(body=body):
                rc, out = self.check(body)
                self.assertEqual(rc, 1, out)

    def test_allowlist_cannot_silence_it(self):
        rc, out = self.check("It is +`r b`.\n", allow="literal,reason\n+,Sign.\n")
        self.assertEqual(rc, 1, out)

    def test_range_idioms_and_compounds_pass(self):
        for body in ("From `r a`--`r b`.\n", "From `r a`-`r b`.\n", "The pre-`r y` era.\n"):
            with self.subTest(body=body):
                rc, out = self.check(body)
                self.assertEqual(rc, 0, out)
```

- [ ] **Step 2:** Run them. The first three FAIL (exit 0).
- [ ] **Step 3: Implement**

```python
# A sign typed against an inline value. The value carries its own sign, so a
# typed "+" before a negative estimate prints "+-0.634", and the typed sign is
# outside the literal alphabet in both directions. Not allowlistable: there is
# no reason that makes it right. Keep the sign in the expression
# (sprintf("%+.3f", x)). The lookbehind spares the range idioms `r a`--`r b` and
# `r a`-`r b` and compounds like pre-`r y`.
SIGN_GLUE = re.compile(r"(?<![-\w`])[+−-](?=`(?:r|\{r\})\s)")
```

In `main`, in the loop over `prose`, scan the raw line (before `INLINE.sub`):

```python
        for m in SIGN_GLUE.finditer(line):
            glued.append((lineno, line[max(0, m.start() - 55):m.end() + 55].strip()))
```

Initialize `glued = []` before the loop. Restructure the report so each failing class prints its own block, and the exit is 1 if **any** class fails. Order: sign glue, then unexplained literals (the existing block, unchanged), then the verdict ceiling (Task 5). The sign-glue block:

```python
    if glued:
        print("SIGN TYPED BESIDE A LIVE VALUE —", len(glued), "sites (not allowlistable)")
        print("  The value carries its own sign; put any forced sign inside the "
              "expression, e.g. sprintf('%+.3f', x).\n")
        for lineno, ctx in glued:
            print(f"  line {lineno}: ...{ctx}...")
```

The PASS line prints only when no class failed.

- [ ] **Step 4:** Run both test files; all PASS. `check_fork.sh`. Commit `feat(prose-check): a sign typed beside an inline value fails and cannot be allowlisted`.

---

### Task 4: Captions — chunk options, fence-line options and R `caption=`/`title=` strings (§D3)

**Interfaces — produces:** `load_manuscript` now fills `captions`. `chunk_captions(lineno, line) -> list[(int, str)]`. Caption text goes through the same `INLINE`/`MATH` blanking, `NUM`, card-word regex and allowlist as prose. Its context string is prefixed `caption: `.

- [ ] **Step 1: Add tests**

```python
class TestCaptions(Case):
    def test_hash_pipe_caption_is_scanned(self):
        body = '```{r}\n#| label: fig-rents\n#| fig-cap: "Rents across 117 markets"\nplot(1)\n```\n'
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'117'", out)
        self.assertIn("caption:", out)

    def test_fence_line_caption_is_scanned(self):
        rc, out = self.check('```{r fig-top, fig.cap="Top 60 shown"}\nplot(1)\n```\n')
        self.assertEqual(rc, 1, out)
        self.assertIn("'60'", out)

    def test_r_caption_and_title_strings_are_scanned(self):
        body = ('```{r}\nmake_ft(d, caption = "Table 4: Returns")\n'
                "modelsummary(m, title = 'Table 5: Panel')\n```\n")
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'4'", out)
        self.assertIn("'5'", out)

    def test_code_comments_and_expr_captions_are_not(self):
        body = ('```{r}\n#| fig-cap: !expr paste("N =", n)\n'
                '# caption = "Table 9"\nx <- 1.20\n```\n')
        rc, out = self.check(body)
        self.assertEqual(rc, 0, out)

    def test_allowlisted_caption_literal_passes(self):
        body = '```{r}\n#| fig-cap: "Rents, 1983 onward"\nplot(1)\n```\n'
        rc, out = self.check(body, allow="literal,reason\n1983,Panel start year.\n")
        self.assertEqual(rc, 0, out)
```

- [ ] **Step 2:** Run them. The first three FAIL (exit 0).
- [ ] **Step 3: Implement**

```python
# Caption text is prose the reader sees, by the same logic that excludes HTML
# comments: the test is whether it reaches the rendered page. Three places carry
# it: a fence-line option, a #| option line, and an R string passed as caption=
# or title= (flextable, modelsummary, gt, labs). Only those string literals are
# admitted -- scanning every R string would re-import the code noise that
# excluding chunks exists to avoid.
# Known limit: a multi-line YAML caption (#| fig-cap: |) is not read.
FENCE_CAP = re.compile(r"""\b(?:fig|tbl)[.-]cap\s*=\s*(["'])(.*?)\1""")
OPT_CAP = re.compile(r"^#\|\s*(?:fig|tbl)-(?:cap|subcap)\s*:\s*(.+?)\s*$")
R_CAP = re.compile(r"""\b(?:caption|title)\s*=\s*(["'])(.*?)(?<!\\)\1""")


def chunk_captions(lineno, line):
    """Reader-visible caption text on one line inside a chunk."""
    s = line.strip()
    m = OPT_CAP.match(s)
    if m:
        value = m.group(1)
        if value.startswith("!expr"):
            return []      # computed in R: no typed literal to find
        return [(lineno, value.strip("\"'"))]
    if s.startswith("#"):
        return []          # an R comment, or a chunk option that is not a caption
    return [(lineno, c.group(2)) for c in R_CAP.finditer(line)]
```

In `load_manuscript`, in the inside-fence branch, add `captions.extend(chunk_captions(i, line))` in an `else:` of the closing-fence test. At the opener, add `captions.extend((i, c.group(2)) for c in FENCE_CAP.finditer(m.group(2)))`. In `main`, factor the literal scan into a local `scan(lineno, text, label)` that runs the existing `NUM` and `wordnum_rx` loops, with `ctx = label + ctx`. Call it over `prose` with `""` and over `captions` with `"caption: "`.

- [ ] **Step 4:** Run both test files; all PASS. `check_fork.sh`. Commit `feat(prose-check): scan caption strings in chunk options and R caption=/title= arguments`.

---

### Task 5: Verdict words beside live values (§D2)

**Interfaces — produces:** `declared(root, key) -> str` ("" if absent; multiple lines joined with `|`), `verdict_rx(extra) -> re.Pattern`, `paragraphs(prose) -> iter[(start_lineno, text)]` and `verdict_hits(prose, rx) -> list[(lineno, word, sentence)]`. Project declarations live in `CLAUDE.md`: `prose-verdict-words: <words>` extends the lexicon, and `prose-verdict-ceiling: <int>` enforces the count.

**Behaviour.** A verdict word counts only when it shares a sentence with an inline expression. No ceiling declared means an advisory count, and the exit code is unaffected. The audit measured 108 typed verdict words in one manuscript, so a hard fail would be unusable on day one. A count above a declared ceiling is exit 1 and lists every hit. A count below it prints a note to lower the ceiling. A non-integer ceiling is exit 2.

- [ ] **Step 1: Add tests**

```python
class TestVerdictWords(Case):
    BODY = ("The estimate is significant at `r p`. It is positive (`r round(b, 2)`).\n\n"
            "Prices were significant in general.\n")

    def test_advisory_by_default(self):
        rc, out = self.check(self.BODY)
        self.assertEqual(rc, 0, out)
        self.assertIn("verdict words beside live values: 2", out)

    def test_word_outside_a_live_sentence_is_not_counted(self):
        rc, out = self.check("Prices were significant in general.\n")
        self.assertIn("verdict words beside live values: 0", out)

    def test_ceiling_exceeded_fails(self):
        rc, out = self.check(self.BODY, claude="prose-verdict-ceiling: 1\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("significant", out)

    def test_ceiling_met_passes_and_lower_ceiling_is_suggested(self):
        rc, out = self.check(self.BODY, claude="prose-verdict-ceiling: 2\n")
        self.assertEqual(rc, 0, out)
        rc, out = self.check(self.BODY, claude="prose-verdict-ceiling: 5\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("lower", out)

    def test_bad_ceiling_is_a_usage_error(self):
        rc, out = self.check(self.BODY, claude="prose-verdict-ceiling: many\n")
        self.assertEqual(rc, 2, out)

    def test_declared_words_extend_the_lexicon(self):
        rc, out = self.check("Returns lag at `r x`.\n", claude="prose-verdict-words: lag\n")
        self.assertIn("verdict words beside live values: 1", out)

    def test_period_inside_an_inline_expression_does_not_split_the_sentence(self):
        rc, out = self.check("It is `r format(b, nsmall = 2)`. Clearly significant.\n")
        self.assertIn("verdict words beside live values: 0", out)
```

- [ ] **Step 2:** Run them. All seven FAIL. Five fail because no verdict line is printed yet; `test_ceiling_exceeded_fails` and `test_bad_ceiling_is_a_usage_error` fail because the exit is 0.
- [ ] **Step 3: Implement**

```python
# Typed verdicts beside a live number. A number can update while the word beside
# it cannot: "outperform (coefficient = -0.634)" is the shipped form of this bug.
# Counted, not failed, unless the project declares a ceiling, because existing
# manuscripts carry dozens and a gate that is red on day one gets waived. A
# ceiling that must not rise is enforceable. The fix is a helper that derives
# the word from the value.
_VERDICT = (r"significant|significantly|insignificant|"
            r"outperform(?:s|ed|ing)?|underperform(?:s|ed|ing)?|"
            r"positive|negative|rises|rose|falls|fell|"
            r"monotonic(?:ally)?|stronger|weaker|null")
LIVE = "\x00"
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def declared(root, key):
    """A `key: value` line in the project's CLAUDE.md, or ""."""
    claude = os.path.join(root, "CLAUDE.md")
    if not os.path.exists(claude):
        return ""
    rx = re.compile(rf"^{re.escape(key)}:\s*(.+?)\s*$", re.M)
    return "|".join(rx.findall(open(claude, encoding="utf-8").read()))


def verdict_rx(extra):
    words = _VERDICT + ("|" + "|".join(re.split(r"[|,\s]+", extra)) if extra else "")
    return re.compile(rf"\b(?:{words})\b", re.I)


def paragraphs(prose):
    """Consecutive prose lines joined into paragraphs, with the first line number."""
    para, start, prev = [], 0, None
    for lineno, line in prose:
        s = line.strip()
        broken = prev is not None and lineno != prev + 1
        prev = lineno
        if broken or not s or s.startswith(("#", ":::")):
            if para:
                yield start, " ".join(para)
            para = []
            if not s or s.startswith(("#", ":::")):
                continue
        if not para:
            start = lineno
        para.append(s)
    if para:
        yield start, " ".join(para)


def verdict_hits(prose, rx):
    out = []
    for start, text in paragraphs(prose):
        for sentence in SENTENCE_END.split(INLINE.sub(LIVE, text)):
            if LIVE in sentence:
                shown = sentence.replace(LIVE, "`r …`")[:160]
                out.extend((start, m.group(0).lower(), shown) for m in rx.finditer(sentence))
    return out
```

In `main`, after `extra_nouns`:

```python
    root = project_root(qmd)
    try:
        v_rx = verdict_rx(declared(root, "prose-verdict-words"))
    except re.error as e:
        print(f"error: prose-verdict-words in CLAUDE.md is not a valid pattern: {e}")
        return 2
    ceiling_s = declared(root, "prose-verdict-ceiling")
    try:
        ceiling = int(ceiling_s) if ceiling_s else None
    except ValueError:
        print(f"error: prose-verdict-ceiling must be an integer, got {ceiling_s!r}")
        return 2
```

After the scans, compute `verdicts = verdict_hits(prose, v_rx)` and `over = ceiling is not None and len(verdicts) > ceiling`. If `over`, print a block `VERDICT WORDS ABOVE CEILING — {n} > {ceiling}`, list every hit as `line {l}: {word} — {sentence}`, and count it as a failing class. **Always** print one line, on pass or fail:

```python
    mode = f"ceiling {ceiling}" if ceiling is not None else \
        "advisory; declare prose-verdict-ceiling: N in CLAUDE.md to enforce"
    print(f"  verdict words beside live values: {len(verdicts)}  ({mode})")
    if ceiling is not None and len(verdicts) < ceiling:
        print(f"  note: lower prose-verdict-ceiling to {len(verdicts)}")
```

- [ ] **Step 4:** Run the full suite: `python3 -m pytest tests/ -q > "$SCRATCH/t5.log" 2>&1 || tail -40 "$SCRATCH/t5.log"`. Expected: all PASS. `check_fork.sh`. Commit `feat(prose-check): count verdict words beside live values; enforce a declared ceiling`.

---

### Task 6: Documentation of the gate's coverage

- [ ] **Step 1:** Rewrite the module docstring of `scripts/prose_number_check.py`. Add short sections for CAPTIONS, SIGN GLUE, VERDICT WORDS and FENCES beside the existing SPELLED-OUT COUNTS, and add exit-code 2's new meaning (unclosed fence). No project nouns.
- [ ] **Step 2:** Read `rules/content-invariants.md` in full. In the INV-11 enforcement-table row, add: `also fails on a sign typed beside an inline value (not allowlistable) and on an unclosed fence (exit 2); scans captions in chunk options and R caption=/title= strings; counts verdict words beside live values, enforced when prose-verdict-ceiling: is declared`.
- [ ] **Step 3:** Read `rules/quarto-empirical.md` in full. Where it documents `prose-number-nouns:`, document `prose-verdict-words:` and `prose-verdict-ceiling:` beside it. If it doesn't document it, add one sentence under write-gate item 3.
- [ ] **Step 4:** `check_fork.sh` exits 0, then the full suite passes. Commit `docs(prose-check): state the gate's new coverage in INV-11 and the write gate`.

---

### Task 7: Fleet gate — measure before merging

Merging makes the stricter gate live in every paper, and some are mid-task (a project whose prose is frozen may run this gate inside its own build gate). So measure first.

- [ ] **Step 1:** Run the **branch** copy against the five manuscripts. Save each full log to the scratchpad:

```bash
WT="<worktree path>"
for m in ESG/manuscript.qmd NAR_settlement/manuscript_NAR_settlement.qmd POGM4/manuscript_quarto_word.qmd affordable_housing_2026/manuscript_affordable_housing_2026.qmd zoning2026/paper/manuscript.qmd; do
  log="$SCRATCH/fleet_${m%%/*}.log"
  python3 "$WT/scripts/prose_number_check.py" "/Users/andrew.mueller/Research/$m" > "$log" 2>&1; echo "$m $?"
done
```

- [ ] **Step 2:** Read every log in full. Tabulate each project: main exit (Task 0), branch exit, the failing classes with counts (sign glue, new caption literals, keys changed by the comma fix, unclosed fence) and the advisory verdict count. Write the table to `$SCRATCH/fleet_impact.md`.
- [ ] **Step 3: Decision rule.**
  - If every manuscript still exits 0, merge `prose-gate-holes` into `main` with `--no-ff`. Then run `./scripts/check_fork.sh`, the full suite and `./scripts/check_install.sh --all`; all must exit 0.
  - If **any** manuscript goes from 0 to non-zero, **do not merge**. Push nothing and leave the branch. Do Task 8 Steps 1–2 on `main` anyway, since those correct false statements and don't depend on the merge. End with the fleet table and ask the author whether to merge. The real findings (for example, sign-glue sites) are the point of the gate; the author decides when each project absorbs them.

---

### Task 8: Close-out

- [ ] **Step 1:** In `CLAUDE.md` § Start here, replace `**Nothing is open in this repo.**` with the true state. Name `docs/plans/2026-09-28-prose-gate-holes.md` as landed at `<sha>` or awaiting the fleet decision, and name the open improvement-ledger rows (as of 2026-09-28, **L-004 and L-005 are `open`** in `docs/improvement-ledger.md`; re-read the ledger before writing).
- [ ] **Step 2:** In `docs/plans/2026-09-23_pipeline-repair.md` Phase 5, append a paragraph: `**Correction (2026-09-28).** "The number-gate holes … either Phase 1 above or genuinely project-local" was wrong: Phase 1 has no such item and the holes are research-wide. They were carried by no plan until docs/plans/2026-09-28-prose-gate-holes.md.`
- [ ] **Step 3:** Append a ledger row: `L-007 | 2026-09-28 | POGM4 | scripts/prose_number_check.py | Project gate audit: sign typed beside an inline value, caption strings in chunks, unclosed fence and typed verdict words all passed the prose-number gate. | landed <sha>` (or `open` if Task 7 stopped the merge). Before writing, read the ledger's header rule on generic notes; the project name belongs only in the `project` column.
- [ ] **Step 4:** Append a `docs/SESSION_REPORT.md` entry: what landed, the fleet table (or a link to it) and the decision owed, if any.
- [ ] **Step 5:** `check_fork.sh`, then commit `docs: correct the open-work pointer; record the prose-gate holes close-out`.
- [ ] **Step 6:** Final message to the author: the outcome in 1–3 sentences; the per-project fleet table if any project went red; the merge decision if one is owed.

---

## Self-review notes

- Coverage: the audit's §D1 is Task 3, §D2 Task 5, §D3 Task 4 and §D6 Task 1; the §A extras are in Task 2. §D4, §D5 and §D8 already landed, and §D7 is project-local (see Spec).
- Deliberately not done: an exhibit-number pattern in captions. `NUM` already flags the digit, and typed `Table N` is `quarto_structure_check.py`'s concern. Multi-line YAML captions are a documented limit.
- `load_prose` survives as a wrapper; nothing outside the script imports it (checked 2026-09-28: no importer in `scripts/`, `tests/` or `hooks/`).
