# ztp-data-tag v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tag every indexed Zotero paper with the datasets it uses (source, type, geography, period, variables with DV role, evidence chunk/page) using SQL grep over ChromaDB plus a local Ollama model — zero Claude tokens per paper.

**Architecture:** A Python package `skills/ztp-data-tag/scripts/data_tag/` run with the `zotpilot` micromamba env. Per paper: read chunks from `chroma.sqlite3` (read-only) → score and select candidate chunks → regex grep against a YAML vocabulary → one `qwen2.5:7b-instruct` call with a JSON schema → normalize/merge → write the sidecar SQLite (truth) → write Zotero tags + one note via pyzotero → render a per-pass Markdown report that Claude reads to tune the vocabulary.

**Tech Stack:** Python 3.12 (`micromamba run -n zotpilot`), sqlite3 stdlib, `pyyaml`, `httpx` (Ollama), `pyzotero 1.13`, `pytest 9`. No chromadb client needed — the Chroma SQLite file is queried directly.

**Spec:** `docs/superpowers/specs/2026-10-07-ztp-data-tag-v2-design.md`

## Global Constraints

- Chroma is **read-only**: open with `sqlite3.connect("file:...?mode=ro", uri=True)`. Zotero SQLite is read-only + immutable: `file:...?mode=ro&immutable=1`. **Never write to either.**
- All Zotero writes go through pyzotero (`zotero.Zotero(library_id, library_type, api_key)`), never the MCP tools. Tags are merged, never replaced (`set_item_tags` is forbidden).
- Note title is exactly `Data (auto-extracted)`; v1 notes are `<div class="zotero-note znv1"><h1>Data (auto-extracted)</h1>…` — match on the `<h1>`.
- Tag namespaces: keep `dataset:<slug>`, `var:<slug>`, `data-tagged`; add `datatype:<slug>`, `dv:<slug>`, `geo:<level>`, `data-tagged:v2`. Skip items carrying `data-tagged:v2`; **reprocess** items with only `data-tagged`.
- Secrets: `ZOTERO_API_KEY` from the environment (`~/.secrets.env`), never in files. Group writes use `library_type="group"`, `library_id="2350352"` for affordable_housing.
- Sidecar path: `~/.local/share/zotpilot/data_tags.sqlite` (override with `DATA_TAGS_DB` env for tests).
- Ollama: `http://localhost:11434`, model `qwen2.5:7b-instruct`, `temperature 0`, `num_ctx 8192`; refuse to start if the server or model is absent.
- Variable naming: no top-level names from the forbidden list in `~/.claude/CLAUDE.md` (`data`, `df`, `file`, `list`, `format`, `str`…). Use descriptive names (`chunk_rows`, `vocab_sources`).
- Run tests with `micromamba run -n zotpilot python -m pytest tests/test_data_tag_*.py -q`. Commit after every green task (local commits only; branch `feat/ztp-data-tag-v2`).

## Review Focus

1. A paper whose chunks never match the data-heading regex (e.g. heading "Empirical Setting") — selection must still return the top cue-scored chunks, never an empty set, unless the paper has zero chunks (then `status=no_candidates`). Pinned in Task 4.
2. Prose containing "cost" / "costs are" must **not** hit the `costar` alias; aliases are word-bounded, case-sensitive where the brand is (`CoStar`). Pinned in Task 2.
3. The model returns an `evidence_chunks` index not in the candidate set, an unknown `type`, or `period.start > period.end` — rows are dropped/nulled with a logged reason, never written. Pinned in Tasks 5–6.
4. Zotero returns HTTP 412 (desktop edit not yet synced) — one re-read + retry, second failure recorded as `status=write_conflict`, the pass continues. Pinned in Task 8.
5. Re-running the same `--pass N` must replace that pass's sidecar rows and update (not duplicate) the Zotero note. Pinned in Tasks 7–8.

## File Structure

```
skills/ztp-data-tag/
  SKILL.md                                  # Task 11 — rewritten workflow
  scripts/
    data_tag.py                             # thin entry: from data_tag.cli import main
    data_vocab.yaml                         # Task 2 — sources/types/geo_levels/dv_classes
    prompts/extract.md                      # Task 5 — the Ollama prompt
    data_tag/
      __init__.py
      vocab.py        # Task 2: load YAML, compile aliases, match(text) → [(slug, span)]
      chroma.py       # Task 3: chunks_for_doc(doc_id) → [Chunk]; indexed_doc_ids()
      candidates.py   # Task 4: score_chunk(), select_candidates(chunks, vocab) → [Chunk]
      extract.py      # Task 5: OllamaClient.extract(candidates, hints) → dict (schema-validated)
      normalize.py    # Task 6: build_records(doc, grep_hits, llm_out, vocab) → DocRecord
      sidecar.py      # Task 7: Sidecar(path): write_pass(), replace_doc(), queries
      zotero_io.py    # Task 8: enumerate_items(), ZoteroWriterV2 (note upsert, tag merge)
      report.py       # Task 9: render_pass_report(sidecar, pass_id) → str
      cli.py          # Task 10: run / undo / query subcommands
tests/
  test_data_tag_vocab.py  test_data_tag_chroma.py  test_data_tag_candidates.py
  test_data_tag_extract.py  test_data_tag_normalize.py  test_data_tag_sidecar.py
  test_data_tag_zotero.py  test_data_tag_report.py  test_data_tag_cli.py
  fixtures/data_tag/                        # chunk texts + expected records
```

Tests import the package via `sys.path.insert(0, "skills/ztp-data-tag/scripts")` in `tests/conftest.py` (add a `data_tag_path` fixture there — Task 1).

---

### Task 1: Scaffold, env check, Ollama contract test

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/__init__.py`, `skills/ztp-data-tag/scripts/data_tag.py`
- Modify: `tests/conftest.py` (append the sys.path insert; create the file if absent)
- Test: `tests/test_data_tag_ollama_contract.py`

**Interfaces:**
- Produces: importable package `data_tag`; `data_tag.OLLAMA_URL = "http://localhost:11434"`, `data_tag.MODEL = "qwen2.5:7b-instruct"`.

- [ ] **Step 1: Pull the model (one-time, ~4.7 GB)**

```bash
ollama pull qwen2.5:7b-instruct
curl -s localhost:11434/api/tags | python3 -c "import sys,json;print([m['name'] for m in json.load(sys.stdin)['models']])"
```
Expected: list includes `qwen2.5:7b-instruct`.

- [ ] **Step 2: Create the package and conftest path**

`skills/ztp-data-tag/scripts/data_tag/__init__.py`:
```python
"""ztp-data-tag v2 — local, grep-first dataset/variable tagging over ChromaDB."""
OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:7b-instruct"
NOTE_TITLE = "Data (auto-extracted)"
MARKER_V1 = "data-tagged"
MARKER_V2 = "data-tagged:v2"
```
`skills/ztp-data-tag/scripts/data_tag.py`:
```python
#!/usr/bin/env python
"""CLI entry. Run with: micromamba run -n zotpilot python skills/ztp-data-tag/scripts/data_tag.py …"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_tag.cli import main  # noqa: E402
if __name__ == "__main__":
    sys.exit(main())
```
Append to `tests/conftest.py`:
```python
import sys
from pathlib import Path
_DT = Path(__file__).resolve().parents[1] / "skills/ztp-data-tag/scripts"
if str(_DT) not in sys.path:
    sys.path.insert(0, str(_DT))
```

- [ ] **Step 3: Write the Ollama contract test (skips when Ollama is down)**

`tests/test_data_tag_ollama_contract.py`:
```python
import json, httpx, pytest
from data_tag import OLLAMA_URL, MODEL

SCHEMA = {"type": "object", "required": ["datasets"],
          "properties": {"datasets": {"type": "array", "items": {
              "type": "object", "required": ["name", "type"],
              "properties": {"name": {"type": "string"},
                             "type": {"type": "string", "enum": ["survey", "other"]}}}}}}

def _ollama_up():
    try:
        names = [m["name"] for m in httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).json()["models"]]
        return MODEL in names
    except Exception:
        return False

@pytest.mark.skipif(not _ollama_up(), reason="Ollama or model not available")
def test_format_schema_returns_valid_json():
    body = {"model": MODEL, "stream": False, "format": SCHEMA,
            "options": {"temperature": 0, "num_ctx": 2048},
            "messages": [{"role": "user", "content":
                "Text: 'We use the American Housing Survey 2015.' List datasets as JSON."}]}
    resp = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=120)
    resp.raise_for_status()
    parsed = json.loads(resp.json()["message"]["content"])
    assert parsed["datasets"] and parsed["datasets"][0]["type"] in ("survey", "other")
```

- [ ] **Step 4: Run it**

Run: `micromamba run -n zotpilot python -m pytest tests/test_data_tag_ollama_contract.py -v`
Expected: PASS (or SKIP with "Ollama or model not available" — then start Ollama and re-run; the contract must PASS once before Task 5). If it FAILS with non-JSON content, record the finding in the plan and switch Task 5 to prompt-embedded schema + post-validation.

- [ ] **Step 5: Commit**

```bash
git add skills/ztp-data-tag/scripts tests/conftest.py tests/test_data_tag_ollama_contract.py
git commit -m "feat(ztp-data-tag): v2 scaffold + Ollama JSON-schema contract test"
```

---

### Task 2: Vocabulary — `data_vocab.yaml` + `vocab.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_vocab.yaml`, `skills/ztp-data-tag/scripts/data_tag/vocab.py`
- Test: `tests/test_data_tag_vocab.py`

**Interfaces:**
- Produces: `Vocab.load(path=None) -> Vocab`; attributes `version:int`, `sources:dict[slug, Source]`, `types:list[str]`, `geo_levels:list[str]`, `dv_classes:dict[slug, list[str]]` (aliases); `Vocab.match_sources(text) -> list[SourceHit]` with `SourceHit(slug, start, end, matched)`; `Vocab.resolve_source(name) -> str|None` (alias or fuzzy-normalized lookup); `Vocab.resolve_dv(name) -> str|None`; `slugify(text) -> str`.

- [ ] **Step 1: Write the failing tests**

`tests/test_data_tag_vocab.py`:
```python
import pytest
from data_tag.vocab import Vocab, slugify

@pytest.fixture(scope="module")
def vocab():
    return Vocab.load()

def test_loads_seed(vocab):
    assert vocab.version >= 1
    assert "costar" in vocab.sources and "hmda" in vocab.sources
    assert "residential-transactions-mls" in vocab.types
    assert "metro" in vocab.geo_levels and "house-price" in vocab.dv_classes

def test_match_costar_word_bounded(vocab):
    hits = vocab.match_sources("We obtain rents from CoStar for 2010–2019.")
    assert [h.slug for h in hits] == ["costar"]
    assert vocab.match_sources("Costs are higher; the costar analysis is irrelevant.") == []

def test_match_hmda_long_alias(vocab):
    hits = vocab.match_sources("Home Mortgage Disclosure Act data cover all lenders.")
    assert hits and hits[0].slug == "hmda"

def test_resolve_source_by_name_and_alias(vocab):
    assert vocab.resolve_source("CoStar Group") == "costar"
    assert vocab.resolve_source("American Community Survey") == "acs"
    assert vocab.resolve_source("REcolorado MLS") == "mls"
    assert vocab.resolve_source("Some Unknown Provider") is None

def test_resolve_dv(vocab):
    assert vocab.resolve_dv("log sale price") == "house-price"
    assert vocab.resolve_dv("monthly asking rent") == "rent"
    assert vocab.resolve_dv("tenure choice") is None

def test_slugify():
    assert slugify("Loan-Denial  Rate (HMDA)") == "loan-denial-rate-hmda"
```

- [ ] **Step 2: Run to verify failure**

Run: `micromamba run -n zotpilot python -m pytest tests/test_data_tag_vocab.py -q`
Expected: FAIL — `ModuleNotFoundError: data_tag.vocab`.

- [ ] **Step 3: Write `data_vocab.yaml` (seed, spec §9)**

```yaml
version: 1
sources:
  costar:   {name: CoStar, aliases: ['\bCoStar\b', '\bCo-Star\b', '\bCoStar Group\b'], type: commercial-property, geo_level: national, access: proprietary}
  rca:      {name: Real Capital Analytics, aliases: ['\bReal Capital Analytics\b', '\bRCA\b(?! Records)'], type: commercial-property, geo_level: national, access: proprietary}
  ncreif:   {name: NCREIF, aliases: ['\bNCREIF\b', '\bNPI\b', '\bODCE\b'], type: commercial-property, geo_level: national, access: proprietary}
  crsp:     {name: CRSP, aliases: ['\bCRSP\b'], type: reit-firm-financials, geo_level: national, access: proprietary}
  compustat: {name: Compustat, aliases: ['\bCompustat\b'], type: reit-firm-financials, geo_level: national, access: proprietary}
  snl:      {name: S&P Global / SNL, aliases: ['\bSNL\b', '\bS&P Global Market Intelligence\b', '\bS&P Capital IQ\b'], type: reit-firm-financials, geo_level: national, access: proprietary}
  bloomberg: {name: Bloomberg, aliases: ['\bBloomberg\b'], type: macro-financial-series, geo_level: global, access: proprietary}
  datastream: {name: Datastream, aliases: ['\bDatastream\b'], type: macro-financial-series, geo_level: global, access: proprietary}
  gresb:    {name: GRESB, aliases: ['\bGRESB\b'], type: reit-firm-financials, geo_level: global, access: proprietary}
  msci_esg: {name: MSCI ESG, aliases: ['\bMSCI ESG\b', '\bMSCI KLD\b', '\bKLD\b'], type: reit-firm-financials, geo_level: global, access: proprietary}
  hmda:     {name: HMDA, aliases: ['\bHMDA\b', 'Home Mortgage Disclosure Act'], type: mortgage-loan-level, geo_level: national, access: public}
  corelogic: {name: CoreLogic, aliases: ['\bCoreLogic\b', '\bDataQuick\b'], type: residential-transactions-deeds, geo_level: national, access: proprietary}
  ztrax:    {name: Zillow ZTRAX, aliases: ['\bZTRAX\b', 'Zillow Transaction and Assessment'], type: residential-transactions-deeds, geo_level: national, access: proprietary}
  zillow:   {name: Zillow (ZHVI/ZORI), aliases: ['\bZHVI\b', '\bZORI\b', '\bZillow Home Value Index\b', '\bZillow Observed Rent Index\b'], type: residential-listings-rents, geo_level: national, access: public}
  redfin:   {name: Redfin, aliases: ['\bRedfin\b'], type: residential-transactions-mls, geo_level: national, access: public}
  attom:    {name: ATTOM, aliases: ['\bATTOM\b'], type: residential-transactions-deeds, geo_level: national, access: proprietary}
  mls:      {name: MLS, aliases: ['\bMLS\b', 'Multiple Listing Service', '\bREcolorado\b', '\bMRIS\b', '\bBright MLS\b'], type: residential-transactions-mls, geo_level: metro, access: proprietary}
  acs:      {name: ACS, aliases: ['\bACS\b', 'American Community Survey'], type: census-acs, geo_level: national, access: public}
  census:   {name: Decennial Census, aliases: ['\bDecennial Census\b', '\b(?:19|20)\d0 Census\b', '\bCensus of Population\b'], type: census-acs, geo_level: national, access: public}
  lehd:     {name: LEHD/LODES, aliases: ['\bLEHD\b', '\bLODES\b'], type: census-acs, geo_level: national, access: public}
  cps:      {name: CPS, aliases: ['\bCPS\b', 'Current Population Survey'], type: survey, geo_level: national, access: public}
  ahs:      {name: AHS, aliases: ['\bAHS\b', 'American Housing Survey'], type: survey, geo_level: national, access: public}
  psid:     {name: PSID, aliases: ['\bPSID\b', 'Panel Study of Income Dynamics'], type: survey, geo_level: national, access: public}
  lihtc:    {name: HUD LIHTC database, aliases: ['\bLIHTC\b', 'Low[- ]Income Housing Tax Credit'], type: administrative-program, geo_level: national, access: public}
  hud_posh: {name: HUD Picture of Subsidized Households, aliases: ['Picture of Subsidized Households', '\bPSH\b'], type: administrative-program, geo_level: national, access: public}
  hud_fmr:  {name: HUD Fair Market Rents, aliases: ['Fair Market Rents?', '\bFMRs?\b'], type: administrative-program, geo_level: national, access: public}
  fema_nfhl: {name: FEMA NFHL / NFIP, aliases: ['\bNFHL\b', '\bNFIP\b', 'FEMA flood', 'Flood Insurance Rate Map', '\bFIRM\b(?!s? (?:size|value|level))', 'Special Flood Hazard Area', '\bSFHA\b'], type: hazard-flood, geo_level: national, access: public}
  noaa_storm: {name: NOAA Storm Events, aliases: ['NOAA Storm Events', 'Billion-Dollar', '\bNCEI\b'], type: hazard-disaster, geo_level: national, access: public}
  fema_decl: {name: FEMA disaster declarations, aliases: ['FEMA disaster declaration', 'Presidential disaster declaration'], type: hazard-disaster, geo_level: national, access: public}
  first_street: {name: First Street Foundation, aliases: ['First Street'], type: hazard-flood, geo_level: national, access: proprietary}
  prism:    {name: PRISM climate, aliases: ['\bPRISM\b'], type: climate-weather, geo_level: national, access: public}
  energy_star: {name: ENERGY STAR / LEED, aliases: ['\bENERGY STAR\b', '\bEnergy Star\b', '\bLEED\b', '\bUSGBC\b'], type: other, geo_level: national, access: public}
  wrluri:   {name: WRLURI, aliases: ['\bWRLURI\b', 'Wharton Residential Land Use'], type: zoning-land-use, geo_level: national, access: public}
  saiz:     {name: Saiz elasticity, aliases: ['Saiz \(2010\)', 'Saiz housing supply elasticit'], type: zoning-land-use, geo_level: metro, access: public}
  assessor: {name: County assessor records, aliases: ['assessor(?:’|\x27)?s? (?:office|records?|data|parcel)', 'tax assessor', 'assessment roll'], type: gis-parcel-boundary, geo_level: county, access: public}
  apartment_list: {name: Apartment List, aliases: ['\bApartment List\b'], type: residential-listings-rents, geo_level: national, access: public}
  yardi:    {name: Yardi Matrix, aliases: ['\bYardi\b'], type: residential-listings-rents, geo_level: national, access: proprietary}
  realpage: {name: RealPage / Axiometrics, aliases: ['\bRealPage\b', '\bAxiometrics\b'], type: residential-listings-rents, geo_level: national, access: proprietary}
  moodys_cre: {name: Moody's CRE / Reis, aliases: ['\bReis\b', 'Moody(?:’|\x27)s (?:CRE|Analytics REIS)'], type: commercial-property, geo_level: national, access: proprietary}
  trepp:    {name: Trepp, aliases: ['\bTrepp\b'], type: commercial-property, geo_level: national, access: proprietary}
  fred:     {name: FRED, aliases: ['\bFRED\b', 'Federal Reserve Economic Data'], type: macro-financial-series, geo_level: national, access: public}
types:
  - residential-transactions-mls
  - residential-transactions-deeds
  - residential-listings-rents
  - commercial-property
  - mortgage-loan-level
  - reit-firm-financials
  - census-acs
  - administrative-program
  - survey
  - hazard-flood
  - hazard-disaster
  - climate-weather
  - zoning-land-use
  - permits-construction
  - gis-parcel-boundary
  - macro-financial-series
  - hand-collected
  - other
geo_levels: [parcel, neighborhood, city, metro, county, state, region, national, multi-country, global]
dv_classes:
  house-price:          ['price', 'home value', 'house value', 'sale price', 'transaction price', 'HPI']
  rent:                 ['rent', 'rental rate', 'asking rent']
  transaction-volume:   ['sales volume', 'number of sales', 'transactions', 'turnover']
  time-on-market:       ['time on market', 'days on market', 'marketing time', 'TOM', 'DOM']
  mortgage-approval:    ['denial', 'approval', 'origination', 'loan application']
  default-foreclosure:  ['default', 'foreclosure', 'delinquen']
  reit-return:          ['REIT return', 'stock return', 'abnormal return', 'excess return']
  cap-rate:             ['cap rate', 'capitalization rate', 'yield']
  construction-permits: ['permits', 'housing starts', 'units built', 'new construction']
  affordability:        ['affordab', 'cost burden', 'rent-to-income', 'price-to-income']
  displacement-mobility:['displacement', 'mobility', 'move-out', 'residential mobility', 'eviction']
  other: []
```

- [ ] **Step 4: Write `vocab.py`**

```python
"""Controlled vocabulary: known sources (regex aliases), closed enums, DV classes."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data_vocab.yaml"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
        if not name:
            return None
        low = name.lower()
        for dv_slug, needles in self.dv_classes.items():
            if any(n.lower() in low for n in needles):
                return dv_slug
        return None
