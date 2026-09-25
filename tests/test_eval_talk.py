import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=False):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


def go(check, transcript, *args):
    with tempfile.TemporaryDirectory() as d:
        t = pathlib.Path(d, "t.jsonl"); t.write_text(transcript)
        r = subprocess.run([sys.executable, str(check), str(t), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout


CHECK = ROOT / "tests" / "evals" / "check_talk.py"
T = (use("u1", "Bash", command="cd talks && ln -s ../manuscript_fixture.qmd manuscript_fixture.qmd")
     + use("u2", "Agent", subagent_type="storyteller", prompt="x")
     + use("u3", "Bash", command="quarto render talks/lightning_talk.qmd")
     + use("u4", "Agent", subagent_type="storyteller-critic", prompt="x"))


class TestTalkChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); (self.p / "talks").mkdir()
        (self.p / "manuscript_fixture.qmd").write_text("x"); (self.p / "talks" / "manuscript_fixture.qmd").symlink_to("../manuscript_fixture.qmd")
        (self.p / "talks" / "lightning_talk.qmd").write_text("## A\n\n{{< embed manuscript_fixture.qmd#fig-trends >}}\n")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_render_before_symlink_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[2] + lines[0] + lines[1] + lines[3], self.p); self.assertEqual(rc, 1); self.assertIn("before the manuscript symlink", out)

    def test_record_score_fails(self):
        rc, out = go(CHECK, T + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score manuscript 90 --critic writer-critic --report x"), self.p); self.assertEqual(rc, 1); self.assertIn("advisory", out)

    def test_tbl_embed_fails(self):
        (self.p / "talks" / "lightning_talk.qmd").write_text("{{< embed manuscript_fixture.qmd#tbl-main >}}\n"); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("tbl- chunk", out)

    def test_path_embed_fails(self):
        (self.p / "talks" / "lightning_talk.qmd").write_text("{{< embed ../manuscript_fixture.qmd#fig-trends >}}\n"); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("bare filename", out)

    def test_tbl_embed_in_backup_passes(self):
        (self.p / "talks" / "lightning_talk.qmd").write_text(
            "{{< embed manuscript_fixture.qmd#fig-trends >}}\n\n## Backup\n\n{{< embed manuscript_fixture.qmd#tbl-main >}}\n"
        )
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
