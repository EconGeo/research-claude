"""tests/mock_zotpilot.py is a stdio JSON-RPC server that answers the ten ZotPilot tools the
bridge skills and the extraction agents call, from tests/fixture-project/zotpilot_fixture.json.
It exists so a skill eval can assert MECHANISM (which tool, in what order, with what flags)
without a Zotero, a ChromaDB or an embedding provider (audit 2026-09-15 §3 P7; plan Part C).
Writes mutate an in-memory copy and are echoed to stderr as `WRITE <tool> <json>`.
"""
import json, pathlib, subprocess, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOCK = ROOT / "tests" / "mock_zotpilot.py"


def call(proc, method, params, id_=1):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def tool(proc, name, **args):
    """Unwrap the MCP content envelope: {"result": <json>} on success, {"error": <text>} on isError."""
    r = call(proc, "tools/call", {"name": name, "arguments": args})
    if "error" in r:
        return r
    res = r["result"]
    text = res["content"][0]["text"]
    return {"error": text} if res.get("isError") else {"result": json.loads(text)}


class TestMock(unittest.TestCase):
    def setUp(self):
        self.p = subprocess.Popen([sys.executable, str(MOCK)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def tearDown(self):
        self.p.terminate()

    def test_initialize_and_tools_list(self):
        r = call(self.p, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})
        self.assertIn("serverInfo", r["result"])
        names = {t["name"] for t in call(self.p, "tools/list", {}, 2)["result"]["tools"]}
        for n in ("get_index_stats", "browse_library", "advanced_search", "search_topic",
                  "search_papers", "get_passage_context", "get_paper_details", "get_notes",
                  "create_note", "manage_tags"):
            self.assertIn(n, names)

    def test_index_stats_counts_the_fixture(self):
        r = tool(self.p, "get_index_stats")
        self.assertEqual(r["result"]["indexed"], 6)
        self.assertEqual(r["result"]["unindexed"], 2)

    def test_search_papers_scopes_by_collection_and_returns_doc_ids(self):
        r = tool(self.p, "search_papers", query="data sources dataset sample period variables methods",
                 collection="Pilot")
        hits = r["result"]["hits"]
        self.assertTrue(hits)
        self.assertTrue(all("doc_id" in h for h in hits))
        self.assertTrue(all(h["doc_id"] in {"D1", "D2", "D3", "D7"} for h in hits))

    def test_unindexed_paper_has_no_chunks(self):
        r = tool(self.p, "search_papers", query="eviction hospital", collection="Pilot")
        self.assertNotIn("D7", {h["doc_id"] for h in r["result"]["hits"]})

    def test_manage_tags_set_is_refused(self):
        r = tool(self.p, "manage_tags", action="set", item_key="K1", tags=["x"])
        self.assertIn("error", r)

    def test_manage_tags_add_without_allow_new_creates_no_new_tag(self):
        r = tool(self.p, "manage_tags", action="add", item_key="K1", tags=["dataset:hmda"])
        self.assertEqual(r["result"]["added"], [])
        r = tool(self.p, "manage_tags", action="add", allow_new=True, item_key="K1", tags=["dataset:hmda"], )
        self.assertEqual(r["result"]["added"], ["dataset:hmda"])

    def test_create_note_idempotent_skips_when_any_note_exists(self):
        r = tool(self.p, "create_note", item_key="K2", idempotent=True, title="Data (auto-extracted)", content="{}")
        self.assertFalse(r["result"]["created"])
        r = tool(self.p, "create_note", item_key="K1", idempotent=True, title="Data (auto-extracted)", content="{}")
        self.assertTrue(r["result"]["created"])

    def test_writes_are_echoed_to_stderr_by_default(self):
        tool(self.p, "manage_tags", action="add", allow_new=True, item_key="K3", tags=["var:move"])
        self.p.stdin.close()
        err = self.p.stderr.read()
        self.assertIn("CALL manage_tags", err)
        self.assertIn("WRITE manage_tags", err)

    def test_results_are_wrapped_in_mcp_content(self):
        r = call(self.p, "tools/call", {"name": "get_index_stats", "arguments": {}})
        self.assertEqual(r["result"]["content"][0]["type"], "text")

    def test_calls_go_to_the_log_file_when_the_env_var_is_set(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            logf = os.path.join(d, "mock.log")
            p = subprocess.Popen([sys.executable, str(MOCK)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env={**os.environ, "MOCK_ZOTPILOT_LOG": logf})
            try:
                tool(p, "get_index_stats")
                tool(p, "create_note", item_key="K1", idempotent=True, title="Data (auto-extracted)", content="{}")
            finally:
                p.terminate()
            text = open(logf).read()
            self.assertIn("CALL get_index_stats", text)
            self.assertIn("WRITE create_note", text)

    # ── tools added for the twenty remaining evals (plan 2026-09-25, Task 0) ──
    def test_search_academic_databases_marks_the_local_duplicate(self):
        r = tool(self.p, "search_academic_databases", query='"staggered difference-in-differences"')
        rows = r["result"]["results"]
        self.assertEqual(len(rows), 6)
        self.assertEqual([x["existing_item_key"] for x in rows if x["local_duplicate"]], ["K2"])
        self.assertTrue(any(x["doi"].startswith("10.1016/") for x in rows))

    def test_ingest_is_a_write_and_returns_one_row_per_candidate(self):
        cands = tool(self.p, "search_academic_databases", query="x")["result"]["results"][:2]
        r = tool(self.p, "ingest_by_identifiers", candidates=cands)
        self.assertEqual(len(r["result"]["results"]), 2)
        self.assertEqual(r["result"]["action_required"], [])
        self.p.stdin.close()
        self.assertIn("WRITE ingest_by_identifiers", self.p.stderr.read())

    def test_browse_library_overview_and_tags(self):
        self.assertEqual(tool(self.p, "browse_library", view="overview")["result"]["papers"], 8)
        tags = tool(self.p, "browse_library", view="tags")["result"]["tags"]
        self.assertEqual({t["name"] for t in tags} & {"AI", "Artificial Intelligence", "LLM"}, {"AI", "Artificial Intelligence", "LLM"})

    def test_get_paper_for_tutor_by_title_carries_persona_null_and_figure_bboxes(self):
        r = tool(self.p, "get_paper_for_tutor", title_or_doc_id="Mortgage denial and neighborhood change")
        self.assertEqual(r["result"]["doc_id"], "D1")
        self.assertIsNone(r["result"]["persona"])
        self.assertEqual(len(r["result"]["figures"]), 2)
        self.assertEqual(len(r["result"]["figures"][0]["bbox"]), 4)
        self.assertEqual(r["result"]["existing_annotations"], [])

    def test_annotate_pdf_and_save_persona_are_writes(self):
        tool(self.p, "save_reading_persona", persona_text="- 英文水平：入门")
        tool(self.p, "annotate_pdf", doc_id="D1", specs_path="/tmp/x.json")
        tool(self.p, "manage_collections", action="add", item_keys=["K1"], collection_key="Pilot")
        tool(self.p, "index_library", item_keys=["K7"])
        self.p.stdin.close()
        err = self.p.stderr.read()
        for w in ("save_reading_persona", "annotate_pdf", "manage_collections", "index_library"):
            self.assertIn(f"WRITE {w}", err)

    def test_profile_library_get_annotations_get_citations_read_only(self):
        self.assertIn("themes", tool(self.p, "profile_library")["result"])
        self.assertEqual(tool(self.p, "get_annotations", item_key="K1")["result"]["annotations"], [])
        self.assertIn("citing", tool(self.p, "get_citations", doc_id="D1", direction="citing")["result"])
        self.p.stdin.close()
        self.assertNotIn("WRITE", self.p.stderr.read())


if __name__ == "__main__":
    unittest.main()
