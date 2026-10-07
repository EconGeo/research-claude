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

def test_rewrite_doc_across_passes_replaces_review_rows(sc):
    sc.begin_pass(1, "g", None, 1, "m", 1); sc.write_doc(rec(), 1, "T", 2020, "3")
    sc.begin_pass(2, "g", None, 1, "m", 1); sc.write_doc(rec(), 2, "T", 2020, "3")
    assert len(sc.open_review()) == 1 and len(sc.open_review(2)) == 1 and sc.open_review(1) == []

def test_rewrite_doc_same_pass_no_duplicate_review(sc):
    sc.begin_pass(1, "g", None, 1, "m", 1)
    sc.write_doc(rec(), 1, "T", 2020, "3"); sc.write_doc(rec(), 1, "T", 2020, "3")
    assert len(sc.open_review(1)) == 1

def test_rewrite_keeps_resolved_review_rows(sc):
    sc.begin_pass(1, "g", None, 1, "m", 1); sc.write_doc(rec(), 1, "T", 2020, "3")
    sc._con.execute("UPDATE review_queue SET status='promoted'"); sc._con.commit()
    sc.write_doc(rec(), 1, "T", 2020, "3")
    st = sorted(r[0] for r in sc._con.execute("SELECT status FROM review_queue"))
    assert st == ["open", "promoted"]

def test_failed_write_doc_rolls_back(sc):
    sc.begin_pass(1, "g", None, 1, "m", 2)
    sc.write_doc(rec("D2"), 1, "Two", 2021, "3")
    bad = rec("D1"); bad.datasets[0].variables[0].name_raw = object()
    with pytest.raises(Exception):
        sc.write_doc(bad, 1, "One", 2020, "3")
    sc.set_doc_status("D2", "needs_review")
    assert sc.datasets_for_doc("D1") == [] and [d["doc_id"] for d in sc.docs_in_pass(1)] == ["D2"]
    assert sc.open_review(1)[0]["doc_id"] == "D2" and len(sc.open_review(1)) == 1
