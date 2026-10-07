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
