"""CLI: run a pass, undo a pass, query the sidecar."""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
from . import MARKER_V2, MODEL, OLLAMA_URL
from .candidates import score_chunk, select_candidates
from .chroma import DEFAULT_CHROMA, ChromaReader
from .extract import OllamaClient, OllamaError
from .normalize import build_records, tags_for
from .report import render_pass_report, write_pass_report
from .sidecar import DEFAULT_SIDECAR, Sidecar
from .vocab import Vocab
from .zotero_io import (DEFAULT_ZOTERO_SQLITE, WriteConflict, ZoteroWriterV2, check_autosync,
                        enumerate_items, render_note_html, resolve_library)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="data_tag")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    common.add_argument("--zotero-sqlite", type=Path, default=DEFAULT_ZOTERO_SQLITE)
    common.add_argument("--library", default="user", help="'user' or 'group:<groupID>'")
    run = sub.add_parser("run", parents=[common])
    run.add_argument("--collection"); run.add_argument("--pass", dest="pass_id", type=int, required=True)
    run.add_argument("--n", type=int, default=15, help="0 = all remaining"); run.add_argument("--dry-run", action="store_true")
    run.add_argument("--refresh-v2", action="store_true", help="reprocess items already carrying data-tagged:v2")
    run.add_argument("--report-dir", type=Path, default=Path("quality_reports/data_tags"))
    run.add_argument("--chroma", type=Path, default=DEFAULT_CHROMA); run.add_argument("--vocab", type=Path)
    run.add_argument("--model", default=os.environ.get("DATA_TAG_MODEL", MODEL))
    undo = sub.add_parser("undo", parents=[common]); undo.add_argument("--pass", dest="pass_id", type=int, required=True)
    undo.add_argument("--yes", action="store_true")
    q = sub.add_parser("query", parents=[common]); q.add_argument("what", choices=["type", "matrix", "topic"]); q.add_argument("value", nargs="?")
    q.add_argument("--chroma", type=Path, default=DEFAULT_CHROMA)
    return p


def _writer_from_env(lib_type: str, api_id: str) -> ZoteroWriterV2:
    key = os.environ.get("ZOTERO_API_KEY")
    if not key:
        raise RuntimeError("ZOTERO_API_KEY not set (source ~/.secrets.env)")
    return ZoteroWriterV2(key, api_id, lib_type)


def run_pass(args, *, chroma: ChromaReader, sidecar: Sidecar, vocab: Vocab, client, writer_factory) -> dict:
    lib_type, api_id, local_lib = resolve_library(args.library, args.zotero_sqlite)
    items = enumerate_items(args.zotero_sqlite, local_lib, args.collection)
    skipped_v2 = [i.key for i in items if MARKER_V2 in i.tags and not args.refresh_v2]
    todo = [i for i in items if i.key not in skipped_v2]
    indexed = chroma.indexed_doc_ids([i.key for i in todo])
    unindexed = [i.key for i in todo if i.key not in indexed]
    todo = [i for i in todo if i.key in indexed]
    if args.n:
        todo = todo[:args.n]
    client.check_ready()
    if not args.dry_run and check_autosync() is False:
        print("WARNING: Zotero auto-sync is off — writes will not appear in desktop Zotero until you sync.", file=sys.stderr)
    writer = None if args.dry_run else writer_factory(lib_type, api_id)
    sidecar.begin_pass(args.pass_id, args.library, args.collection, vocab.version, args.model, len(todo))
    diagnostics: dict[str, dict] = {}
    processed: list[str] = []
    for item in todo:
        t0 = time.time()
        chunks = chroma.chunks_for_doc(item.key)
        candidates = select_candidates(chunks, vocab)
        grep_hits = {c.chunk_index: vocab.match_sources(c.text) for c in chunks}
        grep_hits = {k: v for k, v in grep_hits.items() if v}
        hint_slugs = sorted({h.slug for hits in grep_hits.values() for h in hits})
        status_override = None
        try:
            llm_out, dropped = client.extract(candidates, hint_slugs, vocab) if candidates else ({"datasets": [], "notes": ""}, [])
        except OllamaError as exc:
            llm_out, dropped, status_override = {"datasets": [], "notes": ""}, [f"model_error: {exc}"], "model_error"
        doc = build_records(item.key, chunks, candidates, grep_hits, llm_out, dropped, vocab)
        if status_override:
            doc.status = status_override
        sidecar.write_doc(doc, args.pass_id, item.title, item.year, str(local_lib))
        llm_slugs = {d.src_slug for d in doc.datasets if d.source in ("llm", "merged") and d.src_slug}
        diagnostics[item.key] = {"best_score": max((score_chunk(c, vocab).score for c in chunks), default=0),
                                 "n_candidates": len(candidates), "words": sum(len(c.text.split()) for c in candidates),
                                 "grep_only": sorted(set(hint_slugs) - llm_slugs), "llm_only": sorted(llm_slugs - set(hint_slugs)),
                                 "wall_s": time.time() - t0}
        if writer is not None and doc.status in ("ok", "model_error") and doc.datasets:
            try:
                note_key = writer.upsert_note(item.key, render_note_html(doc, item.title, args.pass_id, vocab.version, args.model))
                added = writer.merge_tags(item.key, tags_for(doc))
                # only record notes this pass created; undo must never delete a pre-existing (e.g. v1) note
                created = getattr(writer, "last_note_created", True)
                sidecar.written_tags(item.key, args.pass_id, added, note_key if created else None)
            except WriteConflict as exc:
                sidecar.set_doc_status(item.key, "write_conflict"); print(f"write conflict {item.key}: {exc}", file=sys.stderr)
        processed.append(item.key)
    report = render_pass_report(sidecar, args.pass_id, vocab, diagnostics,
                                  extra_counts={"skipped_v2": skipped_v2, "unindexed": unindexed})
    out = write_pass_report(report, args.report_dir, args.pass_id)
    print(f"pass {args.pass_id}: {len(processed)} processed, {len(skipped_v2)} skipped (v2), {len(unindexed)} unindexed → {out}")
    return {"processed": processed, "skipped_v2": skipped_v2, "unindexed": unindexed, "report": str(out)}


