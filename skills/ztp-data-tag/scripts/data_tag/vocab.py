"""Controlled vocabulary: known sources (regex aliases), closed enums, DV classes."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data_vocab.yaml"
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_DV_SEP_RE = re.compile(r"[-_/]")


def _norm_dv(text: str) -> str:
    """Replace -, _ and / with spaces and collapse whitespace (for DV needle matching)."""
    return " ".join(_DV_SEP_RE.sub(" ", text).split())


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


@dataclass
class Source:
    slug: str
    name: str
    aliases: list[re.Pattern]
    type: str
    geo_level: str
    access: str


@dataclass
class SourceHit:
    slug: str
    start: int
    end: int
    matched: str


@dataclass
class Vocab:
    version: int
    sources: dict[str, Source]
    types: list[str]
    geo_levels: list[str]
    dv_classes: dict[str, list[str]]
    path: Path = field(default=DEFAULT_PATH)

    @classmethod
    def load(cls, path: Path | None = None) -> "Vocab":
        vocab_path = Path(path) if path else DEFAULT_PATH
        raw = yaml.safe_load(vocab_path.read_text())
        sources = {}
        for slug, spec in raw["sources"].items():
            sources[slug] = Source(
                slug=slug, name=spec["name"],
                aliases=[re.compile(a) for a in spec["aliases"]],
                type=spec["type"], geo_level=spec["geo_level"], access=spec.get("access", ""))
        for src in sources.values():
            if src.type not in raw["types"]:
                raise ValueError(f"source {src.slug}: unknown type {src.type}")
            if src.geo_level not in raw["geo_levels"]:
                raise ValueError(f"source {src.slug}: unknown geo_level {src.geo_level}")
        return cls(version=int(raw["version"]), sources=sources, types=list(raw["types"]),
                   geo_levels=list(raw["geo_levels"]),
                   dv_classes={k: list(v or []) for k, v in raw["dv_classes"].items()}, path=vocab_path)

    def match_sources(self, text: str) -> list[SourceHit]:
        hits: list[SourceHit] = []
        for src in self.sources.values():
            for pat in src.aliases:
                for m in pat.finditer(text):
                    hits.append(SourceHit(src.slug, m.start(), m.end(), m.group(0)))
        hits.sort(key=lambda h: h.start)
        # one hit per slug per text is enough for tagging; keep the first
        seen, unique = set(), []
        for h in hits:
            if h.slug not in seen:
                seen.add(h.slug); unique.append(h)
        return unique

    def resolve_source(self, name: str | None) -> str | None:
        if not name:
            return None
        hits = self.match_sources(name)
        if hits:
            return hits[0].slug
        key = slugify(name)
        for slug, src in self.sources.items():
            if key == slug or key == slugify(src.name):
                return slug
        return None

    def resolve_dv(self, name: str | None) -> str | None:
        """Longest matching needle wins. Input and needles are normalised ([-_/] -> space,
        whitespace collapsed). All-caps needles (TOM, DOM, HPI) match case-sensitively as whole
        words, so "domestic"/"tomorrow" do not hit them; other needles match case-insensitively
        at a word start ("delinquen" covers "delinquency")."""
        if not name:
            return None
        text = _norm_dv(name)
        matches = {}  # dv_slug -> longest matching needle length
        for dv_slug, needles in self.dv_classes.items():
            for needle in needles:
                norm = _norm_dv(needle)
                if norm.isupper():
                    pat = re.compile(r"\b" + re.escape(norm) + r"\b")
                else:
                    pat = re.compile(r"\b" + re.escape(norm), re.I)
                if pat.search(text) and len(norm) > matches.get(dv_slug, -1):
                    matches[dv_slug] = len(norm)
        if not matches:
            return None
        return max(matches, key=matches.get)
