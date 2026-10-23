#!/bin/bash
# Wired by default via seeds/settings.json (Phase 4.1, 2026-09-24 — supersedes the
# 2026-09-08 opt-in ruling, design spec R-7: that default left every generated evidence
# file unprotected in all six repos, and `/review` already had to bolt on its own
# `git status --porcelain` check after "a project gate restamped two committed reports").
# Block accidental edits to protected files
# Extend PROTECTED_PATTERNS below for a project's own extra artifacts
# Hook Event: PreToolUse
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
FILE=""

# Extract file path based on tool type
if [ "$TOOL" = "Edit" ] || [ "$TOOL" = "Write" ]; then
  FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
fi

# Bash branch: a shell write (redirect, tee, sed -i, cp, mv, rm) that names a protected file is
# refused; reads (cat, grep, jq) are not. The pattern list is defined below, so the branch runs
# after it.
if [ -z "$FILE" ] && [ "$TOOL" != "Bash" ]; then
  exit 0
fi

# A Write that CREATES a protected file is the pipeline working, not an accident: every
# critic returns its report as text and the dispatching session saves it to
# quality_reports/reviews/explorer-critic_<date>.md and the like, which match `*-critic_*.md`. Blocking
# creation meant `pipeline.py post` never saw a report and no stage could close (live fixture,
# 2026-09-24: the driver stopped at `data` with `post explorer: FAIL`). What this hook exists
# to stop is a later Edit or overwrite of a report that already exists — R-7's incident was a
# project gate restamping two committed reports. So: create freely, never rewrite.
if [ "$TOOL" = "Write" ] && [ ! -e "$FILE" ]; then
  exit 0
fi

# ============================================================
# Quarto-native defaults — the pipeline's own config and generated evidence.
# CUSTOMIZE: append patterns for a project's own extra artifacts.
# Uses basename matching — add full paths for more precision.
# ============================================================
PROTECTED_PATTERNS=(
  "settings.json"
  "pipeline_state.json"
  "receipts.jsonl"
  "*-critic_*.md"
  "civilize_*_report.md"
  "verify_claims_*.md"
  "verification_report.md"
  "strategy_memo_[0-9]*.md"
  "desk_review.md"
  "referee_domain.md"
  "referee_methods.md"
  "design_lock.json"
  "design_token.json"
  "design_amendments.csv"
  "design_amendments.md"
  "render_fingerprint.json"
  "cold_render.json"
  "findings_ledger.md"
  "rulings_log.md"
)

if [ "$TOOL" = "Bash" ]; then
  # Match write DESTINATIONS only (redirect targets, tee files, last arg of cp/mv/install, rm args,
  # sed -i / perl -i files, dd of=, git mv / git rm paths); quoted text and read-only arguments are
  # never targets. A redirect/tee that CREATES a review-report file is allowed, as Write-create is
  # above. When the command does not tokenize (a quoted string spanning lines), a conservative
  # regex scan of the whole command for destinations replaces the parse; it may refuse a command
  # that only reads. Fails open on any other internal error (hook convention).
  CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
  # No write form at all (redirect, tee, cp/mv/install/rm/dd, sed/perl -i, git mv/rm): nothing below
  # can match, so the python scan is skipped — this branch runs on every Bash call.
  if ! printf '%s' "$CMD" | grep -qE '>|\b(tee|cp|mv|install|rm|dd)\b|\b(sed|perl)\b|\bgit\s+(mv|rm)\b'; then
    exit 0
  fi
  CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
  # The scanner is read into a variable by a top-level heredoc, not run from a heredoc inside $( ):
  # macOS /bin/bash 3.2 counts quotes and parentheses inside a command substitution's heredoc and
  # fails to parse the script (tested: 2026-10-18, `/bin/bash -n` on the inline form).
  IFS= read -r -d '' PF_PY <<'PY'
import fnmatch, os, re, shlex, sys
pats = sys.argv[1:]
KEEP = {"settings.json", "pipeline_state.json", "receipts.jsonl", "design_lock.json", "design_token.json",
        "design_amendments.csv", "design_amendments.md", "render_fingerprint.json", "cold_render.json",
        "findings_ledger.md", "rulings_log.md"}
