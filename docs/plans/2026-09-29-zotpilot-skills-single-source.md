# ZotPilot Skills — One Loaded Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every Claude Code session that loads a ZotPilot skill (`ztp-*`, `seed-papers`) loads the copy in `research-claude/zotpilot-skills/`, vendored from the `EconGeo/ZotPilot` fork, and no other.

**Architecture:** The paper repos already link `zotpilot-skills/` (one copy, no per-paper drift). The problem is a second copy: `zotpilot register`/`setup`/`upgrade` also copies the fork's packaged skills into `~/.claude/skills/ztp-*`. Claude Code runs a user-level skill in preference to a project skill with the same name, so every paper runs that copy, not ours. The fix: add a `deploy_skills` config switch to the fork. When it is `false`, reconcile stops deploying and removes the copies it deployed earlier. Then keep `zotpilot-skills/` current with the fork, and add gates that fail if a user-level copy ever reappears.

**Tech Stack:** Python 3.12 + pytest (fork), bash + Python unittest (research-claude), `claude -p` live evals.

**Spec:** The Context section below (the 2026-09-29 analysis session). There is no separate spec document.

## Context (the spec)

Established 2026-09-29, each finding checked by reading the file or running the command:

- **Paper repos:** all six have `.claude/skills/{ztp-*,seed-papers}` as symlinks into `research-claude/zotpilot-skills/` (`apply.sh:172-175`).
- **Shadow copy:** `~/.claude/skills/ztp-{profile,research,review,setup,tutor}` are real directories, each with a `.zotpilot-version.json`. They were written by `deploy_skills()` (`src/zotpilot/_platforms.py:794`) via `reconcile_runtime` → `apply_runtime_changes`, which is what `register`, `setup` and `upgrade` all call.
- **Precedence (per docs, code.claude.com/docs/en/skills "Resolve skills that share a name"):** "Enterprise over personal, and personal over project." **Tested:** the NAR_settlement session transcript `88e46716…jsonl` loaded `Base directory for this skill: /Users/andrew.mueller/.claude/skills/ztp-research`. That project has its own linked copy.
- **Our copy is behind the fork:** `zotpilot-skills/` is at fork `6e63dd8`. Fork `main` is at `5e5e65a`, and fork commit `6057e79` changed `claude-skills/ztp-research/SKILL.md` (target library, `select_zotero_library`, `save_unconfirmed`). The shadow copy has that change; ours does not. Deleting the shadow copies before a re-sync would downgrade every paper.
- **A `~/Research` skills folder won't load in paper sessions:** `~/Research` is not a git repo, and each paper is its own repo root. Per docs, project skills load from the start directory "and in every parent directory up to the repository root". Skills in `~/Research/.claude/skills/` therefore load only in sessions started in `~/Research` itself.
- **Course sessions load the shadow copies too.** `~/.claude/skills` loads everywhere, including `~/Courses`, which breaks the domain split in `~/.claude/CLAUDE.md`.
- **OpenCode** has the same deployed copies in `~/.config/opencode/skills/ztp-*`. `~/.agents/skills` (Codex) does not exist.
- **Adjacent bug (tested):** `_coerce_value("oa_pdf_upload", "false")` returns the string `'false'`, and `Config.load` computes `bool('false') == True`. So `zotpilot config set oa_pdf_upload false` **enables** Web-API PDF uploads, which `~/.claude/CLAUDE.md` forbids. The new key needs the same coercion path, so both are fixed together.
- **The fork already has a sync test for its own two copies:** `tests/test_skill_sources_in_sync.py` requires `src/zotpilot/skills/*.md` and `claude-skills/*/SKILL.md` to be byte-identical. No work needed there.

## Global Constraints

