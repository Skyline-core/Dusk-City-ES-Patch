from __future__ import annotations
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data")
NEEDLES = [
    b"PlayerPrefLocaleSelector",
    b"m_PlayerPreferenceKey",
    b"StartupLocaleSelectors",
    b"Localization Settings",
    b"LocalizationSettings",
    b"SelectedLocale",
]

def scan(p: str):
    try:
        d = Path(p).read_bytes()
    except OSError:
        return None
    hits = [n.decode("ascii","replace") for n in NEEDLES if n in d]
    return (Path(p).name, hits, p) if hits else None

paths = []
for d in [ROOT / "StreamingAssets" / "aa" / "StandaloneWindows64", ROOT / "StreamingAssets" / "aa" / "DLC1" / "StandaloneWindows64"]:
    if d.is_dir():
        paths += [str(x) for x in d.glob("*.bundle")]
paths += [str(x) for x in ROOT.glob("sharedassets*.assets")]
paths += [str(ROOT / "resources.assets"), str(ROOT / "globalgamemanagers.assets")]

def main():
    results = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for r in ex.map(scan, paths, chunksize=64):
            if r:
                results.append(r)
    for name, hits, full in sorted(results):
        print(full, hits)
    print("TOTAL", len(results))


if __name__ == "__main__":
    main()
