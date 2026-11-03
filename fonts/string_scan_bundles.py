"""Find bundles containing font name strings (binary scan)."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

AA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa")
DIRS = [AA / "StandaloneWindows64", AA / "DLC1" / "StandaloneWindows64"]
NEEDLES = [
    b"Honoka_Shin_Mincho_L SDF",
    b"Corporate-Mincho-ver2 SDF",
    b"Corporate-Mincho",
    b"LiberationSans SDF",
    b"Roboto-Italic-VariableFont",
    b"NotInter-Regular",
]


def scan(path: str) -> tuple[str, list[str]]:
    try:
        data = Path(path).read_bytes()
    except Exception:
        return path, []
    hits = [n.decode("utf-8", "replace") for n in NEEDLES if n in data]
    return path, hits


def main():
    paths = []
    for d in DIRS:
        if d.is_dir():
            paths.extend(str(p) for p in d.glob("*.bundle"))
    print("scanning", len(paths))
    results = []
    workers = min(12, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(scan, p): p for p in paths}
        for fut in as_completed(futs):
            p, hits = fut.result()
            if hits:
                results.append((Path(p).name, hits))
    for name, hits in sorted(results):
        print(name, "->", hits)
    print("bundles with hits:", len(results))


if __name__ == "__main__":
    main()
