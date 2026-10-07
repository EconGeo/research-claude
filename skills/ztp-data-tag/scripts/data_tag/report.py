"""Render the per-pass Markdown report — the only thing Claude reads between passes."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from .sidecar import Sidecar
from .vocab import Vocab


def _cell(text) -> str:
    """Make free text safe inside a Markdown table cell: collapse whitespace, escape pipes."""
    return re.sub(r"\s+", " ", str(text if text is not None else "")).strip().replace("|", "\\|")


def _line(text) -> str:
    """Collapse whitespace so free text stays on one line."""
    return re.sub(r"\s+", " ", str(text if text is not None else "")).strip()


def _yaml_str(text) -> str:
    """JSON string literals are valid YAML double-quoted scalars."""
    return json.dumps(_line(text), ensure_ascii=False)


def _period(row) -> str:
    years = [y for y in (row["period_start"], row["period_end"]) if y]
    return "–".join(str(y) for y in years) if years else "?"


def render_pass_report(sidecar: Sidecar, pass_id: int, vocab: Vocab, diagnostics: dict,
                       extra_counts: dict[str, list[str]] | None = None) -> str:
    pass_row = next(p for p in sidecar.passes() if p["pass_id"] == pass_id)
    docs = sidecar.docs_in_pass(pass_id)
    status_counts = Counter(d["status"] for d in docs)
    wall = sum(diag.get("wall_s", 0) for diag in diagnostics.values())
    lines = [f"# ztp-data-tag pass {pass_id}", "",
             f"- library: `{pass_row['library']}` · collection: `{pass_row['collection'] or 'all'}` · vocab v{pass_row['vocab_version']} · model `{pass_row['model']}` · started {pass_row['started_utc']}",
             f"- processed: {len(docs)} · " + " · ".join(f"{k}: {n}" for k, n in sorted(status_counts.items())) + f" · wall {wall:.0f}s"]
    for key, items in (extra_counts or {}).items():
        detail = f" — {', '.join(_line(i) for i in items)}" if key == "unindexed" and items else ""
        lines.append(f"- {key}: {len(items)}{detail}")
    lines += ["", "## Per paper", "", "| Paper | Dataset | Type | Geography | Period | DVs | Pages | Status |", "|---|---|---|---|---|---|---|---|"]
    for d in docs:
        title = _cell(d["title"])
        datasets = sidecar.datasets_for_doc(d["doc_id"])
        if not datasets:
            lines.append(f"| {title} | — | | | | | | {_cell(d['status'])} |"); continue
        for ds in datasets:
            dvs = ", ".join(sorted({v["dv_class"] or v["slug"] for v in sidecar.variables_for(ds["id"]) if v["role"] == "dependent"}))
            pages = ", ".join(f"p. {e['page_num']}" if e["page_num"] is not None else f"c{e['chunk_index']}" for e in sidecar.evidence_for(ds["id"]))
            name = f"`{_cell(ds['src_slug'])}`" if ds["src_slug"] else f"*{_cell(ds['name_raw'])}* (unlisted)"
            geo = f"{ds['geo_text'] or ''} ({ds['geo_level']})" if ds["geo_level"] else (ds["geo_text"] or "?")
            lines.append(f"| {title} | {name} | {_cell(ds['type_slug'])} | {_cell(geo)} | {_period(ds)} | {_cell(dvs)} | {_cell(pages)} | {_cell(d['status'])} |")
    lines += ["", "## Review queue", ""]
    review = sidecar.open_review(pass_id)
    titles = {d["doc_id"]: d["title"] for d in docs}
    groups: dict[tuple, list] = {}
    for r in review:
        groups.setdefault((r["kind"], r["suggested_slug"] or r["name_raw"]), []).append(r)
    if not groups:
        lines.append("_empty_")
    for (kind, _), rows in groups.items():
        first = rows[0]
        papers = ", ".join(dict.fromkeys(_line(titles.get(r["doc_id"], r["doc_id"])) for r in rows))
        lines.append(f"- **{kind}** `{_line(first['name_raw'])}` → suggested `{_line(first['suggested_slug'])}` — {papers}: {_line(first['snippet'])[:160]}")
    lines += ["", "## Grep vs model", ""]
    for d in docs:
        diag = diagnostics.get(d["doc_id"], {})
        if diag.get("grep_only") or diag.get("llm_only"):
            lines.append(f"- {_line(d['title'])}: grep-only {diag.get('grep_only', [])} (candidate false positives) · model-only {diag.get('llm_only', [])} (candidate aliases)")
    lines += ["", "## Candidate selection", ""]
    for d in docs:
        diag = diagnostics.get(d["doc_id"], {})
        score = diag.get("best_score")
        flag = " ⚠ heading regex missed" if score is not None and score < 5 else ""
        lines.append(f"- {_line(d['title'])}: best score {diag.get('best_score', '?')} · {diag.get('n_candidates', '?')} chunks · {diag.get('words', '?')} words · {diag.get('wall_s', 0):.0f}s{flag}")
    word_counts = [diagnostics[d["doc_id"]]["words"] for d in docs if "words" in diagnostics.get(d["doc_id"], {})]
    if word_counts:
        lines.append(f"- average {sum(word_counts) / len(word_counts):.0f} words over {len(word_counts)} papers")
    lines += ["", "## Proposed vocabulary diff", "", "```yaml", "# promote from review queue (edit aliases/type/geo_level/access before applying):"]
    for (kind, _), rows in groups.items():
        r = rows[0]
        if kind == "source" and r["suggested_slug"] in vocab.sources:
            lines.append(f"  # {_line(r['suggested_slug'])} already in vocab — add alias for {_yaml_str(r['name_raw'])}?")
        elif kind == "source":
            # Word-bounded, regex-escaped alias; every scalar is a quoted YAML string.
            alias = r"(?<!\w)" + re.escape(_line(r["name_raw"])) + r"(?!\w)"
            lines.append(f"  {_yaml_str(r['suggested_slug'])}: {{name: {_yaml_str(r['name_raw'])}, aliases: [{_yaml_str(alias)}], "
                         f"type: other, geo_level: national, access: unknown}}")
        else:
            docs_txt = ", ".join(dict.fromkeys(_line(x["doc_id"]) for x in rows))
            lines.append(f"  # dv_class needle for {_yaml_str(r['name_raw'])} (doc {docs_txt})")
    lines += ["```", ""]
    return "\n".join(lines)


def write_pass_report(markdown: str, out_dir: Path, pass_id: int) -> Path:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pass_{pass_id:02d}.md"
    out.write_text(markdown)
    return out
