"""Score and select the chunks most likely to describe a paper's data and variables."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from .chroma import Chunk
from .vocab import Vocab

# A data/sample/variables heading at the start of the chunk (first non-empty line), with an
# optional section number ("3.", "4.1", "II.") and an optional "and <Sources|Methodology|…>".
HEADING_RE = re.compile(
    r"^\s*(?:(?:\d+(?:\.\d+)*\.?|[IVX]+\.)\s+)?"
    r"(?:Data|DATA|Sample|Variables?)"
    r"(?:\s+(?:and|&)\s+(?:the\s+)?(?:Sample|Sources?|Methodology|Methods?|Variables?|"
    r"Descriptive Statistics|Summary Statistics|Empirical Strategy|Measurement))?"
    r"\s*(?:Sources?|Description)?\s*$",
    re.MULTILINE)
VAR_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?(?:Variable (?:Definitions?|Descriptions?|Construction)|"
    r"Descriptive Statistics|Summary Statistics|Table 1\b)", re.MULTILINE | re.IGNORECASE)
DATA_CUES = re.compile(
    r"data ?set|data source|we (?:use|employ|obtain|collect|draw|rely)|provided by|obtained from|"
    r"observations|sample (?:period|consists|includes|covers)|transactions?|"
    r"(?:19|20)\d\d\s?(?:[–-]|to|through)\s?(?:19|20)\d\d|"
    r"at the (?:tract|block|parcel|county|MSA|zip)", re.IGNORECASE)
VAR_CUES = re.compile(
    r"dependent variable|outcome variable|regress(?:ed)? .{0,40}? on|measured as|defined as|"
    r"is the natural log|dummy (?:variable|equal)|indicator (?:variable|equal)", re.IGNORECASE)
PRIOR_SECTIONS = {"methods", "background", "unknown", "appendix"}


@dataclass
class ChunkScore:
    score: int
    heading: bool
    cues: int
    var_cues: int
    source_hits: list[str] = field(default_factory=list)


def score_chunk(chunk: Chunk, vocab: Vocab) -> ChunkScore:
    text = chunk.text
    heading = bool(HEADING_RE.search(text[:200]))
    var_heading = bool(VAR_HEADING_RE.search(text[:200]))
    cues = min(len(DATA_CUES.findall(text)), 5)
    var_cues = min(len(VAR_CUES.findall(text)), 3)
    hits = [h.slug for h in vocab.match_sources(text)]
    score = (5 if heading else 0) + (3 if var_heading else 0) + cues + var_cues + (2 if hits else 0)
    if chunk.section in PRIOR_SECTIONS:
        score += 1
    if chunk.section == "references":
        score -= 3
    return ChunkScore(score, heading, cues, var_cues, hits)


def select_candidates(chunks: list[Chunk], vocab: Vocab, top_k: int = 10) -> list[Chunk]:
    """Top-k scored chunks plus their immediate neighbours, in document order.

    Works on list positions, not chunk_index: real Chroma data has colliding chunk_index
    values (figure-caption chunks share an index with a body chunk), so a dict keyed by
    chunk_index would silently drop one of each pair.
    """
    if not chunks:
        return []
    ordered = sorted(chunks, key=lambda c: c.chunk_index)  # stable
    scores = [score_chunk(c, vocab).score for c in ordered]  # computed once per chunk
    ranked = sorted(range(len(ordered)), key=lambda i: (-scores[i], i))
    keep: set[int] = set()
    for pos in ranked[:top_k]:
        keep.update(p for p in (pos - 1, pos, pos + 1) if 0 <= p < len(ordered))
    return [ordered[p] for p in sorted(keep)]
