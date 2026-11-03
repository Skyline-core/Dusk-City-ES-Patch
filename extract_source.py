"""Extract ja + en localized text from the game into translation/es_source.json.

Read-only on the game folder. Output schema (see README_translation.md):
{
  "meta": {...},
  "strings": [ {"id": int, "key": str, "ja": str, "en": str, "es": ""}, ... ],
  "scripts": [ {"asset": "Cafe_staff_dhs13", "en_asset": "..._EN", "ja_asset": "...",
                "entries": [ {"path": "idle/texts/0", "voice": str, "ja": str, "en": str, "es": ""}, ... ]}, ... ]
}
"""
import glob
import json
import os
import re

import UnityPy

BASE = r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "es_source.json")


def load(pattern):
    files = glob.glob(os.path.join(BASE, pattern))
    assert len(files) == 1, (pattern, files)
    return UnityPy.load(files[0])


def string_table(pattern):
    for o in load(pattern).objects:
        if o.type.name == "MonoBehaviour":
            return o.read_typetree()


def shared_keys():
    for o in load("localization-assets-shared*").objects:
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            if t["m_Name"] == "Translation Shared Data":
                return {e["m_Id"]: e["m_Key"] for e in t["m_Entries"]}


def text_assets(env):
    out = {}
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            raw = d.m_Script
            out[d.m_Name] = raw if isinstance(raw, str) else bytes(raw).decode("utf-8-sig")
    return out


def collect_texts(node, path=""):
    """Yield (path, dict) for every dict that has a 'text' key."""
    if isinstance(node, dict):
        if "text" in node and isinstance(node["text"], str):
            yield path, node
        for k, v in node.items():
            yield from collect_texts(v, f"{path}/{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from collect_texts(v, f"{path}/{i}")


def main():
    en = string_table("localization-string-tables-english*")
    ja = string_table("localization-string-tables-japanese*")
    keys = shared_keys()
    ja_map = {e["m_Id"]: e["m_Localized"] for e in ja["m_TableData"]}

    strings = []
    for e in en["m_TableData"]:
        i = e["m_Id"]
        strings.append({
            "id": i,
            "key": keys.get(i, ""),
            "ja": ja_map.get(i, ""),
            "en": e["m_Localized"],
            "es": "",
        })

    te = text_assets(load("localization-assets-english(en)_assets_all_2226*"))
    tj = text_assets(load("localization-assets-japanese*"))
    scripts = []
    mismatch = []
    for en_name in sorted(te):
        base = re.sub(r"_EN$", "", en_name)
        ja_name = base if base in tj else None
        en_json = json.loads(te[en_name])
        ja_json = json.loads(tj[ja_name]) if ja_name else None
        ja_texts = dict(collect_texts(ja_json)) if ja_json else {}
        entries = []
        for path, node in collect_texts(en_json):
            jn = ja_texts.get(path)
            if jn is not None and jn.get("voice") != node.get("voice"):
                mismatch.append((en_name, path))
            entries.append({
                "path": path,
                "voice": node.get("voice", ""),
                "ja": jn["text"] if jn else "",
                "en": node["text"],
                "es": "",
            })
        scripts.append({"asset": base, "en_asset": en_name, "ja_asset": ja_name, "entries": entries})

    data = {
        "meta": {
            "game": "Dusk City",
            "note": "Fill the 'es' field of every entry. Keep tags (<br>, <color=...>, <sprite name=...>, \\n, <X>) intact.",
            "string_count": len(strings),
            "script_entry_count": sum(len(s["entries"]) for s in scripts),
        },
        "strings": strings,
        "scripts": scripts,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("strings:", len(strings), "scripts:", len(scripts), "script entries:", data["meta"]["script_entry_count"])
    print("voice mismatches ja/en:", len(mismatch), mismatch[:5])
    print("scripts without ja:", [s["asset"] for s in scripts if not s["ja_asset"]])
    print("entries with empty ja:", sum(1 for s in scripts for e in s["entries"] if not e["ja"]))


if __name__ == "__main__":
    main()