```

- [ ] **Step 5: Run tests**

Run: `micromamba run -n zotpilot python -m pytest tests/test_data_tag_vocab.py -q`
Expected: 6 passed. If `test_resolve_dv` fails on "log sale price" → "price" needle must be present (it is); if `monthly asking rent` resolves to `house-price` first, reorder: `resolve_dv` iterates dict order, so keep `rent` needles distinct from `price` (they are).

- [ ] **Step 6: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_vocab.yaml skills/ztp-data-tag/scripts/data_tag/vocab.py tests/test_data_tag_vocab.py
git commit -m "feat(ztp-data-tag): controlled vocabulary with regex aliases, types, geo levels, DV classes"
```

---

### Task 3: Chroma reader — `chroma.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/chroma.py`
- Test: `tests/test_data_tag_chroma.py`, fixture builder in the test (tiny in-memory Chroma-shaped SQLite)

**Interfaces:**
- Produces: `Chunk(doc_id, chunk_index:int, page_num:int|None, section:str, text:str, total_chunks:int|None)`; `ChromaReader(path) -> .chunks_for_doc(doc_id) -> list[Chunk]` (sorted by chunk_index); `.indexed_doc_ids(candidates: list[str]) -> set[str]`; `.doc_meta(doc_id) -> dict(title, year, publication, doi, tags:list[str], collections:list[str])`.

- [ ] **Step 1: Write the failing tests with a Chroma-shaped fixture DB**

`tests/test_data_tag_chroma.py`:
```python
import sqlite3, pytest
from data_tag.chroma import ChromaReader, Chunk

def _make_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE embeddings (id INTEGER PRIMARY KEY, segment_id TEXT, embedding_id TEXT, seq_id BLOB);
    CREATE TABLE embedding_metadata (id INTEGER, key TEXT, string_value TEXT, int_value INTEGER,
        float_value REAL, bool_value INTEGER, PRIMARY KEY (id, key));
    """)
    rows = []
    def add(i, doc, idx, page, section, text):
        con.execute("INSERT INTO embeddings VALUES (?,?,?,?)", (i, "seg", f"e{i}", b"\x00"))
        for k, v in [("doc_id", doc), ("section", section), ("chroma:document", text),
                     ("doc_title", "T " + doc), ("publication", "JRE"), ("doi", "10.1/x"),
                     ("tags", "Housing; Rent"), ("collections", "affordable_housing; REE")]:
            con.execute("INSERT INTO embedding_metadata (id,key,string_value) VALUES (?,?,?)", (i, k, v))
        for k, v in [("chunk_index", idx), ("page_num", page), ("total_chunks", 3), ("year", 2020)]:
            con.execute("INSERT INTO embedding_metadata (id,key,int_value) VALUES (?,?,?)", (i, k, v))
    add(1, "AAA", 1, 2, "introduction", "Intro text.")
    add(2, "AAA", 0, 1, "abstract", "Abstract text.")
    add(3, "AAA", 2, 3, "methods", "3. Data\nWe use CoStar.")
    add(4, "BBB", 0, 1, "unknown", "Other paper.")
    con.commit(); con.close()

@pytest.fixture
def reader(tmp_path):
    db = tmp_path / "chroma.sqlite3"; _make_db(db)
    return ChromaReader(db)

def test_chunks_sorted_and_typed(reader):
    chunks = reader.chunks_for_doc("AAA")
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert isinstance(chunks[0], Chunk) and chunks[2].page_num == 3 and chunks[2].section == "methods"
    assert chunks[2].text.startswith("3. Data")

def test_missing_doc_returns_empty(reader):
    assert reader.chunks_for_doc("ZZZ") == []

def test_indexed_doc_ids(reader):
    assert reader.indexed_doc_ids(["AAA", "BBB", "ZZZ"]) == {"AAA", "BBB"}

def test_doc_meta(reader):
    meta = reader.doc_meta("AAA")
    assert meta["title"] == "T AAA" and meta["year"] == 2020
    assert meta["tags"] == ["Housing", "Rent"] and "affordable_housing" in meta["collections"]

def test_read_only(reader):
    with pytest.raises(sqlite3.OperationalError):
        reader._con.execute("INSERT INTO embeddings VALUES (99,'s','e',x'00')")
```

- [ ] **Step 2: Run to verify failure**

Run: `micromamba run -n zotpilot python -m pytest tests/test_data_tag_chroma.py -q` → FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Write `chroma.py`**

```python
"""Read-only access to ZotPilot's ChromaDB SQLite file (no chromadb client needed)."""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CHROMA = Path.home() / ".local/share/zotpilot/chroma/chroma.sqlite3"

_CHUNK_SQL = """
SELECT m.id,
       MAX(CASE WHEN m.key='chunk_index'     THEN m.int_value END)    AS chunk_index,
       MAX(CASE WHEN m.key='page_num'        THEN m.int_value END)    AS page_num,
       MAX(CASE WHEN m.key='total_chunks'    THEN m.int_value END)    AS total_chunks,
       MAX(CASE WHEN m.key='section'         THEN m.string_value END) AS section,
       MAX(CASE WHEN m.key='chroma:document' THEN m.string_value END) AS text
FROM embedding_metadata m
WHERE m.id IN (SELECT id FROM embedding_metadata WHERE key='doc_id' AND string_value=?)
GROUP BY m.id
ORDER BY chunk_index
"""

_META_SQL = """
SELECT key, string_value, int_value FROM embedding_metadata
WHERE id = (SELECT MIN(id) FROM embedding_metadata WHERE key='doc_id' AND string_value=?)
  AND key IN ('doc_title','year','publication','doi','tags','collections')
"""


@dataclass
class Chunk:
    doc_id: str
    chunk_index: int
    page_num: int | None
    section: str
    text: str
    total_chunks: int | None = None


class ChromaReader:
    def __init__(self, path: Path | str = DEFAULT_CHROMA):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Chroma DB not found: {self.path}")
        self._con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)

    def chunks_for_doc(self, doc_id: str) -> list[Chunk]:
        rows = self._con.execute(_CHUNK_SQL, (doc_id,)).fetchall()
        return [Chunk(doc_id, int(r[1] or 0), r[2], r[4] or "unknown", r[5] or "", r[3]) for r in rows]

    def indexed_doc_ids(self, candidates: list[str]) -> set[str]:
        found: set[str] = set()
        for i in range(0, len(candidates), 500):
            batch = candidates[i:i + 500]
            marks = ",".join("?" * len(batch))
            rows = self._con.execute(
                f"SELECT DISTINCT string_value FROM embedding_metadata WHERE key='doc_id' AND string_value IN ({marks})",
                batch).fetchall()
            found.update(r[0] for r in rows)
        return found

    def doc_meta(self, doc_id: str) -> dict:
        meta = {"title": "", "year": None, "publication": "", "doi": "", "tags": [], "collections": []}
        for key, sval, ival in self._con.execute(_META_SQL, (doc_id,)):
            if key == "doc_title": meta["title"] = sval or ""
            elif key == "year": meta["year"] = ival
            elif key == "publication": meta["publication"] = sval or ""
            elif key == "doi": meta["doi"] = sval or ""
            elif key in ("tags", "collections"):
                meta[key] = [t.strip() for t in (sval or "").split(";") if t.strip()]
        return meta
```

- [ ] **Step 4: Run tests** → Expected: 5 passed.

- [ ] **Step 5: Smoke-test against the real DB (read-only)**

```bash
micromamba run -n zotpilot python -c "
import sys; sys.path.insert(0,'skills/ztp-data-tag/scripts')
from data_tag.chroma import ChromaReader
r=ChromaReader(); c=r.chunks_for_doc('2WF6CLF5'); print(len(c), c[0].section if c else None, r.doc_meta('2WF6CLF5')['title'][:50])"
```
Expected: a chunk count > 0 and the title "Amenities, affordability, and housing vouchers". (If 0, that item is one of the 11 unindexed — try `2C9XFEWY`.)