create_ok = [q for q in pats if q not in KEEP]
cwd = os.environ.get("PF_CWD") or os.getcwd()
SEP = {";", "&&", "||", "|", "&", "|&", ";;"}
def segments(cmd):
    segs, delim = [], None
    for line in cmd.split("\n"):
        if delim is not None:
            if line.strip() == delim: delim = None
            continue
        m = re.search(r"(?<!<)<<(?!<)-?\s*['\"]?(\w+)", line)  # a triple-angle here-string is not a heredoc
        lex = shlex.shlex(line, posix=False, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        cur = []
        for tok in lex:
            if tok in SEP:
                segs.append(cur); cur = []
            else:
                cur.append(tok)
        segs.append(cur)
        if m: delim = m.group(1)
    return segs
def unq(a):
    return a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "'\"" else a
def nonopt(args):
    return [unq(a) for a in args if not a.startswith("-") and unq(a) != ""]
REDIR = (">", ">>", ">|", "&>", "&>>")
def targets(seg):
    out = []
    for i, tok in enumerate(seg):
        if tok in REDIR and i + 1 < len(seg):
            out.append((unq(seg[i + 1]), True))
    words, skip = [], False
    for i, tok in enumerate(seg):
        if skip: skip = False; continue
        if tok in REDIR + ("<", "<<", "<<<", ">&", "<&"): skip = True; continue
        words.append(tok)
    while words and re.match(r"^\w+=", words[0]): words.pop(0)
    if not words: return out
    c, args = os.path.basename(unq(words[0])), words[1:]
    if c == "git" and args and unq(args[0]) in ("mv", "rm"):
        out += [(a, False) for a in nonopt(args[1:])]
    elif c == "tee": out += [(a, True) for a in nonopt(args)]
    elif c in ("cp", "mv", "install"):
        n = nonopt(args)
        if len(n) >= 2: out.append((n[-1], False))
    elif c == "rm": out += [(a, False) for a in nonopt(args)]
    elif c == "dd": out += [(unq(unq(a)[3:]), False) for a in args if unq(a).startswith("of=")]
    elif c in ("sed", "perl") and any(re.match(r"^-[A-Za-z]*i|^--in-place", a) for a in args):
        out += [(a, False) for a in nonopt(args)]
    return out
DEST = re.compile(r"""(?:&>>?|>>?\|?)\s*[\x27"]?([^\s\x27";&|<>()]+)"""  # redirect target
                  r"""|\bof=[\x27"]?([^\s\x27";&|<>()]+)"""  # dd of
                  r"""|\b(?:tee|rm|cp|mv|install|git\s+(?:mv|rm)|sed\s+-[A-Za-z]*i\S*|perl\s+-[A-Za-z]*i\S*)"""
                  r"""((?:\s+[^\s;&|<>()]+)+)""")                                # every later word
def scan(cmd):
    """Fallback when shlex fails: every word that could be a write destination, as a creating write
    for a redirect or tee (so a new review report stays allowed) and a non-creating one otherwise."""
    out = []
    for m in DEST.finditer(cmd):
        if m.group(1): out.append((m.group(1), True))
        elif m.group(2): out.append((m.group(2), False))
        else:
            creating = m.group(0).lstrip().startswith("tee")
            out += [(w.strip("\x27\""), creating) for w in m.group(3).split() if not w.startswith("-")]
    return out
def all_targets(cmd):
    try:
        segs = segments(cmd)
    except ValueError:
        return scan(cmd)
    return [t for seg in segs for t in targets(seg)]
try:
    for path, creating in all_targets(os.environ["PF_CMD"]):
        base = os.path.basename(path)
        for q in pats:
            if fnmatch.fnmatchcase(base, q):
                full = path if os.path.isabs(path) else os.path.join(cwd, path)
                if creating and q in create_ok and not os.path.exists(full):
                    continue
                print(q); sys.exit(0)
except Exception:
    pass
PY
  HIT=$(PF_CMD="$CMD" PF_CWD="$CWD" python3 -c "$PF_PY" "${PROTECTED_PATTERNS[@]}" 2>/dev/null)
  if [ -n "$HIT" ]; then
    echo "Protected file named in a shell write: $HIT" >&2; exit 2
  fi
  exit 0
fi

BASENAME=$(basename "$FILE")
for PATTERN in "${PROTECTED_PATTERNS[@]}"; do
  # PATTERN must be unquoted here: quoting it inside [[ ]] turns off glob matching and
  # makes every wildcard pattern compare as a literal string, so it never matches anything.
  # This was true of every pattern shipped before 2026-09-24, including the original
  # "strategy-memo-*.md" — and went uncaught for as long as the hook was never wired or tested.
  if [[ "$BASENAME" == $PATTERN ]]; then
    echo "Protected file: $BASENAME. Edit manually or remove protection in .claude/hooks/protect-files.sh" >&2
    exit 2
  fi
done

exit 0
