#!/usr/bin/env python3
"""source_check.py — pull a source paragraph from a local file and match a sentence word for word.

Text that is not in the file is never returned: no match or more than one match gives paragraph None.
"""
from __future__ import annotations
import re, subprocess, unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple

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
