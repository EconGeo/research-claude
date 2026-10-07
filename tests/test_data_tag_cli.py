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
    out = capsys.readouterr().out; assert "Paper A" in out and "national" in out and "rent" in out

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


def test_undo_never_deletes_preexisting_note(env):
    class UpdatedNoteWriter(FakeWriter):
        last_note_created = False
        def __init__(self): super().__init__(); self.removed = []; self.deleted_notes = []
        def remove_tags(self, key, tags): self.removed.append((key, tags))
        def delete_note(self, note_key): self.deleted_notes.append(note_key)
    writer = UpdatedNoteWriter()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    assert Sidecar(env["sidecar"]).writes_in_pass(1)[0]["note_key"] is None
    cli.main(["undo", "--pass", "1", "--yes", "--sidecar", str(env["sidecar"]), "--zotero-sqlite", str(env["zot"]), "--library", "group:2350352"], writer_factory=lambda *a: writer)
    assert writer.removed and writer.deleted_notes == []