- [ ] **Step 6: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/chroma.py tests/test_data_tag_chroma.py
git commit -m "feat(ztp-data-tag): read-only Chroma SQLite reader (chunks, meta, indexed ids)"
```

---

### Task 4: Candidate chunk selection — `candidates.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/candidates.py`
- Test: `tests/test_data_tag_candidates.py`

**Interfaces:**
- Consumes: `Chunk` (Task 3), `Vocab.match_sources` (Task 2).
- Produces: `score_chunk(chunk, vocab) -> ChunkScore(score:int, heading:bool, cues:int, var_cues:int, source_hits:list[str])`; `select_candidates(chunks, vocab, top_k=10) -> list[Chunk]` (document order, neighbours included, deduplicated); constants `HEADING_RE`, `VAR_HEADING_RE`, `DATA_CUES`, `VAR_CUES`.

- [ ] **Step 1: Write the failing tests**

`tests/test_data_tag_candidates.py`:
```python
import pytest
from data_tag.chroma import Chunk
from data_tag.vocab import Vocab
from data_tag.candidates import HEADING_RE, score_chunk, select_candidates

@pytest.fixture(scope="module")
def vocab(): return Vocab.load()

def mk(idx, text, section="unknown", page=None):
    return Chunk("D", idx, page, section, text)

@pytest.mark.parametrize("heading", ["3. Data", "II. Data and Methodology", "Data and Sample",
                                     "DATA", "4.1 Data Sources", "3 Data and Variables", "Sample"])
def test_heading_positive(heading):
    assert HEADING_RE.search(heading + "\nWe use...")

@pytest.mark.parametrize("heading", ["Data availability", "Results", "Data are available on request",
                                     "References", "Appendix: Robustness"])
def test_heading_negative(heading):
    assert not HEADING_RE.search(heading + "\nmore text")

def test_scoring_components(vocab):
    s = score_chunk(mk(5, "3. Data\nWe obtain transactions from CoStar for 2010 to 2019. The dependent variable is log rent.", "methods"), vocab)
    assert s.heading and s.cues >= 3 and s.var_cues >= 1 and s.source_hits == ["costar"]
    assert s.score >= 5 + 3 + 1 + 2 + 1
    assert score_chunk(mk(9, "Smith, J. (2010). Journal. 10, 1-20.", "references"), vocab).score < 0

def test_select_includes_neighbours_in_doc_order(vocab):
    chunks = [mk(i, "filler text about theory", "introduction") for i in range(12)]
    chunks[6] = mk(6, "3. Data\nWe use HMDA observations from 2005 to 2015.", "methods")
    chosen = select_candidates(chunks, vocab, top_k=1)
    assert [c.chunk_index for c in chosen] == [5, 6, 7]

def test_select_never_empty_without_heading(vocab):
    chunks = [mk(0, "Empirical setting. We use data provided by the county assessor; observations span 2000-2010.", "unknown"),
              mk(1, "Theory section.", "introduction")]
    assert [c.chunk_index for c in select_candidates(chunks, vocab, top_k=1)] == [0, 1]

def test_select_empty_for_no_chunks(vocab):
    assert select_candidates([], vocab) == []
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.candidates`.

- [ ] **Step 3: Write `candidates.py`**

```python
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
    r"from (?:19|20)\d\d (?:to|through|–|-) (?:19|20)\d\d|(?:19|20)\d\d\s?[–-]\s?(?:19|20)\d\d|"
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
    if not chunks:
        return []
    by_index = {c.chunk_index: c for c in chunks}
    ranked = sorted(chunks, key=lambda c: (-score_chunk(c, vocab).score, c.chunk_index))
    keep: set[int] = set()
    for c in ranked[:top_k]:
        keep.update(i for i in (c.chunk_index - 1, c.chunk_index, c.chunk_index + 1) if i in by_index)
    return [by_index[i] for i in sorted(keep)]
```

- [ ] **Step 4: Run tests** → Expected: all pass. If a heading test fails, adjust `HEADING_RE` — never the test's positive/negative lists (they are the spec).

- [ ] **Step 5: Diagnostic against the real corpus (read-only; informs pass 1)**

```bash
micromamba run -n zotpilot python -c "
import sys; sys.path.insert(0,'skills/ztp-data-tag/scripts')
from data_tag.chroma import ChromaReader; from data_tag.vocab import Vocab
from data_tag.candidates import select_candidates, score_chunk
r=ChromaReader(); v=Vocab.load()
for d in ['2WF6CLF5','2C9XFEWY','34NHN45H']:
    ch=r.chunks_for_doc(d); c=select_candidates(ch,v)
    print(d, len(ch),'chunks ->',len(c),'cands; words',sum(len(x.text.split()) for x in c), 'best',max((score_chunk(x,v).score for x in ch),default=None))"
```
Expected: 15–35 candidate chunks and 1,500–3,000 words per paper. If words > 3,500, lower `top_k` default to 8.

- [ ] **Step 6: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/candidates.py tests/test_data_tag_candidates.py
git commit -m "feat(ztp-data-tag): heading/cue scoring and candidate chunk selection"
```

---

### Task 5: Local extraction — `extract.py` + `prompts/extract.md`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/extract.py`, `skills/ztp-data-tag/scripts/prompts/extract.md`
- Test: `tests/test_data_tag_extract.py`

**Interfaces:**
- Consumes: `Chunk`, `Vocab`, `OLLAMA_URL`, `MODEL`.
- Produces: `build_schema(vocab) -> dict` (JSON schema with enums); `build_prompt(candidates, grep_hits:list[str], vocab) -> str`; `validate_output(raw:dict, candidate_indices:set[int], vocab) -> tuple[dict, list[str]]` (cleaned output, list of dropped-reason strings); `OllamaClient(url, model).extract(candidates, grep_hits, vocab) -> tuple[dict, list[str]]`; `OllamaClient.check_ready() -> None` (raises `RuntimeError` with the fix). `OllamaError` exception.

- [ ] **Step 1: Write the failing tests (network mocked)**

`tests/test_data_tag_extract.py`:
```python
import json, pytest
from data_tag.chroma import Chunk
from data_tag.vocab import Vocab
from data_tag import extract as ex

@pytest.fixture(scope="module")
def vocab(): return Vocab.load()

def cands():
    return [Chunk("D", 17, 6, "methods", "3. Data\nWe use REcolorado MLS sales for the Denver MSA, 2010–2019."),
            Chunk("D", 18, 6, "methods", "The dependent variable is log sale price; controls include square footage.")]

def test_schema_has_enums(vocab):
    schema = ex.build_schema(vocab)
    ds = schema["properties"]["datasets"]["items"]["properties"]
    assert ds["type"]["enum"] == vocab.types
    assert ds["geography"]["properties"]["level"]["enum"] == vocab.geo_levels
    assert ds["variables"]["items"]["properties"]["role"]["enum"] == ["dependent", "independent", "control", "instrument", "other"]

def test_prompt_labels_chunks_and_hints(vocab):
    prompt = ex.build_prompt(cands(), ["mls"], vocab)
    assert "[chunk 17, p.6]" in prompt and "[chunk 18, p.6]" in prompt
    assert "mls" in prompt and "residential-transactions-mls" in prompt

def test_validate_drops_bad_rows(vocab):
    raw = {"datasets": [
        {"name": "REcolorado MLS", "provider": "REcolorado", "type": "residential-transactions-mls",
         "geography": {"text": "Denver MSA", "level": "metro", "places": ["Denver, CO"]},
         "period": {"start": 2010, "end": 2019}, "unit_of_observation": "sale", "access": "proprietary",
         "variables": [{"name": "log sale price", "role": "dependent"}], "evidence_chunks": [17, 99]},
        {"name": "Mystery", "type": "not-a-type", "evidence_chunks": [17]},
        {"name": "Backwards", "type": "survey", "period": {"start": 2020, "end": 2010}, "evidence_chunks": [18]}]}
    clean, dropped = ex.validate_output(raw, {17, 18}, vocab)
    assert [d["name"] for d in clean["datasets"]] == ["REcolorado MLS", "Backwards"]
    assert clean["datasets"][0]["evidence_chunks"] == [17]
    assert clean["datasets"][1]["period"] == {"start": None, "end": None}
    assert any("not-a-type" in r for r in dropped) and any("99" in r for r in dropped)

def test_extract_uses_format_and_parses(monkeypatch, vocab):
    captured = {}
    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": json.dumps({"datasets": [], "notes": ""})}}
    def fake_post(url, json=None, timeout=None):
        captured["url"], captured["body"] = url, json; return FakeResp()
    monkeypatch.setattr(ex.httpx, "post", fake_post)
    client = ex.OllamaClient("http://x", "m")
    out, dropped = client.extract(cands(), [], vocab)
    assert out == {"datasets": [], "notes": ""} and dropped == []
    assert captured["url"].endswith("/api/chat") and captured["body"]["format"]["type"] == "object"
    assert captured["body"]["options"] == {"temperature": 0, "num_ctx": 8192}

def test_extract_retries_once_then_raises(monkeypatch, vocab):
    calls = {"n": 0}
    class Bad:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "not json"}}
    def fake_post(url, json=None, timeout=None):
        calls["n"] += 1; return Bad()
    monkeypatch.setattr(ex.httpx, "post", fake_post)
    with pytest.raises(ex.OllamaError):
        ex.OllamaClient("http://x", "m").extract(cands(), [], vocab)
    assert calls["n"] == 2
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.extract`.

- [ ] **Step 3: Write `prompts/extract.md`**

```markdown
You are extracting the DATASETS used in an empirical real-estate / urban-economics paper.
You see numbered text chunks from the paper, each labelled `[chunk N, p.P]`.

Return JSON only, matching the schema you were given. Rules:
- One entry per distinct dataset actually USED in the analysis (not merely cited).
- `name`: the dataset as the paper names it. `provider`: the organisation that supplies it, or null.
- `type`: pick the single best value from the allowed list; use "other" only if nothing fits.
- `geography.text`: the paper's own words for coverage (e.g. "Denver–Aurora–Lakewood MSA");
  `geography.level`: one allowed level; `geography.places`: named places, or [].
- `period.start` / `period.end`: four-digit years of the data coverage, or null if not stated.
- `unit_of_observation`: e.g. "single-family sale", "census tract-year", "loan application".
- `variables`: variables the paper takes FROM THIS DATASET. `role` = "dependent" for an outcome
  the paper models, "independent" for the main explanatory variable(s), "control" for controls,
  "instrument" for instruments, otherwise "other".
- `evidence_chunks`: the chunk numbers (from the labels) where this dataset is described.
- Never guess. Unknown → null or []. Do not invent datasets that are not in the text.

Known-source hints found by keyword search (verify, do not blindly copy): {hints}

Allowed `type` values: {types}
Allowed `geography.level` values: {geo_levels}

=== PAPER CHUNKS ===
{chunks}
```

- [ ] **Step 4: Write `extract.py`**

```python
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
                                         "level": {"type": ["string", "null"], "enum": vocab.geo_levels + [None]},
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
    return template.format(hints=hints, types=", ".join(vocab.types),
                           geo_levels=", ".join(vocab.geo_levels), chunks=chunk_text)


def validate_output(raw: dict, candidate_indices: set[int], vocab: Vocab) -> tuple[dict, list[str]]:
    dropped: list[str] = []
    clean_sets = []
    for ds in raw.get("datasets", []) or []:
        name = (ds.get("name") or "").strip()
        if not name:
            dropped.append("dataset without name"); continue
        if ds.get("type") not in vocab.types:
            dropped.append(f"{name}: unknown type {ds.get('type')!r}"); continue
        ev = [i for i in (ds.get("evidence_chunks") or []) if isinstance(i, int) and i in candidate_indices]
        bad_ev = [i for i in (ds.get("evidence_chunks") or []) if i not in candidate_indices]
        if bad_ev:
            dropped.append(f"{name}: evidence chunk(s) {bad_ev} not in candidate set")
        geo = ds.get("geography") or {}
        level = geo.get("level") if geo.get("level") in vocab.geo_levels else None
        period = ds.get("period") or {}
        start, end = period.get("start"), period.get("end")
        if isinstance(start, int) and isinstance(end, int) and start > end:
            dropped.append(f"{name}: period {start}>{end} nulled"); start = end = None
        for yr in (start, end):
            if yr is not None and not (1800 <= yr <= 2100):
                dropped.append(f"{name}: implausible year {yr} nulled"); start = end = None
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
```

- [ ] **Step 5: Run tests** → Expected: 5 passed.

- [ ] **Step 6: Live smoke on one real paper (Ollama must be up)**

```bash
micromamba run -n zotpilot python -c "
import sys, json; sys.path.insert(0,'skills/ztp-data-tag/scripts')
from data_tag.chroma import ChromaReader; from data_tag.vocab import Vocab
from data_tag.candidates import select_candidates; from data_tag.extract import OllamaClient
r=ChromaReader(); v=Vocab.load(); cl=OllamaClient(); cl.check_ready()
c=select_candidates(r.chunks_for_doc('2WF6CLF5'), v)
hits=sorted({h.slug for ch in c for h in v.match_sources(ch.text)})
out,dropped=cl.extract(c,hits,v); print(json.dumps(out,indent=1)[:1500]); print('dropped:',dropped)"
```
Expected: ≥1 dataset with a plausible name/type/geography for "Amenities, affordability, and housing vouchers"; note the wall time. If the output is empty or nonsense, try `qwen2.5:14b-instruct` once (`MODEL` override via `DATA_TAG_MODEL` env — add that one-line env read to `__init__.py`) and record which model pass 1 will use.

- [ ] **Step 7: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/extract.py skills/ztp-data-tag/scripts/prompts/extract.md tests/test_data_tag_extract.py
git commit -m "feat(ztp-data-tag): schema-constrained Ollama extraction with validation"
```

---

### Task 6: Normalize & merge — `normalize.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/normalize.py`
- Test: `tests/test_data_tag_normalize.py`

**Interfaces:**
- Consumes: `Chunk`, `Vocab`, `SourceHit`, validated LLM output (Task 5 shape).
- Produces dataclasses used by Tasks 7–9:
  - `Evidence(chunk_index:int, page_num:int|None, snippet:str)`
  - `Variable(name_raw:str, slug:str, role:str, dv_class:str|None)`
  - `DatasetRecord(name_raw, provider, src_slug, type_slug, geo_text, geo_level, places:list[str], period_start, period_end, unit, access, confidence:float, source:str, variables:list[Variable], evidence:list[Evidence])`
  - `ReviewItem(kind:str, name_raw:str, suggested_slug:str, snippet:str)`
  - `DocRecord(doc_id, status, datasets:list[DatasetRecord], review:list[ReviewItem], dropped:list[str], llm_notes:str)`
  - `infer_geo_level(text, places) -> str|None`; `build_records(doc_id, chunks, candidates, grep_hits:list[SourceHit] per chunk as dict[int, list[SourceHit]], llm_out, dropped, vocab) -> DocRecord`.
  - Tag derivation: `tags_for(doc: DocRecord) -> list[str]` (sorted, unique; includes `data-tagged` and `data-tagged:v2`).

- [ ] **Step 1: Write the failing tests**

`tests/test_data_tag_normalize.py`:
```python
import pytest
from data_tag.chroma import Chunk
from data_tag.vocab import Vocab
from data_tag import normalize as nz

