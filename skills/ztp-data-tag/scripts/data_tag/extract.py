"""One local-LLM call per paper, JSON-schema constrained, validated against the candidate set."""
from __future__ import annotations
import json
from pathlib import Path
import httpx
from . import MODEL, OLLAMA_URL
from .chroma import Chunk
from .vocab import Vocab

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts/extract.md"
ROLES = ["dependent", "independent", "control", "instrument", "other"]


class OllamaError(RuntimeError):
    pass


def build_schema(vocab: Vocab) -> dict:
    nullable_int = {"type": ["integer", "null"]}
    nullable_str = {"type": ["string", "null"]}
    dataset = {
        "type": "object",
        "required": ["name", "type", "geography", "period", "variables", "evidence_chunks"],
        "properties": {
            "name": {"type": "string"},
            "provider": nullable_str,
            "type": {"type": "string", "enum": vocab.types},
            "geography": {"type": "object", "required": ["text", "level", "places"],
                          "properties": {"text": nullable_str,
                                         "level": {"type": ["string", "null"], "enum": vocab.geo_levels},
                                         "places": {"type": "array", "items": {"type": "string"}}}},
            "period": {"type": "object", "required": ["start", "end"],
                       "properties": {"start": nullable_int, "end": nullable_int}},
            "unit_of_observation": nullable_str,
            "access": nullable_str,
            "variables": {"type": "array", "items": {
                "type": "object", "required": ["name", "role"],
                "properties": {"name": {"type": "string"}, "role": {"type": "string", "enum": ROLES}}}},
            "evidence_chunks": {"type": "array", "items": {"type": "integer"}},
        },
    }
    return {"type": "object", "required": ["datasets"],
            "properties": {"datasets": {"type": "array", "items": dataset},
                           "notes": {"type": "string"}}}


def build_prompt(candidates: list[Chunk], grep_hits: list[str], vocab: Vocab) -> str:
    template = PROMPT_PATH.read_text()
    hints = ", ".join(f"{slug} ({vocab.sources[slug].name}, default type {vocab.sources[slug].type})"
                      for slug in grep_hits if slug in vocab.sources) or "none"
    chunk_text = "\n\n".join(f"[chunk {c.chunk_index}, p.{c.page_num if c.page_num is not None else '?'}]\n{c.text.strip()}"
                             for c in candidates)
    # chunk text is a format *value*, so braces inside it are safe; format exactly once.
    return template.format(hints=hints, types=", ".join(vocab.types),
                           geo_levels=", ".join(vocab.geo_levels), chunks=chunk_text)


def _is_year(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1800 <= value <= 2100


def validate_output(raw: dict, candidate_indices: set[int], vocab: Vocab) -> tuple[dict, list[str]]:
    dropped: list[str] = []
    clean_sets = []
    for ds in raw.get("datasets", []) or []:
        name = (ds.get("name") or "").strip()
        if not name:
            dropped.append("dataset without name"); continue
        if ds.get("type") not in vocab.types:
            dropped.append(f"{name}: unknown type {ds.get('type')!r}"); continue
        claimed = ds.get("evidence_chunks") or []
        ev = [i for i in claimed if isinstance(i, int) and i in candidate_indices]
        bad_ev = [i for i in claimed if not (isinstance(i, int) and i in candidate_indices)]
        if bad_ev:
            dropped.append(f"{name}: evidence chunk(s) {bad_ev} not in candidate set")
        geo = ds.get("geography") or {}
        level = geo.get("level") if geo.get("level") in vocab.geo_levels else None
        period = ds.get("period") or {}
        start, end = period.get("start"), period.get("end")
        if isinstance(start, int) and isinstance(end, int) and start > end:
            dropped.append(f"{name}: period {start}>{end} nulled"); start = end = None
        for yr in (start, end):
            if yr is not None and not _is_year(yr):
                dropped.append(f"{name}: implausible year {yr} nulled"); start = end = None
                break
        variables = [{"name": v["name"].strip(), "role": v.get("role") if v.get("role") in ROLES else "other"}
                     for v in (ds.get("variables") or []) if isinstance(v, dict) and v.get("name")]
        clean_sets.append({"name": name, "provider": ds.get("provider"), "type": ds["type"],
                           "geography": {"text": geo.get("text"), "level": level, "places": list(geo.get("places") or [])},
                           "period": {"start": start, "end": end},
                           "unit_of_observation": ds.get("unit_of_observation"), "access": ds.get("access"),
                           "variables": variables, "evidence_chunks": ev})
    return {"datasets": clean_sets, "notes": (raw.get("notes") or "")[:200]}, dropped


class OllamaClient:
    def __init__(self, url: str = OLLAMA_URL, model: str = MODEL, timeout: float = 300.0):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout

    def check_ready(self) -> None:
        try:
            names = [m["name"] for m in httpx.get(f"{self.url}/api/tags", timeout=5).json()["models"]]
        except Exception as exc:
            raise RuntimeError(f"Ollama not reachable at {self.url} — start it (`open -a Ollama`)") from exc
        if self.model not in names:
            raise RuntimeError(f"model {self.model} not pulled — run `ollama pull {self.model}`")

    def _chat(self, prompt: str, schema: dict) -> dict:
        body = {"model": self.model, "stream": False, "format": schema,
                "options": {"temperature": 0, "num_ctx": 8192},
                "messages": [{"role": "user", "content": prompt}]}
        resp = httpx.post(f"{self.url}/api/chat", json=body, timeout=self.timeout)
        resp.raise_for_status()
        return json.loads(resp.json()["message"]["content"])

    def extract(self, candidates: list[Chunk], grep_hits: list[str], vocab: Vocab) -> tuple[dict, list[str]]:
        prompt, schema = build_prompt(candidates, grep_hits, vocab), build_schema(vocab)
        last_exc: Exception | None = None
        for _attempt in range(2):
            try:
                raw = self._chat(prompt, schema)
                return validate_output(raw, {c.chunk_index for c in candidates}, vocab)
            except (json.JSONDecodeError, KeyError, httpx.HTTPError) as exc:
                last_exc = exc
        raise OllamaError(f"extraction failed after 2 attempts: {last_exc}")
