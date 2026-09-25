#!/usr/bin/env python3
"""check_talk.py — /talk create: the relative manuscript symlink is made before any render;
storyteller then storyteller-critic; no record-score (advisory); embeds by bare filename; no
tbl- embeds (tables go to backup slides as figures/images, per the storyteller's rules).
usage: check_talk.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
ln = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"ln\s+-s[^\n]*manuscript_fixture\.qmd", a.get("command", "")))
render = evallib.first(uses, lambda n, a: n == "Bash" and "quarto render" in a.get("command", ""))
if ln is None: fails.append("no Bash `ln -s … manuscript_fixture.qmd` created the talks/ symlink")
elif render is not None and render < ln: fails.append("quarto render ran before the manuscript symlink existed")
s, c = evallib.agent(uses, "storyteller"), evallib.agent(uses, "storyteller-critic")
if s is None: fails.append("storyteller was never dispatched")
if c is None: fails.append("storyteller-critic was never dispatched")
elif s is not None and c < s: fails.append("storyteller-critic ran before storyteller")
if any("record-score" in x for x in evallib.bash(uses)): fails.append("record-score ran — talk scores are advisory and unrecorded")
link = proj / "talks" / "manuscript_fixture.qmd"
if not link.is_symlink(): fails.append("talks/manuscript_fixture.qmd is not a symlink after the run")
talk = proj / "talks" / "lightning_talk.qmd"
if not talk.exists(): fails.append("talks/lightning_talk.qmd was not written")
else:
    embeds = re.findall(r"\{\{<\s*embed\s+([^\s>]+)", talk.read_text())
    bad = [e for e in embeds if not e.startswith("manuscript_fixture.qmd#")]
    if bad: fails.append(f"embeds not by bare filename: {bad}")
    if any("#tbl-" in e for e in embeds): fails.append("a tbl- chunk is embedded (tables belong in backup as figures)")
evallib.finish("check_talk", fails, f"tool_use: {len(uses)} · symlink: {link.is_symlink()} · talk: {talk.exists()}")
