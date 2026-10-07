import re
import yaml
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

def test_report_escaping(tmp_path):
    sc = Sidecar(tmp_path / "s.sqlite"); v = Vocab.load()
    sc.begin_pass(1, "group:1", None, 1, "m", 1)
    ds = DatasetRecord("Pipe | Data\nset", None, None, "other", "A | B", None, [], None, None,
                       None, None, 0.5, "merged", [], [Evidence(1, None, "s")])
    nasty = "Weird: Source's #1 (A+B) [x]"
    sc.write_doc(DocRecord("AAA", "ok", [ds], [ReviewItem("source", nasty, "weird-source", "snip | with\npipe")]), 1, "Ti|tle\nline", 2020, "3")
    md = render_pass_report(sc, 1, v, {})
    row = next(l for l in md.splitlines() if l.startswith("| Ti"))
    assert row.count("|") - row.count("\\|") == 9      # 8 columns -> 9 unescaped pipes
    assert "\n" not in row
    block = md.split("```yaml\n")[1].split("```")[0]
    parsed = yaml.safe_load("\n".join(l for l in block.splitlines()))
    entry = parsed["weird-source"]
    assert entry["name"] == nasty
    assert re.search(entry["aliases"][0], nasty)

def test_report_dedup_and_extras(tmp_path):
    sc = Sidecar(tmp_path / "s.sqlite"); v = Vocab.load()
    known = next(iter(v.sources))
    sc.begin_pass(1, "group:1", None, 1, "m", 2)
    for doc, title in (("AAA", "Paper A"), ("BBB", "Paper B")):
        sc.write_doc(DocRecord(doc, "ok", [], [ReviewItem("source", "Denver Water", "denver-water", "snip"),
                                               ReviewItem("source", "Known Thing", known, "snip")]), 1, title, 2020, "3")
    md = render_pass_report(sc, 1, v, {"AAA": {"words": 1000, "best_score": 9}, "BBB": {"words": 2000}},
                            extra_counts={"skipped_v2": ["X"], "unindexed": ["U1", "U2"]})
    block = md.split("```yaml\n")[1].split("```")[0]
    assert block.count('"denver-water":') == 1 and "already in vocab" in block
    assert list(yaml.safe_load(block)) == ["denver-water"]
    queue = md.split("## Review queue")[1].split("##")[0]
    assert "Paper A" in queue and "Paper B" in queue and queue.count("`Denver Water`") == 1
    assert "average 1500 words over 2 papers" in md
    assert "skipped_v2: 1" in md and "unindexed: 2 — U1, U2" in md
    assert md.count("heading regex missed") == 0
