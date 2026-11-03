"""Scan for VS / locale API strings in bundles."""
from __future__ import annotations
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

AA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64")
NEEDLES = [
    b"LocaleName",
    b"AvailableLocales",
    b"SelectedLocale",
    b"LocalizeManager",
    b"ScriptMachine",
    b"FlowMachine",
    b"Unity.VisualScripting",
    b"SetLocale",
    b"GetLocale",
    b"Languages",
    b"OnLanguageUpdate",
    b"PlayerPrefLocaleSelector",
    b"LocalizationSettings",
]

def scan(p: str):
    try:
        d = Path(p).read_bytes()
    except OSError:
        return None
    hits = [n.decode("ascii", "replace") for n in NEEDLES if n in d]
    return (Path(p).name, hits) if hits else None

def main():
    paths = [str(p) for p in AA.glob("*.bundle")]
    results = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for r in ex.map(scan, paths, chunksize=128):
            if r:
                results.append(r)
    for name, hits in sorted(results, key=lambda x: -len(x[1])):
        print(name, hits)
    print("TOTAL", len(results))

if __name__ == "__main__":
    main()