@pytest.fixture(scope="module")
def vocab(): return Vocab.load()

C17 = Chunk("D", 17, 6, "methods", "3. Data\nWe use REcolorado MLS sales for the Denver MSA, 2010–2019, and FEMA flood maps.")
C18 = Chunk("D", 18, 6, "methods", "The dependent variable is log sale price; controls include square footage.")

def llm():
    return {"datasets": [
        {"name": "REcolorado MLS sales", "provider": "REcolorado", "type": "residential-transactions-mls",
         "geography": {"text": "Denver MSA", "level": None, "places": ["Denver, CO"]},
         "period": {"start": 2010, "end": 2019}, "unit_of_observation": "sale", "access": "proprietary",
         "variables": [{"name": "log sale price", "role": "dependent"}, {"name": "square footage", "role": "control"}],
         "evidence_chunks": [17, 18]},
        {"name": "Denver Water shutoff records", "provider": "Denver Water", "type": "administrative-program",
         "geography": {"text": "City of Denver", "level": "city", "places": ["Denver"]},
         "period": {"start": None, "end": None}, "unit_of_observation": None, "access": None,
         "variables": [{"name": "shutoff count", "role": "independent"}], "evidence_chunks": [17]}],
        "notes": ""}

@pytest.mark.parametrize("text,places,level", [
    ("Denver–Aurora–Lakewood MSA", [], "metro"), ("the state of Colorado", [], "state"),
    ("United States", [], "national"), ("Harris County, Texas", [], "county"),
    ("17 OECD countries", [], "multi-country"), ("", ["Denver, CO"], "city"), ("", [], None)])
def test_infer_geo_level(text, places, level):
    assert nz.infer_geo_level(text, places) == level

def test_build_records_merges_grep_and_llm(vocab):
    grep = {17: vocab.match_sources(C17.text)}
    doc = nz.build_records("D", [C17, C18], [C17, C18], grep, llm(), ["x dropped"], vocab)
    assert doc.status == "ok" and doc.dropped == ["x dropped"]
    by_slug = {d.src_slug: d for d in doc.datasets}
    mls = by_slug["mls"]
    assert mls.source == "merged" and mls.confidence >= 0.9
    assert mls.geo_level == "metro" and mls.period_start == 2010 and mls.places == ["Denver, CO"]
    assert {(v.slug, v.role, v.dv_class) for v in mls.variables} == {("log-sale-price", "dependent", "house-price"), ("square-footage", "control", None)}
    assert sorted(e.chunk_index for e in mls.evidence) == [17, 18] and mls.evidence[0].page_num == 6
    fema = by_slug["fema_nfhl"]
    assert fema.source == "grep" and fema.type_slug == "hazard-flood" and fema.variables == []
    unlisted = [d for d in doc.datasets if d.src_slug is None]
    assert unlisted[0].name_raw == "Denver Water shutoff records" and unlisted[0].source == "llm"
    assert [(r.kind, r.name_raw) for r in doc.review] == [("source", "Denver Water shutoff records")]

def test_dv_review_queue_for_unlisted_dv(vocab):
    out = llm(); out["datasets"][0]["variables"] = [{"name": "tenure choice", "role": "dependent"}]
    doc = nz.build_records("D", [C17, C18], [C17, C18], {}, out, [], vocab)
    assert ("dv_class", "tenure choice") in [(r.kind, r.name_raw) for r in doc.review]

def test_status_no_candidates(vocab):
    doc = nz.build_records("D", [], [], {}, {"datasets": [], "notes": ""}, [], vocab)
    assert doc.status == "no_candidates" and doc.datasets == []

def test_tags_for(vocab):
    grep = {17: vocab.match_sources(C17.text)}
    doc = nz.build_records("D", [C17, C18], [C17, C18], grep, llm(), [], vocab)
    tags = nz.tags_for(doc)
    for expected in ["dataset:mls", "dataset:fema_nfhl", "datatype:residential-transactions-mls", "datatype:hazard-flood",
                     "datatype:administrative-program", "dv:house-price", "geo:metro", "geo:city",
                     "var:log-sale-price", "var:square-footage", "var:shutoff-count", "data-tagged", "data-tagged:v2"]:
        assert expected in tags
    assert not any(t.startswith("dataset:") and "denver-water" in t for t in tags)
    assert tags == sorted(set(tags))
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.normalize`.

- [ ] **Step 3: Write `normalize.py`**

```python
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
    if not chunks:
        return DocRecord(doc_id, "unindexed", dropped=dropped)
    if not candidates:
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
```

- [ ] **Step 4: Run tests** → Expected: all pass. (`infer_geo_level("", ["Denver, CO"])` relies on the `City, ST` regex; "Harris County, Texas" must hit `county` before the state check — the order above does that.)

- [ ] **Step 5: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/normalize.py tests/test_data_tag_normalize.py
git commit -m "feat(ztp-data-tag): merge grep+LLM into dataset records; geo inference; tag derivation"
```

---

### Task 7: Sidecar SQLite — `sidecar.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/sidecar.py`
- Test: `tests/test_data_tag_sidecar.py`

