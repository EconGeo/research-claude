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

def test_colliding_chunk_index_both_survive(vocab):
    chunks = [mk(i, "filler text about theory", "introduction") for i in range(8)]
    chunks[3] = mk(3, "3. Data\nWe use HMDA observations from 2005 to 2015.", "methods")
    chunks.insert(4, mk(3, "Figure 2: caption shares an index with the body chunk", "methods"))
    chosen = select_candidates(chunks, vocab, top_k=1)
    texts = [c.text for c in chosen]
    assert any(t.startswith("3. Data") for t in texts)
    assert any(t.startswith("Figure 2") for t in texts)
