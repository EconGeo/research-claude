#!/usr/bin/env python3
"""source_check.py — pull a source paragraph from a local file and match a sentence word for word.

Text that is not in the file is never returned: no match or more than one match gives paragraph None.
Matching normalises both sides (NFKC, straight quotes, whitespace, line-end hyphenation); what is
shown is the file's own paragraph after the entry's cleanup rules, with only whitespace runs
collapsed (and, inside the matched sentence only, a line-end hyphen break joined as matched).
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, subprocess, sys, unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_block as db

_BLOCK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
_QUOTES = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'",
                         "“": '"', "”": '"', "„": '"', "‟": '"'})

class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True); self.out: List[str] = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
        if tag in _BLOCK: self.out.append("\n\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self.skip = max(0, self.skip - 1)
        if tag in _BLOCK: self.out.append("\n\n")
    def handle_data(self, data):
        if not self.skip: self.out.append(data)

def extract_text(path: Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return subprocess.run(["pdftotext", str(path), "-"], check=True, capture_output=True,
                              text=True, encoding="utf-8").stdout
    raw = Path(path).read_text(encoding="utf-8")
    if suffix in (".html", ".htm"):
        p = _Text(); p.feed(raw); p.close(); return "".join(p.out)
    return raw

_TRAILING_NUMBER = re.compile(r"(?:^|(?<=\s))(\d{1,4})\s*$")


def _strip_line_numbers(text: str) -> str:
    """The `trailing-line-numbers` rule: drop the number a form prints at the end of each line.

    A number ending a line counts as a line number only when it runs in sequence with the
    numbers ending nearby lines (within two candidate lines, rising by at most two per step), so
    "within 30" at the end of a line is kept. A line holding only its line number goes entirely.
    """
    lines = text.split("\n")
    found = []
    for i, line in enumerate(lines):
        match = _TRAILING_NUMBER.search(line)
        if match:
            found.append((i, int(match.group(1))))
    numbered = set()
    for k, (i, value) in enumerate(found):
        for other in (k - 2, k - 1, k + 1, k + 2):
            if other < 0 or other >= len(found):
                continue
            steps = other - k
            diff = found[other][1] - value
            if diff * steps > 0 and abs(diff) <= 2 * abs(steps):
                numbered.add(i)
                break
    out = []
    for i, line in enumerate(lines):
        if i not in numbered:
            out.append(line)
            continue
        kept = _TRAILING_NUMBER.sub("", line).rstrip()
        if kept.strip():
            out.append(kept)
    return "\n".join(out)


def clean(text: str, rules: List[str]) -> str:
    for rule in rules:
        if rule != "trailing-line-numbers":
            raise ValueError(f"unknown cleanup rule: {rule}")
        text = _strip_line_numbers(text)
    return text

def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s).translate(_QUOTES)).strip()


# A line-end hyphen break: a hyphen between word characters, then the line end.
_HYPHEN_BREAK = re.compile(r"-[ \t]*\n\s*")


class _Mapped(NamedTuple):
    """One paragraph twice: as shown (the file's text, whitespace runs collapsed) and as matched
    (normalised), with each matched character's (start, end) in the shown string."""
    display: str
    norm: str
    spans: List[Tuple[int, int]]
    breaks: List[Tuple[int, int]]  # shown ranges of line-end hyphen breaks ("-" and its space)


def _add_norm(norm: List[str], spans: List[Tuple[int, int]], chars: str, start: int, end: int) -> None:
    for ch in chars:
        if ch.isspace():
            if not norm or norm[-1] == " ":
                continue
            ch = " "
        norm.append(ch)
        spans.append((start, end))


def _map_paragraph(raw: str, hyphens: Optional[str]) -> _Mapped:
    """hyphens None: a line-end hyphen is an ordinary character; "join": the hyphen and line end
    are dropped for matching (com-/pensation); "keep": only the line end is (seller-/direct)."""
    display: List[str] = []
    norm: List[str] = []
    spans: List[Tuple[int, int]] = []
    breaks: List[Tuple[int, int]] = []
    shown = 0
    i = 0
    while i < len(raw):
        brk = _HYPHEN_BREAK.match(raw, i) if hyphens else None
        if (brk and i > 0 and raw[i - 1].isalnum() and brk.end() < len(raw)
                and raw[brk.end()].isalnum()):
            display.append("- ")
            breaks.append((shown, shown + 2))
            if hyphens == "keep":
                _add_norm(norm, spans, "-", shown, shown + 1)
            shown += 2
            i = brk.end()
            continue
        if raw[i].isspace():
            j = i
            while j < len(raw) and raw[j].isspace():
                j += 1
            display.append(" ")
            _add_norm(norm, spans, " ", shown, shown + 1)
            shown += 1
            i = j
            continue
        j = i + 1
        while j < len(raw) and unicodedata.combining(raw[j]):
            j += 1
        group = raw[i:j]
        display.append(group)
        matched = unicodedata.normalize("NFKC", group).translate(_QUOTES)
        _add_norm(norm, spans, matched, shown, shown + len(group))
        shown += len(group)
        i = j
    while norm and norm[-1] == " ":
        norm.pop()
        spans.pop()
    return _Mapped("".join(display), "".join(norm), spans, breaks)


def _raw_paragraphs(text: str) -> List[str]:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    return [b.strip() for b in blocks if b.strip()]


def _hits(paragraphs: List[str], sent: str, hyphens: Optional[str]) -> List[Tuple[int, _Mapped, int, int]]:
    hits = []
    pattern = re.compile(rf"(?<!\w){re.escape(sent)}(?!\w)")
    for n, raw in enumerate(paragraphs):
        mapped = _map_paragraph(raw, hyphens)
        for m in pattern.finditer(mapped.norm):
            hits.append((n, mapped, m.start(), m.end()))
    return hits


def find_parts(text: str, sentence: str) -> Tuple[str, Optional[Tuple[str, str, str]], str]:
    """(status, (before, sentence, after), reason): the matched paragraph as the file's own text
    split around the sentence (see the module docstring); None unless status is "ok"."""
    sent = normalise(sentence)
    if not sent:
        return "not-found", None, "empty sentence"
    paragraphs = _raw_paragraphs(text)
    hits: List[Tuple[int, _Mapped, int, int]] = []
    mode: Optional[str] = None
    for mode in (None, "join", "keep"):
        hits = _hits(paragraphs, sent, mode)
        if hits:
            break
    if not hits:
        return "not-found", None, f"not found in file: {sent[:80]}"
    if len(hits) > 1:
        n = len({h[0] for h in hits})
        if n > 1:
            return "ambiguous", None, f"ambiguous: {n} paragraphs"
        return "ambiguous", None, f"ambiguous: {len(hits)} places in one paragraph"
    _, mapped, start, end = hits[0]
    first = mapped.spans[start][0]
    last = mapped.spans[end - 1][1]
    shown = mapped.display[first:last]
    # Inside the sentence only, a line-end hyphen break is shown as it was matched.
    for b_start, b_end in reversed(mapped.breaks):
        if first <= b_start and b_end <= last:
            cut_from = b_start - first if mode == "join" else b_start - first + 1
            shown = shown[:cut_from] + shown[b_end - first:]
    return "ok", (mapped.display[:first], shown, mapped.display[last:]), ""

def underline_markup(parts: Tuple[str, str, str]) -> str:
    before, sent, after = parts
    return f"{before}[{sent}]{{.underline}}{after}"

def find_paragraph(text: str, sentence: str) -> Tuple[str, Optional[str], str]:
    status, parts, reason = find_parts(text, sentence)
    return status, underline_markup(parts) if parts else None, reason


# --- registry, tags, approvals and states -------------------------------------------------------

REGISTRY_REL = Path("quality_reports") / "sources.csv"
APPROVALS_REL = Path("quality_reports") / "source_approvals.csv"
REGISTRY_COLS = ["id", "file", "label", "page", "sentence", "cleanup", "ocr"]
APPROVAL_COLS = ["tag_id", "ref", "claim_sha256", "entry_sha256", "file_sha256", "approved_at"]

APPROVED = "APPROVED"
UNREVIEWED = "UNREVIEWED"
NEEDS_REVIEW = "NEEDS REVIEW"
FAILED = "FAILED"
NOT_HERE = "NOT ON THIS MACHINE"

_ATTRS = re.compile(r"\{([^{}]*)\}")
_REF = re.compile(r"""(?:^|\s)ref=["']([^"']*)["']""")
_ID = re.compile(r"""(?:^|\s)id=["']([^"']*)["']""")
_SRC_CLASS = re.compile(r"(?:^|\s)\.src(?:\s|$)")
_DESIGN_SOURCE = re.compile(r'source:\s*\{[^}]*cite:\s*([^,}\s]+)[^}]*quote:\s*"([^"]*)"')


class Tag(NamedTuple):
    tag_id: str
    ref: str
    claim: str
    from_block: bool = False  # True for the design block's treatment quote (tag id "design")


class Result(NamedTuple):
    tag: Tag
    state: str
    paragraph: Optional[str]
    reason: str
    label: str
    page: str
    ocr: bool
    parts: Optional[Tuple[str, str, str]] = None  # (before, sentence, after), plain text


DESIGN_FORM_REASON = 'design quote not in flow form `source: {cite: …, quote: "…"}`'


def claim_sha256(claim: str) -> str:
    return hashlib.sha256(normalise(claim).encode("utf-8")).hexdigest()


def _cleanup_rules(entry: Dict[str, str]) -> List[str]:
    return [r.strip() for r in (entry.get("cleanup") or "").split(";") if r.strip()]


def entry_sha256(ref: str, entry: Dict[str, str]) -> str:
    """The registry entry as approved: its id, sentence (normalised), cleanup rules, label and page."""
    fields = [ref, normalise(entry.get("sentence") or ""), ";".join(_cleanup_rules(entry)),
              (entry.get("label") or "").strip(), (entry.get("page") or "").strip()]
    return hashlib.sha256("\x1f".join(fields).encode("utf-8")).hexdigest()


def inside_project(file_name: str) -> bool:
    """A registry `file` must be a relative path that stays inside the project."""
    path = Path(os.path.normpath(file_name))
    return not path.is_absolute() and path.parts[:1] != ("..",)


def _closing_bracket(text: str, start: int) -> int:
    """Index of the ']' that balances the '[' at start, or -1."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def scan_tags(qmd_text: str) -> List[Tag]:
    tags: List[Tag] = []
    pos = 0
    while True:
        start = qmd_text.find("[", pos)
        if start == -1:
            break
        end = _closing_bracket(qmd_text, start)
        if end == -1:
            pos = start + 1
            continue
        attrs = _ATTRS.match(qmd_text, end + 1)
        if attrs and _SRC_CLASS.search(attrs.group(1)):
            ref = _REF.search(attrs.group(1))
            tag_id = _ID.search(attrs.group(1))
            tags.append(Tag(tag_id.group(1) if tag_id else "", ref.group(1) if ref else "",
                            qmd_text[start + 1:end]))
            pos = attrs.end()
        else:
            pos = start + 1
    block = db.design_block(qmd_text)
    found = _DESIGN_SOURCE.search(block) if block else None
    if found:
        tags.append(Tag("design", "design:" + found.group(1), found.group(2), True))
    elif block and re.search(r"\bsource:", block) and re.search(r"\bquote:", block):
        tags.append(Tag("design", "", "", True))  # a quote the flow-form pattern cannot read
    return tags


def _read_rows(path: Path, required: str) -> Tuple[List[Dict[str, str]], str]:
    """Rows of a CSV and an error message; the error is empty when the file reads cleanly.

    A missing file is not an error (no rows). A file without the required column,
    or one that is not UTF-8 CSV, gives no rows and a message.
    """
    if not path.is_file():
        return [], ""
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if required not in (reader.fieldnames or []):
                return [], f"{path.name} has no '{required}' column"
            return list(reader), ""
    except (csv.Error, UnicodeDecodeError, OSError) as err:
        return [], f"{path.name} cannot be read: {err}"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_text(path: Path, rules: List[str], cache: Dict[Tuple[str, Tuple[str, ...]], Tuple[bool, str]]) -> Tuple[bool, str]:
    """(True, cleaned text) or (False, error), extracted once per file and cleanup in one check()."""
    key = (str(path), tuple(rules))
    if key not in cache:
        try:
            cache[key] = (True, clean(extract_text(path), rules))
        except (ValueError, OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
            cache[key] = (False, str(err))
    return cache[key]


def _check_tag(root: Path, tag: Tag, registry: Dict[str, Dict[str, str]],
               approvals: Dict[str, Dict[str, str]], registry_error: str,
               approvals_error: str,
               cache: Optional[Dict[Tuple[str, Tuple[str, ...]], Tuple[bool, str]]] = None) -> Result:
    if cache is None:
        cache = {}
    if tag.from_block and not tag.ref:
        return Result(tag, FAILED, None, DESIGN_FORM_REASON, "", "", False)
    if registry_error:
        return Result(tag, FAILED, None, registry_error, "", "", False)
    if not tag.tag_id:
        return Result(tag, FAILED, None, "tag missing id", "", "", False)
    if not tag.ref:
        return Result(tag, FAILED, None, "tag missing ref", "", "", False)
    entry = registry.get(tag.ref)
    if entry is None:
        return Result(tag, FAILED, None, f"no registry entry for {tag.ref}", "", "", False)
    label = entry.get("label") or ""
    page = entry.get("page") or ""
    ocr = (entry.get("ocr") or "").strip().lower() == "true"
    file_name = entry.get("file") or ""
    if file_name and not inside_project(file_name):
        return Result(tag, FAILED, None, "file must be inside the project", label, page, ocr)
    path = root / file_name
    if not file_name or not path.is_file():
        return Result(tag, NOT_HERE, None, f"source file not on this machine: {file_name}",
                      label, page, ocr)
    # The design quote is itself the source text. Any other claim is the paper's own wording,
    # so what must appear in the source is the registry's sentence.
    if tag.tag_id == "design":
        wanted = tag.claim
    else:
        wanted = entry.get("sentence") or ""
        if not wanted.strip():
            return Result(tag, FAILED, None, f"registry entry {tag.ref} has no sentence",
                          label, page, ocr)
    readable, text = _source_text(path, _cleanup_rules(entry), cache)
    if not readable:
        return Result(tag, FAILED, None, f"cannot read source: {text}", label, page, ocr)
    status, parts, reason = find_parts(text, wanted)
    if status == "not-found" and wanted.strip():
        reason = ("design quote " if tag.tag_id == "design" else "registry sentence ") + reason
    if status != "ok":
        return Result(tag, FAILED, None, reason, label, page, ocr)
    paragraph = underline_markup(parts)
    approval = approvals.get(tag.tag_id)
    if approval is None:
        reason = "no approval recorded"
        if approvals_error:
            reason += f" ({approvals_error})"
        return Result(tag, UNREVIEWED, paragraph, reason, label, page, ocr, parts)
    changed = []
    if approval.get("claim_sha256") != claim_sha256(tag.claim):
        changed.append("claim")
    # An approval row from before entry_sha256 existed has none: it reads as a changed entry.
    if approval.get("ref") != tag.ref or approval.get("entry_sha256") != entry_sha256(tag.ref, entry):
        changed.append("source entry")
    if approval.get("file_sha256") != _file_sha256(path):
        changed.append("file")
    if changed:
        return Result(tag, NEEDS_REVIEW, paragraph,
                      "changed since approval: " + " and ".join(changed), label, page, ocr, parts)
    return Result(tag, APPROVED, paragraph, "", label, page, ocr, parts)


def check(root: Path, qmd_text: str) -> List[Result]:
    root = Path(root)
    registry_rows, registry_error = _read_rows(root / REGISTRY_REL, "id")
    approval_rows, approvals_error = _read_rows(root / APPROVALS_REL, "tag_id")
    registry = {}
    for row in registry_rows:
        registry[row["id"]] = row
    approvals = {}
    for row in approval_rows:
        approvals[row["tag_id"]] = row  # the last row for a tag wins
    if approvals_error:
        approvals_error = "approvals could not be read: " + approvals_error
    if registry_error:
        registry_error = "registry unusable: " + registry_error
    tags = scan_tags(qmd_text)
    # Tag ids key the approvals and the Word comments, so each must be unique, and `design`
    # belongs to the design block's quote.
    uses = Counter(t.tag_id for t in tags if t.tag_id and not t.from_block)
    cache: Dict[Tuple[str, Tuple[str, ...]], Tuple[bool, str]] = {}
    results = []
    for tag in tags:
        if not tag.from_block and tag.tag_id == "design":
            results.append(Result(tag, FAILED, None, "tag id design is reserved", "", "", False))
        elif not tag.from_block and uses[tag.tag_id] > 1:
            results.append(Result(tag, FAILED, None, f"duplicate tag id {tag.tag_id}", "", "", False))
        else:
            results.append(_check_tag(root, tag, registry, approvals, registry_error,
                                      approvals_error, cache))
    return results


def fingerprints(root: Path, qmd_text: str, ids: List[str]) -> Dict[str, Dict[str, str]]:
    """What the author sees for each tag id now: claim, registry entry and source file hashes.

    The design-token hook stores these in a sources token when the author approves, and
    `pipeline.py sources approve` refuses if any differs. Raises ValueError naming the first id
    that cannot be fingerprinted (not tagged, tagged twice, no entry, file absent or outside).
    """
    root = Path(root)
    rows, error = _read_rows(root / REGISTRY_REL, "id")
    if error:
        raise ValueError("registry unusable: " + error)
    registry = {row["id"]: row for row in rows}
    tags = scan_tags(qmd_text)
    out: Dict[str, Dict[str, str]] = {}
    for tag_id in ids:
        # `design` names the design block's quote; a .src tag using it is FAILED (reserved).
        matching = [t for t in tags if t.tag_id == tag_id and t.from_block == (tag_id == "design")]
        if not matching:
            raise ValueError(f"the manuscript tags no claim with id {tag_id}")
        if len(matching) > 1:
            raise ValueError(f"tag id {tag_id} is used more than once")
        tag = matching[0]
        entry = registry.get(tag.ref)
        if entry is None:
            raise ValueError(f"no registry entry for {tag.ref or tag_id}")
        file_name = entry.get("file") or ""
        if not file_name or not inside_project(file_name) or not (root / file_name).is_file():
            raise ValueError(f"the source file for {tag_id} is not in the project on this machine")
        out[tag_id] = {"claim_sha256": claim_sha256(tag.claim),
                       "entry_sha256": entry_sha256(tag.ref, entry),
                       "file_sha256": _file_sha256(root / file_name)}
    return out


def warning_lines(results: List[Result]) -> List[str]:
    lines = []
    for r in results:
        if r.state in (FAILED, NEEDS_REVIEW):
            lines.append(f"source-check: {r.state} {r.tag.tag_id} ({r.tag.ref}): {r.reason}")
    unreviewed = sum(1 for r in results if r.state == UNREVIEWED)
    absent = sum(1 for r in results if r.state == NOT_HERE)
    if unreviewed:
        lines.append(f"source-check: {unreviewed} claims not yet reviewed")
    if absent:
        lines.append(f"source-check: {absent} sources not on this machine")
    return lines


# --- command line ---------------------------------------------------------------------------------

_MANUSCRIPT_LINE = re.compile(r"^manuscript:\s*(\S+\.qmd)\s*$", re.M)


def declared_manuscript(root: Path) -> Optional[Path]:
    """The one manuscript named in <root>/CLAUDE.md, or None (same rule as pipeline.py)."""
    claude = root / "CLAUDE.md"
    if not claude.is_file():
        return None
    hits = _MANUSCRIPT_LINE.findall(claude.read_text(encoding="utf-8"))
    if len(hits) != 1:
        return None
    return root / hits[0]


def results_as_json(results: List[Result]) -> str:
    data = {}
    for r in results:
        if r.tag.tag_id == "design" and not r.tag.from_block and "design" in data:
            continue  # the reserved id: the design block's result keeps the key
        before, sentence, after = r.parts if r.parts else (None, None, None)
        data[r.tag.tag_id] = {"state": r.state, "label": r.label, "page": r.page,
                              "ocr": r.ocr, "paragraph": r.paragraph, "reason": r.reason,
                              "before": before, "sentence": sentence, "after": after}
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Check tagged claims against local source files.")
    parser.add_argument("manuscript", nargs="?", help="manuscript .qmd (default: declared in CLAUDE.md)")
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print results as JSON keyed by tag id")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root)
        manuscript = root / args.manuscript if args.manuscript else declared_manuscript(root)
        if manuscript is None or not manuscript.is_file():
            return 0
        results = check(root, manuscript.read_text(encoding="utf-8"))
        if args.json:
            print(results_as_json(results))
        else:
            for line in warning_lines(results):
                print(line)
    except Exception as err:  # fail open: a broken check must never break a render
        print(f"source-check: internal error: {err}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
