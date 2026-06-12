# ZotPilot `delete_note` MCP Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `delete_note` MCP tool to ZotPilot so an agent can delete a child note by its key (closing the gap the `/ztp-data-tag` pilot exposed — there was no way to remove a Data note via MCP).

**Architecture:** Two thin layers mirroring `create_note`: a `ZoteroWriter.delete_note()` method (pyzotero Web API, with a safety guard that only items of `itemType == "note"` are deletable — never a paper/attachment) and a `@mcp.tool`-decorated `delete_note` wrapper in `write_ops.py`. Registration is automatic (the module is already imported by `tools/__init__.py`). Ship on a feature branch → PR to `EconGeo/ZotPilot`.

**Tech Stack:** Python, pyzotero, FastMCP, pytest. Repo: `EconGeo/ZotPilot` (the `submodules/zotpilot` submodule of research-claude).

---

## Context the executor needs

- **Work in:** `~/Academic/research-claude/submodules/zotpilot` — this IS the `EconGeo/ZotPilot` git repo (its own `origin`). All paths below are relative to that directory unless noted.
- **Branch setup (do this first):** the submodule is checked out at a detached commit. Branch off latest main:
  ```bash
  cd ~/Academic/research-claude/submodules/zotpilot
  git fetch origin
  git checkout -b feat/delete-note-tool origin/main
  ```
  (If `origin/main` has diverged badly from the pinned commit and the build breaks, fall back to `git checkout -b feat/delete-note-tool` from the current HEAD and note it in the PR.)