**Interfaces:**
- Consumes: `DocRecord`, `DatasetRecord`, `Variable`, `Evidence`, `ReviewItem` (Task 6).
- Produces: `Sidecar(path) ` with `.begin_pass(pass_id:int, library:str, collection:str|None, vocab_version:int, model:str, n_docs:int) -> None` (upsert; deletes that pass's doc/dataset rows first), `.write_doc(doc: DocRecord, pass_id, title, year, library_id) -> None`, `.set_doc_status(doc_id, status)`, `.written_tags(doc_id, pass_id, tags:list[str], note_key:str|None)` (records what reached Zotero, for undo), `.docs_in_pass(pass_id) -> list[sqlite3.Row]`, `.datasets_for_doc(doc_id) -> list[Row]` (joined with variables/evidence via helper `.variables_for(dataset_id)`, `.evidence_for(dataset_id)`), `.open_review(pass_id=None) -> list[Row]`, `.query_by_type(type_slug) -> list[Row]` (title, geo_text, geo_level, period, DVs), `.source_geo_matrix() -> list[Row]`, `.topic_crosstab(topic_tag:str, chroma_tags_lookup:callable) -> list[Row]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_data_tag_sidecar.py`:
```python
import pytest
from data_tag.sidecar import Sidecar
from data_tag.normalize import DocRecord, DatasetRecord, Variable, Evidence, ReviewItem

def rec(doc="D1", slug="mls"):
    ds = DatasetRecord("REcolorado MLS", "REcolorado", slug, "residential-transactions-mls", "Denver MSA", "metro",
                       ["Denver, CO"], 2010, 2019, "sale", "proprietary", 0.95, "merged",
                       [Variable("log sale price", "log-sale-price", "dependent", "house-price")],
                       [Evidence(17, 6, "We use REcolorado MLS…")])
    return DocRecord(doc, "ok", [ds], [ReviewItem("source", "Denver Water", "denver-water", "snip")], ["drop"], "")

@pytest.fixture
def sc(tmp_path):
    return Sidecar(tmp_path / "t.sqlite")

def test_round_trip(sc):
    sc.begin_pass(1, "group:2350352", None, 1, "qwen2.5:7b-instruct", 1)
    sc.write_doc(rec(), 1, "Title", 2020, "3")
    docs = sc.docs_in_pass(1); assert len(docs) == 1 and docs[0]["status"] == "ok"
    ds = sc.datasets_for_doc("D1"); assert len(ds) == 1 and ds[0]["src_slug"] == "mls" and ds[0]["geo_level"] == "metro"
    assert sc.variables_for(ds[0]["id"])[0]["dv_class"] == "house-price"
    assert sc.evidence_for(ds[0]["id"])[0]["page_num"] == 6
    assert [r["name_raw"] for r in sc.open_review(1)] == ["Denver Water"]

def test_rerun_pass_replaces_rows(sc):
    sc.begin_pass(1, "g", None, 1, "m", 1); sc.write_doc(rec(), 1, "T", 2020, "3")
    sc.begin_pass(1, "g", None, 2, "m", 1); sc.write_doc(rec(slug="redfin"), 1, "T", 2020, "3")
    ds = sc.datasets_for_doc("D1"); assert [d["src_slug"] for d in ds] == ["redfin"]
    assert sc.passes()[0]["vocab_version"] == 2

def test_written_tags_and_undo_lookup(sc):
    sc.begin_pass(1, "g", None, 1, "m", 1); sc.write_doc(rec(), 1, "T", 2020, "3")
    sc.written_tags("D1", 1, ["dataset:mls", "data-tagged:v2"], "NOTEKEY")
    w = sc.writes_in_pass(1); assert w[0]["note_key"] == "NOTEKEY" and "dataset:mls" in w[0]["tags_json"]

def test_query_by_type_and_matrix(sc):
    sc.begin_pass(1, "g", None, 1, "m", 2)
    sc.write_doc(rec("D1"), 1, "Paper One", 2020, "3"); sc.write_doc(rec("D2", "redfin"), 1, "Paper Two", 2021, "3")
    rows = sc.query_by_type("residential-transactions-mls")
    assert sorted(r["title"] for r in rows) == ["Paper One", "Paper Two"] and rows[0]["dvs"] == "house-price"
    matrix = sc.source_geo_matrix(); assert {(r["src_slug"], r["geo_level"], r["n"]) for r in matrix} == {("mls", "metro", 1), ("redfin", "metro", 1)}
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.sidecar`.

- [ ] **Step 3: Write `sidecar.py`**

```python
"""The sidecar SQLite: source of truth for every pass, dataset, variable and evidence row."""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .normalize import DocRecord

DEFAULT_SIDECAR = Path(os.environ.get("DATA_TAGS_DB", Path.home() / ".local/share/zotpilot/data_tags.sqlite"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS passes (pass_id INTEGER PRIMARY KEY, library TEXT, collection TEXT, n_docs INTEGER,
    vocab_version INTEGER, model TEXT, started_utc TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, library_id TEXT, title TEXT, year INTEGER,
    pass_id INTEGER, status TEXT, llm_notes TEXT, dropped_json TEXT);
CREATE TABLE IF NOT EXISTS datasets (id INTEGER PRIMARY KEY, doc_id TEXT, pass_id INTEGER, name_raw TEXT, provider TEXT,
    src_slug TEXT, type_slug TEXT, geo_text TEXT, geo_level TEXT, places_json TEXT, period_start INTEGER,
    period_end INTEGER, unit TEXT, access TEXT, confidence REAL, source TEXT);
CREATE TABLE IF NOT EXISTS variables (id INTEGER PRIMARY KEY, dataset_id INTEGER, name_raw TEXT, slug TEXT, role TEXT, dv_class TEXT);
CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY, dataset_id INTEGER, chunk_index INTEGER, page_num INTEGER, snippet TEXT);
CREATE TABLE IF NOT EXISTS review_queue (id INTEGER PRIMARY KEY, pass_id INTEGER, kind TEXT, name_raw TEXT, doc_id TEXT,
    suggested_slug TEXT, snippet TEXT, status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS zotero_writes (id INTEGER PRIMARY KEY, doc_id TEXT, pass_id INTEGER, tags_json TEXT,
    note_key TEXT, written_utc TEXT);
CREATE INDEX IF NOT EXISTS ix_datasets_doc ON datasets(doc_id);
CREATE INDEX IF NOT EXISTS ix_datasets_type ON datasets(type_slug);
CREATE INDEX IF NOT EXISTS ix_datasets_src ON datasets(src_slug);
"""


class Sidecar:
    def __init__(self, path: Path | str = DEFAULT_SIDECAR):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(self.path); self._con.row_factory = sqlite3.Row
        self._con.executescript(SCHEMA)

    # ---- passes -------------------------------------------------------------
    def begin_pass(self, pass_id: int, library: str, collection: str | None, vocab_version: int, model: str, n_docs: int) -> None:
        con = self._con
        doc_ids = [r[0] for r in con.execute("SELECT doc_id FROM documents WHERE pass_id=?", (pass_id,))]
        for doc_id in doc_ids:
            self._delete_doc_rows(doc_id)
        con.execute("DELETE FROM review_queue WHERE pass_id=? AND status='open'", (pass_id,))
        con.execute("INSERT OR REPLACE INTO passes VALUES (?,?,?,?,?,?,?,?)",
                    (pass_id, library, collection, n_docs, vocab_version, model, datetime.now(timezone.utc).isoformat(timespec="seconds"), ""))
        con.commit()

    def passes(self) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM passes ORDER BY pass_id").fetchall()

    # ---- documents ----------------------------------------------------------
    def _delete_doc_rows(self, doc_id: str) -> None:
        con = self._con
        ids = [r[0] for r in con.execute("SELECT id FROM datasets WHERE doc_id=?", (doc_id,))]
        if ids:
            marks = ",".join("?" * len(ids))
            con.execute(f"DELETE FROM variables WHERE dataset_id IN ({marks})", ids)
            con.execute(f"DELETE FROM evidence WHERE dataset_id IN ({marks})", ids)
        con.execute("DELETE FROM datasets WHERE doc_id=?", (doc_id,))
        con.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))

    def write_doc(self, doc: DocRecord, pass_id: int, title: str, year: int | None, library_id: str) -> None:
        con = self._con
        self._delete_doc_rows(doc.doc_id)
        con.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                    (doc.doc_id, library_id, title, year, pass_id, doc.status, doc.llm_notes, json.dumps(doc.dropped)))
        for d in doc.datasets:
            cur = con.execute("INSERT INTO datasets (doc_id,pass_id,name_raw,provider,src_slug,type_slug,geo_text,geo_level,"
                              "places_json,period_start,period_end,unit,access,confidence,source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (doc.doc_id, pass_id, d.name_raw, d.provider, d.src_slug, d.type_slug, d.geo_text, d.geo_level,
                               json.dumps(d.places), d.period_start, d.period_end, d.unit, d.access, d.confidence, d.source))
            ds_id = cur.lastrowid
            con.executemany("INSERT INTO variables (dataset_id,name_raw,slug,role,dv_class) VALUES (?,?,?,?,?)",
                            [(ds_id, v.name_raw, v.slug, v.role, v.dv_class) for v in d.variables])
            con.executemany("INSERT INTO evidence (dataset_id,chunk_index,page_num,snippet) VALUES (?,?,?,?)",
                            [(ds_id, e.chunk_index, e.page_num, e.snippet) for e in d.evidence])
        con.executemany("INSERT INTO review_queue (pass_id,kind,name_raw,doc_id,suggested_slug,snippet) VALUES (?,?,?,?,?,?)",
                        [(pass_id, r.kind, r.name_raw, doc.doc_id, r.suggested_slug, r.snippet) for r in doc.review])
        con.commit()

    def set_doc_status(self, doc_id: str, status: str) -> None:
        self._con.execute("UPDATE documents SET status=? WHERE doc_id=?", (status, doc_id)); self._con.commit()

    def written_tags(self, doc_id: str, pass_id: int, tags: list[str], note_key: str | None) -> None:
        self._con.execute("INSERT INTO zotero_writes (doc_id,pass_id,tags_json,note_key,written_utc) VALUES (?,?,?,?,?)",
                          (doc_id, pass_id, json.dumps(tags), note_key, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        self._con.commit()

    # ---- reads --------------------------------------------------------------
    def docs_in_pass(self, pass_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM documents WHERE pass_id=? ORDER BY doc_id", (pass_id,)).fetchall()

    def datasets_for_doc(self, doc_id: str) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM datasets WHERE doc_id=? ORDER BY id", (doc_id,)).fetchall()

    def variables_for(self, dataset_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM variables WHERE dataset_id=? ORDER BY id", (dataset_id,)).fetchall()

    def evidence_for(self, dataset_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM evidence WHERE dataset_id=? ORDER BY chunk_index", (dataset_id,)).fetchall()

    def open_review(self, pass_id: int | None = None) -> list[sqlite3.Row]:
        if pass_id is None:
            return self._con.execute("SELECT * FROM review_queue WHERE status='open' ORDER BY kind, name_raw").fetchall()
        return self._con.execute("SELECT * FROM review_queue WHERE status='open' AND pass_id=? ORDER BY kind, name_raw", (pass_id,)).fetchall()

    def writes_in_pass(self, pass_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM zotero_writes WHERE pass_id=? ORDER BY id", (pass_id,)).fetchall()

    def query_by_type(self, type_slug: str) -> list[sqlite3.Row]:
        return self._con.execute("""
            SELECT d.doc_id, doc.title, doc.year, d.name_raw, d.src_slug, d.geo_text, d.geo_level, d.period_start, d.period_end,
                   (SELECT group_concat(DISTINCT v.dv_class) FROM variables v WHERE v.dataset_id=d.id AND v.role='dependent') AS dvs
            FROM datasets d JOIN documents doc ON doc.doc_id=d.doc_id
            WHERE d.type_slug=? ORDER BY doc.year, doc.title""", (type_slug,)).fetchall()

    def source_geo_matrix(self) -> list[sqlite3.Row]:
        return self._con.execute("""
            SELECT COALESCE(src_slug, '(unlisted) ' || name_raw) AS src_slug, geo_level, COUNT(DISTINCT doc_id) AS n
            FROM datasets GROUP BY 1, 2 ORDER BY n DESC, 1""").fetchall()

    def topic_crosstab(self, topic_tag: str, doc_tags_lookup) -> list[sqlite3.Row]:
        """doc_tags_lookup(doc_id) -> list[str] of Zotero topic tags (from ChromaReader.doc_meta)."""
        rows = self._con.execute("SELECT DISTINCT doc_id FROM datasets").fetchall()
        keep = [r["doc_id"] for r in rows if topic_tag.lower() in [t.lower() for t in doc_tags_lookup(r["doc_id"])]]
        if not keep:
            return []
        marks = ",".join("?" * len(keep))
        return self._con.execute(f"""
            SELECT COALESCE(src_slug, '(unlisted) ' || name_raw) AS src_slug, type_slug, COUNT(DISTINCT doc_id) AS n
            FROM datasets WHERE doc_id IN ({marks}) GROUP BY 1, 2 ORDER BY n DESC""", keep).fetchall()
```

- [ ] **Step 4: Run tests** → Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/sidecar.py tests/test_data_tag_sidecar.py
git commit -m "feat(ztp-data-tag): sidecar SQLite with pass replacement, write log and cross-tab queries"
```

---

### Task 8: Zotero I/O — `zotero_io.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/zotero_io.py`
- Test: `tests/test_data_tag_zotero.py`

**Interfaces:**
- Consumes: `DocRecord` (Task 6), `NOTE_TITLE`, `MARKER_V2`.
- Produces:
  - `ZoteroItem(key, title, year, tags:list[str])`
  - `enumerate_items(zotero_sqlite:Path, library_id:int, collection_name:str|None) -> list[ZoteroItem]` — non-deleted regular items, sorted by key, with their current tags (read from the local SQLite, read-only+immutable).
  - `resolve_library(spec:str, zotero_sqlite) -> tuple[str lib_type, str api_id, int local_library_id]` — `"user"` → `("user", ZOTERO_USER_ID env, 1)`; `"group:2350352"` → `("group", "2350352", <libraryID from groups table>)`.
  - `check_autosync(prefs_js:Path) -> bool|None` (None = pref absent → Zotero default true).
  - `render_note_html(doc: DocRecord, title:str, pass_id:int, vocab_version:int, model:str) -> str` — spec §7: `<h1>Data (auto-extracted)</h1>`, v1-compatible JSON `<p>`, HTML table, footer.
  - `ZoteroWriterV2(api_key, api_id, lib_type)` with `.upsert_note(item_key, html) -> str note_key`, `.merge_tags(item_key, tags) -> list[str] added`, both with one 412 retry; raises `WriteConflict` on the second 412.

- [ ] **Step 1: Write the failing tests (pyzotero mocked; local SQLite fixture)**

`tests/test_data_tag_zotero.py`:
```python
import sqlite3, json, pytest
from data_tag import zotero_io as zio
from data_tag.normalize import DocRecord, DatasetRecord, Variable, Evidence

def _zot_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INTEGER, libraryID INTEGER, key TEXT);
    CREATE TABLE itemTypes (itemTypeID INTEGER, typeName TEXT);
    CREATE TABLE deletedItems (itemID INTEGER);
    CREATE TABLE fields (fieldID INTEGER, fieldName TEXT);
    CREATE TABLE itemData (itemID INTEGER, fieldID INTEGER, valueID INTEGER);
    CREATE TABLE itemDataValues (valueID INTEGER, value TEXT);
    CREATE TABLE tags (tagID INTEGER, name TEXT);
    CREATE TABLE itemTags (itemID INTEGER, tagID INTEGER, type INTEGER);
    CREATE TABLE collections (collectionID INTEGER, collectionName TEXT, libraryID INTEGER, key TEXT);
    CREATE TABLE collectionItems (collectionID INTEGER, itemID INTEGER);
    CREATE TABLE groups (groupID INTEGER, libraryID INTEGER, name TEXT);
    INSERT INTO itemTypes VALUES (1,'journalArticle'),(2,'attachment'),(3,'note');
    INSERT INTO fields VALUES (1,'title'),(2,'date');
    INSERT INTO groups VALUES (2350352, 3, 'affordable_housing');
    INSERT INTO items VALUES (1,1,3,'BBB'),(2,1,3,'AAA'),(3,2,3,'PDF1'),(4,1,3,'DEL'),(5,1,1,'USR');
    INSERT INTO deletedItems VALUES (4);
    INSERT INTO itemDataValues VALUES (1,'Paper B'),(2,'Paper A'),(3,'2019-03-01');
    INSERT INTO itemData VALUES (1,1,1),(2,1,2),(2,2,3);
    INSERT INTO tags VALUES (1,'data-tagged:v2'),(2,'Housing');
    INSERT INTO itemTags VALUES (1,1,0),(2,2,0);
    INSERT INTO collections VALUES (10,'REE',3,'CK');
    INSERT INTO collectionItems VALUES (10,2);
    """); con.commit(); con.close()

@pytest.fixture
def zdb(tmp_path):
    p = tmp_path / "zotero.sqlite"; _zot_db(p); return p

def test_enumerate_items_sorted_with_tags(zdb):
    items = zio.enumerate_items(zdb, 3, None)
    assert [i.key for i in items] == ["AAA", "BBB"]
    assert items[0].title == "Paper A" and items[0].year == 2019 and items[0].tags == ["Housing"]
    assert items[1].tags == ["data-tagged:v2"]

def test_enumerate_items_by_collection(zdb):
    assert [i.key for i in zio.enumerate_items(zdb, 3, "REE")] == ["AAA"]

def test_resolve_library(zdb, monkeypatch):
    monkeypatch.setenv("ZOTERO_USER_ID", "5848868")
    assert zio.resolve_library("user", zdb) == ("user", "5848868", 1)
    assert zio.resolve_library("group:2350352", zdb) == ("group", "2350352", 3)

def test_check_autosync(tmp_path):
    p = tmp_path / "prefs.js"; p.write_text('user_pref("extensions.zotero.sync.autoSync", false);')
    assert zio.check_autosync(p) is False
    p.write_text('user_pref("x", 1);'); assert zio.check_autosync(p) is None

def _doc():
    ds = DatasetRecord("REcolorado MLS", "REcolorado", "mls", "residential-transactions-mls", "Denver MSA", "metro", ["Denver, CO"],
                       2010, 2019, "sale", "proprietary", 0.95, "merged",
                       [Variable("log sale price", "log-sale-price", "dependent", "house-price"), Variable("sqft", "sqft", "control", None)],
                       [Evidence(17, 6, "snip")])
    return DocRecord("AAA", "ok", [ds])

def test_render_note_html_v1_compatible():
    html = zio.render_note_html(_doc(), "Paper A", 1, 1, "qwen2.5:7b-instruct")
    assert html.startswith("<h1>Data (auto-extracted)</h1>")
    start = html.index("{"); end = html.index("}</p>") + 1
    import html as h; v1 = json.loads(h.unescape(html[start:end]))
    assert v1["datasets"] == ["REcolorado MLS"] and v1["variables"] == ["log sale price", "sqft"]
    assert v1["unit"] == "sale" and v1["timespan"] == "2010-2019" and v1["schema"] == "v2"
    assert "<table>" in html and "<b>log sale price</b>" in html and "p. 6" in html and "pass 1" in html

class FakeZot:
    def __init__(self):
        self.items_db = {"AAA": {"key": "AAA", "version": 5, "data": {"key": "AAA", "version": 5, "tags": [{"tag": "Housing"}]}}}
        self.notes = []; self.updated = []; self.fail_412_once = False
    def item(self, key): return json.loads(json.dumps(self.items_db[key]))
    def children(self, key, itemType=None): return [n for n in self.notes if n["data"]["parentItem"] == key]
    def item_template(self, t): return {"itemType": "note", "note": "", "tags": [], "parentItem": ""}
    def create_items(self, payload):
        n = {"key": f"N{len(self.notes)+1}", "version": 1, "data": {**payload[0], "key": f"N{len(self.notes)+1}", "version": 1}}
        self.notes.append(n); return {"success": {"0": n["key"]}, "failed": {}}
    def update_item(self, item):
        if self.fail_412_once:
            self.fail_412_once = False
            raise zio.PreConditionFailed("412")
        self.updated.append(item); self.items_db[item["key"]] = item if item["key"] in self.items_db else self.items_db.get(item["key"])
        for n in self.notes:
            if n["key"] == item["key"]: n["data"] = item["data"]
        return True

def _writer(fake):
    w = zio.ZoteroWriterV2.__new__(zio.ZoteroWriterV2); w._zot = fake; return w

def test_upsert_note_creates_then_updates():
    fake = FakeZot(); w = _writer(fake)
    k1 = w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v1</p>")
    k2 = w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v2</p>")
    assert k1 == k2 == "N1" and len(fake.notes) == 1 and "v2" in fake.notes[0]["data"]["note"]

def test_merge_tags_adds_only_new_and_retries_412():
    fake = FakeZot(); fake.fail_412_once = True; w = _writer(fake)
    added = w.merge_tags("AAA", ["Housing", "dataset:mls", "data-tagged:v2"])
    assert added == ["data-tagged:v2", "dataset:mls"]
    assert sorted(t["tag"] for t in fake.updated[-1]["data"]["tags"]) == ["Housing", "data-tagged:v2", "dataset:mls"]

def test_merge_tags_second_412_raises():
    fake = FakeZot(); w = _writer(fake)
    def always(_): raise zio.PreConditionFailed("412")
    fake.update_item = always
    with pytest.raises(zio.WriteConflict):
        w.merge_tags("AAA", ["x"])
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.zotero_io`.

- [ ] **Step 3: Write `zotero_io.py`**

```python
"""Zotero side: enumerate items from the local SQLite (read-only); write notes/tags via pyzotero."""
from __future__ import annotations
import html as html_mod
import json, os, re, sqlite3
from dataclasses import dataclass
from pathlib import Path
from pyzotero import zotero
from pyzotero.zotero_errors import PreConditionFailed  # HTTP 412
from . import NOTE_TITLE
from .normalize import DocRecord

DEFAULT_ZOTERO_SQLITE = Path("/Users/andrew.mueller/Library/CloudStorage/OneDrive-UniversityofDenver/Zotero/zotero.sqlite")
DEFAULT_PREFS = next(iter(Path.home().glob("Library/Application Support/Zotero/Profiles/*/prefs.js")), None)


class WriteConflict(RuntimeError):
    pass


@dataclass
class ZoteroItem:
    key: str
    title: str
    year: int | None
    tags: list[str]


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def resolve_library(spec: str, zotero_sqlite: Path = DEFAULT_ZOTERO_SQLITE) -> tuple[str, str, int]:
    if spec == "user":
        user_id = os.environ.get("ZOTERO_USER_ID")
        if not user_id:
            raise RuntimeError("ZOTERO_USER_ID not set (source ~/.secrets.env)")
        return "user", user_id, 1
    m = re.fullmatch(r"group:(\d+)", spec)
    if not m:
        raise ValueError(f"library spec must be 'user' or 'group:<groupID>', got {spec!r}")
    con = _ro(zotero_sqlite)
    row = con.execute("SELECT libraryID FROM groups WHERE groupID=?", (int(m.group(1)),)).fetchone()
    con.close()
    if not row:
        raise ValueError(f"group {m.group(1)} not in local Zotero database")
    return "group", m.group(1), int(row[0])


def enumerate_items(zotero_sqlite: Path, library_id: int, collection_name: str | None) -> list[ZoteroItem]:
    con = _ro(zotero_sqlite)
    sql = """
    SELECT i.itemID, i.key,
      (SELECT v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID
         WHERE d.itemID=i.itemID AND f.fieldName='title') AS title,
      (SELECT v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID
         WHERE d.itemID=i.itemID AND f.fieldName='date') AS date
    FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID
    WHERE i.libraryID=? AND t.typeName NOT IN ('attachment','note','annotation')
      AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
    """
    params: list = [library_id]
    if collection_name:
        sql += " AND i.itemID IN (SELECT ci.itemID FROM collectionItems ci JOIN collections c ON c.collectionID=ci.collectionID WHERE c.libraryID=? AND c.collectionName=?)"
        params += [library_id, collection_name]
    sql += " ORDER BY i.key"
    items = []
    for item_id, key, title, date in con.execute(sql, params):
        tags = [r[0] for r in con.execute("SELECT t.name FROM itemTags it JOIN tags t ON t.tagID=it.tagID WHERE it.itemID=? ORDER BY t.name", (item_id,))]
        year = int(date[:4]) if date and date[:4].isdigit() else None
        items.append(ZoteroItem(key, title or "", year, tags))
    con.close()
    return items


def check_autosync(prefs_js: Path | None = DEFAULT_PREFS) -> bool | None:
    if not prefs_js or not Path(prefs_js).exists():
        return None
    m = re.search(r'"extensions\.zotero\.sync\.autoSync",\s*(true|false)', Path(prefs_js).read_text())
    return None if not m else m.group(1) == "true"


def _v1_json(doc: DocRecord) -> dict:
    names = [d.name_raw for d in doc.datasets]
    variables = [v.name_raw for d in doc.datasets for v in d.variables]
    units = sorted({d.unit for d in doc.datasets if d.unit})
    years = [y for d in doc.datasets for y in (d.period_start, d.period_end) if y]
    access = sorted({d.access for d in doc.datasets if d.access})
    return {"datasets": names, "variables": variables, "unit": "; ".join(units),
            "timespan": f"{min(years)}-{max(years)}" if years else "", "access": "; ".join(access),
            "source": "full-text", "schema": "v2"}


def render_note_html(doc: DocRecord, title: str, pass_id: int, vocab_version: int, model: str) -> str:
    esc = html_mod.escape
    parts = [f"<h1>{esc(NOTE_TITLE)}</h1>", f"<p>{esc(json.dumps(_v1_json(doc)))}</p>",
             "<table><tr><th>Dataset</th><th>Type</th><th>Geography</th><th>Period</th><th>Variables</th><th>Pages</th></tr>"]
    for d in doc.datasets:
        period = "–".join(str(y) for y in (d.period_start, d.period_end) if y) or "?"
        geo = esc(d.geo_text or "") + (f" ({d.geo_level})" if d.geo_level else "")
        variables = ", ".join(f"<b>{esc(v.name_raw)}</b>" if v.role == "dependent" else esc(v.name_raw) for v in d.variables)
        pages = ", ".join(f"p. {e.page_num}" if e.page_num is not None else f"chunk {e.chunk_index}" for e in d.evidence)
        name = esc(d.name_raw) + (f" <code>{d.src_slug}</code>" if d.src_slug else " <i>(unlisted)</i>")
        parts.append(f"<tr><td>{name}</td><td>{esc(d.type_slug)}</td><td>{geo}</td><td>{period}</td><td>{variables}</td><td>{pages}</td></tr>")
    parts.append("</table>")
    chunk_ids = ", ".join(str(e.chunk_index) for d in doc.datasets for e in d.evidence)
    parts.append(f"<p><small>ztp-data-tag v2 · pass {pass_id} · vocab v{vocab_version} · {esc(model)} · chunks {chunk_ids} · {esc(title)}</small></p>")
    return "".join(parts)


class ZoteroWriterV2:
    def __init__(self, api_key: str, api_id: str, lib_type: str):
        self._zot = zotero.Zotero(api_id, lib_type, api_key)

    def _update_with_retry(self, fetch, mutate) -> dict:
        item = fetch()
        mutate(item)
        try:
            self._zot.update_item(item); return item
        except PreConditionFailed:
            item = fetch(); mutate(item)
            try:
                self._zot.update_item(item); return item
            except PreConditionFailed as exc:
                raise WriteConflict(f"412 twice on {item.get('key')}") from exc

    def _find_note(self, item_key: str) -> dict | None:
        for child in self._zot.children(item_key, itemType="note"):
            if f"<h1>{NOTE_TITLE}</h1>" in (child.get("data") or {}).get("note", ""):
                return child
        return None

    def upsert_note(self, item_key: str, note_html: str) -> str:
        existing = self._find_note(item_key)
        if existing:
            def mutate(n): n["data"]["note"] = note_html
            self._update_with_retry(lambda: self._zot.item(existing["key"]), mutate)
            return existing["key"]
        template = self._zot.item_template("note")
        self._zot.url_params = None
        template["parentItem"], template["note"], template["tags"] = item_key, note_html, []
        result = self._zot.create_items([template])
        if not result.get("success"):
            raise RuntimeError(f"note create failed: {result}")
        return list(result["success"].values())[0]

    def merge_tags(self, item_key: str, tags: list[str]) -> list[str]:
        added: list[str] = []
        def mutate(item):
            existing = {t["tag"] for t in item["data"].get("tags", [])}
            added[:] = sorted(set(tags) - existing)
            item["data"]["tags"] = [{"tag": t} for t in sorted(existing | set(tags))]
        self._update_with_retry(lambda: self._zot.item(item_key), mutate)
        return added
```

- [ ] **Step 4: Run tests** → Expected: 9 passed. If `pyzotero.zotero_errors.PreConditionFailed` does not exist in 1.13.1, check `micromamba run -n zotpilot python -c "import pyzotero.zotero_errors as e; print([n for n in dir(e) if 'Pre' in n or '412' in n])"` and import the name it prints.

- [ ] **Step 5: Smoke the read side on the real group library**

```bash
micromamba run -n zotpilot python -c "
import sys; sys.path.insert(0,'skills/ztp-data-tag/scripts')
from data_tag.zotero_io import *
print(resolve_library('group:2350352')); it=enumerate_items(DEFAULT_ZOTERO_SQLITE, 3, None); print(len(it), it[0]); print('autosync:', check_autosync())"
```
Expected: `('group', '2350352', 3)`, 59 items, first key `2C9XFEWY`, autosync `None` or `True`.

- [ ] **Step 6: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/zotero_io.py tests/test_data_tag_zotero.py
git commit -m "feat(ztp-data-tag): Zotero enumeration (local SQLite) and pyzotero note upsert / tag merge with 412 retry"
```

---

### Task 9: Pass report — `report.py`

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/report.py`
- Test: `tests/test_data_tag_report.py`

**Interfaces:**
- Consumes: `Sidecar` (Task 7), `Vocab`.
- Produces: `render_pass_report(sidecar, pass_id, vocab, diagnostics: dict[doc_id, dict(best_score:int, n_candidates:int, words:int, grep_only:list[str], llm_only:list[str], wall_s:float)]) -> str`; `write_pass_report(markdown, out_dir:Path, pass_id) -> Path` (`out_dir/pass_NN.md`).

- [ ] **Step 1: Write the failing test**

`tests/test_data_tag_report.py`:
```python
from data_tag.sidecar import Sidecar
from data_tag.vocab import Vocab
from data_tag.report import render_pass_report, write_pass_report
from data_tag.normalize import DocRecord, DatasetRecord, Variable, Evidence, ReviewItem

def test_report_sections(tmp_path):
    sc = Sidecar(tmp_path / "s.sqlite"); v = Vocab.load()
    sc.begin_pass(1, "group:2350352", None, 1, "qwen2.5:7b-instruct", 2)
    ds = DatasetRecord("REcolorado MLS", None, "mls", "residential-transactions-mls", "Denver MSA", "metro", [], 2010, 2019,
                       "sale", None, 0.95, "merged", [Variable("log sale price", "log-sale-price", "dependent", "house-price")], [Evidence(17, 6, "s")])
    sc.write_doc(DocRecord("AAA", "ok", [ds], [ReviewItem("source", "Denver Water", "denver-water", "snip")]), 1, "Paper A", 2020, "3")
    sc.write_doc(DocRecord("BBB", "model_error"), 1, "Paper B", 2021, "3")
    diag = {"AAA": {"best_score": 9, "n_candidates": 20, "words": 1800, "grep_only": ["fema_nfhl"], "llm_only": [], "wall_s": 12.5},
            "BBB": {"best_score": 3, "n_candidates": 12, "words": 900, "grep_only": [], "llm_only": [], "wall_s": 0}}
    md = render_pass_report(sc, 1, v, diag)
    for needle in ["# ztp-data-tag pass 1", "processed: 2", "model_error: 1", "| Paper A |", "`mls`", "metro", "2010–2019", "house-price", "p. 6",
                   "## Review queue", "Denver Water", "## Grep vs model", "fema_nfhl", "## Candidate selection", "Paper B", "best score 3",
                   "## Proposed vocabulary diff", "denver-water"]:
        assert needle in md, needle
    out = write_pass_report(md, tmp_path / "qr", 1)
    assert out.name == "pass_01.md" and out.read_text() == md
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.report`.

- [ ] **Step 3: Write `report.py`**

```python
"""Render the per-pass Markdown report — the only thing Claude reads between passes."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from .sidecar import Sidecar
from .vocab import Vocab


