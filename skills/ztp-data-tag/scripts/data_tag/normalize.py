"""Merge grep hits and LLM output into per-paper records; derive tags."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from .chroma import Chunk
from .vocab import SourceHit, Vocab, slugify
from . import MARKER_V1, MARKER_V2

US_STATES = {"alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware","florida",
    "georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky","louisiana","maine","maryland",
    "massachusetts","michigan","minnesota","mississippi","missouri","montana","nebraska","nevada","new hampshire",
    "new jersey","new mexico","new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
    "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington",
    "west virginia","wisconsin","wyoming"}


def infer_geo_level(text: str | None, places: list[str]) -> str | None:
    low = (text or "").lower()
    if re.search(r"\b(oecd|countries|cross-country|international|european union|eu-\d+)\b", low): return "multi-country"
    if re.search(r"\b(global|worldwide)\b", low): return "global"
    if re.search(r"\b(united states|u\.s\.|usa|nationwide|national|all u\.?s\.? )", low): return "national"
    if re.search(r"\b(msa|cbsa|metropolitan|metro)\b", low): return "metro"
    if re.search(r"\bcount(y|ies)\b", low): return "county"
    if re.search(r"\b(census tract|block group|neighborhood|neighbourhood|zip code)\b", low): return "neighborhood"
    if re.search(r"\bparcel\b", low): return "parcel"
    if re.search(r"\bstate of\b", low) or any(s in low for s in US_STATES): return "state"
    if re.search(r"\bcity of\b", low): return "city"
    if re.search(r"\bregion\b", low): return "region"
    if places and len(places) == 1 and re.match(r"^[A-Z][\w .'-]+,\s*[A-Z]{2}$", places[0]): return "city"
    return None


@dataclass
class Evidence:
    chunk_index: int
    page_num: int | None
    snippet: str


@dataclass
class Variable:
    name_raw: str
    slug: str
    role: str
    dv_class: str | None


@dataclass
class DatasetRecord:
    name_raw: str
    provider: str | None
    src_slug: str | None
    type_slug: str
    geo_text: str | None
    geo_level: str | None
    places: list[str]
    period_start: int | None
    period_end: int | None
    unit: str | None
    access: str | None
    confidence: float
    source: str                      # grep | llm | merged
    variables: list[Variable] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ReviewItem:
    kind: str                        # source | dv_class
    name_raw: str
    suggested_slug: str
    snippet: str


@dataclass
class DocRecord:
    doc_id: str
    status: str                      # ok | no_candidates | model_error | unindexed | write_conflict
    datasets: list[DatasetRecord] = field(default_factory=list)
    review: list[ReviewItem] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    llm_notes: str = ""


def _snippet(chunk: Chunk, start: int | None = None, width: int = 300) -> str:
    text = " ".join(chunk.text.split())
    if start is None or len(text) <= width:
        return text[:width]
    lo = max(0, start - width // 3)
    return text[lo:lo + width]


def _evidence_from_grep(hits_by_chunk: dict[int, list[SourceHit]], by_index: dict[int, Chunk], slug: str) -> list[Evidence]:
    out = []
    for idx, hits in hits_by_chunk.items():
        for h in hits:
            if h.slug == slug and idx in by_index:
                out.append(Evidence(idx, by_index[idx].page_num, _snippet(by_index[idx], h.start)))
    return out


def build_records(doc_id: str, chunks: list[Chunk], candidates: list[Chunk],
                  grep_hits: dict[int, list[SourceHit]], llm_out: dict, dropped: list[str], vocab: Vocab) -> DocRecord:
    if not chunks or not candidates:
        return DocRecord(doc_id, "no_candidates", dropped=dropped)
    by_index = {c.chunk_index: c for c in chunks}
    records: dict[str, DatasetRecord] = {}
    unlisted: list[DatasetRecord] = []
    review: list[ReviewItem] = []

    # grep layer
    for idx, hits in grep_hits.items():
        for h in hits:
            if h.slug in records:
                continue
            src = vocab.sources[h.slug]
            records[h.slug] = DatasetRecord(src.name, None, h.slug, src.type, None, src.geo_level, [], None, None,
                                            None, src.access, 0.9, "grep",
                                            evidence=_evidence_from_grep(grep_hits, by_index, h.slug))
    # llm layer
    for ds in llm_out.get("datasets", []):
        slug = vocab.resolve_source(ds["name"]) or vocab.resolve_source(ds.get("provider"))
        variables = []
        for v in ds["variables"]:
            dv_class = vocab.resolve_dv(v["name"]) if v["role"] == "dependent" else None
            if v["role"] == "dependent" and dv_class is None:
                review.append(ReviewItem("dv_class", v["name"], slugify(v["name"]), ds["name"]))
            variables.append(Variable(v["name"], slugify(v["name"]), v["role"], dv_class))
        evidence = [Evidence(i, by_index[i].page_num, _snippet(by_index[i])) for i in ds["evidence_chunks"] if i in by_index]
        geo_level = ds["geography"]["level"] or infer_geo_level(ds["geography"]["text"], ds["geography"]["places"])
        if slug and slug in records:
            rec = records[slug]
            rec.source, rec.confidence = "merged", max(rec.confidence, 0.95)
            rec.name_raw, rec.provider = ds["name"], ds.get("provider")
            rec.type_slug = ds["type"]
            rec.geo_text, rec.geo_level = ds["geography"]["text"], geo_level or rec.geo_level
            rec.places = ds["geography"]["places"]
            rec.period_start, rec.period_end = ds["period"]["start"], ds["period"]["end"]
            rec.unit, rec.access = ds.get("unit_of_observation"), ds.get("access") or rec.access
            rec.variables = variables
            seen = {e.chunk_index for e in rec.evidence}
            rec.evidence += [e for e in evidence if e.chunk_index not in seen]
            continue
        rec = DatasetRecord(ds["name"], ds.get("provider"), slug, ds["type"], ds["geography"]["text"], geo_level,
                            ds["geography"]["places"], ds["period"]["start"], ds["period"]["end"],
                            ds.get("unit_of_observation"), ds.get("access"), 0.7 if slug else 0.6, "llm",
                            variables, evidence)
        if slug:
            records[slug] = rec
        else:
            unlisted.append(rec)
            review.append(ReviewItem("source", ds["name"], slugify(ds.get("provider") or ds["name"]),
                                     evidence[0].snippet if evidence else ""))
    return DocRecord(doc_id, "ok", list(records.values()) + unlisted, review, dropped, llm_out.get("notes", ""))


def tags_for(doc: DocRecord) -> list[str]:
    tags = {MARKER_V1, MARKER_V2}
    for d in doc.datasets:
        if d.src_slug:
            tags.add(f"dataset:{d.src_slug}")
        tags.add(f"datatype:{d.type_slug}")
        if d.geo_level:
            tags.add(f"geo:{d.geo_level}")
        for v in d.variables:
            tags.add(f"var:{v.slug}")
            if v.dv_class:
                tags.add(f"dv:{v.dv_class}")
    return sorted(tags)
