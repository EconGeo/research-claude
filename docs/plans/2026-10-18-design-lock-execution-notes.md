# Design lock and prose binding — execution notes (2026-10-18)

Execution record for `docs/plans/2026-10-12-design-lock-and-prose-binding.md`, Tasks 1–15 plus the
final whole-branch review and its fix wave (branch `feat/design-lock-prose-binding`, not merged).
Tasks 16 (merge, re-link, live evals) and 17 (paper retrofits) are not done: they need the author.

## Decisions for the author before Task 16 Step 4–5

1. **The pre-commit hook would block manuscript commits in 4 of 5 unretrofitted papers** (read-only run of the
   branch's `prose_number_check.py`; the new surface scans find true positives):

   | Paper | main | branch | Newly flagged |
   |---|---|---|---|
   | ESG | PASS | FAIL | 4 literals in the YAML abstract placeholder |
   | POGM4 | PASS | FAIL | 2000 ×7 and 382 ×2 in `notes=` captions |
   | affordable_housing_2026 | FAIL | FAIL (3 → 4) | |
   | zoning2026 | FAIL | FAIL (2 → 9) | abstract `$p<0.003$`, a math star legend written with `<` |
   | NAR_settlement | PASS | PASS | |

   This conflicts with the 2026-09-28 ruling that papers fix gate findings on their own schedule. Options:
   install `core.hooksPath` only in papers that pass (the plan's default: Step 5 is per-paper), or make
   commit-check's prose check a WARN for NOT-RETROFITTED papers.
2. **`check_install --all` goes red after the re-link:** `gitignore-covers` in all six projects (no
   `.claude/state/design_token.json` line; seeds never overwrite), `claude-md-design-facts` in
   NAR_settlement (CLAUDE.md:19), and `claude-md-size` + design facts in NAR_settlement_legacy_archive.
   Decide whether `apply.sh --link` should append missing required `.gitignore` lines.
3. **`/analyze`, `/write`, `/revise` now run `pre` as a blocking step** for every paper (spec §7), so any
   failing `pre coder`/`pre writer` predicate stops those skills.
4. **The cold-render requirement fires on any R chunk change**, not only model chunks (spec §7 says model
   chunks). Narrow it, or accept extra cold renders on long papers.
5. **The overfull-box check is inert** unless a project sets `latex-clean: false` (tested: Quarto deletes
   the LaTeX log otherwise).
6. **The author-token boundary is a text match.** Known evasions remain (variables/fragments,
   `|& claude`, `claude -p "$(cat f)"`, indirect writers); hardening needs a different mechanism.
7. **A re-signed amendment's "re-run the checks" rule is satisfied by any edit to a `checks` line**, so an
   honest identical re-run needs a cosmetic edit, and a dishonest one passes. A follow-up could hash each
   exploration file into the lock.

## Rulings made without the author (in order; each with what it costs if wrong)

- Execute Tasks 1–15 and Task 16 Steps 1–3 (whole-branch review = SDD final review; full pytest + check_fork; read-only commit-check survey of paper projects). Stop before Task 16 Step 4 (merge to main makes the change live in six papers), Step 5 (re-link), Step 6–7, and all of Task 17 (author-gated, other repos) — merges and other-repo work need the author — cost if wrong: author has to say "merge" one turn later.
- Fixture stays tests/fixture-project (plan), not tests/fixtures/design-lock/ (spec §9 path) — the existing FixtureCase and run_fixture.sh already centre on it, and §9's substance (each planted defect fails) is unchanged — cost if wrong: a later move of test files.
- core.md rule 13 vs author_token docstring "quoted in rule 13": Task 13 implementer adds the full approval grammar (whole line, case-insensitive, optional ".", not in fences/quotes, exactly one per message, 30-min/next-message/one-use freshness) to rule 13 — the docstring promises it and the token is the security boundary — cost if wrong: two extra lines in core.md.
- Task 2 Step 4 and Task 13 Step 4 live `claude -p` checks run with no timeout, from a scratch project / repo root; results recorded as tested: — cost if wrong: none beyond run time.
- Commit trailers name the model that actually wrote the commit (subagent harness gives e.g. Claude Haiku 5.5) rather than the plan's fixed Opus 5.5 line — accurate attribution beats a fixed string — cost if wrong: cosmetic trailer text.
- Task 2 Important 2 (nested `claude -p` self-approval) — close it in Task 4: design-guard denies any Bash command that invokes `claude` and contains `approve design` (case-insensitive); Task 2 fix round documents it as a known limit pointing at design-guard — the hook payload cannot tell a nested prompt from a human one, and design-guard already owns token-related Bash denials — cost if wrong: an evasion via a constructed string remains (same class as the plan's known path-fragment limit).
- Task 4 Important 1 (plan-mandated regex over-denies) — the protect-files Bash branch matches DESTINATIONS only (shlex-tokenised, quoted text never a target): the target of >/>>, tee's file args, the last arg of cp/mv/install, rm's args, sed -i/perl -i file args, and `git mv`/`git rm` path args; a redirect that creates a path that does not yet exist stays allowed for critic-report patterns (Write-create parity, the 2026-09-24 incident); parsing may be done by an inline python3 helper — spec §7 asks for a Bash-WRITE check, and the brief's regex flags reads and commit messages — cost if wrong: an exotic write form slips through (Edit/Write and design-guard still cover the main paths).
- Task 4 Important 2 — design-guard's Bash token check matches `design_token.json`, not the bare substring `design_token` — tests/test_design_token.py and grep/git on it are legitimate; the token path is what matters — cost if wrong: a command that builds the path from fragments evades (already the plan's stated known limit).
- Task 7 jargon ID pattern — replace `\b(?:R|F|L)-\d{1,3}\b` (re.I) with case-sensitive `(?-i:\b(?:F|L)-0\d\d\b)` (zero-padded ledger/improvement IDs as the pipeline writes them) and `\bruling R-\d{1,3}\b` (case-insensitive) — bare R-1/R-2 are zoning districts in this author's field, and jargon is deliberately unallowlistable — cost if wrong: an unprefixed ruling ID or an ID ≥ 100 reaches a manuscript unflagged.
- Task 7 threshold WARN exempts 0 (`if (b > 0)` is a sign check, a legitimate raw-inline-if binding per rule 14) — the brief's "other than 0.10/0.1/0.05/0.01" would warn on every sign check — cost if wrong: a literal-0 threshold on a p-value goes unwarned.
- Task 7 multi-word jargon matched per paragraph (joined lines), not per line — hard-wrapped prose would evade every multi-word pattern — cost if wrong: none material.
- Task 11 OVERFULL check stays log-optional (critic_inputs writes "latex log: absent") rather than forcing `latex-clean: false` on every project — changing every paper's render config is the author's call and outside this plan's scope — cost if wrong: overfull boxes keep going unflagged until a project opts in; listed for the author in the final message.
- NA_VALUE is blocking under write-gate item 4 with no escape hatch — keep it blocking (the spec wants NA on the page caught) and have Task 13 add to rules/quarto-empirical.md item 4 that a deliberate placeholder is written "n.a." or "—", never "NA" — cost if wrong: an author has to rewrite one placeholder cell.
- Task 12 Important (plan-mandated apply.sh snippet) — use `git rev-parse --git-path hooks` (absolutised) for the own-hooks check, so linked worktrees see the shared hooks dir — the brief's snippet breaks the "never overwrite existing .git/hooks" guarantee on the path check_install recommends — cost if wrong: none.
- Task 13 deviation (a) — /review blocks on `pre writer` only for design-lock CHANGED/UNLOCKED; other pre FAILs are reported, not blocking — /review exists to score below-gate work and adoption depends on it; the brief's "blocking" would make /review unusable on exactly the work it reviews — cost if wrong: a review runs on a manuscript failing some other pre predicate (it was already allowed before this plan).
- Task 13 deviation (b) — /analyze runs `design status` and the sign-off step before `pre coder` — `pre coder` fails on UNSIGNED, so the brief's order deadlocks signing — cost if wrong: none.
- Task 13 deviation (d) — accept skill budget raises (review 13,500→14,450, write 9,100→9,600) — the new blocking steps are required text; already shortened — cost if wrong: ~1.4k chars per invocation of those skills.
- close the seeds/quarto-preamble.tex ≤ gap inside Task 15's fix round (add the fixture's mapping to the seed; rules/quarto-empirical.md names the two lines for papers whose preamble was seeded earlier) — the shipped rule tells papers to print ≤ and the seed can't; fixing it before the merge is cheaper than a separate task — cost if wrong: two preamble lines in new papers.
- Task 15 deviation (e) `rerun:` field accepted as a test of gate mechanics; the gate-level gap (checks_changed is satisfied by any textual edit; an honest identical re-run needs a cosmetic edit) is recorded for the author, not fixed — "fix the fixture, never the gate" — cost if wrong: an amendment can be re-signed without a genuine re-run.
- Final I1 (token boundary) — design-guard additionally denies Bash that (i) mentions `author_token`, (ii) runs `claude` fed by `<` redirect or a pipe, (iii) mentions `design_lock` together with an interpreter (python/perl/ruby/node/Rscript); no process-ancestry check in design-token.py (the desktop app and the top-level CLI make ancestor counting unreliable, untestable without live runs) and no commit-check token cross-check (the token is gitignored local state, so a coauthor's fresh clone would be blocked) — residual text-match limit stays documented and goes to the author — cost if wrong: a deliberately evasive session can still self-approve.
- Final I2 — claims helpers resolve fingerprint and data paths from the project root (walk up from getwd() to the dir holding CLAUDE.md), base R only, re-pasted into the fixture — zoning2026-style subdirectory manuscripts would otherwise never write a readable fingerprint — cost if wrong: none.
- Final I3 — cold_render.json records a hash of chunk_code(ms) and commit-check compares that, so prose-only edits after a cold render don't force another; the "any chunk" vs "model chunks" trigger stays broad and goes to the author — cost if wrong: extra cold renders on long papers until the author narrows it.
- Final I4 (merge impact on unretrofitted papers: pre-commit would block 4 of 5; blocking `pre` in skills; check_install --all red; gitignore top-up) — no code change; it is Task 16 Step 3/5's author decision, reported with the per-paper table — cost if wrong: none before the author decides.
- Final I5 + must-fix minors — fix in the one fix wave: radix sort in rc_fingerprint; protect-files `&>`/`&>>`, `dd of=`, regex fallback when shlex fails (not fail-open), `<<<` here-string; wire_guard_hooks uses the seed's per-hook timeout for stale-stages; `ledger add --creator` validated against registry agents; NA_VALUE skips `Inf.`-before-capital abbreviations — cheap and each closes a real hole — cost if wrong: none.
- Final: parked — protect-files shlex-fallback scan denies heredoc-form `git commit -m "$(cat <<'EOF' …)"` messages that mention rm/cp/mv/tee/install/-> next to a protected filename — Ruling: real, deferred; inside the ruled conservative-fallback trade-off, 0 such messages in the last 300 commits of each paper — cost if wrong: an occasional commit message has to be reworded.
- Final: parked — design-guard misses `echo x |& claude -p` and `claude -p "$(cat f)"` — Ruling: real, deferred to the author with the text-match known limit — cost if wrong: two more self-approval forms.
- Final: parked — check_render skips sentence-final "Inf." before a capital — Ruling: accepted consequence of the Inf.-abbreviation ruling — cost if wrong: a leaked Inf at sentence end goes unflagged.
- Task 16 Step 3 survey done read-only from the final reviewer's per-paper prose-check run instead of `git -C <paper> add -N` + commit-check — `add -N` changes each paper's index — cost if wrong: the commit-check's other gates (structure, design, staleness) weren't run per paper; the prose check is the one that differs for unretrofitted papers.

## Deferred minor findings (not fixed; the final review triaged them as able to wait; the items it called must-fix were fixed in a8c0088)

- Task 1: minor (deferred): column-0 list item ends block (design_block.py:115)
- Task 1: minor (deferred): one opcode spanning sibling fields names only first field (187-190)
- Task 1: minor (deferred): check_field truncates quoted values at whitespace (166-168)
- Task 1: minor (deferred): unclosed p.open() in amendment_count / test (224, test:320)
- Task 1: minor (deferred): manuscript_path accepts .. / absolute path (231)
- Task 1: minor (deferred): test_no_alpha_or_verdicts_needed asserts on own constant (plan-mandated)
- Task 1: minor (deferred): no tests for checks_changed, malformed span, corrupt lock JSON
- Task 2: minor (deferred): corrupt token JSON raises in _read (revoke swallowed; check/consume raise) — author_token.py:41
- Task 2: minor (deferred): consume read-then-write not atomic
- Task 2: minor (deferred): fence tracking ignores fence type/length; indented code blocks counted
- Task 2: minor (deferred): hook not tested with unlock approval or two-line approval; wire test uses check_wanted() not module-load raise
- Task 2: minor (deferred): unlock reason loses one trailing "."
- Task 2: minor (deferred): report pasted no pytest output for fix round
- Task 3: minor (deferred): token consumed before amendment/lock writes; write failure leaves UNLOCKED with spent token
- Task 3: minor (deferred): already-signed sign re-evaluates checks (deleted exploration fails sign)
- Task 3: minor (deferred): missing tests — unlock when not SIGNED, predicate in UNLOCKED / CHANGED-block-deleted, seed-amendment arg errors (empty --old rejected)
- Task 3: minor (deferred): unreachable `return 2` in design_cmd
- Task 3: minor (deferred): lock with null/non-string block or hash passes key check → design sign AttributeError traceback (pipeline.py:357)
- Task 3: minor (deferred): dangling design_lock.json symlink treated as no lock (Path.exists follows symlinks) (pipeline.py:354)
- Task 4: minor (deferred): INPLACE_RE treats manuscript as source arg (cp ms backup denied while signed)
- Task 4: minor (deferred): `git checkout -- quality_reports/design_lock.json` allowed (restores committed lock)
- Task 4: minor (deferred): wire_guard_hooks docstring line over-long
- Task 5: minor (deferred): rc_design(tempfile()) test matches any error + emits readLines warning; no tests for missing design: block / hypothesis without spec
- Task 5: minor (deferred): fixest_multi test only checks name, not digest change
- Task 5: minor (deferred): unlisted model classes silently not fingerprinted — header note
- Task 5: minor (deferred): rmarkdown:: used without library(rmarkdown) note (readable-code.md line 74)
- Task 5: minor (deferred): long lines; -0.00 formatting
- Task 6: minor (deferred): abstract-termination tests end with digitless key; `$5.00 or $6.50` mislabelled math:; `!expr` YAML scanned as text
- Task 7: minor (deferred): THRESH misses nested calls `if (rc_p(b) < 0.07)`; warns on non-p literals like `n > 100`
- Task 7: minor (deferred): open(qmd).read() handle; prose-jargon tokens single-regex, no \b, doc it; 160-char print truncation
- Task 8: minor (deferred): malformed render_fingerprint.json → raw JSONDecodeError (fails closed, no message)
- Task 8: minor (deferred): `overall` predicate not stale-checked (score --gate covers indirectly)
- Task 8: minor (deferred): tests lack strategy/referee staleness, design-hash trigger, head populated in git repo, hook non-stale-exit case
- Task 9: minor (deferred): settle uses git diff-tree without --root (first commit lists nothing)
- Task 9: minor (deferred): newline in finding collapsed to space (acceptable)
- Task 9: minor (deferred): transition tests miss close --sha / --pending on closed pending, decline on pending/declined/rejected/closed pending
- Task 10: minor (deferred): critic_context declared_manuscript unguarded (traceback without manuscript:); ledger cells not |-escaped in context table; no test that section-scoped receipts are ignored
- Task 11: minor (deferred): Unicode minus −Inf reported as Inf; report lacked pasted output
- Task 12: minor (deferred): unused import/param in tests; check_refs git/ row flag only matches backticked names; check_refs/check_install cases not seen red
- Task 13: minor (deferred): check_single_manuscript case-sensitive extensions (.r/.rmd), inline `r source()` not scanned
- Task 13: minor (deferred): `cache.extra uses file.mtime()` loosely worded checklist line (code-review-17-categories.md:112)
- Task 14: minor (deferred): star test regex lowercase-p only, limited suffixes; table-standards.md:57 example lacks stars_note pointer; p-hacking check editor.md only
- Task 15: minor (deferred): references.bib note prints in fixture reference list

## Pre-flight scan

| Tasks | Shared file / interface | Finding |
|---|---|---|
| 1→2,3,4,7,8,12 | design_block.py API | Consumers use only names Task 1 lists. OK |
| 1 self | test_span (3,14) vs BASE | Counted: design: L3 … size: L14. OK |
| 1 self | needs_rerun cases vs RERUN_FIELDS/_outcomes | estimand change → field hypotheses.H1, outcomes equal → False; others True. OK |
| 2→3,4 | author_token check/consume, TOKEN_REL | Same signatures. OK |
| 2,4,8 | wire_guard_hooks.py WANTED, seeds/settings.json, hooks/README.md | Sequential edits, additive. OK |
| 3 self | test_amendment_writes_csv expects fields [inference, checks.size] and "+  inference:" in MD | difflib opcodes give two replace ops; unified diff of normalised lines carries "+  inference:". OK |
| 3 self | test_pre_coder_blocks_unsigned in temp root with only rules/registry.yaml | `pre` may need more of the tree; implementer adapts setup, not assertion. Note |
| 4 self | design-guard tests use ProjectCase (manuscript_p.qmd) | ProjectCase exists in tests/test_guard_hooks.py with proj/ms/run_hook/denied. OK |
| 4 vs 2 | design-guard denies any Bash naming design_token | Also blocks reads (cat). Acceptable: token is hook-written only. OK |
| 5→8,12,15 | fingerprint JSON keys estimates_hash/data_hash/design_hash | Consistent across 8, 12. OK |
| 6→7 | prose_number_check.py | Sequential; 7 says no existing test changes. OK |
| 8 vs 13 | stale-stages text cites "rule 15 of core.md" | Task 13 numbers re-estimation rule 15. OK |
| 2 vs 13 | author_token docstring says grammar quoted in core.md rule 13 | Rule 13 text gives the two lines but not the fence/quote/one-per-message details. Minor — Ruling below |
| 8→12,15 | stale_reason: lock present + no fingerprint = stale | Task 15 writes stub fingerprint in FixtureCase. OK |
| 9→12 | ledger settle via post-commit | OK |
| 12 self | apply.sh "hooks loop links hooks/git as one dir link" | Unverified claim about apply.sh; implementer reads apply.sh. Note |
| 13 vs 14 | rules/quarto-empirical.md, rules/content-invariants.md | Line hints in 14 shift after 13; edit by content. OK |
| 14 self | test_star_convention exemption "names APSA" | journal-profiles.md other-cutoff lines (531,549,567) all name APSA. OK |
| 15 vs spec §9 | spec says fixture at tests/fixtures/design-lock/; plan adopts tests/fixture-project | Ruling below |
| 16,17 | merge to main, re-link six papers, paper-repo retrofits | Side effects outside worktree. Ruling below |