def _period(row) -> str:
    years = [y for y in (row["period_start"], row["period_end"]) if y]
    return "–".join(str(y) for y in years) if years else "?"


def render_pass_report(sidecar: Sidecar, pass_id: int, vocab: Vocab, diagnostics: dict) -> str:
    pass_row = next(p for p in sidecar.passes() if p["pass_id"] == pass_id)
    docs = sidecar.docs_in_pass(pass_id)
    status_counts = Counter(d["status"] for d in docs)
    wall = sum(diag.get("wall_s", 0) for diag in diagnostics.values())
    lines = [f"# ztp-data-tag pass {pass_id}", "",
             f"- library: `{pass_row['library']}` · collection: `{pass_row['collection'] or 'all'}` · vocab v{pass_row['vocab_version']} · model `{pass_row['model']}` · started {pass_row['started_utc']}",
             f"- processed: {len(docs)} · " + " · ".join(f"{k}: {n}" for k, n in sorted(status_counts.items())) + f" · wall {wall:.0f}s", "",
             "## Per paper", "", "| Paper | Dataset | Type | Geography | Period | DVs | Pages | Status |", "|---|---|---|---|---|---|---|---|"]
    for d in docs:
        datasets = sidecar.datasets_for_doc(d["doc_id"])
        if not datasets:
            lines.append(f"| {d['title']} | — | | | | | | {d['status']} |"); continue
        for ds in datasets:
            dvs = ", ".join(sorted({v["dv_class"] or v["slug"] for v in sidecar.variables_for(ds["id"]) if v["role"] == "dependent"}))
            pages = ", ".join(f"p. {e['page_num']}" if e["page_num"] is not None else f"c{e['chunk_index']}" for e in sidecar.evidence_for(ds["id"]))
            name = f"`{ds['src_slug']}`" if ds["src_slug"] else f"*{ds['name_raw']}* (unlisted)"
            geo = f"{ds['geo_text'] or ''} ({ds['geo_level']})" if ds["geo_level"] else (ds["geo_text"] or "?")
            lines.append(f"| {d['title']} | {name} | {ds['type_slug']} | {geo} | {_period(ds)} | {dvs} | {pages} | {d['status']} |")
    lines += ["", "## Review queue", ""]
    review = sidecar.open_review(pass_id)
    if not review:
        lines.append("_empty_")
    for r in review:
        lines.append(f"- **{r['kind']}** `{r['name_raw']}` → suggested `{r['suggested_slug']}` — {r['doc_id']}: {r['snippet'][:160]}")
    lines += ["", "## Grep vs model", ""]
    for d in docs:
        diag = diagnostics.get(d["doc_id"], {})
        if diag.get("grep_only") or diag.get("llm_only"):
            lines.append(f"- {d['title']}: grep-only {diag.get('grep_only', [])} (candidate false positives) · model-only {diag.get('llm_only', [])} (candidate aliases)")
    lines += ["", "## Candidate selection", ""]
    for d in docs:
        diag = diagnostics.get(d["doc_id"], {})
        flag = " ⚠ heading regex missed" if diag.get("best_score", 0) < 5 else ""
        lines.append(f"- {d['title']}: best score {diag.get('best_score', '?')} · {diag.get('n_candidates', '?')} chunks · {diag.get('words', '?')} words · {diag.get('wall_s', 0):.0f}s{flag}")
    lines += ["", "## Proposed vocabulary diff", "", "```yaml", "# promote from review queue (edit aliases/type/geo before applying):"]
    for r in review:
        if r["kind"] == "source":
            lines.append(f"  {r['suggested_slug']}: {{name: {r['name_raw']}, aliases: ['\\\\b{r['name_raw']}\\\\b'], type: other, geo_level: national, access: unknown}}")
        else:
            lines.append(f"  # dv_class needle for '{r['name_raw']}' (doc {r['doc_id']})")
    lines += ["```", ""]
    return "\n".join(lines)


def write_pass_report(markdown: str, out_dir: Path, pass_id: int) -> Path:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pass_{pass_id:02d}.md"
    out.write_text(markdown)
    return out
```

- [ ] **Step 4: Run tests** → Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ztp-data-tag/scripts/data_tag/report.py tests/test_data_tag_report.py
git commit -m "feat(ztp-data-tag): per-pass Markdown report with review queue and vocabulary diff"
```

---

### Task 10: CLI — `cli.py` (`run`, `undo`, `query`) + dry-run integration

