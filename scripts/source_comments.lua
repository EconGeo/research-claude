--[[
source_comments.lua — the sourced Word build: each tagged claim gets a Word comment showing its
source paragraph, with the supporting sentence underlined.

Off unless the render sets `source-comments: true` (pipeline.py sources docx passes
-M source-comments:true) and the output is docx. Otherwise the document is returned untouched,
so the plain build and every PDF render are unchanged.

When on, it runs `python3 .claude/scripts/source_check.py --json` once and replaces each
[claim]{.src ref="R" id="I"} span with
  [<label>, p. <page>. [OCR] <STATE>: <paragraph>]{.comment-start id="N" author="Source check"}
  claim
  []{.comment-end id="N"}
The state prefix is left out when the claim is APPROVED. A FAILED or NOT ON THIS MACHINE claim
gets "SOURCE CHECK <STATE>: <reason>" and never source text. A claim with no result gets
"SOURCE CHECK FAILED: no check result for <id>". If the check cannot be run or prints no JSON,
every claim gets "SOURCE CHECK FAILED: source check unavailable". The filter never fails the
render. The design quote (result id "design") anchors on the first [...]{.src-design} span, and
is skipped when the manuscript has none.

-- tested: 2026-10-26, Quarto 1.9.37 / pandoc 3.8.3: a project-level `filters:` in _quarto.yml
   applies to `quarto render x.qmd --to docx` (a probe filter ran on that command).
-- tested: 2026-10-26, Quarto 1.9.37: `quarto render x.qmd --to docx --output y.docx
   -M source-comments:true` writes y.docx and leaves x.docx alone (x.docx mtime unchanged); the
   filter sees meta["source-comments"] as the boolean true, and pandoc.pipe runs in the
   project directory, so the relative script path resolves.
Pandoc reads id="I" on a span as its identifier, not as a key-value attribute, so the tag id
is span.identifier, and the comment spans carry their number the same way.
The comment text is read as markdown without the smart extension, so source punctuation stays
as the check returned it (no curled quotes, no non-breaking space after "p.").

-- tested: 2026-10-26, pandoc 3.8.3: pandoc.json.decode returns nil (no error) for empty or
   non-JSON text, and JSON null decodes to a userdata, not nil.
]]

local AUTHOR = "Source check"
local FAILED = "FAILED"
local NOT_HERE = "NOT ON THIS MACHINE"
local APPROVED = "APPROVED"

local function run_check()
  local ok, out = pcall(pandoc.pipe, "python3", {".claude/scripts/source_check.py", "--json"}, "")
  if not ok or type(out) ~= "string" then
    return nil
  end
  local decoded_ok, results = pcall(pandoc.json.decode, out, false)
  if not decoded_ok or type(results) ~= "table" then
    return nil
  end
  return results
end

local function text_or_empty(value)
  if type(value) == "string" then
    return value
  end
  return ""
end

local function failure_text(state, reason)
  return pandoc.Inlines("SOURCE CHECK " .. state .. ": " .. reason)
end

local function comment_content(result, tag_id)
  if result == nil then
    return failure_text(FAILED, "no check result for " .. tag_id)
  end
  local state = text_or_empty(result.state)
  local paragraph = result.paragraph
  if state == FAILED or state == NOT_HERE or type(paragraph) ~= "string" then
    if state == "" then
      state = FAILED
    end
    return failure_text(state, text_or_empty(result.reason))
  end
  local header = text_or_empty(result.label)
  local page = text_or_empty(result.page)
  if page ~= "" then
    header = header .. ", p. " .. page
  end
  header = header .. ". "
  if result.ocr == true then
    header = header .. "[OCR] "
  end
  if state ~= APPROVED then
    header = header .. state .. ": "
  end
  local blocks = pandoc.read(header .. paragraph, "markdown-smart").blocks
  if #blocks == 0 or blocks[1].content == nil then
    return failure_text(FAILED, "source paragraph could not be shown")
  end
  return blocks[1].content
end

local function wrap(span, content, number)
  local id = tostring(number)
  local start = pandoc.Span(content, pandoc.Attr(id, {"comment-start"}, {author = AUTHOR}))
  local finish = pandoc.Span({}, pandoc.Attr(id, {"comment-end"}))
  local out = pandoc.Inlines({start})
  out:extend(span.content)
  out:insert(finish)
  return out
end

function Pandoc(doc)
  if doc.meta["source-comments"] ~= true or not FORMAT:match("docx") then
    return nil
  end
  local results = run_check()
  local next_id = 0
  local design_done = false

  local function on_span(span)
    local content
    if span.classes:includes("src") then
      if results == nil then
        content = failure_text(FAILED, "source check unavailable")
      else
        local tag_id = span.identifier
        content = comment_content(results[tag_id], tag_id)
      end
    elseif span.classes:includes("src-design") and not design_done then
      design_done = true
      if results == nil or results["design"] == nil then
        return nil
      end
      content = comment_content(results["design"], "design")
    else
      return nil
    end
    next_id = next_id + 1
    return wrap(span, content, next_id)
  end

  return doc:walk({Span = on_span})
end
