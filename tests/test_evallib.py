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
 '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"u2","name":"Agent","input":{"subagent_type":"writer","prompt":"x"}}]}}\n'
 '{"type":"assistant","parent_tool_use_id":"u2","message":{"content":[{"type":"tool_use","id":"u3","name":"WebSearch","input":{"query":"x"}}]}}\n')
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
        self.assertEqual([x[0] for x in u], ["Bash", "Agent", "WebSearch"])
        self.assertEqual(u[0][2], "u1")

    def test_main_session_tool_uses_excludes_subagent_calls(self):
        # u3 (WebSearch) carries parent_tool_use_id "u2" — a subagent's own tool call, folded
        # into the same transcript as the main session's. tool_uses() sees all three; the
        # session-only view must drop the nested one.
        self.assertEqual(len(evallib.tool_uses(self.t)), 3)
        m = evallib.main_session_tool_uses(self.t)
        self.assertEqual(len(m), 2)
        self.assertEqual([x[0] for x in m], ["Bash", "Agent"])
        self.assertNotIn("WebSearch", [x[0] for x in m])

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

    def test_bash_joins_line_continuations(self):
        # A `git … \` + newline + `push` must not slip past a one-line "never pushes" regex.
        u = [("Bash", {"command": "git -C x \\\n  push origin main"}, "u9")]
        self.assertEqual(evallib.bash(u), ["git -C x push origin main"])


if __name__ == "__main__":
    unittest.main()
