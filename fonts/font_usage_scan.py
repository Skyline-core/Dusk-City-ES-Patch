"""Count TMP m_fontAsset usage per font name across all bundles."""
from __future__ import annotations

import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import UnityPy

AA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa")
DIRS = [AA / "StandaloneWindows64", AA / "DLC1" / "StandaloneWindows64"]
STATIC = [Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\resources.assets")]


def scan(path: str) -> Counter:
    c: Counter = Counter()
    try:
        env = UnityPy.load(path)
    except Exception:
        return c
    font_names: dict[int, str] = {}
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if "m_CharacterTable" in tree and tree.get("m_Name"):
            font_names[obj.path_id] = str(tree["m_Name"])
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        fa = tree.get("m_fontAsset")
        if isinstance(fa, dict):
            pid = fa.get("m_PathID")
            if pid in font_names:
                c[font_names[pid]] += 1
            elif pid and pid != 0:
                c[f"<external path_id={pid}>"] += 1
    return c


def main():
    paths = [str(p) for p in STATIC if p.is_file()]
    for d in DIRS:
        if d.is_dir():
            paths.extend(str(p) for p in d.glob("*.bundle"))
    total: Counter = Counter()
    workers = min(8, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(scan, p) for p in paths]
        for i, fut in enumerate(as_completed(futs), 1):
            if i % 1000 == 0:
                print(i, "/", len(paths))
            total.update(fut.result())
    print("=== TMP m_fontAsset usage (all containers) ===")
    for name, n in total.most_common():
        print(f"{n:6d}  {name}")


if __name__ == "__main__":
    main()
