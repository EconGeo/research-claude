--[[
source_comments.lua — the sourced Word build: each tagged claim gets a Word comment showing its
source paragraph, with the supporting sentence underlined.

Off unless the render sets `source-comments: true` (pipeline.py sources docx passes
-M source-comments:true) and the output is docx. Otherwise the document is returned untouched,
so the plain build and every PDF render are unchanged.

When on, it runs `python3 <project>/.claude/scripts/source_check.py <this .qmd> --root <project>
--json` once and replaces each [claim]{.src ref="R" id="I"} span with a comment-start span
(identifier N, author "Source check"), the claim, and a comment-end span (identifier N).
The comment reads "<label>, p. <page>. [OCR] <STATE>: <before><sentence><after>", with the
sentence underlined; the state is left out when the claim is APPROVED and [OCR] when the source
is not OCR text. A FAILED or NOT ON THIS MACHINE claim gets "SOURCE CHECK <STATE>: <reason>"
and never source text. A claim with no result gets "SOURCE CHECK FAILED: no check result for
<id>". If the check cannot be run or prints no JSON, every claim gets "SOURCE CHECK FAILED:
source check unavailable". The filter never fails the render. The design quote (result id
"design") anchors on the first [...]{.src-design} span, and is skipped when there is none.

Source text is never parsed as markdown: before, sentence and after are plain strings from the
check, turned into Str and Space inlines only, so characters such as * $ \ ^ ~ @ < ` reach Word
as they are in the file. Pandoc reads id="I" on a span as its identifier, so the tag id is
span.identifier, and the comment spans carry their number the same way.

-- tested: 2026-10-26, Quarto 1.9.37 / pandoc 3.8.3: a project-level `filters:` in _quarto.yml
   applies to `quarto render x.qmd --to docx` (a probe filter ran on that command).
-- tested: 2026-10-26, Quarto 1.9.37: `quarto render x.qmd --to docx --output y.docx
   -M source-comments:true` writes y.docx and leaves x.docx alone (x.docx mtime unchanged), and
   the filter sees meta["source-comments"] as the boolean true.
-- tested: 2026-10-26, Quarto 1.9.37: the filter's working directory is the manuscript's own
   directory (sub/ for `quarto render sub/m.qmd`), not the project; quarto.project.directory and
   QUARTO_PROJECT_DIR both give the project; PANDOC_STATE.input_files[1] is a temporary .md,
   while quarto.doc.input_file is the absolute path of the .qmd being rendered.
-- tested: 2026-10-26, pandoc 3.8.3: pandoc.json.decode returns nil (no error) for empty or
   non-JSON text, and JSON null decodes to a userdata, not nil.
]]

local AUTHOR = "Source check"
local FAILED = "FAILED"
local NOT_HERE = "NOT ON THIS MACHINE"
local APPROVED = "APPROVED"

local function text_or_empty(value)
  if type(value) == "string" then
    return value
  end
  return ""
end

local function project_root()
  if quarto ~= nil and quarto.project ~= nil and type(quarto.project.directory) == "string" then
    return quarto.project.directory
  end
  local from_env = os.getenv("QUARTO_PROJECT_DIR")
  if from_env ~= nil and from_env ~= "" then
    return from_env
  end
  return pandoc.system.get_working_directory()
end

local function input_file()
  if quarto ~= nil and quarto.doc ~= nil and type(quarto.doc.input_file) == "string" then
    return quarto.doc.input_file
  end
  return nil
end

local function run_check()
  local root = project_root()
  local args = {root .. "/.claude/scripts/source_check.py"}
  local manuscript = input_file()
  if manuscript ~= nil then
    table.insert(args, manuscript)
  end
  table.insert(args, "--root")
  table.insert(args, root)
  table.insert(args, "--json")
  local ok, out = pcall(pandoc.pipe, "python3", args, "")
  if not ok or type(out) ~= "string" then
    return nil
  end
  local decoded_ok, results = pcall(pandoc.json.decode, out, false)
  if not decoded_ok or type(results) ~= "table" then
    return nil
  end
  return results
end

local function plain_inlines(text)
  local out = pandoc.Inlines({})
  if text == "" then
    return out
  end
  if text:match("^%s") then
    out:insert(pandoc.Space())
  end
  local first = true
  for word in text:gmatch("%S+") do
    if not first then
      out:insert(pandoc.Space())
    end
    out:insert(pandoc.Str(word))
    first = false
  end
  if text:match("%s$") and not first then
    out:insert(pandoc.Space())
  end
  return out
end

local function failure_text(state, reason)
  return plain_inlines("SOURCE CHECK " .. state .. ": " .. reason)
end

local function comment_content(result, tag_id)
  if result == nil then
    return failure_text(FAILED, "no check result for " .. tag_id)
  end
  local state = text_or_empty(result.state)
  if state == "" then
    state = FAILED
  end
  local sentence = result.sentence
  if state == FAILED or state == NOT_HERE or type(sentence) ~= "string" then
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
  local out = plain_inlines(header)
  out:extend(plain_inlines(text_or_empty(result.before)))
  out:insert(pandoc.Underline(plain_inlines(sentence)))
  out:extend(plain_inlines(text_or_empty(result.after)))
  return out
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
