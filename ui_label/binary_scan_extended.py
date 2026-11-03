"""Extended binary needle scan for language UI strings."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

AA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa")
DATA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data")

NEEDLES: list[tuple[str, bytes]] = [
    ("日本語", "日本語".encode("utf-8")),
    ("简体中文", "简体中文".encode("utf-8")),
    ("English", b"English"),
    ("English_utf16", "English".encode("utf-16-le")),
    ("Japanese (ja)", b"Japanese (ja)"),
    ("Chinese (Simplified)", b"Chinese (Simplified)"),
    ("m_Options", b"m_Options"),
    ("TMP_Dropdown", b"TMP_Dropdown"),
    ("LocalizeManager", b"LocalizeManager"),
    ("OnLanguageUpdate", b"OnLanguageUpdate"),
    ("zh-CN", b"zh-CN"),
    ("dropdown", b"dropdown"),
    ("LanguageDropdown", b"LanguageDropdown"),
    ("m_LocaleName", b"m_LocaleName"),
]


def scan_file(path: str) -> tuple[str, list[str]] | None:
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError:
        return None
    hits = [label for label, needle in NEEDLES if needle in data]
    if not hits:
        return None
    return p.name, hits


def main():
    paths: list[str] = []
    for d in [AA / "StandaloneWindows64", AA / "DLC1" / "StandaloneWindows64"]:
        if d.is_dir():
            paths.extend(str(p) for p in d.glob("*.bundle"))
    for pat in ["globalgamemanagers*", "resources.assets", "sharedassets*.assets", "level0*"]:
        paths.extend(str(p) for p in DATA.glob(pat))

    workers = min(16, os.cpu_count() or 4)
    results: list[tuple[str, list[str]]] = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(scan_file, p): p for p in paths}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                results.append(r)

    # Score: prioritize language menu signals
    def score(item: tuple[str, list[str]]) -> int:
        _, hits = item
        s = len(hits)
        if "English" in hits or "English_utf16" in hits:
            s += 10
        if "日本語" in hits or "简体中文" in hits:
            s += 10
        if "m_Options" in hits or "TMP_Dropdown" in hits:
            s += 5
        return s

    results.sort(key=score, reverse=True)
    for name, hits in results:
        print(f"{name}\t{hits}")
    print("TOTAL", len(results))


if __name__ == "__main__":
    main()
