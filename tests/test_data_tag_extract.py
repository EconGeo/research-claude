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

def test_validate_tolerates_non_int_evidence(vocab):
    raw = {"datasets": [{"name": "X", "type": "survey", "evidence_chunks": ["a", None, [1], 17]}]}
    clean, dropped = ex.validate_output(raw, {17}, vocab)
    assert clean["datasets"][0]["evidence_chunks"] == [17] and dropped
