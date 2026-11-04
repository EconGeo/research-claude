# Fail-open hook audit — 2026-11-04

**Question.** After EconGeo/research-claude#6 (one malformed log line turned critic-pairing off
for good, silently), do any other wired hooks have an input that switches their check off with
no message?

**Scope.** Every hook `seeds/settings.json` wires (critic-pairing, design-guard, design-token,
dispatch-log, protect-files, read-gate ×2, script-guard, stale-stages), `run-hook.sh`, and the
git hooks `hooks/git/pre-commit` and `post-commit`. All read to the end. "Backstop" means a
second gate that still catches the case.

## Findings

| # | Hook | Input that turns it off | Silent? | Backstop | Severity |
|---|------|-------------------------|---------|----------|----------|
| 1 | design-guard.py | `quality_reports/design_lock.json` unreadable (e.g. merge-conflict markers) | yes | commit-check: `design_state` treats an unreadable lock as CHANGED and refuses the commit | medium |
| 2 | design-guard.py | manuscript has one non-UTF-8 byte (`ms.read_text()` raises) | yes | commit-check crashes on the same read, so the commit is refused (loudly, with a traceback) | medium-low |
| 3 | protect-files.sh | `jq` not on the hook's PATH | yes (stderr only) | none | medium for a coauthor without jq; nil here (`/usr/bin/jq` present) |
| 4 | stale-stages.py | `pipeline.py stale` crashes or takes > 20 s | yes | commit-check refuses manuscript commits on a stale score | low |

**1 — tested.** A signed lock, then the lock file rewritten with `<<<<<<< / ======= / >>>>>>>`
around two copies: an Edit that changes `cluster: region` → `cluster: state` in the design block
is allowed. Cause: `db.read_lock` raises `JSONDecodeError`, the `except Exception: sys.exit(0)`
at the bottom allows the call. `pipeline.py design_state` already makes the opposite choice
("existence, not the parsed value, decides a lock exists"), so the hook and the commit gate
disagree about the same file. The lock is committed, so a merge conflict on it is the realistic
path.

**2 — tested.** Same signed lock, one `\xe9` byte appended to the manuscript body: the same
design-changing Edit is allowed. `ms.read_text()` raises `UnicodeDecodeError` before the hash
comparison.

**3 — tested.** `env -i PATH=<dir with cat, basename, python3, grep, printf>` and an Edit of
`quality_reports/pipeline_state.json`: exit 0 (allowed); with jq, exit 2 (refused). `TOOL` comes
back empty, so the first branch exits 0 for every tool. The README lists jq as a requirement;
nothing at run time says it is missing except a stderr line the user does not normally see
(`unverified:` that Claude Code hides exit-0 stderr outside verbose mode). `python3` is already
required, so the hook could parse its JSON with it and drop jq.

**4 — not tested (read only).** `p.returncode != 1` returns 0 for a crash (exit 2 / traceback)
and `TimeoutExpired` reaches the outer `except`. The SessionStart notice is lost, but the
pre-commit gate enforces staleness independently.

## Checked and clean

- **critic-pairing.py** — fixed in `c657341`. A registry that will not parse still turns it off
  silently, by design (mid-edit/mid-merge is transient; `check_install` covers a broken registry).
- **read-gate.py** — fixed in `c657341`. A failure on the PostToolUse side records nothing, which
  later produces a false *deny* (loud). The PreToolUse side could only fail open on a state file
  missing a key, and the file is now written atomically by the hook alone.
- **design-token.py** — any failure means no token is issued; `pipeline.py design sign` then
  refuses with "no author token" (fails closed, loud).
- **dispatch-log.py** — a lost write either drops a creator line (critic-pairing misses one run)
  or a critic line (critic-pairing blocks — loud). Only OSError on append; low.
- **script-guard.py** — a failure allows a new script, but the only raising paths are a
  non-dict payload and filesystem errors on `resolve()`; nothing a project file can trigger
  persistently.
- **run-hook.sh** — a missing hook is skipped with a stderr line by design (an unlinked
  worktree must still start); `check_install` is the backstop.
- **pre-commit** — no `python3` skips with a stderr notice by design. **post-commit** — ledger
  settle is advisory.

## Pattern behind #6, and in the tests

The tests for these hooks check that a bad input *does not crash*. Only a few check that the
guard *still guards* afterwards; #6's test required silence. Each fix below should come with a
test that the check still refuses after the bad input.

## Fixes (branch `fix/fail-open-hooks`)

Each comes with a test that the guard still refuses after the bad input; all six new tests fail
on the pre-fix hooks and pass after.

1. **design-guard, unreadable lock.** A lock file that exists but does not parse, is not an
   object, or has no `hash` counts as signed, as `design_state` treats it. With no signed hash to
   compare, an edit may not change the design block as it stands now; the rest of the manuscript
   stays editable, and a Bash in-place write is refused. The message says "design_lock.json is
   unreadable — restore it from git or ask the author" (the words `design_state` uses).
2. **design-guard, stray byte.** The manuscript is read with `errors="surrogateescape"`, and
   `design_block.design_hash` encodes with `surrogateescape`, so valid UTF-8 hashes exactly as
   before and a bad byte hashes instead of raising.
3. **protect-files.** A `field()` helper uses jq when present and python3 otherwise; all four
   payload reads go through it.
4. **stale-stages.** A crash is told apart from a finding: exit 1 with a traceback and no
   `STALE` line, any other non-0/1 exit, or the 20 s timeout prints a `systemMessage` that the
   check could not run, with the last stderr line. Config errors (`pipeline.py: …` via
   `sys.exit`) stay silent, as before. Read-only finding #4 was also off in one detail: a Python
   crash exits 1, the same code as a finding, not 2.