**Files:**
- Create: `skills/ztp-data-tag/scripts/data_tag/cli.py`
- Test: `tests/test_data_tag_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 2–9.
- Produces: `main(argv=None) -> int`; `run_pass(args, *, chroma, sidecar, vocab, client, writer_factory) -> dict summary` (dependency-injected for tests); subcommands:
  - `run --library user|group:<id> [--collection NAME] --pass N [--n 15] [--dry-run] [--refresh-v2] [--report-dir DIR] [--chroma PATH] [--zotero-sqlite PATH] [--sidecar PATH]`
  - `undo --pass N [--yes]` — removes, per `zotero_writes` row, the tags that pass **added** (`tags_json`) and restores the note to the previous pass's render if one exists, else deletes the note; prints what it will do and stops unless `--yes`.
  - `query type <type_slug> | matrix | topic <tag>` — prints a Markdown table from the sidecar.

- [ ] **Step 1: Write the failing tests (end-to-end with fakes; no network, no Zotero)**

`tests/test_data_tag_cli.py`:
```python
import json, sqlite3, pytest
from pathlib import Path
from data_tag import cli
from data_tag.chroma import ChromaReader
from data_tag.sidecar import Sidecar
from data_tag.vocab import Vocab
from test_data_tag_chroma import _make_db as make_chroma
from test_data_tag_zotero import _zot_db as make_zot

class FakeClient:
    def __init__(self): self.calls = 0
    def check_ready(self): pass
    def extract(self, candidates, hits, vocab):
        self.calls += 1
        return ({"datasets": [{"name": "CoStar", "provider": "CoStar Group", "type": "commercial-property",
                 "geography": {"text": "United States", "level": "national", "places": []}, "period": {"start": 2010, "end": 2019},
                 "unit_of_observation": "property", "access": "proprietary",
                 "variables": [{"name": "asking rent", "role": "dependent"}], "evidence_chunks": [candidates[-1].chunk_index]}],
                 "notes": ""}, [])

class FakeWriter:
    def __init__(self): self.notes = {}; self.tags = {}
    def upsert_note(self, key, html): self.notes[key] = html; return "NOTE-" + key
    def merge_tags(self, key, tags): self.tags[key] = tags; return tags

@pytest.fixture
def env(tmp_path, monkeypatch):
    chroma = tmp_path / "chroma.sqlite3"; make_chroma(chroma)
    zot = tmp_path / "zotero.sqlite"; make_zot(zot)
    monkeypatch.setenv("ZOTERO_API_KEY", "k"); monkeypatch.setenv("ZOTERO_USER_ID", "1")
    return dict(chroma=chroma, zot=zot, sidecar=tmp_path / "sc.sqlite", report=tmp_path / "qr")

def _args(env, extra=()):
    return ["run", "--library", "group:2350352", "--pass", "1", "--n", "15", "--chroma", str(env["chroma"]),
            "--zotero-sqlite", str(env["zot"]), "--sidecar", str(env["sidecar"]), "--report-dir", str(env["report"]), *extra]

def test_dry_run_writes_sidecar_and_report_not_zotero(env):
    client, writer = FakeClient(), FakeWriter()
    summary = cli.main(_args(env, ["--dry-run"]), client=client, writer_factory=lambda *a: writer)
    # AAA is indexed (chunks in chroma) and untagged; BBB carries data-tagged:v2 → skipped; AAA only processed
    assert summary["processed"] == ["AAA"] and summary["skipped_v2"] == ["BBB"] and summary["unindexed"] == []
    assert client.calls == 1 and writer.notes == {} and writer.tags == {}
    sc = Sidecar(env["sidecar"]); ds = sc.datasets_for_doc("AAA")
    assert ds[0]["src_slug"] == "costar" and ds[0]["source"] == "merged"
    assert (env["report"] / "pass_01.md").exists()

def test_live_run_writes_note_then_tags(env):
    writer = FakeWriter()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    assert "AAA" in writer.notes and "<h1>Data (auto-extracted)</h1>" in writer.notes["AAA"]
    assert "data-tagged:v2" in writer.tags["AAA"] and "dataset:costar" in writer.tags["AAA"] and "dv:rent" in writer.tags["AAA"]
    sc = Sidecar(env["sidecar"]); w = sc.writes_in_pass(1); assert w[0]["note_key"] == "NOTE-AAA"

def test_refresh_v2_reprocesses(env):
    writer = FakeWriter()
    summary = cli.main(_args(env, ["--refresh-v2", "--dry-run"]), client=FakeClient(), writer_factory=lambda *a: writer)
    assert "BBB" in summary["processed"] or "BBB" in summary["unindexed"]  # BBB has 1 chunk in fixture → processed

def test_model_error_keeps_grep_rows(env):
    class Boom(FakeClient):
        def extract(self, *a): from data_tag.extract import OllamaError; raise OllamaError("x")
    cli.main(_args(env, ["--dry-run"]), client=Boom(), writer_factory=lambda *a: FakeWriter())
    sc = Sidecar(env["sidecar"]); doc = sc.docs_in_pass(1)[0]
    assert doc["status"] == "model_error" and sc.datasets_for_doc("AAA")[0]["source"] == "grep"

def test_query_type_prints_table(env, capsys):
    cli.main(_args(env, ["--dry-run"]), client=FakeClient(), writer_factory=lambda *a: FakeWriter())
    cli.main(["query", "type", "commercial-property", "--sidecar", str(env["sidecar"])])
    out = capsys.readouterr().out; assert "T AAA" in out and "national" in out and "rent" in out

def test_undo_requires_yes_and_removes_added_tags(env):
    class RecordingWriter(FakeWriter):
        def __init__(self): super().__init__(); self.removed = []; self.deleted_notes = []
        def remove_tags(self, key, tags): self.removed.append((key, tags))
        def delete_note(self, note_key): self.deleted_notes.append(note_key)
    writer = RecordingWriter()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    cli.main(["undo", "--pass", "1", "--sidecar", str(env["sidecar"]), "--zotero-sqlite", str(env["zot"]), "--library", "group:2350352"], writer_factory=lambda *a: writer)
    assert writer.removed == []  # no --yes → dry preview only
    cli.main(["undo", "--pass", "1", "--yes", "--sidecar", str(env["sidecar"]), "--zotero-sqlite", str(env["zot"]), "--library", "group:2350352"], writer_factory=lambda *a: writer)
    assert writer.removed and "dataset:costar" in writer.removed[0][1] and writer.deleted_notes == ["NOTE-AAA"]
```

- [ ] **Step 2: Run to verify failure** → `ModuleNotFoundError: data_tag.cli`.

- [ ] **Step 3: Add `remove_tags` / `delete_note` to `ZoteroWriterV2` (Task 8 file)**

Append inside the class in `zotero_io.py`:
```python
    def remove_tags(self, item_key: str, tags: list[str]) -> None:
        def mutate(item):
            drop = set(tags)
            item["data"]["tags"] = [t for t in item["data"].get("tags", []) if t["tag"] not in drop]
        self._update_with_retry(lambda: self._zot.item(item_key), mutate)

    def delete_note(self, note_key: str) -> None:
        note = self._zot.item(note_key)
        if (note.get("data") or {}).get("itemType") != "note":
            raise RuntimeError(f"{note_key} is not a note; refusing to delete")
        self._zot.delete_item(note)
```

- [ ] **Step 4: Write `cli.py`**

```python
"""CLI: run a pass, undo a pass, query the sidecar."""
from __future__ import annotations
import argparse, os, sys, time
from pathlib import Path
from . import MARKER_V2, MODEL, OLLAMA_URL
from .candidates import score_chunk, select_candidates
from .chroma import DEFAULT_CHROMA, ChromaReader
from .extract import OllamaClient, OllamaError
from .normalize import DocRecord, build_records, tags_for
from .report import render_pass_report, write_pass_report
from .sidecar import DEFAULT_SIDECAR, Sidecar
from .vocab import Vocab
from .zotero_io import (DEFAULT_ZOTERO_SQLITE, WriteConflict, ZoteroWriterV2, check_autosync,
                        enumerate_items, render_note_html, resolve_library)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="data_tag")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    common.add_argument("--zotero-sqlite", type=Path, default=DEFAULT_ZOTERO_SQLITE)
    common.add_argument("--library", default="user", help="'user' or 'group:<groupID>'")
    run = sub.add_parser("run", parents=[common])
    run.add_argument("--collection"); run.add_argument("--pass", dest="pass_id", type=int, required=True)
    run.add_argument("--n", type=int, default=15, help="0 = all remaining"); run.add_argument("--dry-run", action="store_true")
    run.add_argument("--refresh-v2", action="store_true", help="reprocess items already carrying data-tagged:v2")
    run.add_argument("--report-dir", type=Path, default=Path("quality_reports/data_tags"))
    run.add_argument("--chroma", type=Path, default=DEFAULT_CHROMA); run.add_argument("--vocab", type=Path)
    run.add_argument("--model", default=os.environ.get("DATA_TAG_MODEL", MODEL))
    undo = sub.add_parser("undo", parents=[common]); undo.add_argument("--pass", dest="pass_id", type=int, required=True)
    undo.add_argument("--yes", action="store_true")
    q = sub.add_parser("query", parents=[common]); q.add_argument("what", choices=["type", "matrix", "topic"]); q.add_argument("value", nargs="?")
    q.add_argument("--chroma", type=Path, default=DEFAULT_CHROMA)
    return p


def _writer_from_env(lib_type: str, api_id: str) -> ZoteroWriterV2:
    key = os.environ.get("ZOTERO_API_KEY")
    if not key:
        raise RuntimeError("ZOTERO_API_KEY not set (source ~/.secrets.env)")
    return ZoteroWriterV2(key, api_id, lib_type)


def run_pass(args, *, chroma: ChromaReader, sidecar: Sidecar, vocab: Vocab, client, writer_factory) -> dict:
    lib_type, api_id, local_lib = resolve_library(args.library, args.zotero_sqlite)
    items = enumerate_items(args.zotero_sqlite, local_lib, args.collection)
    skipped_v2 = [i.key for i in items if MARKER_V2 in i.tags and not args.refresh_v2]
    todo = [i for i in items if i.key not in skipped_v2]
    indexed = chroma.indexed_doc_ids([i.key for i in todo])
    unindexed = [i.key for i in todo if i.key not in indexed]
    todo = [i for i in todo if i.key in indexed]
    if args.n:
        todo = todo[:args.n]
    client.check_ready()
    if not args.dry_run and check_autosync() is False:
        print("WARNING: Zotero auto-sync is off — writes will not appear in desktop Zotero until you sync.", file=sys.stderr)
    writer = None if args.dry_run else writer_factory(lib_type, api_id)
    sidecar.begin_pass(args.pass_id, args.library, args.collection, vocab.version, args.model, len(todo))
    diagnostics: dict[str, dict] = {}
    processed: list[str] = []
    for item in todo:
        t0 = time.time()
        chunks = chroma.chunks_for_doc(item.key)
        candidates = select_candidates(chunks, vocab)
        grep_hits = {c.chunk_index: vocab.match_sources(c.text) for c in chunks}
        grep_hits = {k: v for k, v in grep_hits.items() if v}
        hint_slugs = sorted({h.slug for hits in grep_hits.values() for h in hits})
        status_override = None
        try:
            llm_out, dropped = client.extract(candidates, hint_slugs, vocab) if candidates else ({"datasets": [], "notes": ""}, [])
        except OllamaError as exc:
            llm_out, dropped, status_override = {"datasets": [], "notes": ""}, [f"model_error: {exc}"], "model_error"
        doc = build_records(item.key, chunks, candidates, grep_hits, llm_out, dropped, vocab)
        if status_override:
            doc.status = status_override
        sidecar.write_doc(doc, args.pass_id, item.title, item.year, str(local_lib))
        llm_slugs = {d.src_slug for d in doc.datasets if d.source in ("llm", "merged") and d.src_slug}
        diagnostics[item.key] = {"best_score": max((score_chunk(c, vocab).score for c in chunks), default=0),
                                 "n_candidates": len(candidates), "words": sum(len(c.text.split()) for c in candidates),
                                 "grep_only": sorted(set(hint_slugs) - llm_slugs), "llm_only": sorted(llm_slugs - set(hint_slugs)),
                                 "wall_s": time.time() - t0}
        if writer is not None and doc.status in ("ok", "model_error") and doc.datasets:
            try:
                note_key = writer.upsert_note(item.key, render_note_html(doc, item.title, args.pass_id, vocab.version, args.model))
                added = writer.merge_tags(item.key, tags_for(doc))
                sidecar.written_tags(item.key, args.pass_id, added, note_key)
            except WriteConflict as exc:
                sidecar.set_doc_status(item.key, "write_conflict"); print(f"write conflict {item.key}: {exc}", file=sys.stderr)
        processed.append(item.key)
    report = render_pass_report(sidecar, args.pass_id, vocab, diagnostics)
    out = write_pass_report(report, args.report_dir, args.pass_id)
    print(f"pass {args.pass_id}: {len(processed)} processed, {len(skipped_v2)} skipped (v2), {len(unindexed)} unindexed → {out}")
    return {"processed": processed, "skipped_v2": skipped_v2, "unindexed": unindexed, "report": str(out)}


def undo_pass(args, *, sidecar: Sidecar, writer_factory) -> int:
    lib_type, api_id, _ = resolve_library(args.library, args.zotero_sqlite)
    writes = sidecar.writes_in_pass(args.pass_id)
    if not writes:
        print(f"pass {args.pass_id}: nothing was written to Zotero"); return 0
    import json
    for w in writes:
        print(f"{w['doc_id']}: remove {json.loads(w['tags_json'])}; delete note {w['note_key']}")
    if not args.yes:
        print("dry preview — re-run with --yes to apply"); return 0
    writer = writer_factory(lib_type, api_id)
    for w in writes:
        writer.remove_tags(w["doc_id"], json.loads(w["tags_json"]))
        if w["note_key"]:
            writer.delete_note(w["note_key"])
        sidecar.set_doc_status(w["doc_id"], "undone")
    print(f"pass {args.pass_id}: undone {len(writes)} items"); return 0


def _print_rows(rows, cols) -> None:
    print("| " + " | ".join(cols) + " |"); print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |")


def query(args, *, sidecar: Sidecar, chroma_factory) -> int:
    if args.what == "type":
        _print_rows(sidecar.query_by_type(args.value), ["title", "year", "name_raw", "src_slug", "geo_text", "geo_level", "period_start", "period_end", "dvs"])
    elif args.what == "matrix":
        _print_rows(sidecar.source_geo_matrix(), ["src_slug", "geo_level", "n"])
    else:
        chroma = chroma_factory()
        _print_rows(sidecar.topic_crosstab(args.value, lambda d: chroma.doc_meta(d)["tags"]), ["src_slug", "type_slug", "n"])
    return 0


