"""Quick scan: list bundles containing TMP_FontAsset or Font by type only."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import UnityPy

AA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa")
BUNDLE_DIRS = [
    AA / "StandaloneWindows64",
    AA / "DLC1" / "StandaloneWindows64",
]
STATIC = [
    Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\resources.assets"),
    Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\sharedassets0.assets"),
]


def scan_one(path: str) -> dict:
    hits = {"fonts": 0, "tmp": 0, "tmp_names": [], "font_names": []}
    try:
        env = UnityPy.load(path)
    except Exception as e:
        return {"path": path, "error": str(e)}
    for obj in env.objects:
        tn = obj.type.name
        if tn == "Font":
            hits["fonts"] += 1
            try:
                hits["font_names"].append(obj.read().m_Name)
            except Exception:
                hits["font_names"].append("?")
        elif tn == "MonoBehaviour":
            try:
                tree = obj.read_typetree()
                if "m_CharacterTable" in tree and "m_FaceInfo" in tree:
                    hits["tmp"] += 1
                    hits["tmp_names"].append(tree.get("m_Name", "?"))
                script = tree.get("m_Script") or {}
                if isinstance(script, dict) and script.get("m_Name") == "TMP_Settings":
                    hits["tmp_settings"] = True
            except Exception:
                pass
    return {"path": path, **hits}


def main():
    paths = [str(p) for p in STATIC if p.is_file()]
    for d in BUNDLE_DIRS:
        if d.is_dir():
            paths.extend(str(p) for p in d.glob("*.bundle"))
    print("bundles+static", len(paths))
    results = []
    workers = min(8, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(scan_one, p): p for p in paths}
        for i, fut in enumerate(as_completed(futs), 1):
            if i % 500 == 0:
                print(i, "/", len(paths))
            r = fut.result()
            if r.get("tmp") or r.get("fonts"):
                if r.get("tmp") or (r.get("fonts") and r["fonts"] > 0):
                    results.append(r)
    results.sort(key=lambda x: (-x.get("tmp", 0), -x.get("fonts", 0)))
    for r in results:
        print(
            f"tmp={r.get('tmp',0)} fonts={r.get('fonts',0)} "
            f"names={r.get('tmp_names')} / {r.get('font_names')} :: {Path(r['path']).name}"
        )
    print("TOTAL with font/tmp:", len(results))


if __name__ == "__main__":
    main()
