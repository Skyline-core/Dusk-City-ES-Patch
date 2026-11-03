"""Shared misc-text path navigation, filtering, and bundle helpers."""
from __future__ import annotations

import json
import re
from typing import Any

import UnityPy

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
BRACKET = re.compile(r"^(\w+)\[(\d+)\]$")

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
        "sleep",
    }
)

TMP_PLACEHOLDERS = frozenset(
    {
        "New Text",
        "Button",
        "Item description is here\nsecond line\nthird line\nfourth line\nfinal line",
        "ItemNameaaaaaaaaaa",
    }
)

SKIP_CLASSES = frozenset(
    {
        "BallHitChecer",
        "DronePawn",
        "ObjectSwitcher",
        "StrayCatLab.Game.MovingPlatformController",
        "StrayCatLab.Game.TrainPusher",
        "UnityEngine.EventSystems.StandaloneInputModule",
        "StrayCatLab.Utilities.Audio.BGMTrigger",
        "UnityEngine.Localization.Tables.SharedTableData",
        "UnityEventHolder",
        "Dieselmine.Utilities.GameVariable.IntVariableTable",
        "WaterSurface",
        "MonoBehaviour",
    }
)

IN_SCOPE_CLASSES = frozenset(
    {
        "StrayCatLab.Game.Interactable",
        "StrayCatLab.Game.ItemData",
        "TMPro.TextMeshProUGUI",
        "UnityEngine.UI.Text",
        "UnityEngine.Localization.Locale",
        "StrayCatLab.Game.WeaponUpgrade",
        "StrayCatLab.Game.SnakeBoss",
    }
)

DEBUG_UI_PREFIXES = (
    "CPU:",
    "GPU:",
    "RAM:",
    "VRAM:",
    "OS:",
    "Graphics API:",
    "Screen:",
    "VR:",
    "Window:",
)


def parse_token(token: str) -> list[str | int]:
    m = BRACKET.match(token)
    if m:
        return [m.group(1), int(m.group(2))]
    return [token]


def split_field(field: str) -> tuple[list[Any], str]:
    """Return (path_segments, leaf_field) for typetree / VS blob navigation."""
    if field.startswith("_data."):
        return ["_data"], field[6:]
    if not field or "." not in field:
        m = BRACKET.match(field)
        if m:
            return [m.group(1), int(m.group(2))], ""
        return [], field
    parts = field.split(".")
    path: list[Any] = []
    for p in parts[:-1]:
        path.extend(parse_token(p))
    leaf = parts[-1]
    m = BRACKET.match(leaf)
    if m:
        path.extend([m.group(1), int(m.group(2))])
        return path, ""
    return path, leaf


def navigate(obj: Any, path: list[Any]) -> Any:
    cur = obj
    for seg in path:
        if isinstance(cur, dict):
            cur = cur.get(seg)
        elif isinstance(cur, list) and isinstance(seg, int):
            cur = cur[seg] if 0 <= seg < len(cur) else None
        else:
            return None
    return cur


def read_json_subpath(blob: str, subpath: str) -> str | None:
    if not blob or not blob.startswith("{"):
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    path, leaf = split_field(subpath) if subpath else ([], "")
    node = navigate(data, path) if path else data
    if leaf:
        if not isinstance(node, dict):
            return None
        val = node.get(leaf)
    else:
        val = node
    return val if isinstance(val, str) else None


def write_json_subpath(blob: str, subpath: str, new_val: str) -> str:
    data = json.loads(blob)
    path, leaf = split_field(subpath) if subpath else ([], "")
    node = navigate(data, path) if path else data
    if leaf:
        if not isinstance(node, dict):
            raise KeyError(f"VS parent not dict at {path!r}")
        node[leaf] = new_val
    else:
        raise KeyError("VS subpath missing leaf")
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def read_string(tree: dict, path: list[Any], field: str) -> str | None:
    if path == ["_data"] and field:
        raw = tree.get("_data")
        if isinstance(raw, str):
            return read_json_subpath(raw, field)
        if isinstance(raw, dict):
            inner = raw.get("_json") or raw.get("json")
            if isinstance(inner, str):
                return read_json_subpath(inner, field)
        return None
    node = navigate(tree, path) if path else tree
    if field:
        if not isinstance(node, dict):
            return None
        val = node.get(field)
    else:
        val = node
    return val if isinstance(val, str) else None


def write_string(tree: dict, path: list[Any], field: str, new_val: str) -> None:
    if path == ["_data"] and field:
        raw = tree.get("_data")
        if isinstance(raw, str):
            tree["_data"] = write_json_subpath(raw, field, new_val)
            return
        if isinstance(raw, dict):
            for key in ("_json", "json"):
                inner = raw.get(key)
                if isinstance(inner, str):
                    raw[key] = write_json_subpath(inner, field, new_val)
                    return
        raise KeyError("_data VS blob missing")
    node = navigate(tree, path) if path else tree
    if field:
        if not isinstance(node, dict):
            raise KeyError(f"path {path!r} not dict")
        node[field] = new_val
    else:
        raise KeyError("empty field for write")


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


