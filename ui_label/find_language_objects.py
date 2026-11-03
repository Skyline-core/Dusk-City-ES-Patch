"""Find GameObjects / TMP text named like Language across bundles."""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

NEEDLE_NAMES = (
    b"Language",
    b"language",
    b"Locale",
    b"Localize",
    b"TMP_Dropdown",
    b"Dropdown",
    b"\xe8\xa8\x80\xe8\xaa\x9e",  # 言語
)


def worker(path: str) -> list[dict]:
    import UnityPy

    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError:
        return []
    if not any(n in raw for n in NEEDLE_NAMES):
        return []
    hits = []
    try:
        env = UnityPy.load(path)
    except Exception:
        return [{"file": p.name, "error": "load_failed"}]
    for o in env.objects:
        try:
            if o.type.name == "GameObject":
                t = o.read_typetree()
                name = t.get("m_Name", "")
                if not any(x in name for x in ("Language", "language", "Locale", "Localize", "Dropdown", "言語")):
                    continue
                hits.append({"file": p.name, "path_id": o.path_id, "type": "GameObject", "name": name})
            elif o.type.name == "MonoBehaviour":
                t = o.read_typetree()
                name = t.get("m_Name", "")
                blob = json.dumps(t, ensure_ascii=False, default=str)
                if not any(x in name or x in blob for x in ("Language", "Locale", "Dropdown", "LocalizeManager", "TMP_Dropdown", "m_Options", "言語")):
                    continue
                rec = {"file": p.name, "path_id": o.path_id, "type": "MonoBehaviour", "name": name}
                if "m_text" in t:
                    rec["m_text"] = t["m_text"]
                if "m_Options" in t:
                    rec["m_Options"] = t["m_Options"]
                hits.append(rec)
        except Exception:
            continue
    return hits


def main():
    data = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data")
    aa = data / "StreamingAssets" / "aa" / "StandaloneWindows64"
    paths = [str(p) for p in aa.glob("*.bundle")]
    paths += [str(p) for p in data.glob("sharedassets*.assets")]
    paths += [str(data / "level0"), str(data / "resources.assets"), str(data / "globalgamemanagers.assets")]

    all_hits: list[dict] = []
    workers = min(10, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(worker, p): p for p in paths}
        done = 0
        for fut in as_completed(futs):
            all_hits.extend(fut.result())
            done += 1
            if done % 500 == 0:
                print("progress", done, len(paths), "hits", len(all_hits))

    out = Path(__file__).parent / "language_objects.json"
    out.write_text(json.dumps(all_hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total hits", len(all_hits), "->", out)


if __name__ == "__main__":
    main()
