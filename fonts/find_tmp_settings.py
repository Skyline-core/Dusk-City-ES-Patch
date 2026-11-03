from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import UnityPy

ROOT = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data")
PATHS = list(ROOT.glob("*.assets")) + list(ROOT.glob("sharedassets*.assets"))
PATHS += list((ROOT / "StreamingAssets" / "aa" / "StandaloneWindows64").glob("*.bundle"))


def one(path: str):
    try:
        env = UnityPy.load(path)
    except Exception:
        return None
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            t = obj.read_typetree()
        except Exception:
            continue
        if "m_defaultFontAsset" in t or "m_fallbackFontAssets" in t:
            return {
                "file": Path(path).name,
                "name": t.get("m_Name"),
                "default": t.get("m_defaultFontAsset"),
                "fallbacks": t.get("m_fallbackFontAssets"),
                "dynamic": t.get("m_enableDynamicAtlasSystem"),
            }
    return None


def main():
    with ProcessPoolExecutor(min(8, os.cpu_count() or 4)) as ex:
        for r in ex.map(one, [str(p) for p in PATHS]):
            if r:
                print(r)


if __name__ == "__main__":
    main()
