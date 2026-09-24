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
    return call(proc, "tools/call", {"name": name, "arguments": args})


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

    def test_writes_are_echoed_to_stderr(self):
        tool(self.p, "manage_tags", action="add", allow_new=True, item_key="K3", tags=["var:move"])
        self.p.stdin.close()
        err = self.p.stderr.read()
        self.assertIn("WRITE manage_tags", err)


if __name__ == "__main__":
    unittest.main()
