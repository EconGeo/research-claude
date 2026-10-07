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
    for expected in ["dataset:mls", "datatype:residential-transactions-mls",
                     "dv:house-price", "geo:metro", "data-tagged", "data-tagged:v2"]:
        assert expected in tags
    assert not any(t.startswith("var:") for t in tags)
    # unlisted datasets (no vocabulary src_slug) yield no datatype:/geo: tags
    assert "datatype:administrative-program" not in tags and "geo:city" not in tags
    # Controller ruling (final review, finding 3): grep-only datasets (source == "grep", never
    # confirmed by the model) stay in the sidecar/note/report but produce NO Zotero tags.
    assert "dataset:fema_nfhl" not in tags and "datatype:hazard-flood" not in tags
    assert not any(t.startswith("dataset:") and "denver-water" in t for t in tags)
    assert tags == sorted(set(tags))


def test_duplicate_slug_llm_datasets_union(vocab):
    out = llm()
    out["datasets"] = [out["datasets"][0], {
        "name": "MLS listings", "provider": "REcolorado", "type": "residential-transactions-mls",
        "geography": {"text": None, "level": None, "places": []}, "period": {"start": None, "end": None},
        "unit_of_observation": None, "access": None,
        "variables": [{"name": "days on market", "role": "dependent"}, {"name": "square footage", "role": "control"}],
        "evidence_chunks": [18]}]
    doc = nz.build_records("D", [C17, C18], [C17, C18], {}, out, [], vocab)
    mls = [d for d in doc.datasets if d.src_slug == "mls"]
    assert len(mls) == 1 and mls[0].source == "llm" and mls[0].name_raw == "REcolorado MLS sales"
    assert {v.slug for v in mls[0].variables} == {"log-sale-price", "square-footage", "days-on-market"}
    assert sorted(e.chunk_index for e in mls[0].evidence) == [17, 18]
    assert mls[0].period_start == 2010 and mls[0].geo_text == "Denver MSA" and mls[0].places == ["Denver, CO"]


def test_grep_merge_null_does_not_overwrite(vocab):
    out = llm()
    out["datasets"] = [{"name": "REcolorado MLS sales", "provider": None, "type": "residential-transactions-mls",
        "geography": {"text": None, "level": None, "places": []}, "period": {"start": None, "end": None},
        "unit_of_observation": None, "access": None, "variables": [], "evidence_chunks": []}]
    grep = {17: vocab.match_sources(C17.text)}
    doc = nz.build_records("D", [C17, C18], [C17, C18], grep, out, [], vocab)
    mls = [d for d in doc.datasets if d.src_slug == "mls"][0]
    assert mls.source == "merged" and mls.access == vocab.sources["mls"].access
    assert mls.geo_level == vocab.sources["mls"].geo_level and mls.evidence


@pytest.mark.parametrize("text,places,level", [
    ("Washington, DC", [], "city"), ("Washington D.C.", [], "city"), ("District of Columbia", [], "city"),
    ("Indiana University", [], None), ("Denver, Colorado", [], "city"), ("state of the art", [], None),
    ("USAID", [], None), ("", ["Colorado"], "state"), ("Colorado", [], "state"), ("Colorado, Wyoming", [], "state")])
def test_infer_geo_level_probes(text, places, level):
    assert nz.infer_geo_level(text, places) == level


@pytest.mark.parametrize("text,level", [
    ("Indiana University", None), ("Colorado State University", None), ("New York State", "state"),
    ("Washington State", "state"), ("Texas state", "state"), ("Florida Department of Revenue", "state")])
def test_infer_geo_level_institution_exclusion(text, level):
    assert nz.infer_geo_level(text, []) == level


def test_tags_for_grep_only_doc_gets_markers_only(vocab):
    grep = {17: vocab.match_sources(C17.text)}
    doc = nz.build_records("D", [C17, C18], [C17, C18], grep, {"datasets": [], "notes": ""}, [], vocab)
    assert doc.datasets and all(d.source == "grep" for d in doc.datasets)
    assert nz.tags_for(doc) == ["data-tagged", "data-tagged:v2"]


def test_tags_for_skips_empty_slugs():
    ds = nz.DatasetRecord("X", None, None, "", None, None, [], None, None, None, None, 0.6, "llm",
                          [nz.Variable("Δ", "", "control", None), nz.Variable("rent", "rent", "dependent", "rent")])
    tags = nz.tags_for(nz.DocRecord("D", "ok", [ds]))
    assert not any(t.startswith(("var:", "datatype:", "geo:", "dataset:")) for t in tags) and "dv:rent" in tags


def test_page_labels_sorted_unique():
    refs = [(7, 30), (1, 2), (1, 3), (None, 9), (1, 4), (None, 5), (None, 9)]
    assert nz.page_labels(refs) == ["p. 1", "p. 7", "chunk 5", "chunk 9"]
    assert nz.page_labels(refs, "c") == ["p. 1", "p. 7", "c5", "c9"]