def main(argv=None, *, client=None, writer_factory=None):
    args = _parser().parse_args(argv)
    sidecar = Sidecar(args.sidecar)
    writer_factory = writer_factory or _writer_from_env
    if args.cmd == "run":
        vocab = Vocab.load(args.vocab)
        client = client or OllamaClient(OLLAMA_URL, args.model)
        return run_pass(args, chroma=ChromaReader(args.chroma), sidecar=sidecar, vocab=vocab, client=client, writer_factory=writer_factory)
    if args.cmd == "undo":
        return undo_pass(args, sidecar=sidecar, writer_factory=writer_factory)
    return query(args, sidecar=sidecar, chroma_factory=lambda: ChromaReader(args.chroma))
```

- [ ] **Step 5: Run the whole suite**

Run: `micromamba run -n zotpilot python -m pytest tests/test_data_tag_*.py -q`
Expected: all pass. (`main` returns the summary dict for `run`, 0 for others — tests rely on that; the `data_tag.py` entry wraps it with `sys.exit(0 if isinstance(r, dict) else r)` — update the entry file accordingly.)

- [ ] **Step 6: Real dry run on 3 known papers (no Zotero writes; Ollama up)**

```bash
source ~/.secrets.env
micromamba run -n zotpilot python skills/ztp-data-tag/scripts/data_tag.py run --library group:2350352 --pass 0 --n 3 --dry-run --report-dir /tmp/dt_smoke 2>&1 | tail -5
sed -n 1,40p /tmp/dt_smoke/pass_00.md
```
Expected: 3 processed; the per-paper table names at least one plausible dataset per paper with geography and a DV. Pass 0 is a scratch pass — `begin_pass(0, …)` replaces it on every smoke run.

- [ ] **Step 7: Commit**

```bash
git add skills/ztp-data-tag/scripts tests/test_data_tag_cli.py
git commit -m "feat(ztp-data-tag): CLI run/undo/query with dry-run and end-to-end tests"
```

---

### Task 11: Rewrite `SKILL.md`, update README, check the skill contract

**Files:**
- Modify: `skills/ztp-data-tag/SKILL.md` (full replacement), `README.md:558-561` and `README.md:590`
- Test: existing `tests/test_skill_contracts.py`, `tests/test_allowed_tools.py` (they lint every `skills/*/SKILL.md`)

- [ ] **Step 1: Replace `skills/ztp-data-tag/SKILL.md` with this content**

````markdown
---
name: ztp-data-tag
description: >
  Tag Zotero papers with the datasets they use (source, type, geography, period, variables, dependent variables, evidence page) using SQL grep over ChromaDB plus a local Ollama model — no Claude tokens per paper. Use for "tag my library with datasets", "what data do my papers use", "which papers use MLS data and where". Runs 15-paper passes, one collection at a time; Claude only reads the pass report and tunes the vocabulary.
argument-hint: "[--library user|group:<id>] [--collection NAME] [--pass N] [--yes]"
allowed-tools: Read, Edit, Bash
---

# ztp-data-tag v2 — local, grep-first dataset/variable tagging

Spec: `docs/superpowers/specs/2026-10-07-ztp-data-tag-v2-design.md` (research-claude).
Code: `scripts/data_tag.py` beside this file (package `scripts/data_tag/`), run with the
`zotpilot` micromamba env. Nothing here calls the ZotPilot MCP tools; the script reads the
Chroma and Zotero SQLite files read-only and writes Zotero through pyzotero.

## What a pass does

For each of N papers: select data/variable chunks from Chroma → regex grep against
`scripts/data_vocab.yaml` → one `qwen2.5:7b-instruct` call → merge → write the sidecar
(`~/.local/share/zotpilot/data_tags.sqlite`) → write Zotero tags + one "Data (auto-extracted)"
note → render `quality_reports/data_tags/pass_NN.md`.

Tags written: `dataset:<slug>` (vocabulary sources only), `datatype:<type>`, `geo:<level>`,
`var:<slug>`, `dv:<class>`, `data-tagged`, `data-tagged:v2`. Geography detail, periods and
evidence pages live in the sidecar and the note.

## Preconditions (stop with the fix if unmet)

1. `source ~/.secrets.env` in the shell you run from — `ZOTERO_API_KEY`, `ZOTERO_USER_ID`.
2. Ollama up with the model: `curl -s localhost:11434/api/tags | grep -q qwen2.5:7b-instruct`
   — else `open -a Ollama`, `ollama pull qwen2.5:7b-instruct` (see `/ztp-ollama`).
3. Papers indexed in Chroma. Unindexed items are listed in the report; index them with
   `mcp__zotpilot__index_library` (Ollama must be up) and include them in a later pass.

## Step 1 — Dry run (always first on a new collection or after a vocabulary change)

```bash
micromamba run -n zotpilot python .claude/skills/ztp-data-tag/scripts/data_tag.py run \
  --library group:2350352 --pass <N> --n 15 --dry-run
```
Read `quality_reports/data_tags/pass_NN.md` **in full**. Check the per-paper table against
2–3 papers the user knows. The sidecar is written even in dry-run (pass rows are replaced on
re-run); Zotero is not touched.

## Step 2 — **USER_REQUIRED**: approve the live run

Show the user the per-paper table and the review queue. Ask for an explicit yes before any
non-dry run. `--yes` in the skill invocation counts as that yes for the current pass only.

## Step 3 — Live run

Same command without `--dry-run`. Notes are written before tags; `data-tagged:v2` is the
idempotency marker — items carrying it are skipped on later passes (`--refresh-v2` forces
reprocessing). v1 items (`data-tagged` without `:v2`) are reprocessed and their note updated
in place.

## Step 4 — Tune between passes (this is where Claude tokens go)

From the report: (a) **Review queue** — promote real sources into `data_vocab.yaml` `sources`
(slug, name, regex aliases, type, geo_level, access) and DV needles into `dv_classes`;
(b) **Grep vs model** — model-only slugs need an alias, grep-only slugs may be false positives
(tighten the regex); (c) **Candidate selection** — papers flagged "heading regex missed" need a
`HEADING_RE` extension in `scripts/data_tag/candidates.py` *and* a positive case in
`tests/test_data_tag_candidates.py`. Bump `version:` in the YAML. Run
`micromamba run -n zotpilot python -m pytest tests/test_data_tag_*.py -q` in research-claude,
commit, then run the next pass with `--pass N+1`. Promotions are a **USER_REQUIRED** gate:
list them, wait for yes.

## Queries (sidecar; no Zotero needed)

```bash
micromamba run -n zotpilot python .claude/skills/ztp-data-tag/scripts/data_tag.py query type residential-transactions-mls
micromamba run -n zotpilot python .claude/skills/ztp-data-tag/scripts/data_tag.py query matrix
micromamba run -n zotpilot python .claude/skills/ztp-data-tag/scripts/data_tag.py query topic "Housing rental yield"
```

## Undo

`data_tag.py undo --pass N` previews; `--yes` removes the tags that pass **added** and deletes
the notes it wrote, using the sidecar's write log. Tags that existed before the pass are untouched.

## Whole-library run (only after the user says so)

`--library user --n 0 --pass N` processes every remaining indexed item; resumable via the
marker. Expect hours on local hardware; run it in a terminal tab, not inside a Claude turn.

## Rules

- Never call `manage_tags(action="set")` or any MCP write — the script merges tags itself.
- Never write to `chroma.sqlite3` or `zotero.sqlite`.
- No Claude-side extraction fallback. If the model is weak on a paper, the fix is the
  vocabulary, the heading regex, or `DATA_TAG_MODEL=qwen2.5:14b-instruct` — never Claude.
- Confirm before every live pass and before every vocabulary promotion.
````

- [ ] **Step 2: Update README**

Replace `README.md:558-561` with:
```markdown
To build a data-discovery index over your **existing** library — not through the vault,
directly against Zotero — run `/ztp-data-tag`: it finds each paper's datasets (source, type,
geography, period, variables and dependent variables, with the evidence page) using SQL grep
over ChromaDB plus a local Ollama model, and writes them back as tags, a "Data" note and a
queryable sidecar DB — 15 papers per pass, no Claude tokens per paper. See its entry below.
```
Replace `README.md:590` with:
```markdown
| `/ztp-data-tag` | Tag papers with the datasets they use — source, type, geography, period, variables/DVs, evidence page — via grep + local Ollama; 15-paper passes, sidecar DB for cross-tabs |
```

- [ ] **Step 3: Run the skill-contract tests and the full data_tag suite**

Run: `micromamba run -n zotpilot python -m pytest tests/test_skill_contracts.py tests/test_allowed_tools.py tests/test_data_tag_*.py -q`
Expected: all pass. If a contract test rejects the frontmatter (e.g. `allowed-tools` must include `Agent`, or description length), fix the frontmatter to the contract — do not weaken the test.

- [ ] **Step 4: Verify the link lands in a paper project**

```bash
bash apply.sh --list | grep -n "ztp-data-tag"
ls -la ~/Research/zoning2026/.claude/skills/ztp-data-tag 2>/dev/null | head -2
```
Expected: listed; the symlink points at `skills/ztp-data-tag` (a directory link, so `scripts/` arrives with it).

- [ ] **Step 5: Commit**

```bash
git add skills/ztp-data-tag/SKILL.md README.md
git commit -m "docs(ztp-data-tag): v2 workflow — local passes, review-queue tuning, queries, undo"
```

---

### Task 12: Pass 1 on affordable_housing (USER_REQUIRED gates)

No new code. Run from a paper project that links research-claude (so `quality_reports/data_tags/` lands in the project), or from research-claude with `--report-dir`.

- [ ] **Step 1: Dry run**

```bash
source ~/.secrets.env
micromamba run -n zotpilot python skills/ztp-data-tag/scripts/data_tag.py run --library group:2350352 --pass 1 --n 15 --dry-run --report-dir quality_reports/data_tags 2>&1 | tail -3
```
Read `quality_reports/data_tags/pass_01.md` in full. Record: wall time per paper, how many papers hit the heading regex, review-queue size.

- [ ] **Step 2: USER gate** — show the per-paper table; the user spot-checks 2–3 papers in Zotero. Acceptance (spec §11): ≥ 12/15 correct primary dataset + geography, ≥ 10/15 correct DV. Below that: tune (Task 11 Step 4 loop) and re-run `--pass 1 --dry-run` before any live write.

- [ ] **Step 3: Live run** (after yes) — same command without `--dry-run`. Confirm in desktop Zotero that one item shows the new tags and the "Data (auto-extracted)" note.

- [ ] **Step 4: Promote the review queue** (USER gate), bump vocab `version: 2`, run tests, commit:
```bash
git add skills/ztp-data-tag/scripts/data_vocab.yaml
git commit -m "vocab(ztp-data-tag): v2 — promotions from pass 1"
```

- [ ] **Step 5: Pass 2** — `--pass 2 --n 15 --dry-run` on the next 15 (the marker skips pass-1 items), then the gate, then live. Repeat until the 42 indexed items are done; then `mcp__zotpilot__index_library` for the 11 unindexed and a final pass.

- [ ] **Step 6: Findings note** — append to `docs/SESSION_REPORT.md`: per-pass precision as judged, model used, vocabulary version reached, open issues. Decide with the user whether `agents/data-tag-extractor.md` (v1, now unused) should be deleted — **ask, never assume**.

---

## Self-Review

**Spec coverage**
- §4.1 steps 1–8 → Tasks 8 (enumerate), 4 (select), 2 (grep), 5 (extract), 6 (normalize), 7 (sidecar), 8 (Zotero), 9 (report); orchestration Task 10. ✓
- §4.2 vocabulary + version bump → Task 2; promotion loop → Task 11 Step 4, Task 12 Step 4. ✓
- §5.1 schema incl. variable roles → Task 5 `build_schema`; §5.2 sidecar tables incl. `review_queue`, `passes`, write log for undo → Task 7. Cross-tab acceptance queries → Task 7 tests + Task 10 `query`. ✓
- §6 model, `temperature 0`, `num_ctx 8192`, readiness check, one retry, `model_error` keeps grep rows → Tasks 5, 10 (`test_model_error_keeps_grep_rows`). ✓
- §7 namespaces kept/added, v1 reprocessing, note title + v1 JSON line + table + footer, pyzotero direct, 412 retry, autosync warning, merge-never-replace → Tasks 6 (`tags_for`), 8, 10. ✓
- §8 report sections 1–6 → Task 9. ✓  §9 seed vocabulary → Task 2 YAML. ✓  §10 workflow + undo → Tasks 10–11. ✓  §11 tests → every task; live acceptance → Task 12. ✓
- §12 out of scope respected: no classifier change, no Claude fallback, no v1 tag cleanup.

**Placeholder scan** — no TBD/TODO; every code step is complete; Task 11 Step 3 names the exact tests.

**Type consistency** — `Chunk(doc_id, chunk_index, page_num, section, text, total_chunks)` used identically in Tasks 3–6, 10; `DocRecord/DatasetRecord/Variable/Evidence/ReviewItem` field order in Task 6 matches the positional constructors in Tasks 7–10 tests; `Sidecar` method names (`begin_pass`, `write_doc`, `written_tags`, `writes_in_pass`, `docs_in_pass`, `datasets_for_doc`, `variables_for`, `evidence_for`, `open_review`, `passes`, `query_by_type`, `source_geo_matrix`, `topic_crosstab`, `set_doc_status`) match across Tasks 7, 9, 10; `ZoteroWriterV2.upsert_note/merge_tags/remove_tags/delete_note` match Tasks 8, 10; `OllamaClient.check_ready/extract` match Tasks 5, 10; `main()` returns a dict for `run` (tests in Task 10) — entry script adjusted in Task 10 Step 5.

**Review Focus → tests**: (1) Task 4 `test_select_never_empty_without_heading`; (2) Task 2 `test_match_costar_word_bounded`; (3) Task 5 `test_validate_drops_bad_rows`; (4) Task 8 `test_merge_tags_adds_only_new_and_retries_412` / `test_merge_tags_second_412_raises`; (5) Task 7 `test_rerun_pass_replaces_rows` + Task 8 `test_upsert_note_creates_then_updates`. ✓
