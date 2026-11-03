#!/usr/bin/env python3
"""Scan Dusk City assets for player-visible text not covered by existing translation work.

Read-only on game files. Set DUSK_GAME_PATH to the game install root.

Writes:
  translation/research/remaining_text/candidates.json
  translation/research/remaining_text/REMAINING_TEXT.md
  translation/research/remaining_text/scan_stats.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import UnityPy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
DATA = GAME / "Dusk City_Data"
AA = DATA / "StreamingAssets" / "aa"

# --- classification helpers (module-level for workers) ---

DG_KEYS = frozenset({"edges", "nodes", "labelNodes", "labels", "groups", "references"})

JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
EN_WORD_RE = re.compile(r"\b[A-Za-z]{2,}\b")
GUID_RE = re.compile(r"^[0-9a-f]{32}$", re.I)
VOICE_ID = re.compile(r"^[a-z]{2,4}\d{3,5}$", re.I)
VOICE_ID_DLC = re.compile(r"^DLC\d+_[a-z]+\d+$", re.I)
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
SKIP_FIELD_SUFFIX = (
    "portKey",
    "m_Script",
    "m_GameObject",
    "m_Father",
    "m_PrefabInstance",
    "m_CorrespondingSourceObject",
    "fileID",
    "guid",
    "m_AssetGUID",
    "m_AddressableAssetReference",
)
VS_PORT_LITERALS = frozenset(
    {
        "controlInput",
        "controlOutput",
        "trueOutput",
        "falseOutput",
        "null",
        "self",
        "valueInput",
        "valueOutput",
        "enter",
        "exit",
        "start",
        "stop",
        "pause",
        "resume",
    }
)

KNOWN_NOISE_EXACT = frozenset(
    {
        "Option A",
        "Option B",
        "Option C",
        "m_Name",
        "UnityEngine",
        "MonoBehaviour",
        "GameObject",
        "Default",
        "None",
        "True",
        "False",
        "true",
        "false",
        "Begin",
        "Start",
        "Invoke",
        "Complete",
        "Launch",
        "Entry",
        "Group",
        "Cutscene",
        "Freeroam",
    }
)

SKIP_CLASS_PREFIXES = (
    "UnityEngine.InputSystem.",
    "UnityEngine.Rendering.",
    "UnityEngine.Timeline.",
    "UnityEngine.UIElements.",
    "Unity.VisualScripting.Variables",
)

SKIP_CLASSES = frozenset(
    {
        "AnimatorPageTransition",
        "UnityEngine.EventSystems.EventTrigger",
    }
)

VS_GRAPH_CLASSES = frozenset(
    {
        "Unity.VisualScripting.ScriptMachine",
        "Unity.VisualScripting.StateMachine",
        "Kanono1Status",
    }
)

VS_CONTENT_KEYS = frozenset(
    {
        "label",
        "title",
        "summary",
        "text",
        "message",
        "tooltip",
        "hint",
        "description",
        "body",
        "subtitle",
    }
)

PLAYER_FIELD_MARKERS = (
    ".text",
    ".description",
    ".itemName",
    ".itemLeveltext",
    "m_text",
    "m_Text",
    ".displayName",
    ".areaName",
    ".label",
    ".speechText",
    ".prompt",
)

# Populated in main, copied to workers via initializer
EXCLUDE_TEXT: frozenset[str] = frozenset()
EXCLUDE_ASSET_PREFIXES: tuple[str, ...] = ()


def is_dialogue_graph(tree: dict) -> bool:
    if not DG_KEYS.issubset(tree.keys()):
        return False
    refs = tree.get("references")
    if not isinstance(refs, dict):
        return False
    ref_ids = refs.get("RefIds")
    return isinstance(ref_ids, list) and len(ref_ids) > 0


def is_gamescript(tree: dict) -> bool:
    return isinstance(tree.get("m_commandDatas"), list)


def should_skip_class(class_name: str) -> bool:
    if class_name in SKIP_CLASSES:
        return True
    return any(class_name.startswith(p) for p in SKIP_CLASS_PREFIXES)


def is_whitelisted_field(field_path: str) -> bool:
    return any(m in field_path for m in PLAYER_FIELD_MARKERS)


def is_noise_string(s: str, *, field_path: str = "") -> bool:
    if not s or s in KNOWN_NOISE_EXACT:
        return True
    if is_whitelisted_field(field_path):
        return False
    if s.startswith("--") or s.startswith("<?") or s.startswith("<![CDATA["):
        return True
    if s.startswith("{") and ("$type" in s or "$ref" in s or '"nest"' in s):
        return True
    if s.startswith("<") and ">" in s and ("/" in s or s.count("<") >= 2):
        return True
    if "Assembly-CSharp" in s or "UnityEngine." in s:
        return True
    if s.startswith("CPU:") or s.startswith("GPU:") or s.startswith("RAM:") or s.startswith("VRAM:"):
        return True
    if "[#" in s or "####" in s:
        return True
    if len(s) > 8000:
        return True
    if GUID_RE.match(s.strip()):
        return True
    if VOICE_ID.match(s) or VOICE_ID_DLC.match(s):
        return True
    if HEX_COLOR.match(s):
        return True
    if s.startswith("Assets/") or "\\Assets\\" in s or s.startswith("Library/"):
        return True
    if "{" in s and "}" in s and "m_FileID" in s:
        return True
    if s in EXCLUDE_TEXT:
        return True
    if s in VS_PORT_LITERALS:
        return True
    # single identifier token
    if " " not in s and "/" not in s:
        if re.fullmatch(r"[a-z][a-zA-Z0-9_]*", s) and len(s) < 40:
            return True
        if re.fullmatch(r"[A-Z][a-zA-Z0-9]*(?:\.[A-Z][a-zA-Z0-9]*)+", s):
            return True
        if re.fullmatch(r"[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+", s) and len(s) < 48:
            return True
    return False


def is_english_prose(s: str, *, field_path: str = "") -> bool:
    if is_noise_string(s, field_path=field_path):
        return False
    if not re.search(r"[A-Za-z]", s):
        return False
    if JP_RE.search(s):
        return False
    words = EN_WORD_RE.findall(s)
    if len(words) >= 2:
        return True
    if " " in s and len(words) >= 1 and len(s) >= 6:
        return True
    if re.match(r"^[A-Z][a-z]+(?:[''][a-z]+)?[!?.]?$", s):
        return True
    if len(words) == 1 and len(words[0]) >= 10 and " " in s:
        return True
    if is_whitelisted_field(field_path) and len(words) >= 1 and len(s.strip()) >= 2:
        return True
    return False


def is_japanese_visible(s: str, *, field_path: str = "") -> bool:
    if not s or is_noise_string(s, field_path=field_path):
        return False
    return bool(JP_RE.search(s))


def should_skip_field(field_path: str) -> bool:
    if is_whitelisted_field(field_path):
        return False
    low = field_path.lower()
    for token in (
        "persistentcalls",
        "m_actionmaps",
        "m_rules",
        "m_controlschemes",
        "m_targetassemblytypename",
        "m_objectargumentassemblytypename",
        "m_methodname",
        "onrecieveevent",
        "m_onclick",
        "portkey",
        "entrystatename",
        "m_editorclassidentifier",
        "entries[",
        ".key",
        "m_animationtriggers",
        "m_faceinfo",
        "m_customblends",
    ):
        if token in low:
            return True
    for suf in SKIP_FIELD_SUFFIX:
        if suf.lower() in low:
            return True
    if low.endswith(".type") or low.endswith(".rid"):
        return True
    base = field_path.rsplit(".", 1)[-1]
    if base in ("m_EditorClassIdentifier", "m_EditorHideFlags", "m_Name", "key", "m_Name"):
        if not is_whitelisted_field(field_path):
            return True
    if base == "m_Name" and "GameObject" not in field_path:
        return True
    return False


def iter_vs_string_literals(obj: Any, parent_key: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        if "$type" in obj and "GraphGroup" in str(obj.get("$type", "")):
            lab = obj.get("label")
            if isinstance(lab, str):
                found.append(("GraphGroup.label", lab))
        if "$content" in obj and isinstance(obj["$content"], str):
            leaf = parent_key.rsplit(".", 1)[-1]
            if leaf in VS_CONTENT_KEYS:
                found.append((parent_key, obj["$content"]))
        for k, v in obj.items():
            fp = f"{parent_key}.{k}" if parent_key else k
            found.extend(iter_vs_string_literals(v, fp))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(iter_vs_string_literals(v, f"{parent_key}[{i}]"))
    return found


def parse_vs_blob(raw: str) -> list[tuple[str, str]]:
    if not raw or not raw.startswith("{"):
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    found: list[tuple[str, str]] = []
    embed = (data.get("nest") or {}).get("embed") or {}
    for k in ("title", "summary"):
        v = embed.get(k)
        if isinstance(v, str) and v:
            found.append((f"embed.{k}", v))
    found.extend(iter_vs_string_literals(data))
    return found


def collect_vs_data_strings(tree: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    data = tree.get("_data")
    if isinstance(data, str):
        for fp, s in parse_vs_blob(data):
            out.append((f"_data.{fp}", s))
    elif isinstance(data, dict):
        raw = data.get("_json") or data.get("json")
        if isinstance(raw, str):
            for fp, s in parse_vs_blob(raw):
                out.append((f"_data.{fp}", s))
    for key in ("jsonData", "m_GraphData", "graphData"):
        raw = tree.get(key)
        if isinstance(raw, str):
            for fp, s in parse_vs_blob(raw):
                out.append((f"{key}.{fp}", s))
    return out


def build_script_map(env: UnityPy.Environment) -> dict[int, str]:
    out: dict[int, str] = {}
    for o in env.objects:
        if o.type.name != "MonoScript":
            continue
        try:
            st = o.read_typetree()
            ns = st.get("m_Namespace") or ""
            cls = st.get("m_ClassName") or "MonoBehaviour"
            out[o.path_id] = f"{ns}.{cls}" if ns else cls
        except Exception:
            continue
    return out


def resolve_script(script_map: dict[int, str], tree: dict) -> str:
    sp = tree.get("m_Script")
    if not isinstance(sp, dict):
        return "MonoBehaviour"
    pid = sp.get("m_PathID")
    if pid is None:
        return "MonoBehaviour"
    return script_map.get(pid, "MonoBehaviour")


def asset_table_skip(tree: dict) -> bool:
    name = str(tree.get("m_Name") or "")
    if name in ("Translation_en", "Translation_ja", "Translation_zh-CN", "Image_en", "Image_ja", "Image_zh-CN"):
        return True
    return False


def text_asset_skip(name: str) -> bool:
    n = name or ""
    if n.endswith("_EN") or n.endswith("_CN"):
        return True
    for pref in EXCLUDE_ASSET_PREFIXES:
        if n.startswith(pref):
            return True
    return False


@dataclass
class RawHit:
    category: str
    class_name: str
    field: str
    text: str
    location: dict[str, Any]


@dataclass
class FileScanResult:
    file: str
    relpath: str
    error: str | None = None
    hits: list[RawHit] = field(default_factory=list)
    dg_assets: int = 0
    dg_english_strings: int = 0
    gamescript_assets: int = 0
    ja_hits: list[RawHit] = field(default_factory=list)
    localized_images: list[dict[str, Any]] = field(default_factory=list)


def walk_strings(
    obj: Any,
    prefix: str,
    category: str,
    class_name: str,
    loc: dict[str, Any],
    out: list[RawHit],
    ja_out: list[RawHit],
    *,
    in_command_datas: bool = False,
) -> None:
    if isinstance(obj, str):
        if in_command_datas:
            return
        if should_skip_field(prefix):
            return
        if is_japanese_visible(obj, field_path=prefix):
            ja_out.append(RawHit(category, class_name, prefix, obj, loc))
        if is_english_prose(obj, field_path=prefix):
            out.append(RawHit(category, class_name, prefix, obj, loc))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k == "m_commandDatas":
                walk_strings(v, prefix, category, class_name, loc, out, ja_out, in_command_datas=True)
                continue
            if k in ("m_Script", "m_GameObject", "references") and category != "visual_scripting":
                continue
            fp = f"{prefix}.{k}" if prefix else k
            walk_strings(v, fp, category, class_name, loc, out, ja_out, in_command_datas=in_command_datas)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_strings(v, f"{prefix}[{i}]", category, class_name, loc, out, ja_out, in_command_datas=in_command_datas)


def count_dg_english(tree: dict) -> int:
    n = 0

    def w(o: Any) -> None:
        nonlocal n
        if isinstance(o, str) and len(o) > 1 and o not in EXCLUDE_TEXT:
            if JP_RE.search(o):
                return
            if re.search(r"[A-Za-z]", o):
                words = EN_WORD_RE.findall(o)
                if len(words) >= 2 or (" " in o and words):
                    n += 1
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ("m_Script", "m_GameObject"):
                    continue
                w(v)
        elif isinstance(o, list):
            for v in o:
                w(v)

    w(tree)
    return n


def scan_visual_scripting(
    env: UnityPy.Environment, relpath: str, script_map: dict[int, str]
) -> FileScanResult:
    res = FileScanResult(relpath, relpath)
    for o in env.objects:
        if o.type.name not in ("MonoScript", "MonoBehaviour", "ScriptableObject"):
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        cls = (
            resolve_script(script_map, tree)
            if o.type.name == "MonoBehaviour"
            else str(tree.get("m_Name") or o.type.name)
        )
        is_vs = False
        if "ScriptGraphAsset" in cls or cls.endswith(".ScriptGraphAsset"):
            is_vs = True
        if any(k in tree for k in ("jsonData", "_data", "graphData", "m_GraphData")):
            if "m_commandDatas" not in tree and not is_dialogue_graph(tree):
                is_vs = True
        if not is_vs:
            continue
        loc = {"file": relpath, "path_id": o.path_id, "unity_type": o.type.name}
        for fp, s in collect_vs_data_strings(tree):
            if is_japanese_visible(s, field_path=fp):
                res.ja_hits.append(RawHit("visual_scripting", cls, fp, s, loc))
            if is_english_prose(s, field_path=fp):
                res.hits.append(RawHit("visual_scripting", cls, fp, s, loc))
    return res


def scan_file(path: Path, relpath: str) -> FileScanResult:
    res = FileScanResult(str(path), relpath)
    try:
        env = UnityPy.load(str(path))
    except Exception as e:
        res.error = str(e)[:200]
        return res

    script_map = build_script_map(env)

    for o in env.objects:
        tname = o.type.name
        try:
            if tname == "TextAsset":
                ta = o.read()
                name = getattr(ta, "m_Name", "") or ""
                if text_asset_skip(name):
                    continue
                text = ""
                try:
                    text = ta.text
                except Exception:
                    try:
                        text = ta.read_typetree().get("m_Script") or ""
                    except Exception:
                        pass
                if not isinstance(text, str):
                    continue
                loc = {"file": relpath, "path_id": o.path_id, "asset_name": name}
                if is_japanese_visible(text[:5000]):
                    res.ja_hits.append(
                        RawHit("text_asset", "TextAsset", "text", text[:500], loc)
                    )
                if is_english_prose(text[:5000]):
                    res.hits.append(RawHit("text_asset", "TextAsset", "text", text[:500], loc))
                continue

            if tname in ("Texture2D", "Sprite"):
                try:
                    data = o.read()
                    name = getattr(data, "m_Name", "") or ""
                except Exception:
                    continue
                if name.endswith("_EN") or name.endswith("_en"):
                    w = h = 0
                    try:
                        w, h = int(getattr(data, "m_Width", 0)), int(getattr(data, "m_Height", 0))
                    except Exception:
                        pass
                    res.localized_images.append(
                        {
                            "name": name,
                            "width": w,
                            "height": h,
                            "file": relpath,
                            "path_id": o.path_id,
                            "unity_type": tname,
                        }
                    )
                continue

            if tname == "AnimationClip":
                try:
                    tree = o.read_typetree()
                except Exception:
                    continue
                events = tree.get("m_Events") or []
                loc = {"file": relpath, "path_id": o.path_id, "asset_name": tree.get("m_Name")}
                for i, ev in enumerate(events):
                    if not isinstance(ev, dict):
                        continue
                    for key in ("functionName", "stringParameter", "objectReferenceParameter"):
                        val = ev.get(key)
                        if isinstance(val, str):
                            fp = f"m_Events[{i}].{key}"
                            if is_japanese_visible(val):
                                res.ja_hits.append(RawHit("animation", "AnimationClip", fp, val, loc))
                            if is_english_prose(val):
                                res.hits.append(RawHit("animation", "AnimationClip", fp, val, loc))
                continue

            if tname not in ("MonoBehaviour", "ScriptableObject"):
                continue

            tree = o.read_typetree()
            if asset_table_skip(tree):
                continue

            if is_gamescript(tree):
                res.gamescript_assets += 1
                continue

            if is_dialogue_graph(tree):
                res.dg_assets += 1
                res.dg_english_strings += count_dg_english(tree)
                continue

            cls = (
                resolve_script(script_map, tree)
                if tname == "MonoBehaviour"
                else str(tree.get("m_Name") or tname)
            )
            if should_skip_class(cls) or cls in VS_GRAPH_CLASSES:
                continue
            loc = {"file": relpath, "path_id": o.path_id, "unity_type": tname}

            # TMP / legacy UI
            for ui_key in ("m_text", "m_Text"):
                if ui_key in tree and isinstance(tree[ui_key], str):
                    val = tree[ui_key]
                    cat = "tmp_ui" if ui_key == "m_text" else "ui_text"
                    if is_japanese_visible(val):
                        res.ja_hits.append(RawHit(cat, cls, ui_key, val, loc))
                    if is_english_prose(val):
                        res.hits.append(RawHit(cat, cls, ui_key, val, loc))

            # Dropdown options
            opts = tree.get("m_Options")
            if isinstance(opts, dict):
                arr = opts.get("m_Options") or opts.get("m_OptionsArray") or []
                if isinstance(arr, list):
                    for i, item in enumerate(arr):
                        if isinstance(item, dict):
                            mt = item.get("m_Text")
                            if isinstance(mt, str):
                                fp = f"m_Options.m_Options[{i}].m_Text"
                                if is_japanese_visible(mt):
                                    res.ja_hits.append(RawHit("tmp_ui", cls, fp, mt, loc))
                                if is_english_prose(mt):
                                    res.hits.append(RawHit("tmp_ui", cls, fp, mt, loc))

            cat = "scriptable_object" if tname == "ScriptableObject" else "mono_behaviour"
            if cls == "MonoBehaviour":
                for key, val in tree.items():
                    if not isinstance(val, str):
                        continue
                    if not is_whitelisted_field(key):
                        continue
                    if is_japanese_visible(val, field_path=key):
                        res.ja_hits.append(RawHit(cat, cls, key, val, loc))
                    if is_english_prose(val, field_path=key):
                        res.hits.append(RawHit(cat, cls, key, val, loc))
            else:
                walk_strings(tree, "", cat, cls, loc, res.hits, res.ja_hits)

        except Exception:
            continue

    vs_extra = scan_visual_scripting(env, relpath, script_map)
    res.hits.extend(vs_extra.hits)
    res.ja_hits.extend(vs_extra.ja_hits)
    return res


def load_exclusions() -> tuple[frozenset[str], tuple[str, ...]]:
    texts: set[str] = set()
    prefixes: set[str] = set()

    src = ROOT / "es_source.json"
    if src.is_file():
        data = json.loads(src.read_text(encoding="utf-8"))
        for row in data.get("strings") or []:
            for k in ("en", "ja", "key"):
                v = row.get(k)
                if v:
                    texts.add(v)
        for sc in data.get("scripts") or []:
            name = sc.get("name") or sc.get("asset") or ""
            if name:
                prefixes.add(str(name).split("_EN")[0])
            for e in sc.get("entries") or []:
                for k in ("en", "ja"):
                    v = e.get(k)
                    if v:
                        texts.add(v)

    scripts = ROOT / "es_source_scripts.json"
    if scripts.is_file():
        data = json.loads(scripts.read_text(encoding="utf-8"))
        for row in data.get("texts") or data.get("strings") or []:
            en = row.get("en")
            if en:
                texts.add(en)

    return frozenset(texts), tuple(sorted(prefixes))


def collect_scan_paths() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    if AA.is_dir():
        for p in sorted(AA.rglob("*.bundle")):
            try:
                rel = p.relative_to(AA).as_posix()
            except ValueError:
                rel = p.name
            out.append((p, rel))
    data = DATA
    for name in ("globalgamemanagers", "globalgamemanagers.assets", "resources.assets"):
        fp = data / name
        if fp.is_file():
            out.append((fp, name))
    for fp in sorted(data.glob("sharedassets*.assets")):
        out.append((fp, fp.name))
    for fp in sorted(data.glob("level*")):
        if fp.is_file() and fp.suffix not in (".resS",):
            out.append((fp, fp.name))
    return out


def merge_hits(all_hits: list[RawHit]) -> list[dict[str, Any]]:
    bucket: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for h in all_hits:
        key = (h.category, h.class_name, h.field, h.text)
        if key not in bucket:
            bucket[key] = {
                "category": h.category,
                "class": h.class_name,
                "field": h.field,
                "text": h.text,
                "locations": [],
            }
        locs = bucket[key]["locations"]
        if h.location not in locs:
            locs.append(h.location)
    merged = list(bucket.values())
    merged.sort(key=lambda x: (x["category"], x["class"], x["text"]))
    return merged


def summarize_by_class(hits: list[dict[str, Any]], limit_examples: int = 5) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for h in hits:
        groups[(h["category"], h["class"])].append(h)
    summary = []
    for (cat, cls), items in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        fields = Counter(h["field"].split(".")[0] if h["field"] else "?" for h in items)
        texts = sorted({h["text"] for h in items})
        summary.append(
            {
                "category": cat,
                "class": cls,
                "distinct_strings": len(texts),
                "hit_records": len(items),
                "top_fields": dict(fields.most_common(8)),
                "examples": texts[:limit_examples],
                "files": sorted({loc["file"] for h in items for loc in h["locations"]})[:12],
            }
        )
    return summary


def write_report(
    path: Path,
    merged: list[dict[str, Any]],
    ja_merged: list[dict[str, Any]],
    stats: dict[str, Any],
    images: list[dict[str, Any]],
) -> None:
    lines: list[str] = []
    lines.append("# Remaining player-visible text (survey)")
    lines.append("")
    lines.append(f"**Game path:** `{GAME}`  ")
    lines.append(f"**Generated:** {stats['generated']}  ")
    lines.append(f"**Scanner:** `translation/research/remaining_text/scan_remaining_text.py`")
    lines.append("")
    lines.append("## Exclusions (not listed as remaining work)")
    lines.append("")
    lines.append("- Unity `Translation_en` / H-scene `*_EN` TextAssets / `Image_en` table entries (handled via `es_source.json`).")
    lines.append("- GameScript `m_commandDatas` literals (handled via `es_source_scripts.json`).")
    lines.append(
        f"- Dialogue graph MonoBehaviours (edges/nodes/labelNodes/…): **{stats['dialogue_graph_assets']} assets**, "
        f"~**{stats['dialogue_graph_english_strings']}** English prose strings counted inside (patched elsewhere)."
    )
    lines.append("")
    lines.append("## Summary counts")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|------:|")
    for k, v in stats["counts"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## Categories (storage + patch approach + priority)")
    lines.append("")

    cat_notes = {
        "tmp_ui": (
            "TMP `m_text` / `TMP_Dropdown.m_Options` on prefabs in Addressables or built-in scenes.",
            "UnityPy `read_typetree()` → edit string fields → `obj.save()` / rebundle; same CRC forge flow as other bundle patches.",
            "**High** — menus, HUD, interaction prompts baked into prefabs.",
        ),
        "ui_text": (
            "Legacy `UnityEngine.UI.Text` (`m_Text`).",
            "Typetree string replace in bundle or sharedassets.",
            "**High** where present (mostly legacy UI).",
        ),
        "mono_behaviour": (
            "Serialized string fields on scene/prefab components (quest titles, labels, custom UI data).",
            "Typetree walk + patch per `path_id`; resolve class via `m_Script` → `MonoScript.m_ClassName`.",
            "**High** for gameplay/UI components; filter out Visual Scripting port identifiers.",
        ),
        "scriptable_object": (
            "ScriptableObject assets (items, galleries, config) with string lists.",
            "Typetree edit in owning bundle.",
            "**Medium–High** if shown in inventory/gallery/achievement UI.",
        ),
        "text_asset": (
            "Standalone `TextAsset` JSON/CSV/TXT (not `_EN` voice scripts).",
            "Replace `TextAsset` bytes or typetree `m_Script` text; watch encoding.",
            "**Medium** — depends on runtime loader.",
        ),
        "visual_scripting": (
            "Unity Visual Scripting graphs (`ScriptGraphAsset`, `_data` / `jsonData` string literals).",
            "Typetree edit of literal strings inside graph JSON; avoid port keys.",
            "**High** for language dropdown / flow UI wired in VS.",
        ),
        "animation": (
            "`AnimationClip.m_Events` string parameters.",
            "Typetree event array edit.",
            "**Low–Medium** — rare for player-readable copy.",
        ),
        "localized_image": (
            "Sprites/textures named `*_EN` / `*_en` (localized UI images).",
            "Replace texture in bundle; keep name/`Image_en` GUID keys (Spanish hijacks `en` slot).",
            "**High** for tutorial/sign graphics; 88 pairs noted in catalog survey.",
        ),
    }

    by_cat: Counter[str] = Counter()
    for h in merged:
        by_cat[h["category"]] += 1

    for cat in sorted(by_cat.keys()):
        note = cat_notes.get(cat, ("See candidates.json", "UnityPy typetree", "**TBD**"))
        lines.append(f"### `{cat}` — {by_cat[cat]} distinct strings")
        lines.append("")
        lines.append(f"- **Storage:** {note[0]}")
        lines.append(f"- **Patch:** {note[1]}")
        lines.append(f"- **Player priority:** {note[2]}")
        lines.append("")

    if images:
        lines.append("## Localized images (`*_EN` / `*_en`)")
        lines.append("")
        lines.append(f"Distinct names: **{len({i['name'] for i in images})}** (instances in files: {len(images)}).")
        lines.append("")
        lines.append("Text-bearing candidates (filename hints: tutorial, guide, hint, text, title, menu, help, tip):")
        hints = ("tutorial", "guide", "hint", "text", "title", "menu", "help", "tip", "how", "control")
        text_like = [i for i in images if any(h in i["name"].lower() for h in hints)]
        for i in sorted(text_like, key=lambda x: x["name"])[:40]:
            lines.append(f"- `{i['name']}` ({i['width']}x{i['height']}) — `{i['file']}`")
        if len(text_like) > 40:
            lines.append(f"- … and {len(text_like) - 40} more (see `scan_stats.json`).")
        lines.append("")

    lines.append("## Top component classes (English prose)")
    lines.append("")
    for row in stats["class_summary"][:25]:
        lines.append(
            f"- **{row['class']}** ({row['category']}): {row['distinct_strings']} strings — "
            f"fields {row['top_fields']}; e.g. {row['examples'][:3]}"
        )
    lines.append("")
    lines.append("## Japanese text in non-JP assets (possible EN-locale leaks)")
    lines.append("")
    ja_by_cat = stats.get("japanese_by_category", {})
    if ja_by_cat:
        for cat, n in sorted(ja_by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"- `{cat}`: **{n}** distinct strings")
        lines.append("")
        for row in stats.get("japanese_examples", [])[:15]:
            lines.append(f"  - [{row['category']}] `{row['text'][:80]}`")
    else:
        lines.append("- None matched heuristics.")
    lines.append("")
    lines.append("## Player-impact ranking (recommended order)")
    lines.append("")
    lines.append(
        f"0. **Dialogue graph nodes** (excluded here) — ~**{stats['dialogue_graph_english_strings']}** "
        f"English strings in **{stats['dialogue_graph_assets']}** graph assets; typetree patch on graph "
        f"`references.RefIds[].data` (handled by dialogue graph pipeline)."
    )
    ranking = stats.get("priority_ranking", [])
    for i, row in enumerate(ranking, 1):
        lines.append(
            f"{i}. **{row['label']}** — ~{row['distinct']} distinct strings; {row['approach']}"
        )
    pf = stats.get("player_facing_gameplay", {})
    if pf:
        lines.append("")
        lines.append("### High-confidence gameplay copy (subset)")
        lines.append("")
        for label, n in pf.items():
            lines.append(f"- **{label}**: {n} distinct strings")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _worker_init(exclude_text: frozenset[str], exclude_prefixes: tuple[str, ...]) -> None:
    global EXCLUDE_TEXT, EXCLUDE_ASSET_PREFIXES
    EXCLUDE_TEXT = exclude_text
    EXCLUDE_ASSET_PREFIXES = exclude_prefixes


def main() -> int:
    global EXCLUDE_TEXT, EXCLUDE_ASSET_PREFIXES
    if not DATA.is_dir():
        print(f"Missing game data: {DATA}", file=sys.stderr)
        return 1

    exclude_text, exclude_prefixes = load_exclusions()
    EXCLUDE_TEXT = exclude_text
    EXCLUDE_ASSET_PREFIXES = exclude_prefixes

    paths = collect_scan_paths()
    print(f"Scanning {len(paths)} files under {GAME}", flush=True)

    all_hits: list[RawHit] = []
    all_ja: list[RawHit] = []
    all_images: list[dict[str, Any]] = []
    dg_assets = 0
    dg_en = 0
    gs_assets = 0
    errors: list[str] = []

    workers = min(16, max(2, (os.cpu_count() or 4) - 1))
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_worker_init,
        initargs=(exclude_text, exclude_prefixes),
    ) as ex:
        futs = {ex.submit(scan_file, p, rel): rel for p, rel in paths}
        done = 0
        for fut in as_completed(futs):
            done += 1
            if done % 500 == 0:
                print(f"  … {done}/{len(futs)}", flush=True)
            r = fut.result()
            if r.error:
                errors.append(f"{r.relpath}: {r.error}")
            all_hits.extend(r.hits)
            all_ja.extend(r.ja_hits)
            all_images.extend(r.localized_images)
            dg_assets += r.dg_assets
            dg_en += r.dg_english_strings
            gs_assets += r.gamescript_assets

    merged = merge_hits(all_hits)
    ja_merged = merge_hits(all_ja)

    by_cat_distinct = Counter(h["category"] for h in merged)
    ja_by_cat = Counter(h["category"] for h in ja_merged)

    priority_ranking = []
    labels = {
        "tmp_ui": ("Prefab TMP / dropdown labels", "Typetree `m_text` / options in scene bundles"),
        "visual_scripting": ("Visual Scripting UI literals", "Graph typetree string literals"),
        "mono_behaviour": ("Component serialized UI copy", "Typetree per MonoBehaviour"),
        "scriptable_object": ("ScriptableObject tables", "Typetree on SO assets"),
        "text_asset": ("Loose TextAssets", "TextAsset body replace"),
        "ui_text": ("Legacy UI Text", "Typetree `m_Text`"),
        "animation": ("Animation event strings", "Clip event typetree"),
        "localized_image": ("Localized PNG/UI art", "Texture swap in Addressables"),
    }
    for cat, _ in sorted(by_cat_distinct.items(), key=lambda x: -x[1]):
        label, approach = labels.get(cat, (cat, "UnityPy typetree"))
        priority_ranking.append({"label": label, "distinct": by_cat_distinct[cat], "approach": approach})
    img_names = len({i["name"] for i in all_images})
    if img_names:
        priority_ranking.append(
            {
                "label": "Localized `_EN` images",
                "distinct": img_names,
                "approach": "Replace sprites/textures; keep Addressables names",
            }
        )

    player_facing_gameplay = {
        "Interactable.text (world prompts)": sum(
            1 for h in merged if h["class"] == "StrayCatLab.Game.Interactable" and h["field"] == "text"
        ),
        "ItemData (names/descriptions)": sum(
            1 for h in merged if h["class"] == "StrayCatLab.Game.ItemData"
        ),
        "Locale display names (en/zh/ja)": sum(
            1 for h in merged if h["class"] == "UnityEngine.Localization.Locale"
        ),
        "TMP in-scene (m_text)": sum(
            1
            for h in merged
            if h["field"] in ("m_text", "m_Text")
            and h["class"] not in ("UnityEngine.UI.Text", "MonoBehaviour")
            and not h["text"].startswith("New Text")
        ),
    }

    stats = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "game_path": str(GAME),
        "files_scanned": len(paths),
        "scan_errors": len(errors),
        "dialogue_graph_assets": dg_assets,
        "dialogue_graph_english_strings": dg_en,
        "gamescript_assets_skipped": gs_assets,
        "exclude_text_count": len(exclude_text),
        "counts": {
            "distinct_english_candidates": len(merged),
            "distinct_japanese_leaks": len(ja_merged),
            "localized_image_instances": len(all_images),
            "localized_image_unique_names": img_names,
            **{f"english_{k}": v for k, v in sorted(by_cat_distinct.items())},
        },
        "class_summary": summarize_by_class(merged),
        "japanese_by_category": dict(ja_by_cat),
        "japanese_examples": [{"category": h["category"], "text": h["text"]} for h in ja_merged[:30]],
        "priority_ranking": priority_ranking,
        "errors_sample": errors[:20],
        "player_facing_gameplay": player_facing_gameplay,
    }

    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "candidates.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (HERE / "scan_stats.json").write_text(
        json.dumps({**stats, "localized_images": all_images}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(HERE / "REMAINING_TEXT.md", merged, ja_merged, stats, all_images)

    print(f"Done. {len(merged)} English candidates, {len(ja_merged)} Japanese leaks, {img_names} image names.")
    print(f"Wrote {HERE / 'candidates.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
