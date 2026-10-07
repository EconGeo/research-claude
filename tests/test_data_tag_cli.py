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
    assert "BBB" in summary["processed"]  # BBB has 1 chunk in the fixture

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
    w1 = Sidecar(env["sidecar"]).writes_in_pass(1)[0]; assert w1["note_created"] == 0
    cli.main(["undo", "--pass", "1", "--yes", "--sidecar", str(env["sidecar"]), "--zotero-sqlite", str(env["zot"]), "--library", "group:2350352"], writer_factory=lambda *a: writer)
    assert writer.removed and writer.deleted_notes == []


UNDO = lambda env, *extra: ["undo", "--pass", "1", "--sidecar", str(env["sidecar"]), "--zotero-sqlite", str(env["zot"]), *extra]


class RecWriter(FakeWriter):
    def __init__(self):
        super().__init__(); self.removed = []; self.deleted_notes = []; self.restored = []
    def remove_tags(self, key, tags): self.removed.append((key, tags))
    def delete_note(self, note_key): self.deleted_notes.append(note_key)
    def restore_note(self, note_key, html): self.restored.append((note_key, html))


def test_note_logged_even_if_merge_tags_conflicts_and_undo_deletes_it(env):
    class W(RecWriter):
        def merge_tags(self, key, tags): raise cli.WriteConflict("412 twice")
    writer = W()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    sc = Sidecar(env["sidecar"])
    assert sc.docs_in_pass(1)[0]["status"] == "write_conflict" and sc.writes_in_pass(1)[0]["note_key"] == "NOTE-AAA"
    cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: writer)
    assert writer.deleted_notes == ["NOTE-AAA"] and writer.removed == []  # empty tag list: no remove_tags call


def test_write_error_continues_and_report_exists(env):
    class W(RecWriter):
        def merge_tags(self, key, tags): raise RuntimeError("boom")
    writer = W()
    summary = cli.main(_args(env, ["--refresh-v2"]), client=FakeClient(), writer_factory=lambda *a: writer)
    assert summary["processed"] == ["AAA", "BBB"]  # BBB still processed after AAA's write error
    assert {d["doc_id"]: d["status"] for d in Sidecar(env["sidecar"]).docs_in_pass(1)}["AAA"] == "write_error"
    assert (env["report"] / "pass_01.md").exists()


def test_undo_twice_acts_once(env):
    writer = RecWriter()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: writer)
    cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: writer)
    assert len(writer.removed) == 1 and writer.deleted_notes == ["NOTE-AAA"]


def test_undo_continues_after_row_error_and_resumes(env):
    class W(RecWriter):
        fail = True
        def remove_tags(self, key, tags):
            if self.fail: raise RuntimeError("net")
            super().remove_tags(key, tags)
    writer = W()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    assert cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: writer) == 1
    writer.fail = False
    assert cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: writer) == 0
    assert len(writer.removed) == 1 and writer.deleted_notes == ["NOTE-AAA"]


def test_undo_restores_preexisting_note_html(env):
    class W(RecWriter):
        last_note_created = False
        last_note_prev_html = "<h1>Data (auto-extracted)</h1><p>v1 original</p>"
    writer = W()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: writer)
    assert writer.restored == [("NOTE-AAA", "<h1>Data (auto-extracted)</h1><p>v1 original</p>")] and writer.deleted_notes == []


def test_undo_uses_pass_library_and_refuses_mismatch(env, capsys):
    writer = RecWriter(); seen = []
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)
    assert cli.main(UNDO(env, "--library", "user", "--yes"), writer_factory=lambda *a: writer) == 2
    assert writer.removed == [] and "refusing" in capsys.readouterr().err
    cli.main(UNDO(env, "--yes"), writer_factory=lambda *a: (seen.append(a), writer)[1])  # no --library
    assert seen == [("group", "2350352")] and writer.removed


def test_live_rerun_same_pass_replays_same_docs(env):
    writer = FakeWriter()
    cli.main(_args(env), client=FakeClient(), writer_factory=lambda *a: writer)  # AAA tagged live? FakeWriter doesn't set Zotero tags
    summary = cli.main(_args(env, ["--n", "1"]), client=FakeClient(), writer_factory=lambda *a: writer)
    assert summary["processed"] == ["AAA"] and summary["skipped_v2"] == []
    assert [d["doc_id"] for d in Sidecar(env["sidecar"]).docs_in_pass(1)] == ["AAA"]


def test_rerun_exempt_from_v2_marker(env):
    # BBB carries the marker in Zotero, but pass 1 already holds it: a re-run replays it, ignoring --n
    cli.main(_args(env, ["--refresh-v2", "--dry-run"]), client=FakeClient(), writer_factory=lambda *a: FakeWriter())
    summary = cli.main(_args(env, ["--n", "1", "--dry-run"]), client=FakeClient(), writer_factory=lambda *a: FakeWriter())
    assert summary["processed"] == ["AAA", "BBB"]


def test_zero_dataset_docs_from_other_pass_are_skipped(env):
    from data_tag.normalize import DocRecord
    sc = Sidecar(env["sidecar"]); sc.begin_pass(5, "group:2350352", None, 1, "m", 1)
    sc.write_doc(DocRecord("AAA", "no_candidates"), 5, "Paper A", 2019, "3")
    skipped = cli.main(_args(env, ["--dry-run"]), client=FakeClient(), writer_factory=lambda *a: FakeWriter())
    assert skipped["processed"] == [] and skipped["skipped_sidecar"] == ["AAA"]
    refreshed = cli.main(_args(env, ["--dry-run", "--refresh-v2"]), client=FakeClient(), writer_factory=lambda *a: FakeWriter())
    assert "AAA" in refreshed["processed"]


def test_negative_n_and_missing_query_value_rejected(env):
    with pytest.raises(SystemExit): cli.main(_args(env, ["--n", "-1"]))
    with pytest.raises(SystemExit): cli.main(["query", "type", "--sidecar", str(env["sidecar"])])
