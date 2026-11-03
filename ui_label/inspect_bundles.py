"""Deep UnityPy inspect of candidate bundles for language UI."""
from __future__ import annotations

import json
from pathlib import Path

import UnityPy

TARGETS = [
    Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\localization-locales_assets_all.bundle"),
    Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\7ff7bbb50d8963f8cfda64e43d946131.bundle"),
]

NEEDLES = [
    "English", "Japanese", "Chinese", "日本語", "简体中文", "m_Options",
    "LocalizeManager", "Languages", "Locale", "dropdown",
]


def walk_tree(obj, depth=0, max_depth=8):
    if depth > max_depth:
        return None
    if isinstance(obj, str):
        return obj if any(n in obj for n in NEEDLES) else None
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and any(n in k for n in NEEDLES):
                out[k] = v
                continue
            sub = walk_tree(v, depth + 1, max_depth)
            if sub is not None:
                out[k] = sub
        return out if out else None
    if isinstance(obj, list):
        out = []
        for v in obj:
            sub = walk_tree(v, depth + 1, max_depth)
            if sub is not None:
                out.append(sub)
        return out if out else None
    return None


def inspect_path(path: Path) -> list[dict]:
    records = []
    env = UnityPy.load(str(path))
    for o in env.objects:
        try:
            if o.type.name == "MonoBehaviour":
                t = o.read_typetree()
            elif o.type.name == "TextAsset":
                ta = o.read()
                text = getattr(ta, "text", "") or ""
                if any(n in text for n in NEEDLES):
                    records.append({
                        "path_id": o.path_id,
                        "type": "TextAsset",
                        "name": ta.m_Name,
                        "snippet": text[:500],
                    })
                continue
            else:
                continue
        except Exception as e:
            continue
        name = t.get("m_Name", "")
        blob = json.dumps(t, ensure_ascii=False, default=str)
        if not any(n in blob for n in NEEDLES):
            continue
        rec = {
            "path_id": o.path_id,
            "type": "MonoBehaviour",
            "name": name,
            "keys": list(t.keys())[:30],
        }
        if "m_Options" in t:
            rec["m_Options"] = t["m_Options"]
        for fk in ("m_text", "m_LocaleName", "m_Name"):
            if fk in t and isinstance(t[fk], str) and any(n in t[fk] for n in NEEDLES):
                rec[fk] = t[fk]
        trimmed = walk_tree(t)
        if trimmed:
            rec["trimmed"] = trimmed
        records.append(rec)
    return records


def main():
    all_out = {}
    for p in TARGETS:
        if not p.is_file():
            all_out[p.name] = {"error": "missing"}
            continue
        print("Inspecting", p.name)
        all_out[p.name] = inspect_path(p)
        print("  hits", len(all_out[p.name]))

    out = Path(__file__).parent / "inspect_bundles.json"
    out.write_text(json.dumps(all_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", out)


if __name__ == "__main__":
    main()