def gameobject_path_id(tree: dict) -> int | None:
    go = tree.get("m_GameObject")
    if isinstance(go, dict):
        pid = go.get("m_PathID")
        if pid is not None:
            return int(pid)
    return None


def has_localize_on_same_go(env: UnityPy.Environment, script_map: dict[int, str], path_id: int) -> bool:
    monos = [o for o in env.objects if o.type.name == "MonoBehaviour"]
    target_go: int | None = None
    for o in monos:
        if o.path_id != path_id:
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        target_go = gameobject_path_id(t)
        break
    if target_go is None:
        return False
    for o in monos:
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if gameobject_path_id(t) != target_go:
            continue
        cls = resolve_script(script_map, t)
        if "LocalizeStringEvent" in cls or cls.endswith(".LocalizeStringEvent"):
            return True
    return False


def is_vs_player_visible(field: str, text: str) -> bool:
    if text in VS_PORT_LITERALS:
        return False
    if field.endswith("GraphGroup.label"):
        return False
    if ".defaultValues.label" in field:
        if " " not in text and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", text):
            return False
    if field.startswith("_data.embed.title") or field.startswith("_data.embed.summary"):
        return bool(re.search(r"[A-Za-z]", text) and (" " in text or len(text) > 12))
    return False


def classify_kind(category: str, class_name: str, field: str) -> str:
    if class_name == "StrayCatLab.Game.Interactable":
        return "interactable"
    if class_name == "StrayCatLab.Game.ItemData":
        return "item"
    if class_name == "TMPro.TextMeshProUGUI" or field == "m_text":
        return "tmp_ui"
    if class_name == "UnityEngine.UI.Text" or field == "m_Text":
        return "ui_text"
    if class_name == "UnityEngine.Localization.Locale":
        return "locale"
    if category == "visual_scripting":
        return "visual_scripting"
    return "other"


def inclusion_decision(entry: dict[str, Any]) -> tuple[bool, str]:
    cat = entry["category"]
    cls = entry["class"]
    field = entry["field"]
    text = entry["text"]

    if not entry.get("locations"):
        return False, "no_locations"

    for loc in entry["locations"]:
        f = loc.get("file") or ""
        if not f.startswith("StandaloneWindows64/") or not f.endswith(".bundle"):
            return False, "non_bundle_asset"

    if cls in SKIP_CLASSES:
        return False, "skip_class"

    if cat == "visual_scripting":
        if is_vs_player_visible(field, text):
            return True, ""
        return False, "vs_internal_label"

    if cat == "tmp_ui" and cls != "TMPro.TextMeshProUGUI":
        return False, "tmp_ui_noise_class"

    if cls == "MonoBehaviour" and field == "m_text":
        return False, "placeholder_mono"

    if cls == "TMPro.TextMeshProUGUI" or (field == "m_text" and cat == "mono_behaviour"):
        if text in TMP_PLACEHOLDERS:
            return False, "tmp_placeholder"
        if cls == "TMPro.TextMeshProUGUI" or cat == "mono_behaviour":
            return True, ""

    if cls in IN_SCOPE_CLASSES:
        if cls == "UnityEngine.UI.Text":
            if text.lower() in ("mb", "fps", "ms", "dB", "ram", "mono", "audio", "avg", "allocated", "reserved"):
                return True, ""
            if any(text.startswith(p) for p in DEBUG_UI_PREFIXES):
                return True, ""
            if cat == "ui_text":
                return True, ""
            return False, "ui_text_debug_short"
        if cls == "UnityEngine.Localization.Locale":
            if field.startswith("m_Identifier"):
                return False, "locale_code"
            return True, ""
        return True, ""

    return False, "out_of_scope"


def load_en_to_ja(root) -> dict[str, str]:
    from pathlib import Path

    src_path = Path(root) / "es_source.json"
    if not src_path.is_file():
        return {}
    data = json.loads(src_path.read_text(encoding="utf-8"))
    m: dict[str, str] = {}
    for sc in data.get("scripts") or []:
        for e in sc.get("entries") or []:
            en = e.get("en") or ""
            ja = e.get("ja") or ""
            if en and ja and en not in m:
                m[en] = ja
    for row in data.get("strings") or []:
        en = row.get("en") or ""
        ja = row.get("ja") or ""
        if en and ja and en not in m:
            m[en] = ja
    return m


def load_translation_en_keys(root) -> set[str]:
    from pathlib import Path

    keys: set[str] = set()
    src_path = Path(root) / "es_source.json"
    if not src_path.is_file():
        return keys
    data = json.loads(src_path.read_text(encoding="utf-8"))
    for row in data.get("strings") or []:
        for k in ("en", "ja", "key"):
            v = row.get(k)
            if v:
                keys.add(v)
    return keys
