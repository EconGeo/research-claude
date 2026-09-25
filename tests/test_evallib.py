"""tests/evals/evallib.py is what every checker after the first three parses with."""
import pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "evals"))
import evallib  # noqa: E402

T = (
 '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"u1","name":"Bash","input":{"command":"ls"}}]}}\n'
 '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"u1","content":[{"type":"text","text":"denied"}],"is_error":true}]}}\n'
 'not json\n'
 '{"type":"assistant","message":{"content":"a plain string, not a list"}}\n'
 '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"u2","name":"Agent","input":{"subagent_type":"writer","prompt":"x"}}]}}\n')
M = ('CALL search_topic {"query": "a"}\n'
     'WRITE manage_tags {"action": "add", "item_key": "K1"} -> {"added": []}\n'
     'garbage line\n')


class TestEvallib(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.t = pathlib.Path(self.d.name, "t.jsonl"); self.t.write_text(T)
        self.m = pathlib.Path(self.d.name, "m.log"); self.m.write_text(M)

    def tearDown(self):
        self.d.cleanup()

    def test_tool_uses_in_order_with_ids(self):
        u = evallib.tool_uses(self.t)
        self.assertEqual([x[0] for x in u], ["Bash", "Agent"])
        self.assertEqual(u[0][2], "u1")

    def test_tool_results_keyed_by_id(self):
        r = evallib.tool_results(self.t)
        self.assertEqual(r["u1"], ("denied", True))

    def test_mock_calls_parse_call_and_write(self):
        c = evallib.mock_calls(self.m)
        self.assertEqual([(k, t) for k, t, _, _ in c], [("CALL", "search_topic"), ("WRITE", "manage_tags")])
        self.assertEqual(c[1][3], {"added": []})

    def test_first_bash_agent(self):
        u = evallib.tool_uses(self.t)
        self.assertEqual(evallib.first(u, lambda n, a: n == "Agent"), 1)
        self.assertEqual(evallib.bash(u), ["ls"])
        self.assertEqual(evallib.agent(u, "writer"), 1)
        self.assertIsNone(evallib.agent(u, "coder"))


if __name__ == "__main__":
    unittest.main()