- The fork `EconGeo/ZotPilot` is the only source. Never vendor from upstream `xunhe730/ZotPilot`; never install from PyPI (`zotpilot-skills/VENDORED.md`).
- `~/projects/zotpilot` is an **editable install and it IS the live MCP server.** Do all fork work in a git worktree. Never `git checkout` a branch in `~/projects/zotpilot`.
- Fork test command (subset runs must pass `--no-cov`; the repo's coverage floor fails any partial run): `cd <worktree> && PYTHONPATH=src ~/micromamba/envs/zotpilot/bin/python -m pytest -q --no-cov <tests>`
- Local commits only. Pushing a branch, opening a PR, and merging on GitHub each need the user's explicit OK.
- In research-claude: branch first, since `scripts/`, `tests/` and `zotpilot-skills/` edits are live through links. Run `./scripts/check_fork.sh` (exit 0) before any commit touching a shipped dir.
- Live evals: **never** set `EVAL_TIMEOUT` or add any timeout (CLAUDE.md, user ruling 2026-09-25).
- No project, journal or dataset name in `agents/ skills/ rules/ hooks/ templates/`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A `ztp-*` directory in `~/.claude/skills` that ZotPilot did not write** (no `.zotpilot-version.json`, or a symlink) must never be deleted by undeploy. Pinned in Task 2, `test_undeploy_removes_only_marked_real_dirs`.
2. **A hand-edited `config.json` with `"deploy_skills": "false"` (a string)** must mean false, not `bool("false") == True`. Pinned in Task 1, `test_string_false_is_false`.
3. **A `config.json` that `Config.load` rejects** (e.g. an invalid `chunker_backend`) must still honour `deploy_skills: false`. Otherwise one bad key silently re-deploys the shadow copies. Pinned in Task 2, `test_deploy_setting_read_despite_invalid_config`.
4. **A personal skill that is a symlink to the same `zotpilot-skills/` directory** is not a shadow (per docs, same target loads once) and must not fail `check_install`. Pinned in Task 5, `test_symlink_to_same_target_is_not_a_shadow`.
5. **`check_install --all` with no network** must WARN, not FAIL, on the fork-freshness check. Pinned in Task 5, `test_fork_unreachable_warns`.

---

### Task 1: Fork — `deploy_skills` config key and strict boolean coercion

**Repo:** fork worktree. Create it first:

```bash
git -C ~/projects/zotpilot fetch -q origin
git -C ~/projects/zotpilot worktree add ~/projects/zotpilot-deploy-optout -b feat/deploy-skills-opt-out origin/main
cd ~/projects/zotpilot-deploy-optout
```

**Files:**
- Modify: `src/zotpilot/config.py` (the `Config` dataclass after `oa_pdf_upload`, `load()`, `save()`)
- Modify: `src/zotpilot/cli.py:666-672` (`_SCALAR_TYPES`)
- Test: `tests/test_config_bool_fields.py` (create)

**Interfaces:**
- Produces: `Config.deploy_skills: bool` (default `True`); `zotpilot.config._as_bool(value, default: bool) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config_bool_fields.py
"""Boolean config fields must coerce from the CLI and from hand-edited JSON alike.

`zotpilot config set oa_pdf_upload false` used to store the string "false", and
Config.load's bool("false") read it back as True — enabling the very upload the
setting exists to disable.
"""
from __future__ import annotations

import json

import pytest

from zotpilot.cli import _coerce_value
from zotpilot.config import Config


@pytest.mark.parametrize("key", ["oa_pdf_upload", "deploy_skills"])
def test_cli_coerces_false_to_bool(key):
    assert _coerce_value(key, "false") is False
    assert _coerce_value(key, "true") is True


def test_deploy_skills_defaults_true(tmp_path):
    assert Config.load(tmp_path / "missing.json").deploy_skills is True


def test_deploy_skills_false_round_trips(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"deploy_skills": False}))
    cfg = Config.load(path)
    assert cfg.deploy_skills is False
    cfg.save(path)
    assert json.loads(path.read_text())["deploy_skills"] is False


@pytest.mark.parametrize("key", ["oa_pdf_upload", "deploy_skills"])
def test_string_false_is_false(tmp_path, key):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({key: "false"}))
    assert getattr(Config.load(path), key) is False
```

- [ ] **Step 2: Run and confirm they fail**

Run: `PYTHONPATH=src ~/micromamba/envs/zotpilot/bin/python -m pytest -q --no-cov tests/test_config_bool_fields.py`
Expected: FAIL. `_coerce_value` returns `'false'`; `Config` has no `deploy_skills`.

- [ ] **Step 3: Implement**

In `src/zotpilot/config.py`, add above `@dataclass class Config`:

```python
def _as_bool(value, default: bool) -> bool:
    """A config boolean, accepting a hand-edited "true"/"false" string as well as JSON bools.

    bool("false") is True, which is how `oa_pdf_upload: "false"` once enabled uploads.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    if value is None:
        return default
    return bool(value)
```

After the `oa_pdf_upload: bool = False` field:

```python
    # Copy the packaged ztp-* skills into each client's user-level skills dir
    # (~/.claude/skills, ...) on register/setup/upgrade. Set false when a project
    # pipeline vendors the skills itself: a user-level copy outranks a project copy
    # of the same name in Claude Code, so it would silently replace the vendored one.
    deploy_skills: bool = True
```

In `load()`, replace `oa_pdf_upload=bool(data.get("oa_pdf_upload", False)),` with:

```python
            oa_pdf_upload=_as_bool(data.get("oa_pdf_upload"), False),
            deploy_skills=_as_bool(data.get("deploy_skills"), True),
```

In `save()`, after `"oa_pdf_upload": self.oa_pdf_upload,` add `"deploy_skills": self.deploy_skills,`.

In `src/zotpilot/cli.py`, change `_SCALAR_TYPES` to end:

```python
    "embedding_dimensions": int, "preflight_enabled": bool,
    "oa_pdf_upload": bool, "deploy_skills": bool,
}
```

- [ ] **Step 4: Run and confirm they pass, then run the existing config tests**

Run: `PYTHONPATH=src ~/micromamba/envs/zotpilot/bin/python -m pytest -q --no-cov tests/test_config_bool_fields.py tests/test_ingest_library_targeting.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/zotpilot/config.py src/zotpilot/cli.py tests/test_config_bool_fields.py
git commit -m "fix(config): coerce boolean fields strictly; add deploy_skills

\`config set oa_pdf_upload false\` stored the string \"false\", which Config.load
read back as True. deploy_skills (default true) gates user-level skill deployment.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Fork — reconcile honours `deploy_skills: false` (no deploy, remove own copies, clean drift)

**Files:**
- Modify: `src/zotpilot/_platforms.py`: dataclasses `PlatformRuntimeState`, `DesiredRuntime`, `ChangeSet`, `ApplyResult` (lines ~79-122); `inspect_current_state` (~445); `plan_runtime_changes` (~490); `apply_runtime_changes` (~527); `reconcile_runtime` (~552); `register` (~1009); new `_managed_skill_dirs`, `_skill_deploy_enabled`, `undeploy_skills` next to `deploy_skills` (~794)
- Modify: `claude-skills/ztp-setup/SKILL.md` step 7 **and** `src/zotpilot/skills/ztp-setup.md` step 7 (byte-identical; `tests/test_skill_sources_in_sync.py` enforces it)
- Test: `tests/test_skill_deploy_opt_out.py` (create)

**Interfaces:**
- Consumes: `Config.deploy_skills` (Task 1) — but read from raw JSON, not via `Config.load` (Review Focus 3).
- Produces: `DesiredRuntime.deploy_skills: bool = True`; `PlatformRuntimeState.managed_skill_dirs: tuple[str, ...] = ()`; `ChangeSet.undeploy_skill_platforms: tuple[str, ...] = ()`; `ApplyResult.undeployed: tuple[str, ...] = ()`; `undeploy_skills(platforms: list[str]) -> dict[str, bool]`; `_skill_deploy_enabled(config_path: Path | None = None) -> bool`; drift reason string `"skills-deployed-while-disabled"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_skill_deploy_opt_out.py
"""deploy_skills=false: reconcile neither deploys nor reports drift for missing skills,
and removes only the skill dirs ZotPilot itself deployed (real dir + version marker)."""
from __future__ import annotations

import json
from unittest.mock import patch

from zotpilot._platforms import (
    DesiredRuntime,
    PlatformRuntimeState,
    RuntimeState,
    _skill_deploy_enabled,
    _skill_source_files,
    plan_runtime_changes,
    reconcile_runtime,
    undeploy_skills,
)


def _state(**kw) -> RuntimeState:
    base = dict(platform="claude-code", label="Claude Code", supported=True, detected=True,
                registered=True, command="/usr/bin/zotpilot", args=("mcp", "serve"), env={},
                skill_hash_ok=False)
    base.update(kw)
    return RuntimeState("0.5.0", ("claude-code",), {"claude-code": PlatformRuntimeState(**base)})


def _desired(deploy: bool) -> DesiredRuntime:
    return DesiredRuntime(command="/usr/bin/zotpilot", args=("mcp", "serve"), env={},
                          targets=("claude-code",), deploy_skills=deploy)


def test_disabled_and_absent_is_clean():
    changes = plan_runtime_changes(_desired(False), _state())
    assert changes.deploy_skill_platforms == ()
    assert changes.undeploy_skill_platforms == ()
    assert changes.drift_state == "clean"


def test_disabled_with_deployed_copies_undeploys():
    changes = plan_runtime_changes(_desired(False), _state(managed_skill_dirs=("/h/.claude/skills/ztp-research",)))
    assert changes.undeploy_skill_platforms == ("claude-code",)
    assert changes.deploy_skill_platforms == ()
    assert changes.reasons["claude-code"] == ["skills-deployed-while-disabled"]
    assert changes.drift_state == "needs-sync"


def test_enabled_behaviour_unchanged():
    changes = plan_runtime_changes(_desired(True), _state())
    assert changes.deploy_skill_platforms == ("claude-code",)
    assert changes.undeploy_skill_platforms == ()


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path / ".claude" / "skills"


def test_undeploy_removes_only_marked_real_dirs(tmp_path, monkeypatch):
    skills = _home(tmp_path, monkeypatch)
    names = [p.stem for p in _skill_source_files()]
    marked, unmarked, linked = names[0], names[1], names[2]
    (skills / marked).mkdir(parents=True)
    (skills / marked / "SKILL.md").write_text("x")
    (skills / marked / ".zotpilot-version.json").write_text("{}")
    (skills / unmarked).mkdir()
    (skills / unmarked / "SKILL.md").write_text("hand-made")
    elsewhere = tmp_path / "vendored" / linked
    elsewhere.mkdir(parents=True)
    (elsewhere / ".zotpilot-version.json").write_text("{}")
    (skills / linked).symlink_to(elsewhere)

    assert undeploy_skills(["claude-code"]) == {"claude-code": True}
    assert not (skills / marked).exists()
    assert (skills / unmarked / "SKILL.md").read_text() == "hand-made"
    assert (skills / linked).is_symlink() and elsewhere.is_dir()


def _write_config(tmp_path, data):
    cfg = tmp_path / ".config" / "zotpilot" / "config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps(data))
    return cfg


def test_deploy_setting_read_despite_invalid_config(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    cfg = _write_config(tmp_path, {"deploy_skills": False, "chunker_backend": "bogus"})
    assert _skill_deploy_enabled(cfg) is False


def test_deploy_setting_defaults_true(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert _skill_deploy_enabled(tmp_path / "nope.json") is True


def test_reconcile_end_to_end_plans_undeploy(tmp_path, monkeypatch):
    skills = _home(tmp_path, monkeypatch)
    _write_config(tmp_path, {"deploy_skills": False})
    name = _skill_source_files()[0].stem
    (skills / name).mkdir(parents=True)
    (skills / name / ".zotpilot-version.json").write_text("{}")
    from zotpilot._platforms import _runtime_invocation
    cmd, args = _runtime_invocation()
    with (
        patch("zotpilot._platforms.detect_platforms", return_value=["claude-code"]),
        patch("zotpilot._platforms._inspect_registration", return_value=(True, cmd, args, {}, None)),
    ):
        result = reconcile_runtime(platforms=["claude-code"], apply=False)
    assert result.desired.deploy_skills is False
    assert result.changes.undeploy_skill_platforms == ("claude-code",)
    assert result.changes.deploy_skill_platforms == ()
```

- [ ] **Step 2: Run and confirm they fail**

Run: `PYTHONPATH=src ~/micromamba/envs/zotpilot/bin/python -m pytest -q --no-cov tests/test_skill_deploy_opt_out.py`
Expected: FAIL. `ImportError: cannot import name '_skill_deploy_enabled'`.

- [ ] **Step 3: Implement**

Dataclasses (append each new field last, with a default, so existing positional constructions such as `ChangeSet(("codex",), ("codex",), "needs-sync", {...})` in `tests/test_reconcile_runtime.py` keep working):

```python
# PlatformRuntimeState — after registration_hash_ok
    managed_skill_dirs: tuple[str, ...] = ()

# DesiredRuntime — after source_dir
    deploy_skills: bool = True

# ChangeSet — after reasons
    undeploy_skill_platforms: tuple[str, ...] = ()

# ApplyResult — after restart_required
    undeployed: tuple[str, ...] = ()
```

Next to `deploy_skills()`:

```python
def _skill_deploy_enabled(config_path: Path | None = None) -> bool:
    """The ``deploy_skills`` setting, read straight from config.json.

    Not via Config.load: that raises on unrelated invalid keys, and falling back to
    "deploy" there would silently re-create the user-level copies this switch removes.
    """
    from .config import _as_bool, _default_config_dir
    path = config_path or (_default_config_dir() / "config.json")
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return _as_bool(data.get("deploy_skills") if isinstance(data, dict) else None, True)


def _managed_skill_dirs(plat: str) -> tuple[str, ...]:
    """Skill dirs for ``plat`` that ZotPilot itself deployed: a real directory carrying its
    version marker. A symlink or an unmarked directory belongs to something else."""
    skills_dir = PLATFORMS.get(plat, {}).get("skills_dir")
    if not skills_dir:
        return ()
    base = Path(skills_dir).expanduser()
    found = []
    for source in _skill_source_files():
        target = base / _skill_name_for_file(source)
        if target.is_dir() and not target.is_symlink() and _version_marker_path(target).is_file():
            found.append(str(target))
    return tuple(found)


def undeploy_skills(platforms: list[str]) -> dict[str, bool]:
    """Remove the skill dirs ZotPilot deployed (``deploy_skills`` is false)."""
    results: dict[str, bool] = {}
    for plat in platforms:
        ok = True
        for path in _managed_skill_dirs(plat):
            try:
                shutil.rmtree(path)
                print(f"  {PLATFORMS[plat]['label']}: removed {path} (deploy_skills is false)")
            except OSError as exc:
                print(f"  ERROR: could not remove {path}: {exc}", file=sys.stderr)
                ok = False
        results[plat] = ok
    return results
```

`inspect_current_state`: pass `managed_skill_dirs=_managed_skill_dirs(plat),` into `PlatformRuntimeState(...)`.

`plan_runtime_changes`: add `undeploy: list[str] = []` beside `deploy`, and replace

```python
        if not state.skill_hash_ok:
            deploy.append(plat)
            platform_reasons.append("skills-out-of-sync")
```

with

```python
        if desired.deploy_skills:
            if not state.skill_hash_ok:
                deploy.append(plat)
                platform_reasons.append("skills-out-of-sync")
        elif state.managed_skill_dirs:
            undeploy.append(plat)
            platform_reasons.append("skills-deployed-while-disabled")
```

and add `undeploy_skill_platforms=tuple(dict.fromkeys(undeploy)),` to the returned `ChangeSet`.

`apply_runtime_changes`: after the deploy block,

```python
    undeployed: list[str] = []
    if changes.undeploy_skill_platforms:
        undeploy_results = undeploy_skills(list(changes.undeploy_skill_platforms))
        undeployed = [plat for plat, ok in undeploy_results.items() if ok]
```

and return `ApplyResult(deployed=..., registered=..., restart_required=bool(deployed or registered or undeployed), undeployed=tuple(undeployed))`.

`reconcile_runtime`: add `deploy_skills=_skill_deploy_enabled(),` to `DesiredRuntime(...)`.

`register`: extend the per-platform result with a third conjunct:

```python
        ) and (
            plat not in result.changes.undeploy_skill_platforms
            or plat in result.applied.undeployed
        )
```

`ztp-setup` step 7, in **both** `claude-skills/ztp-setup/SKILL.md` and `src/zotpilot/skills/ztp-setup.md`. Replace the line `7. MCP registration and skill deployment are included in \`zotpilot setup\`. Advanced repair only: \`zotpilot install\` (alias: \`zotpilot register\`).` with:

```markdown
7. MCP registration and skill deployment are included in `zotpilot setup`. Advanced repair only: `zotpilot install` (alias: `zotpilot register`).

   **Skill deployment can be turned off.** When a project pipeline ships these skills itself,
   a user-level copy (`~/.claude/skills/ztp-*`) outranks the project's copy of the same name,
   so run `zotpilot config set deploy_skills false` and then `zotpilot register`: it stops
   deploying and removes the copies it deployed before. Never re-enable it to "fix" a missing
   skill in that setup — re-link the project instead.
```

- [ ] **Step 4: Run the new tests, then the whole suite with coverage**

Run: `PYTHONPATH=src ~/micromamba/envs/zotpilot/bin/python -m pytest -q --no-cov tests/test_skill_deploy_opt_out.py tests/test_reconcile_runtime.py tests/test_skill_sources_in_sync.py tests/test_platforms_cross.py`
Expected: all PASS.
Run: `PYTHONPATH=src ~/micromamba/envs/zotpilot/bin/python -m pytest -q 2>&1 | tail -5`
Expected: PASS, with the coverage floor met.

- [ ] **Step 5: Commit**

```bash
git add src/zotpilot/_platforms.py claude-skills/ztp-setup/SKILL.md src/zotpilot/skills/ztp-setup.md tests/test_skill_deploy_opt_out.py
git commit -m "feat(platforms): deploy_skills=false stops user-level skill deployment

Reconcile no longer deploys ztp-* skills or reports their absence as drift, and
removes the copies it deployed earlier (marker-bearing real dirs only). A
user-level skill outranks a project skill of the same name in Claude Code, so a
pipeline that vendors these skills needs them absent from ~/.claude/skills.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Fork — land on `main` (user-gated)

- [ ] **Step 1:** Ask the user for OK to push `feat/deploy-skills-opt-out` and open a PR on `EconGeo/ZotPilot`. Do not push without it.
- [ ] **Step 2:** On OK: `git push -u origin feat/deploy-skills-opt-out`, then `gh pr create --repo EconGeo/ZotPilot --base main` with a body summarising Tasks 1-2 and ending with the 🤖 attribution line.
- [ ] **Step 3:** Merge only on the user's explicit OK (`gh pr merge --merge`). Then `git -C ~/projects/zotpilot pull --ff-only` (the live editable install; `main` is checked out there) and `git -C ~/projects/zotpilot worktree remove ~/projects/zotpilot-deploy-optout`.
- [ ] **Step 4:** Confirm the live install has the change:
  `~/micromamba/envs/zotpilot/bin/python -c "from zotpilot.config import Config; print(Config.load().deploy_skills)"`
  Expected: `True` (the key is not set yet; Task 6 sets it).

---

### Task 4: research-claude — sync script gains `--check`, writes its own provenance line; re-sync

**Repo:** `~/Academic/research-claude`, on the branch `zotpilot-skills-single-source` (created with this plan): `git switch zotpilot-skills-single-source`.

**Files:**
- Modify: `scripts/sync-zotpilot-skills.sh`
- Modify: `zotpilot-skills/**` (re-synced), `zotpilot-skills/VENDORED.md`
- Test: `tests/test_sync_zotpilot_skills.py` (create)

**Interfaces:**
- Produces: `scripts/sync-zotpilot-skills.sh --check [ref]`. Exit codes: 0 = identical to the fork, 1 = differs (nothing written), anything else = fetch failed. `ZOTPILOT_FORK_URL` overrides the fork URL (tests only). A normal sync rewrites the `- Vendored from commit:` line itself.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sync_zotpilot_skills.py
"""sync-zotpilot-skills.sh against a local stand-in fork: --check reports drift without
writing; a real sync overwrites and records the source commit in VENDORED.md itself."""
import os, pathlib, shutil, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(*a, cwd=None, env=None):
    return subprocess.run(list(a), cwd=cwd, env=env, capture_output=True, text=True)

class TestSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.fork = t / "fork"; (self.fork / "claude-skills" / "ztp-x").mkdir(parents=True)
        (self.fork / "claude-skills" / "ztp-x" / "SKILL.md").write_text("new\n")
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(self.fork)]
        run("git", "init", "-q", "-b", "main", str(self.fork)); run(*g, "add", "-A"); run(*g, "commit", "-qm", "c")
        self.sha = run(*g, "rev-parse", "--short", "HEAD").stdout.strip()
        self.rc = t / "rc"; (self.rc / "scripts").mkdir(parents=True)
        shutil.copy(ROOT / "scripts" / "sync-zotpilot-skills.sh", self.rc / "scripts")
        dest = self.rc / "zotpilot-skills" / "ztp-x"; dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("old\n")
        (self.rc / "zotpilot-skills" / "VENDORED.md").write_text("- Vendored from commit: `aaaaaaa` (old)\n")
        self.env = dict(os.environ, ZOTPILOT_FORK_URL=f"file://{self.fork}")
    def tearDown(self): self.tmp.cleanup()
    def sync(self, *a): return run("bash", str(self.rc / "scripts" / "sync-zotpilot-skills.sh"), *a, env=self.env)

    def test_check_reports_drift_and_writes_nothing(self):
        r = self.sync("--check")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual((self.rc / "zotpilot-skills" / "ztp-x" / "SKILL.md").read_text(), "old\n")

    def test_sync_overwrites_and_records_commit(self):
        self.assertEqual(self.sync().returncode, 0)
        self.assertEqual((self.rc / "zotpilot-skills" / "ztp-x" / "SKILL.md").read_text(), "new\n")
        self.assertIn(f"`{self.sha}`", (self.rc / "zotpilot-skills" / "VENDORED.md").read_text())
        self.assertEqual(self.sync("--check").returncode, 0)

    def test_unreachable_fork_is_not_exit_1(self):
        self.env["ZOTPILOT_FORK_URL"] = f"file://{self.rc}/no-such-repo"
        self.assertNotIn(self.sync("--check").returncode, (0, 1))

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2: Run and confirm they fail**

Run: `python3 -m pytest -q tests/test_sync_zotpilot_skills.py`
Expected: FAIL. `--check` is treated as a git ref, and the URL is not overridable.

- [ ] **Step 3: Implement.** In `scripts/sync-zotpilot-skills.sh`, replace the usage comment and the argument/URL lines:

```bash
# Usage:  ./scripts/sync-zotpilot-skills.sh [--check] [git-ref]
#   git-ref defaults to the fork's default branch.
#   --check  compare only: exit 0 identical, 1 differs (nothing written), other = fetch failed.
#   ZOTPILOT_FORK_URL overrides the fork URL (tests only).

set -euo pipefail

FORK_URL="${ZOTPILOT_FORK_URL:-https://github.com/EconGeo/ZotPilot.git}"
CHECK=false
if [[ "${1:-}" == "--check" ]]; then CHECK=true; shift; fi
REF="${1:-}"
```

Make the clone quiet on stderr (`git clone --quiet ... 2>/dev/null || { echo "Error: could not fetch $FORK_URL" >&2; exit 3; }`). After `SRC_COMMIT=...`, insert:

```bash
if [[ "$CHECK" == true ]]; then
  if diff -rq --exclude=VENDORED.md "$TMP/zp/claude-skills" "$DEST" >/dev/null 2>&1; then
    echo "✓ zotpilot-skills/ matches EconGeo/ZotPilot@${SRC_COMMIT}"; exit 0
  fi
  echo "✗ zotpilot-skills/ differs from EconGeo/ZotPilot@${SRC_COMMIT} — run scripts/sync-zotpilot-skills.sh:"
  diff -rq --exclude=VENDORED.md "$TMP/zp/claude-skills" "$DEST" | sed 's/^/    /'
  exit 1
fi
```

Replace the three trailing `echo` lines with:

```bash
if [[ -f "$DEST/VENDORED.md" ]]; then
  perl -pi -e "s/^- Vendored from commit: .*/- Vendored from commit: \`${SRC_COMMIT}\` (synced $(date +%F) by scripts\/sync-zotpilot-skills.sh)/" "$DEST/VENDORED.md"
fi
echo "✓ Refreshed zotpilot-skills/ from EconGeo/ZotPilot@${SRC_COMMIT} — review the diff and commit."
```

- [ ] **Step 4: Run tests, then sync for real**

Run: `python3 -m pytest -q tests/test_sync_zotpilot_skills.py` → Expected: 3 passed.
Run: `./scripts/sync-zotpilot-skills.sh && git diff --stat -- zotpilot-skills/`
Expected: `ztp-research/SKILL.md` (the `6057e79` change), `ztp-setup/SKILL.md` (Task 2 step 7) and `VENDORED.md` change; the skill set is unchanged. Read the full diff before committing.
Run: `./scripts/sync-zotpilot-skills.sh --check` → Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
./scripts/check_fork.sh
git add scripts/sync-zotpilot-skills.sh tests/test_sync_zotpilot_skills.py zotpilot-skills/
git commit -m "zotpilot-skills: re-sync to fork main; sync script gains --check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: research-claude — `check_install` fails on a shadowing personal skill; warns on fork drift

**Files:**
- Modify: `scripts/check_install.sh`: new check 4b after check 4 (`link-target`, ~line 189); fork-freshness block in the `--all` branch (~line 336)
- Test: `tests/test_check_install_personal_shadow.py` (create)

**Interfaces:**
- Consumes: `sync-zotpilot-skills.sh --check` exit codes (Task 4).
- Produces: check names `personal-shadow` (FAIL) and `zotpilot-vendored` (PASS/WARN). Env `CLAUDE_PERSONAL_SKILLS_DIR` (default `$HOME/.claude/skills`) and `ZOTPILOT_FORK_URL` are overridable for tests.

- [ ] **Step 1: Write the failing tests** (fixture pattern copied from `tests/test_check_install.py`)

```python
# tests/test_check_install_personal_shadow.py
"""check_install.sh `personal-shadow`: a user-level skill with a project skill's name runs
instead of it (Claude Code: personal over project), so it FAILs — unless both are the same
target. `zotpilot-vendored` (--all only) WARNs, never FAILs, when the fork is unreachable."""
import os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "check_install.sh")

class TestPersonalShadow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "agents").mkdir(parents=True); (self.rc / "skills" / "ztp-x").mkdir(parents=True)
        (self.rc / "agents" / "a.md").write_text("a\n"); (self.rc / "skills" / "ztp-x" / "SKILL.md").write_text("s\n")
        self.p = t / "proj"; (self.p / ".claude" / "skills").mkdir(parents=True)
        os.symlink(self.rc / "skills" / "ztp-x", self.p / ".claude" / "skills" / "ztp-x")
        self.home = t / "home-skills"; self.home.mkdir()
    def tearDown(self): self.tmp.cleanup()
    def line(self, check):
        env = dict(os.environ, CLAUDE_PERSONAL_SKILLS_DIR=str(self.home))
        out = subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True, env=env).stdout
        return next((l for l in out.splitlines() if f"[{check}]" in l), "")

    def test_no_personal_copy_passes(self):
        self.assertTrue(self.line("personal-shadow").startswith("PASS"), self.line("personal-shadow"))

    def test_real_personal_copy_fails(self):
        (self.home / "ztp-x").mkdir(); (self.home / "ztp-x" / "SKILL.md").write_text("other\n")
        l = self.line("personal-shadow")
        self.assertTrue(l.startswith("FAIL") and "ztp-x" in l, l)

    def test_symlink_to_same_target_is_not_a_shadow(self):
        os.symlink(self.rc / "skills" / "ztp-x", self.home / "ztp-x")
        self.assertTrue(self.line("personal-shadow").startswith("PASS"), self.line("personal-shadow"))

class TestForkFreshness(unittest.TestCase):
    def test_fork_unreachable_warns(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, RESEARCH_DIR=d, ZOTPILOT_FORK_URL=f"file://{d}/no-such-repo")
            out = subprocess.run(["bash", SCRIPT, "--all"], capture_output=True, text=True, env=env).stdout
            l = next((x for x in out.splitlines() if "[zotpilot-vendored]" in x), "")
            self.assertTrue(l.startswith("WARN"), out)

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2: Run and confirm they fail**

Run: `python3 -m pytest -q tests/test_check_install_personal_shadow.py`
Expected: FAIL. No `[personal-shadow]` or `[zotpilot-vendored]` line exists yet.

- [ ] **Step 3: Implement.** After the `link-target` block (the `else ok link-target …; fi` line), insert:

```bash
  # ── 4b. No personal skill shadows a project skill ─────────────────────────
  # Claude Code runs ~/.claude/skills/<name> INSTEAD of .claude/skills/<name> when both
  # exist ("personal over project", code.claude.com/docs/en/skills). `zotpilot register`
  # deployed exactly that for every ztp-* skill until deploy_skills=false (2026-09-29):
  # every paper silently ran the fork's user-level copies, not zotpilot-skills/.
  # A personal entry resolving to the same directory loads once and is not a shadow.
  local HOME_SKILLS="${CLAUDE_PERSONAL_SKILLS_DIR:-$HOME/.claude/skills}" shadow=() n
  if [[ -d "$P/.claude/skills" && -d "$HOME_SKILLS" ]]; then
    for l in "$P/.claude/skills"/*; do
      n="$(basename "$l")"
      [[ -e "$HOME_SKILLS/$n" || -L "$HOME_SKILLS/$n" ]] || continue
      [[ "$(cd "$HOME_SKILLS/$n" 2>/dev/null && pwd -P)" == "$(cd "$l" 2>/dev/null && pwd -P)" ]] && continue
      shadow+=("$n")
    done
  fi
  if [[ ${#shadow[@]} -gt 0 ]]; then
    bad personal-shadow "${#shadow[@]} skill(s) in $HOME_SKILLS run instead of this project's: ${shadow[*]}"
    echo "    (ZotPilot: zotpilot config set deploy_skills false && zotpilot register)"
  else ok personal-shadow "no personal skill overrides a project skill"; fi
```

In the `--all` branch, after the `for p in …; done` loop:

```bash
  # Vendored ZotPilot skills vs the fork. Network, so WARN-only; exit 1 = differs.
  zp_out="$("$(dirname "$0")/sync-zotpilot-skills.sh" --check 2>&1)"; zp_rc=$?
  case $zp_rc in
    0) ok zotpilot-vendored "zotpilot-skills/ matches the fork" ;;
    1) warn zotpilot-vendored "zotpilot-skills/ is behind the fork — run scripts/sync-zotpilot-skills.sh"
       printf '%s\n' "$zp_out" | sed -n '2,6p' ;;
    *) warn zotpilot-vendored "could not reach the fork (offline?) — freshness not checked" ;;
  esac
```

- [ ] **Step 4: Run the new and existing check_install tests**

Run: `python3 -m pytest -q tests/test_check_install_personal_shadow.py tests/test_check_install.py tests/test_check_install_clone_links.py`
Expected: all PASS.
Run: `./scripts/check_install.sh --all 2>&1 | grep -E 'personal-shadow|zotpilot-vendored|check_install:'`
Expected **before Task 6**: `FAIL [personal-shadow] … ztp-profile ztp-research ztp-review ztp-setup ztp-tutor` in each of the six projects. That is the red this gate exists for. `PASS [zotpilot-vendored]`.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_install.sh tests/test_check_install_personal_shadow.py
git commit -m "check_install: fail on a personal skill shadowing a project skill; warn on fork drift

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Go live — turn deployment off, remove the shadow copies, cover `~/Research` root sessions

**Files:**
- Create: `scripts/link-zotpilot-skills.sh`
- Machine state (not in a repo): `~/.config/zotpilot/config.json`, `~/.claude/skills/ztp-*`, `~/.config/opencode/skills/ztp-*`, `~/Research/.claude/skills/`

**Interfaces:**
- Consumes: Task 2 (`deploy_skills`, undeploy), Task 4 (re-synced copy), Task 5 (`personal-shadow`).
- Produces: `scripts/link-zotpilot-skills.sh <dir>`, which links each `zotpilot-skills/*/` into `<dir>/.claude/skills/` and leaves a real directory there alone.

- [ ] **Step 1: Turn deployment off and reconcile**

```bash
zotpilot config set deploy_skills false
zotpilot register 2>&1 | tail -15
```

Expected: five `Claude Code: removed …/.claude/skills/ztp-*` lines and five `OpenCode: removed …` lines.

- [ ] **Step 2: Verify**

```bash
ls ~/.claude/skills | grep -E '^(ztp-|seed-papers)' || echo "none"      # → none
zotpilot doctor 2>&1 | grep -E 'Drift|Restart'                          # → Drift: clean · Restart: no
zotpilot register 2>&1 | grep -c removed                                # → 0 (idempotent; nothing re-deployed)
./scripts/check_install.sh --all 2>&1 | grep -E 'personal-shadow|check_install:'   # → PASS ×6, ✓ PASS
```

- [ ] **Step 3: `~/Research` root sessions.** A session started in `~/Research` (not a git repo) loads `~/Research/.claude/skills/`. Create `scripts/link-zotpilot-skills.sh`:

```bash
#!/usr/bin/env bash
# link-zotpilot-skills.sh <dir> — link each vendored ZotPilot skill into <dir>/.claude/skills/.
# For a directory that is not a paper project but hosts sessions (the research root), so it
# loads the same zotpilot-skills/ copy the papers do. A real directory there is left alone.
set -euo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
DIR="$(cd "${1:?usage: link-zotpilot-skills.sh <dir>}" && pwd -P)"
mkdir -p "$DIR/.claude/skills"
for s in "$RC/zotpilot-skills"/*/; do
  n="$(basename "$s")"; t="$DIR/.claude/skills/$n"
  if [[ -e "$t" && ! -L "$t" ]]; then echo "  ⤷ $n is a real directory — left alone"; continue; fi
  ln -sfn "$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "${s%/}" "$DIR/.claude/skills")" "$t"
  echo "  $n -> zotpilot-skills/$n"
done
```

Run: `chmod +x scripts/link-zotpilot-skills.sh && ./scripts/link-zotpilot-skills.sh ~/Research && ls -la ~/Research/.claude/skills | grep -E 'ztp-|seed'`
Expected: six symlinks into `research-claude/zotpilot-skills/`.

- [ ] **Step 4: Live proof, one skill.** Start a session with the ZotPilot mock (the harness registers it). Record which copy loaded:

```bash
KEEP=1 bash tests/evals/ztp-research.sh
grep -o 'Base directory for this skill: [^"\\]*' <kept-dir>/eval.stream.jsonl
```

Expected: `…/<kept-dir>/.claude/skills/ztp-research`, not `~/.claude/skills/…`. No timeout (Global Constraints).

- [ ] **Step 5: Commit**

```bash
git add scripts/link-zotpilot-skills.sh
git commit -m "scripts: link-zotpilot-skills.sh for non-project session roots

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Evals assert the project copy loaded

**Files:**
- Modify: `tests/evals/evallib.py` (new function `skills_loaded_outside_project`)
- Modify: `tests/evals/check_ztp_research.py`, `check_ztp_review.py`, `check_ztp_profile.py`, `check_ztp_tutor.py`, `check_seed_papers.py` (one line each, just before `evallib.finish(...)`)
- Test: `tests/test_evallib_skill_origin.py` (create)

**Interfaces:**
- Produces: `evallib.skills_loaded_outside_project(transcript_path) -> list[str]`: the base directories of `ztp-*`/`seed-papers` skill loads that were not under `<transcript dir>/.claude/skills/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_evallib_skill_origin.py
import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "evals"))
import evallib

def transcript(d, base):
    line = {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": f"Base directory for this skill: {base}\n\n# ZTP"}]}}
    p = pathlib.Path(d) / "eval.stream.jsonl"; p.write_text(json.dumps(line) + "\n"); return p

class T(unittest.TestCase):
    def test_project_copy_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evallib.skills_loaded_outside_project(transcript(d, f"{d}/.claude/skills/ztp-research")), [])
    def test_personal_copy_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evallib.skills_loaded_outside_project(transcript(d, "/Users/x/.claude/skills/ztp-research")),
                             ["/Users/x/.claude/skills/ztp-research"])
    def test_unrelated_skill_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evallib.skills_loaded_outside_project(transcript(d, "/Users/x/.claude/skills/regression-table")), [])

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2: Run and confirm it fails**

Run: `python3 -m pytest -q tests/test_evallib_skill_origin.py`
Expected: FAIL, `AttributeError: … has no attribute 'skills_loaded_outside_project'`.

- [ ] **Step 3: Implement.** In `tests/evals/evallib.py`, before `finish`:

```python
_BASE_DIR = re.compile(r"Base directory for this skill: (.+?)(?:\n|$)")


def skills_loaded_outside_project(path) -> list[str]:
    """Base dirs of ZotPilot skill loads (ztp-*, seed-papers) NOT from this eval project's
    .claude/skills/. Claude Code runs a same-named ~/.claude/skills copy instead of the project's
    ("personal over project"), which is how every paper once ran the fork's user-level copies.
    The eval project is the transcript's directory; compared both as given and resolved, since
    mktemp's /var is /private/var on macOS. Base dirs are link paths, so never resolve those."""
    p = pathlib.Path(path)
    roots = {str(p.parent.absolute()), str(p.parent.resolve())}
    out = []
    for content in _messages(path):
        for b in content:
            if not (isinstance(b, dict) and b.get("type") == "text"):
                continue
            for m in _BASE_DIR.finditer(b.get("text", "")):
                d = m.group(1).strip()
                if not re.fullmatch(r"ztp-[\w-]+|seed-papers", pathlib.PurePath(d).name):
                    continue
                if not any(d.startswith(r + "/.claude/skills/") for r in roots):
                    out.append(d)
    return out
```

In each of the five checkers, just before `evallib.finish(...)`:

```python
for d in evallib.skills_loaded_outside_project(sys.argv[1]): fails.append(f"skill loaded from outside the project: {d}")
```

- [ ] **Step 4: Run unit tests, then the five live evals** (sequentially, no timeout)

Run: `python3 -m pytest -q tests/test_evallib_skill_origin.py` → PASS.
Run (with `SCRATCH` set to the session's scratchpad directory): `for e in ztp-research ztp-review ztp-profile ztp-tutor seed-papers; do bash tests/evals/$e.sh > "$SCRATCH/eval-$e.log" 2>&1; echo "$e exit $?"; done`. Print exit codes only; read a log only when its eval fails.
Expected: all exit 0. If a checker fails on skill **behaviour** (not origin), the old runs were grading the shadow copy, and this is the first time the vendored copy has been graded. Report it; do not patch a vendored skill in place (fix in the fork, re-sync).

- [ ] **Step 5: Commit**

```bash
git add tests/evals/evallib.py tests/evals/check_ztp_*.py tests/evals/check_seed_papers.py tests/test_evallib_skill_origin.py
git commit -m "evals: ZotPilot checkers fail when a skill loads from outside the project

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Docs, pointers, close-out

**Files:**
- Modify: `zotpilot-skills/VENDORED.md`: new section "Only this copy may load"
- Modify: `CLAUDE.md`: the `zotpilot-skills/` bullet in "Where things go"
- Modify: `README.md`: the ZotPilot install step (Step 7)
- Modify: `docs/SESSION_REPORT.md` (append a 2026-09-29 entry)

- [ ] **Step 1: `VENDORED.md`.** Add after "Provenance / refresh":

```markdown
## Only this copy may load

`zotpilot register` / `setup` / `upgrade` used to copy the fork's packaged skills into
`~/.claude/skills/ztp-*` (and OpenCode's skills dir). Claude Code runs a user-level skill
*instead of* a project skill with the same name, so every paper ran those copies, not this
directory. Found and fixed 2026-09-29 (`docs/plans/2026-09-29-zotpilot-skills-single-source.md`):

- The machine runs with `zotpilot config set deploy_skills false`. `register` then deploys
  nothing and removes what it deployed before. **Never set it back to true.**
- `check_install.sh` FAILs `personal-shadow` if any user-level skill shares a project skill's
  name, and (`--all`) WARNs `zotpilot-vendored` when this directory is behind the fork.
- `scripts/sync-zotpilot-skills.sh` writes the commit line below itself; `--check` compares only.
- Sessions started in the research root get the same copy through
  `scripts/link-zotpilot-skills.sh ~/Research`.
```

- [ ] **Step 2: `CLAUDE.md`.** In the `zotpilot-skills/` bullet, after "…is never edited in place.", add: `It is the only ZotPilot skill copy any session may load: user-level deployment is off (\`deploy_skills false\`), and \`check_install\` fails on a shadowing \`~/.claude/skills\` entry — see \`zotpilot-skills/VENDORED.md\` "Only this copy may load".`
- [ ] **Step 3: `README.md`.** Read Step 7 in full, then add after the `pip install git+…` line: `zotpilot config set deploy_skills false` with one sentence on why (the project links the skills; a user-level copy would override them).
- [ ] **Step 4: Session report.** Append a 2026-09-29 entry to `docs/SESSION_REPORT.md`: the finding (shadowing, evidence transcript), the fork PR/merge SHA, the re-sync SHA, gates added, eval results, and the open items below.
- [ ] **Step 5: Gates and commit**

```bash
./scripts/check_fork.sh                 # exit 0
./scripts/check_install.sh --all        # exit 0
python3 -m pytest -q tests/ 2>&1 | tail -3
git add zotpilot-skills/VENDORED.md CLAUDE.md README.md docs/SESSION_REPORT.md
git commit -m "docs: ZotPilot skills load from zotpilot-skills/ only

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Then merge `zotpilot-skills-single-source` into `main` locally (`git switch main && git merge --no-ff zotpilot-skills-single-source`). Do not push without asking.

---

## Left open (user decisions, not tasks)

- **`~/Research/NAR_settlement_legacy_archive/.claude/skills/`** holds *real* `ztp-*` copies from 2026-06-17. The user-level copies used to override them; after Task 6, a session started in that archive loads its own stale copies. Options: delete those directories, or leave the archive untouched.
- **`~/Research/.claude/skills/obsidian-digest-sync`** is a leftover. The skill was removed from the pipeline on 2026-09-09.
- **OpenCode** loses its ZotPilot skills in Task 6, because `deploy_skills` applies to all platforms. If OpenCode is in use, link `zotpilot-skills/*` into `~/.config/opencode/skills/`, the same way Task 6 Step 3 handles the research root.
- **Cloud and Cowork sessions** read neither `~/.claude/skills` nor the gitignored project links. That is out of scope here.