def undo_pass(args, *, sidecar: Sidecar, writer_factory) -> int:
    lib_type, api_id, _ = resolve_library(args.library, args.zotero_sqlite)
    writes = sidecar.writes_in_pass(args.pass_id)
    if not writes:
        print(f"pass {args.pass_id}: nothing was written to Zotero"); return 0
    for w in writes:
        print(f"{w['doc_id']}: remove {json.loads(w['tags_json'])}; " + (f"delete note {w['note_key']}" if w["note_key"] else "leave pre-existing note"))
    if not args.yes:
        print("dry preview — re-run with --yes to apply"); return 0
    writer = writer_factory(lib_type, api_id)
    for w in writes:
        writer.remove_tags(w["doc_id"], json.loads(w["tags_json"]))
        if w["note_key"]:
            writer.delete_note(w["note_key"])
        sidecar.set_doc_status(w["doc_id"], "undone")
    print(f"pass {args.pass_id}: undone {len(writes)} items"); return 0


def _print_rows(rows, cols) -> None:
    print("| " + " | ".join(cols) + " |"); print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |")


def query(args, *, sidecar: Sidecar, chroma_factory) -> int:
    if args.what == "type":
        _print_rows(sidecar.query_by_type(args.value), ["title", "year", "name_raw", "src_slug", "geo_text", "geo_level", "period_start", "period_end", "dvs"])
    elif args.what == "matrix":
        _print_rows(sidecar.source_geo_matrix(), ["src_slug", "geo_level", "n"])
    else:
        chroma = chroma_factory()
        _print_rows(sidecar.topic_crosstab(args.value, lambda d: chroma.doc_meta(d)["tags"]), ["src_slug", "type_slug", "n"])
    return 0


def main(argv=None, *, client=None, writer_factory=None):
    args = _parser().parse_args(argv)
    sidecar = Sidecar(args.sidecar)
    writer_factory = writer_factory or _writer_from_env
    if args.cmd == "run":
        vocab = Vocab.load(args.vocab)
        client = client or OllamaClient(OLLAMA_URL, args.model)
        return run_pass(args, chroma=ChromaReader(args.chroma), sidecar=sidecar, vocab=vocab, client=client, writer_factory=writer_factory)
    if args.cmd == "undo":
        return undo_pass(args, sidecar=sidecar, writer_factory=writer_factory)
    return query(args, sidecar=sidecar, chroma_factory=lambda: ChromaReader(args.chroma))
