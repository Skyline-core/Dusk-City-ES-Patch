"""Find TMP_Dropdown assets with serialized m_Options across game data."""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).parent / "dropdown_hits.json"


def scan_bundle(path: str) -> list[dict]:
    import UnityPy

    hits = []
    try:
        env = UnityPy.load(path)
    except Exception:
        return hits
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if "m_Options" not in t:
            continue
        opts = t.get("m_Options")
        opt_list = None
        if isinstance(opts, dict):
            opt_list = opts.get("m_Options") or opts.get("options")
        elif isinstance(opts, list):
            opt_list = opts
        texts = []
        if isinstance(opt_list, list):
            for item in opt_list:
                if isinstance(item, dict):
                    texts.append(item.get("m_Text") or item.get("text"))
        hits.append({
            "file": Path(path).name,
            "path_id": o.path_id,
            "name": t.get("m_Name"),
            "options_text": texts,
            "raw_options": opts,
        })
    return hits


def main():
    data = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data")
    aa = data / "StreamingAssets" / "aa"
    paths = []
    for d in [aa / "StandaloneWindows64", aa / "DLC1" / "StandaloneWindows64"]:
        if d.is_dir():
            paths.extend(str(p) for p in d.glob("*.bundle"))
    for pat in ["sharedassets*.assets", "level0", "resources.assets"]:
        paths.extend(str(p) for p in data.glob(pat))

    # Pre-filter: must contain OptionData or m_Options string in binary
    filtered = []
    for p in paths:
        try:
            b = Path(p).read_bytes()
        except OSError:
            continue
        if b"m_Options" in b or b"OptionData" in b:
            filtered.append(p)

    print("candidates", len(filtered), "of", len(paths))
    all_hits: list[dict] = []
    workers = min(8, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(scan_bundle, p): p for p in filtered}
        for fut in as_completed(futs):
            all_hits.extend(fut.result())

    OUT.write_text(json.dumps(all_hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print("dropdowns", len(all_hits), "->", OUT)
    for h in all_hits[:20]:
        print(h["file"], h.get("name"), h.get("options_text"))


if __name__ == "__main__":
    main()