- **How MCP tools register:** a tool is just a function decorated `@mcp.tool(tags=tool_tags("extended", "write"))` in a module that `src/zotpilot/tools/__init__.py` imports. `write_ops.py` is already imported there, so **adding the decorated function is all the registration needed** — no `__init__.py` or `profiles.py` edits. `mcp.tool` is wrapped (`state.py:_callable_tool`) to preserve the plain callable, so the decorated function is still directly callable in tests.
- **Writer pattern:** `src/zotpilot/zotero_writer.py` has `ZoteroWriter`, whose `self._zot` is a pyzotero `zotero.Zotero(...)` client. Relevant existing methods:
  - `delete_item(self, item_key) -> bool` — `item = self._zot.item(key); self._zot.delete_item(item)`. Trashes ANY item (no type guard — that's why we need `delete_note`).
  - `create_note(...)`, `get_notes(...)`.
  A pyzotero item is a dict: `item["data"]["itemType"]` (e.g. `"note"`, `"journalArticle"`), `item["data"]["note"]` (note HTML), `item["data"]["parentItem"]`.
- **ZotPilot note marker:** notes created by ZotPilot via `create_note(idempotent=true)` get a `[ZotPilot]` prefix in their `<h1>` title (stored in `item["data"]["note"]`). The default `require_zotpilot=True` guard uses this so the tool won't delete the user's hand-written notes.
- **Tool wrapper pattern:** `write_ops.py` tools use `from ..state import ToolError, _get_writer, _get_zotero, mcp` and `from .profiles import tool_tags`. `create_note` is at `write_ops.py:153-189` (decorator `@mcp.tool(tags=tool_tags("extended", "write"))`). Use `Annotated[type, Field(description=...)]` for params.
- **Test mocking:** writer tests build a `ZoteroWriter` via `__new__` (bypass `__init__`, which needs real creds) and set `w._zot = MagicMock()`. Tool tests patch `zotpilot.tools.write_ops._get_writer`. See `tests/test_tools_write_batch.py` and `tests/test_notes.py`.
- **Run tests:** from `submodules/zotpilot`, `uv run pytest <path> -v` (the repo uses `uv`/`uv.lock`). If `uv` is unavailable but deps are installed in the active env, `python -m pytest <path> -v` works.
- **Commit trailer:** end commit messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## File Structure

- `src/zotpilot/zotero_writer.py` — **modify:** add `ZoteroWriter.delete_note()` (the guarded delete logic).
- `src/zotpilot/tools/write_ops.py` — **modify:** add the `@mcp.tool` `delete_note` wrapper.
- `tests/test_delete_note.py` — **create:** writer-level guard tests + tool-level delegation test.

---

### Task 1: `ZoteroWriter.delete_note()` with the note-type guard

**Files:**
- Create: `tests/test_delete_note.py`
- Modify: `src/zotpilot/zotero_writer.py` (add method near `delete_item`, ~line 433)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_delete_note.py`:

```python
"""Tests for ZoteroWriter.delete_note and the delete_note MCP tool."""
from unittest.mock import MagicMock, patch

import pytest

from zotpilot.zotero_writer import ZoteroWriter


@pytest.fixture
def writer():
    # Bypass __init__ (which needs real API creds); inject a mock pyzotero client.
    w = ZoteroWriter.__new__(ZoteroWriter)
    w._zot = MagicMock()
    return w


def _note_item(item_type="note",
               note_html="<h1>[ZotPilot] Data (auto-extracted)</h1><p>...</p>",
               parent="PARENT1"):
    return {"key": "NOTE123",
            "data": {"itemType": item_type, "note": note_html, "parentItem": parent}}


def test_delete_note_happy(writer):
    writer._zot.item.return_value = _note_item()
    result = writer.delete_note("NOTE123")
    assert result == {"deleted": True, "note_key": "NOTE123", "parent_key": "PARENT1"}
    writer._zot.delete_item.assert_called_once()


def test_delete_note_refuses_non_note(writer):
    writer._zot.item.return_value = _note_item(item_type="journalArticle")
    result = writer.delete_note("PAPER1")
    assert result["deleted"] is False
    assert result["reason"] == "not_a_note"
    writer._zot.delete_item.assert_not_called()


def test_delete_note_requires_zotpilot_marker_by_default(writer):
    writer._zot.item.return_value = _note_item(note_html="<h1>My own note</h1><p>hi</p>")
    result = writer.delete_note("NOTE123", require_zotpilot=True)
    assert result["deleted"] is False
    assert result["reason"] == "not_a_zotpilot_note"
    writer._zot.delete_item.assert_not_called()


def test_delete_note_override_allows_any_note(writer):
    writer._zot.item.return_value = _note_item(note_html="<h1>My own note</h1><p>hi</p>")
    result = writer.delete_note("NOTE123", require_zotpilot=False)
    assert result["deleted"] is True
    writer._zot.delete_item.assert_called_once()


def test_delete_note_not_found(writer):
    writer._zot.item.side_effect = Exception("404 not found")
    result = writer.delete_note("MISSING")
    assert result["deleted"] is False
    assert result["reason"] == "not_found"
    writer._zot.delete_item.assert_not_called()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_delete_note.py -v`
Expected: FAIL — `AttributeError: 'ZoteroWriter' object has no attribute 'delete_note'` (the tool-delegation test is added in Task 2; for now these 5 writer tests are the target).

- [ ] **Step 3: Implement `ZoteroWriter.delete_note`**

In `src/zotpilot/zotero_writer.py`, add this method immediately after `delete_item` (the method ending around line 442):

```python
    def delete_note(self, note_key: str, require_zotpilot: bool = True) -> dict:
        """Delete a child note by its key (moves it to Zotero trash).

        Safety: only items of itemType 'note' are deletable here — never a
        paper or attachment. By default refuses notes not created by ZotPilot
        (those lacking the '[ZotPilot]' marker); pass require_zotpilot=False to
        delete any note by key.

        Returns:
            {"deleted": True, "note_key": ..., "parent_key": ...} on success, or
            {"deleted": False, "reason": ..., "note_key": ...} when a guard blocks it.
        """
        try:
            item = self._zot.item(note_key)
        except Exception as e:
            logger.warning("delete_note(%s) lookup failed: %s", note_key, e)
            return {"deleted": False, "reason": "not_found", "note_key": note_key}

        data = item.get("data", {})
        if data.get("itemType") != "note":
            return {
                "deleted": False,
                "reason": "not_a_note",
                "note_key": note_key,
                "item_type": data.get("itemType"),
            }

        if require_zotpilot and "[ZotPilot]" not in (data.get("note") or ""):
            return {"deleted": False, "reason": "not_a_zotpilot_note", "note_key": note_key}

        self._zot.delete_item(item)
        return {"deleted": True, "note_key": note_key, "parent_key": data.get("parentItem")}
```

(`logger` is already defined at module scope in `zotero_writer.py`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_delete_note.py -v`
Expected: the 5 writer tests PASS. (`test_delete_note_tool_delegates_to_writer` doesn't exist yet — added in Task 2.)

- [ ] **Step 5: Commit**

```bash
git add src/zotpilot/zotero_writer.py tests/test_delete_note.py
git commit -m "feat(writer): add ZoteroWriter.delete_note with note-type + ZotPilot guards

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `delete_note` MCP tool wrapper

**Files:**
- Modify: `src/zotpilot/tools/write_ops.py` (add after the `create_note` tool, ~line 189)
- Modify: `tests/test_delete_note.py` (add the tool-delegation test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_delete_note.py`:

```python
def test_delete_note_tool_delegates_to_writer():
    from zotpilot.tools import write_ops
    mock_writer = MagicMock()
    mock_writer.delete_note.return_value = {"deleted": True, "note_key": "N1", "parent_key": "P1"}
    with patch("zotpilot.tools.write_ops._get_writer", return_value=mock_writer):
        result = write_ops.delete_note("N1")
    assert result == {"deleted": True, "note_key": "N1", "parent_key": "P1"}
    mock_writer.delete_note.assert_called_once_with("N1", require_zotpilot=True)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_delete_note.py::test_delete_note_tool_delegates_to_writer -v`
Expected: FAIL — `AttributeError: module 'zotpilot.tools.write_ops' has no attribute 'delete_note'`.

- [ ] **Step 3: Implement the tool**

In `src/zotpilot/tools/write_ops.py`, add immediately after the `create_note` function (which ends at the line `    return result` around line 189, before `def _extract_tag_item`):

```python
@mcp.tool(tags=tool_tags("extended", "write"))
def delete_note(
    note_key: Annotated[str, Field(description="Zotero item key of the NOTE to delete")],
    require_zotpilot: Annotated[
        bool,
        Field(description="If true (default), only delete notes created by ZotPilot "
                          "(marked '[ZotPilot]'); refuse otherwise. Set false to delete any note by key."),
    ] = True,
) -> dict:
    """Delete a child note by its key. Requires ZOTERO_API_KEY.

    Safety: only items of type 'note' are deletable here — never a paper or
    attachment. Returns {"deleted": True/False, ...}; when False, 'reason' explains
    (not_found / not_a_note / not_a_zotpilot_note).
    """
    return _get_writer().delete_note(note_key, require_zotpilot=require_zotpilot)
```

(`Annotated`, `Field`, `mcp`, `tool_tags`, and `_get_writer` are already imported at the top of `write_ops.py`.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_delete_note.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/zotpilot/tools/write_ops.py tests/test_delete_note.py
git commit -m "feat(tools): expose delete_note MCP tool (write profile)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Regression check, registration sanity, push + PR

**Files:** none (verification + git)

- [ ] **Step 1: Run the related test suites for regressions**

Run: `uv run pytest tests/test_delete_note.py tests/test_notes.py tests/test_tools_write_batch.py -v`
Expected: all PASS (no regressions in existing note/write tests).

- [ ] **Step 2: Confirm the tool is registered on the MCP server**

Run:
```bash
uv run python -c "import zotpilot.tools; from zotpilot.tools import write_ops; print('callable:', callable(write_ops.delete_note))"
```
Expected: prints `callable: True` and no import errors (importing `zotpilot.tools` runs the `@mcp.tool` registration; the call confirms the decorated function is still a usable callable).

- [ ] **Step 3: Push the branch**

```bash
git push -u origin feat/delete-note-tool
```

- [ ] **Step 4: Open a PR to EconGeo/ZotPilot**

```bash
gh pr create --repo EconGeo/ZotPilot --base main --head feat/delete-note-tool \
  --title "feat: add delete_note MCP tool" \
  --body "$(cat <<'EOF'
Adds a `delete_note` MCP tool so agents can remove a child note by its key —
the gap surfaced while piloting the research-claude `/ztp-data-tag` skill (there
was no MCP path to delete a note, only create/get).

- `ZoteroWriter.delete_note(note_key, require_zotpilot=True)` — trashes the note
  via the Web API, guarded so **only items of itemType 'note' are deletable**
  (never a paper/attachment), and by default only ZotPilot-marked notes.
- `delete_note` MCP tool (extended/write profile) wrapping it.
- Unit tests for the guards (non-note refusal, ZotPilot-marker default, override,
  not-found) and the tool delegation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed. (If `gh` isn't authenticated, stop and report the branch is pushed so the user can open the PR manually.)

- [ ] **Step 5: Report the PR URL**

Report the PR URL and the branch name back to the user. Do NOT self-merge — leave the merge decision to the user.

---

### Task 4 (FOLLOW-UP — only after the PR is merged): adopt `delete_note` in research-claude

Do this in a later pass once the ZotPilot PR is merged to `main`.

**Files:**
- Modify: `skills/ztp-data-tag/SKILL.md` (research-claude) — Undo section
- Modify: `submodules/zotpilot` pointer (research-claude)

- [ ] **Step 1: Bump the submodule pointer**

```bash
cd ~/Academic/research-claude/submodules/zotpilot
git fetch origin && git checkout main && git pull
cd ~/Academic/research-claude
git add submodules/zotpilot
```

- [ ] **Step 2: Update the skill's Undo section**

In `skills/ztp-data-tag/SKILL.md`, replace the "Notes:" bullet under `## Undo` (which currently says notes must be deleted manually) with:

```
- **Notes:** delete the "Data (auto-extracted)" note with
  `mcp__zotpilot__delete_note(note_key=...)` (find the key via
  `mcp__zotpilot__get_notes(item_key=...)`). It only deletes items of type 'note'
  and, by default, only ZotPilot-created notes.
```

- [ ] **Step 3: Commit + push (research-claude)**

```bash
cd ~/Academic/research-claude
git add skills/ztp-data-tag/SKILL.md submodules/zotpilot
git commit -m "feat: adopt zotpilot delete_note in ztp-data-tag undo; bump submodule

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
```

---

## Self-Review

**Spec coverage:**
- `delete_note` MCP tool → Task 2. ✓
- Safe (never deletes a paper) → Task 1 `itemType == "note"` guard + `test_delete_note_refuses_non_note`. ✓
- Won't nuke user's own notes by default → `require_zotpilot` guard + marker test; override path tested. ✓
- Registered/visible like other write tools → automatic via `@mcp.tool(tags=tool_tags("extended","write"))`; Task 3 Step 2 confirms. ✓
- Pushed to EconGeo/ZotPilot → Task 3 (branch + PR). ✓
- research-claude adopts it → Task 4 (gated on merge). ✓

**Placeholder scan:** No TBD/"handle errors"/"similar to" — full method, full tool, full test code inline; exact commands with expected output. ✓

**Type/name consistency:** `delete_note(note_key, require_zotpilot=True)` signature identical across the writer method (Task 1 Step 3), the tool wrapper (Task 2 Step 3), and both tests. Return dict keys (`deleted`, `reason`, `note_key`, `parent_key`, `item_type`) consistent between implementation and assertions. Reasons used: `not_found`, `not_a_note`, `not_a_zotpilot_note`. ✓

---

## Execution note

The user asked to checkpoint + clear, then start this in a fresh session. When you start it: read this plan, then use **superpowers:subagent-driven-development** (fresh subagent per task, two-stage review). All work is in `submodules/zotpilot` (the `EconGeo/ZotPilot` repo) except Task 4, which is research-claude. **Task 4 is gated on the PR being merged — do not run it until then.** The implementer needs a working ZotPilot dev env (`uv` or the deps installed) to run pytest; no live Zotero/network is required (tests mock pyzotero).
