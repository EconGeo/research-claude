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

class FakeResp:
    def __init__(self, status_code): self.status_code = status_code

class FakeZot:
    def __init__(self):
        self.items_db = {"AAA": {"key": "AAA", "version": 5, "data": {"key": "AAA", "version": 5, "tags": [{"tag": "Housing"}]}}}
        self.notes = []; self.updated = []; self.fail_412_once = False; self.status_seq = []
    def item(self, key):
        if key in self.items_db: return json.loads(json.dumps(self.items_db[key]))
        return json.loads(json.dumps(next(n for n in self.notes if n["key"] == key)))
    def children(self, key, itemType=None): return [n for n in self.notes if n["data"]["parentItem"] == key]
    def item_template(self, t): return {"itemType": "note", "note": "", "tags": [], "parentItem": ""}
    def create_items(self, payload):
        n = {"key": f"N{len(self.notes)+1}", "version": 1, "data": {**payload[0], "key": f"N{len(self.notes)+1}", "version": 1}}
        self.notes.append(n); return {"success": {"0": n["key"]}, "failed": {}}
    def update_item(self, payload):
        # real pyzotero update_item takes the inner data dict (has "key" and "version"); wrap for assertions
        assert "data" not in payload and "key" in payload and "version" in payload, "must pass item['data']"
        item = {"key": payload["key"], "data": payload}
        if self.status_seq:
            code = self.status_seq.pop(0)
            if code >= 300: return FakeResp(code)
        if self.fail_412_once:
            self.fail_412_once = False
            raise zio.PreConditionFailed("412")
        self.updated.append(item)
        if item["key"] in self.items_db: self.items_db[item["key"]] = item
        for n in self.notes:
            if n["key"] == item["key"]: n["data"] = item["data"]
        return FakeResp(204)

def _writer(fake):
    w = zio.ZoteroWriterV2.__new__(zio.ZoteroWriterV2); w._zot = fake; return w

def test_upsert_note_creates_then_updates():
    fake = FakeZot(); w = _writer(fake)
    k1 = w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v1</p>")
    k2 = w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v2</p>")
    assert k1 == k2 == "N1" and len(fake.notes) == 1 and "v2" in fake.notes[0]["data"]["note"]
    assert w.last_note_created is False
    w2 = _writer(FakeZot()); assert w2.last_note_created is None
    w2.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v1</p>"); assert w2.last_note_created is True

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


def test_status_412_returned_not_raised_retries_then_succeeds():
    fake = FakeZot(); fake.status_seq = [412, 204]; w = _writer(fake)
    assert w.merge_tags("AAA", ["x"]) == ["x"] and len(fake.updated) == 1

def test_status_412_returned_twice_raises_write_conflict():
    fake = FakeZot(); fake.status_seq = [412, 412]; w = _writer(fake)
    with pytest.raises(zio.WriteConflict):
        w.merge_tags("AAA", ["x"])

def test_other_non_2xx_status_raises_runtimeerror_with_key():
    fake = FakeZot(); fake.status_seq = [403]; w = _writer(fake)
    with pytest.raises(RuntimeError, match="403.*AAA"):
        w.merge_tags("AAA", ["x"])

def test_merge_tags_preserves_existing_tag_dicts_and_type():
    fake = FakeZot(); fake.items_db["AAA"]["data"]["tags"] = [{"tag": "auto", "type": 1}, {"tag": "Housing"}]
    w = _writer(fake)
    assert w.merge_tags("AAA", ["new", "auto"]) == ["new"]
    assert fake.updated[-1]["data"]["tags"] == [{"tag": "auto", "type": 1}, {"tag": "Housing"}, {"tag": "new"}]

def test_real_pyzotero_update_item_on_412_with_mock_transport():
    """Pins real-client behaviour offline: does update_item raise on 412?"""
    import httpx
    from pyzotero import zotero
    seen = []
    def handler(request):
        seen.append((request.method, str(request.url)))
        return httpx.Response(412, text="precondition failed")
    zot = zotero.Zotero("1", "user", "k")
    zot.client = httpx.Client(transport=httpx.MockTransport(handler))
    zot.item_fields = lambda: [{"field": "note"}, {"field": "itemType"}]  # no network
    payload = {"key": "AAA", "version": 5, "itemType": "note", "note": "x", "tags": []}
    with pytest.raises(zio.PreConditionFailed):
        zot.update_item(payload)
    assert seen and all(m == "PATCH" for m, _ in seen)  # only the mocked PATCH; nothing escaped


def test_remove_tags_keeps_remaining_dicts_and_type():
    fake = FakeZot(); fake.items_db["AAA"]["data"]["tags"] = [{"tag": "auto", "type": 1}, {"tag": "Housing"}, {"tag": "dataset:x"}]
    w = _writer(fake)
    w.remove_tags("AAA", ["dataset:x", "absent"])
    assert fake.updated[-1]["data"]["tags"] == [{"tag": "auto", "type": 1}, {"tag": "Housing"}]

def test_remove_tags_retries_412():
    fake = FakeZot(); fake.fail_412_once = True; fake.items_db["AAA"]["data"]["tags"] = [{"tag": "Housing"}, {"tag": "x"}]
    w = _writer(fake); w.remove_tags("AAA", ["x"])
    assert fake.updated[-1]["data"]["tags"] == [{"tag": "Housing"}]

def test_delete_note_refuses_non_note():
    fake = FakeZot(); deleted = []; fake.delete_item = deleted.append
    w = _writer(fake)
    fake.items_db["AAA"]["data"]["itemType"] = "journalArticle"
    with pytest.raises(RuntimeError, match="not a note"):
        w.delete_note("AAA")
    w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1>")
    w.delete_note("N1"); assert len(deleted) == 1 and deleted[0]["key"] == "N1"


def test_upsert_note_captures_prev_html_and_restore_note():
    fake = FakeZot(); w = _writer(fake)
    w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v1 original</p>")
    assert w.last_note_prev_html is None
    w.upsert_note("AAA", "<h1>Data (auto-extracted)</h1><p>v2</p>")
    assert w.last_note_prev_html == "<h1>Data (auto-extracted)</h1><p>v1 original</p>"
    w.restore_note("N1", w.last_note_prev_html)
    assert "v1 original" in fake.notes[0]["data"]["note"]

def test_delete_note_missing_is_already_deleted():
    fake = FakeZot()
    def gone(key): raise zio.ResourceNotFoundError("404")
    fake.item = gone; w = _writer(fake)
    w.delete_note("N9")  # no raise
