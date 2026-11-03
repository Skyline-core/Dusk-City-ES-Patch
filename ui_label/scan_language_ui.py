"""Find language-selection UI strings in game assets (read-only)."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

GAME = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City")
DATA = GAME / "Dusk City_Data"
AA = DATA / "StreamingAssets" / "aa"
OUT = Path(__file__).resolve().parent / "scan_results.json"

NEEDLES_UTF8 = [
    "English",
    "Japanese",
    "Chinese",
    "日本語",
    "简体中文",
    "中文",
    "English (en)",
    "Japanese (ja)",
    "Chinese (Simplified)",
    "Español",
    "Language",
    "言語",
    "语言",
]

NEEDLES_BYTES = [s.encode("utf-8") for s in NEEDLES_UTF8]


def binary_scan(path: str) -> dict:
    p = Path(path)
    try:
        data = p.read_bytes()
    except Exception as e:
        return {"path": path, "error": str(e)}
    hits = [s for s in NEEDLES_UTF8 if s.encode("utf-8") in data]
    if not hits:
        return {}
    return {"file": p.name, "full": str(p), "kind": "binary", "needles": hits}


def collect_paths() -> list[str]:
    paths: list[str] = []
    for d in [AA / "StandaloneWindows64", AA / "DLC1" / "StandaloneWindows64"]:
        if d.is_dir():
            paths.extend(str(p) for p in d.glob("*.bundle"))
    for name in ["globalgamemanagers", "globalgamemanagers.assets"]:
        fp = DATA / name
        if fp.is_file():
            paths.append(str(fp))
    for pat in ["resources.assets", "sharedassets*.assets", "level0", "level0.resS"]:
        paths.extend(str(p) for p in DATA.glob(pat))
    return paths


def unitypy_inspect(paths: list[str]) -> list[dict]:
    import UnityPy

    results: list[dict] = []
    for path in paths:
        try:
            env = UnityPy.load(path)
        except Exception as e:
            results.append({"path": path, "unitypy_error": str(e)})
            continue
        for obj in env.objects:
            try:
                if obj.type.name in ("MonoBehaviour", "GameObject", "TextAsset"):
                    data = obj.read()
                    raw = data.read_typetree() if hasattr(data, "read_typetree") else None
                else:
                    continue
            except Exception:
                continue
            if raw is None:
                continue
            blob = json.dumps(raw, ensure_ascii=False, default=str)
            found = [n for n in NEEDLES_UTF8 if n in blob]
            if not found:
                continue
            entry = {
                "file": Path(path).name,
                "full": path,
                "path_id": obj.path_id,
                "type": obj.type.name,
                "name": getattr(data, "m_Name", None) or getattr(data, "name", None),
                "needles": found,
            }
            # TMP_Dropdown options
            if "m_Options" in raw:
                entry["field"] = "m_Options"
                entry["m_Options"] = raw.get("m_Options")
            for key in ("m_text", "m_LocaleName", "m_Name"):
                if key in raw and any(n in str(raw[key]) for n in NEEDLES_UTF8):
                    entry.setdefault("fields", {})[key] = raw[key]
            results.append(entry)
    return results


def main():
    paths = collect_paths()
    print(f"Binary scan: {len(paths)} files", flush=True)
    binary_hits: list[dict] = []
    workers = min(16, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(binary_scan, p): p for p in paths}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                binary_hits.append(r)
    binary_hits.sort(key=lambda x: x["file"])

    # UnityPy on binary hits + known bundle
    inspect_set = {h["full"] for h in binary_hits}
    known = AA / "StandaloneWindows64" / "localization-locales_assets_all.bundle"
    if known.is_file():
        inspect_set.add(str(known))
    for extra in [
        AA / "StandaloneWindows64" / "7ff7bbb50d8963f8cfda64e43d946131.bundle",
    ]:
        if extra.is_file():
            inspect_set.add(str(extra))

    print(f"UnityPy inspect: {len(inspect_set)} files", flush=True)
    detailed = unitypy_inspect(sorted(inspect_set))

    out = {
        "binary_hit_count": len(binary_hits),
        "binary_hits": binary_hits,
        "unitypy_hits": detailed,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Binary hits: {len(binary_hits)}, UnityPy hits: {len(detailed)}")


if __name__ == "__main__":
    main()
