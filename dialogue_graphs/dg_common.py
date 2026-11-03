"""Shared dialogue-graph detection and string field rules."""
from __future__ import annotations

import re
from typing import Any

DG_GRAPH_KEYS = frozenset(
    {"m_GameObject", "m_Enabled", "m_Script", "m_Name", "edges", "nodes", "labelNodes", "labels", "groups", "references"}
)

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
GUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
HEX32 = re.compile(r"^[0-9a-f]{32}$", re.I)
CAMEL_KEY = re.compile(r"^[A-Z][a-zA-Z0-9]*Key$")
SCENE_OR_ASSET = re.compile(
    r"^(Assets/|Scene|sc_|sec\d|pa_|est\d|his\d|DLC\d+_|kun_|maj_|mog_|sic_|non_)",
    re.I,
)

# (class, field_suffix) -> kind; field is path under data e.g. "text", "entries[0].key"
TRANSLATABLE: dict[tuple[str, str], str] = {
    ("ChoiseOptionNode", "text"): "choice",
    ("DialogueBenchChoiseOption", "text"): "choice",
    ("SayNode", "text"): "say",
    ("SendGlobalEventDialogueNode", "message"): "message",
}

# Always skip these field paths (any class)
SKIP_FIELD_SUFFIXES = frozenset(
    {
        "guid",
        "flagName",
        "interactableKey",
        "startlabel",
        "hideObjectKey",
        "positionKey",
        "labelReference.guid",
        "scriptReference.m_AssetGUID",
        "scriptReference.m_SubObjectName",
        "scriptReference.m_SubObjectType",
        "prefabReference.m_AssetGUID",
        "prefabReference.m_SubObjectName",
        "prefabReference.m_SubObjectType",
    }
)

SKIP_FIELD_PATTERNS = (
    re.compile(r"\.key$"),
    re.compile(r"^entries\[\d+\]\.key$"),
    re.compile(r"^m_"),
)


def is_dialogue_graph_tree(tree: dict) -> bool:
    if not isinstance(tree, dict):
        return False
    if not {"references", "nodes", "edges"}.issubset(tree.keys()):
        return False
    refs = tree.get("references")
    if not isinstance(refs, dict):
        return False
    ref_ids = refs.get("RefIds")
    return isinstance(ref_ids, list) and len(ref_ids) > 0


def has_references_mono(tree: dict) -> bool:
    refs = tree.get("references")
    if not isinstance(refs, dict):
        return False
    ref_ids = refs.get("RefIds")
    return isinstance(ref_ids, list) and len(ref_ids) > 0


def _field_suffix(path: str) -> str:
    """Normalize data.xxx path to suffix for rule lookup."""
    if path.startswith("data."):
        path = path[5:]
    return path


def is_internal_string(text: str, field: str) -> bool:
    if not text:
        return True
    if JP.search(text):
        return True
    suf = _field_suffix(field)
    if suf in SKIP_FIELD_SUFFIXES:
        return True
    for pat in SKIP_FIELD_PATTERNS:
        if pat.search(suf):
            return True
    if GUID.match(text.strip()) or HEX32.match(text.strip()):
        return True
    if CAMEL_KEY.match(text) and " " not in text:
        return True
    if SCENE_OR_ASSET.match(text):
        return True
    # PascalCase single token flag-like
    if re.match(r"^[A-Z][a-zA-Z0-9_]+$", text) and len(text) < 40 and " " not in text:
        if text.endswith("Key") or "Flag" in text or text.endswith("Mode"):
            return True
    return False


def classify_string(node_class: str, field: str, text: str) -> str | None:
    suf = _field_suffix(field)
    if is_internal_string(text, field):
        # Explicit translatable overrides internal heuristics
        key = (node_class, suf)
        if key not in TRANSLATABLE:
            return None
    key = (node_class, suf)
    if key in TRANSLATABLE:
        return TRANSLATABLE[key]
    # Heuristic: English-like text in known player fields
    if suf == "text" and node_class.endswith("OptionNode"):
        return "choice"
    if suf == "text" and "ChoiseOption" in node_class:
        return "choice"
    if suf in ("text", "message") and len(text) >= 2:
        if re.search(r"[A-Za-z]", text) and not is_internal_string(text, field):
            return "other"
    return None


def walk_data_strings(data: Any, prefix: str = "data", out: list[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    if out is None:
        out = []
    if isinstance(data, str):
        out.append((prefix, data))
    elif isinstance(data, dict):
        for k, v in data.items():
            walk_data_strings(v, f"{prefix}.{k}" if prefix else k, out=out)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            walk_data_strings(v, f"{prefix}[{i}]", out=out)
    return out


def iter_graph_text_hits(tree: dict, graph_name: str) -> list[dict]:
    """Yield translatable hits from RefIds."""
    hits: list[dict] = []
    refs = tree.get("references") or {}
    ref_ids = refs.get("RefIds") or []
    for rid, entry in enumerate(ref_ids):
        if not isinstance(entry, dict):
            continue
        t = entry.get("type") or {}
        node_class = str(t.get("class") or "")
        data = entry.get("data")
        if not isinstance(data, dict):
            continue
        for field, text in walk_data_strings(data):
            kind = classify_string(node_class, field, text)
            if kind:
                hits.append(
                    {
                        "rid": rid,
                        "node_class": node_class,
                        "field": _field_suffix(field),
                        "text": text,
                        "kind": kind,
                    }
                )
    # Editor label names on graph (not player-facing)
    return hits


def set_data_field(data: dict, field_suffix: str, value: str) -> None:
    """Set data.<field_suffix> supporting entries[0].key style."""
    parts: list[str | int] = []
    for part in field_suffix.replace("data.", "").split("."):
        if "[" in part:
            name, idx = part.split("[", 1)
            parts.append(name)
            parts.append(int(idx.rstrip("]")))
        else:
            parts.append(part)
    cur: Any = data
    for i, p in enumerate(parts[:-1]):
        if isinstance(p, int):
            cur = cur[p]
        else:
            cur = cur[p]
    last = parts[-1]
    if isinstance(last, int):
        cur[last] = value
    else:
        cur[last] = value
