#!/usr/bin/env python3
"""source_check.py — pull a source paragraph from a local file and match a sentence word for word.

Text that is not in the file is never returned: no match or more than one match gives paragraph None.
"""
from __future__ import annotations
import csv, hashlib, re, subprocess, sys, unicodedata
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

def clean(text: str, rules: List[str]) -> str:
    for rule in rules:
        if rule != "trailing-line-numbers":
            raise ValueError(f"unknown cleanup rule: {rule}")
        lines = [ln for ln in text.split("\n") if not re.fullmatch(r"\s*\d{1,4}\s*", ln) or not ln.strip()]
        text = "\n".join(re.sub(r" \d{1,4}\s*$", "", ln) for ln in lines)
    return text

def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s).translate(_QUOTES)).strip()

def _paragraphs(text: str) -> List[str]:
    return [p for p in (normalise(b) for b in re.split(r"\n\s*\n", text.replace("\r\n", "\n"))) if p]

def _hits(text: str, sent: str) -> List[Tuple[int, str, int]]:
    return [(n, para, m.start()) for n, para in enumerate(_paragraphs(text))
            for m in re.finditer(rf"(?<!\w){re.escape(sent)}(?!\w)", para)]

def find_paragraph(text: str, sentence: str) -> Tuple[str, Optional[str], str]:
    sent = normalise(sentence)
    if not sent:
        return "not-found", None, "empty sentence"
    hits = _hits(text, sent) or _hits(text.replace("-\n", ""), sent)
    if not hits:
        return "not-found", None, f"not found: {sent[:80]}"
    if len(hits) > 1:
        n = len({h[0] for h in hits}); k = n if n > 1 else len(hits)
        return "ambiguous", None, f"ambiguous: {k} paragraphs" if n > 1 else f"ambiguous: {k} places in one paragraph"
    _, para, i = hits[0]
    return "ok", f"{para[:i]}[{sent}]{{.underline}}{para[i + len(sent):]}", ""


# --- registry, tags, approvals and states -------------------------------------------------------

REGISTRY_REL = Path("quality_reports") / "sources.csv"
APPROVALS_REL = Path("quality_reports") / "source_approvals.csv"
REGISTRY_COLS = ["id", "file", "label", "page", "sentence", "cleanup", "ocr"]
APPROVAL_COLS = ["tag_id", "ref", "claim_sha256", "file_sha256", "approved_at"]

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


class Result(NamedTuple):
    tag: Tag
    state: str
    paragraph: Optional[str]
    reason: str
    label: str
    page: str
    ocr: bool


def claim_sha256(claim: str) -> str:
    return hashlib.sha256(normalise(claim).encode("utf-8")).hexdigest()


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
            break
        attrs = _ATTRS.match(qmd_text, end + 1)
        if attrs and _SRC_CLASS.search(attrs.group(1)):
            ref = _REF.search(attrs.group(1))
            tag_id = _ID.search(attrs.group(1))
            if ref and tag_id:
                tags.append(Tag(tag_id.group(1), ref.group(1), qmd_text[start + 1:end]))
            pos = attrs.end()
        else:
            pos = start + 1
    block = db.design_block(qmd_text)
    found = _DESIGN_SOURCE.search(block) if block else None
    if found:
        tags.append(Tag("design", "design:" + found.group(1), found.group(2)))
    return tags


def _read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_tag(root: Path, tag: Tag, registry: Dict[str, Dict[str, str]],
               approvals: Dict[str, Dict[str, str]]) -> Result:
    entry = registry.get(tag.ref)
    if entry is None:
        return Result(tag, FAILED, None, f"no registry entry for {tag.ref}", "", "", False)
    label = entry.get("label", "")
    page = entry.get("page", "")
    ocr = entry.get("ocr", "").strip().lower() == "true"
    path = root / entry.get("file", "")
    if not path.is_file():
        return Result(tag, NOT_HERE, None, f"source file not on this machine: {entry.get('file', '')}",
                      label, page, ocr)
    rules = [r.strip() for r in entry.get("cleanup", "").split(";") if r.strip()]
    try:
        text = clean(extract_text(path), rules)
    except (ValueError, OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
        return Result(tag, FAILED, None, f"cannot read source: {err}", label, page, ocr)
    status, paragraph, reason = find_paragraph(text, tag.claim)
    if status != "ok":
        return Result(tag, FAILED, None, reason, label, page, ocr)
    approval = approvals.get(tag.tag_id)
    if approval is None:
        return Result(tag, UNREVIEWED, paragraph, "no approval recorded", label, page, ocr)
    changed = []
    if approval.get("claim_sha256") != claim_sha256(tag.claim):
        changed.append("claim")
    if approval.get("file_sha256") != _file_sha256(path):
        changed.append("file")
    if changed:
        return Result(tag, NEEDS_REVIEW, paragraph,
                      "changed since approval: " + " and ".join(changed), label, page, ocr)
    return Result(tag, APPROVED, paragraph, "", label, page, ocr)


def check(root: Path, qmd_text: str) -> List[Result]:
    root = Path(root)
    registry = {row["id"]: row for row in _read_rows(root / REGISTRY_REL)}
    approvals = {}
    for row in _read_rows(root / APPROVALS_REL):
        approvals[row["tag_id"]] = row  # the last row for a tag wins
    return [_check_tag(root, tag, registry, approvals) for tag in scan_tags(qmd_text)]


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
