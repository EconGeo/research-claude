#!/usr/bin/env python3
"""registry_lib.py — load and validate rules/registry.yaml (stdlib, Python 3.9).

The registry is written in a restricted YAML subset so hooks and gates can read it under
/usr/bin/python3 with no PyYAML: block mappings, block lists, single-line scalars, `[]`,
`#` comments. parse_agree() cross-checks against PyYAML when it is importable.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROLES = {"creator", "critic", "referee", "infrastructure"}
FIELDS = ["role", "kind", "parallel_group", "requires", "produces", "critic",
          "escalation_target", "component", "quality_weight", "conditional", "writes"]
PRED_TYPES = {"path", "section", "score", "fresh", "render", "critic-ran", "prose-check", "chunk", "any_of"}
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:(\s|$)")

# ── restricted YAML ─────────────────────────────────────────────────────────
def _strip_comment(raw: str) -> str:
    if raw.lstrip().startswith("#"):
        return ""
    out, quote = [], None
    for i, ch in enumerate(raw):
        if quote:
            out.append(ch)
            if ch == quote: quote = None
        elif ch in "\"'":
            quote = ch; out.append(ch)
        elif ch == "#" and (i == 0 or raw[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()

def _scalar(s: str) -> Any:
    s = s.strip()
    if s == "[]": return []
    if s == "{}": return {}
    if s in ("null", "~", ""): return None
    if s == "true": return True
    if s == "false": return False
    if (s[0] == s[-1]) and s[0] in "\"'" and len(s) >= 2: return s[1:-1]
    if re.fullmatch(r"-?\d+", s): return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s): return float(s)
    return s

def load_yaml_subset(text: str) -> Any:
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        s = _strip_comment(raw)
        if s.strip() == "": continue
        lines.append((len(s) - len(s.lstrip(" ")), s.strip()))
    if not lines: return {}
    val, i = _block(lines, 0, lines[0][0])
    if i != len(lines):
        raise ValueError(f"registry.yaml: unparsed content at line item {i}: {lines[i][1]!r}")
    return val

def _block(lines, i, indent):
    return _list(lines, i, indent) if lines[i][1].startswith("- ") or lines[i][1] == "-" else _map(lines, i, indent)

def _map(lines, i, indent):
    out: Dict[str, Any] = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        item = lines[i][1]
        if not KEY_RE.match(item):
            raise ValueError(f"registry.yaml: expected 'key:' got {item!r}")
        key, _, rest = item.partition(":")
        key = key.strip(); rest = rest.strip()
        if rest == "":
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                val, i = _block(lines, i + 1, lines[i + 1][0])
            else:
                val, i = None, i + 1
        else:
            val, i = _scalar(rest), i + 1
        out[key] = val
    return out, i

def _list(lines, i, indent):
    out: List[Any] = []
    while i < len(lines) and lines[i][0] == indent and (lines[i][1].startswith("- ") or lines[i][1] == "-"):
        item = lines[i][1][1:].strip()
        if item == "":
            val, i = _block(lines, i + 1, lines[i + 1][0]); out.append(val); continue
        if KEY_RE.match(item):
            key, _, rest = item.partition(":")
            first: Dict[str, Any] = {}
            if rest.strip() == "" and i + 1 < len(lines) and lines[i + 1][0] > indent + 2:
                val, i = _block(lines, i + 1, lines[i + 1][0]); first[key.strip()] = val
            else:
                first[key.strip()] = _scalar(rest); i += 1
            if i < len(lines) and lines[i][0] == indent + 2 and not lines[i][1].startswith("- "):
                more, i = _map(lines, i, indent + 2); first.update(more)
            out.append(first); continue
        out.append(_scalar(item)); i += 1
    return out, i

# ── registry ────────────────────────────────────────────────────────────────
def registry_path(root: Path) -> Path:
    return Path(root) / "rules" / "registry.yaml"

def load_registry(root: Path) -> Dict[str, Any]:
    reg = load_yaml_subset(registry_path(root).read_text())
    if reg.get("schema_version") != 1:
        raise ValueError("registry.yaml: schema_version must be 1")
    return reg

def component_weights(reg) -> Dict[str, float]:
    return {k: float(v["weight"]) for k, v in reg["components"].items()}

def creators(reg) -> List[str]:
    return [a for a, e in reg["agents"].items() if e.get("role") == "creator"]

def critic_of(reg, agent: str) -> Optional[str]:
    c = reg["agents"].get(agent, {}).get("critic")
    return None if c in (None, "none") else c

def _check_pred(p, where, problems):
    if not isinstance(p, dict) or "type" not in p:
        problems.append(f"{where}: predicate is not a mapping with a type"); return
    t = p["type"]
    if t not in PRED_TYPES: problems.append(f"{where}: unknown predicate type {t!r}"); return
    need = {"path": ["glob"], "section": ["file", "heading"], "score": ["component", "min"],
            "chunk": ["label_glob", "min"], "any_of": ["of"]}.get(t, [])
    for k in need:
        if k not in p: problems.append(f"{where}: {t} predicate missing {k!r}")
    if t == "any_of":
        for j, q in enumerate(p.get("of") or []): _check_pred(q, f"{where}.of[{j}]", problems)
    if "producer" in p and not str(p["producer"]).startswith("/"):
        problems.append(f"{where}: producer must be a /skill invocation")

def validate_registry(reg) -> List[str]:
    problems: List[str] = []
    comps = set(reg.get("components", {}))
    agents = reg.get("agents", {})
    for name, e in agents.items():
        for f in FIELDS:
            if f not in e: problems.append(f"{name}: missing field {f}")
        if e.get("role") not in ROLES: problems.append(f"{name}: role must be one of {sorted(ROLES)}")
        if e.get("kind") not in ("agent", "skill"): problems.append(f"{name}: kind must be agent|skill")
        comp = e.get("component")
        if comp not in comps and comp != "none": problems.append(f"{name}: component {comp!r} not declared")
        crit = e.get("critic")
        w = float(e.get("quality_weight") or 0)
        if crit in (None, "none"):
            if e.get("role") == "creator" and w > 0:
                problems.append(f"{name}: creator with weight {w} has no critic")
        else:
            if crit not in agents: problems.append(f"{name}: critic {crit!r} is not a registry entry")
            elif agents[crit].get("role") != "critic": problems.append(f"{name}: critic {crit!r} does not have role critic")
        esc = e.get("escalation_target")
        if esc != "user" and esc not in agents: problems.append(f"{name}: escalation_target {esc!r} unknown")
        for j, p in enumerate(e.get("requires") or []): _check_pred(p, f"{name}.requires[{j}]", problems)
        for j, p in enumerate(e.get("produces") or []): _check_pred(p, f"{name}.produces[{j}]", problems)
        if not isinstance(e.get("writes"), list): problems.append(f"{name}: writes must be a list")
    for c, spec in reg.get("components", {}).items():
        sb = spec.get("scored_by")
        if sb not in agents: problems.append(f"components.{c}: scored_by {sb!r} unknown")
    return problems

QUALITY_ROW = re.compile(r"^\|\s*`?([a-z]+)`?\s*\|\s*([0-9.]+)\s*\|", re.M)

def weights_report(reg, quality_md: str) -> List[str]:
    problems: List[str] = []
    cw = component_weights(reg)
    cond = {k for k, v in reg["components"].items() if v.get("conditional")}
    base = sum(v for k, v in cw.items() if k not in cond)
    if abs(base - 100) > 1e-9: problems.append(f"non-conditional component weights sum to {base}, not 100")
    per_comp: Dict[str, float] = {}
    for a, e in reg["agents"].items():
        c = e.get("component")
        if c in cw: per_comp[c] = per_comp.get(c, 0.0) + float(e.get("quality_weight") or 0)
    for c, w in cw.items():
        if abs(per_comp.get(c, 0.0) - w) > 1e-9:
            problems.append(f"component {c}: agents declare {per_comp.get(c, 0.0)}, component says {w}")
    md = {m.group(1): float(m.group(2)) for m in QUALITY_ROW.finditer(quality_md)}
    for c, w in cw.items():
        if c not in md: problems.append(f"quality.md: no weight row for {c}")
        elif abs(md[c] - w) > 1e-9: problems.append(f"quality.md: {c} = {md[c]}, registry = {w}")
    return problems

def parse_agree(root: Path) -> str:
    text = registry_path(root).read_text()
    try:
        import yaml  # type: ignore
    except Exception:
        return "SKIP"
    return "PASS" if yaml.safe_load(text) == load_yaml_subset(text) else "FAIL"
