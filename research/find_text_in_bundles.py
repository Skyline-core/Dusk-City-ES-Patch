"""Search every Addressables bundle (+ static assets) for a UTF-8 / UTF-16LE string. Read-only.
Usage: python find_text_in_bundles.py "text one" ["text two" ...]
"""
import os
import struct
import sys
from multiprocessing import Pool
from pathlib import Path

import lz4.block

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "bundle_builder"))
from crc_forge import Bundle  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or HERE.parent.parent.parent)
DATA = GAME / "Dusk City_Data"
NEEDLES = [a.encode() for a in sys.argv[1:]] + [a.encode("utf-16le") for a in sys.argv[1:]]


def decompress_stream(path):
    raw = Path(path).read_bytes()
    if raw[:7] != b"UnityFS":
        return raw
    b = Bundle(raw)
    # re-walk blocks to get data (Bundle only keeps crc); decode again
    import zlib  # noqa
    p = b.data_start
    out = []
    from crc_forge import _dec
    for u, c, f in b.blocks:
        out.append(_dec(raw[p:p + c], f & 0x3F, u))
        p += c
    return b"".join(out)


def scan(path):
    try:
        data = decompress_stream(path)
    except Exception as e:  # noqa
        return (str(path), "ERR " + str(e)[:60])
    hits = [n.decode("utf-8", "ignore") if i < len(NEEDLES) // 2 else n.decode("utf-16le", "ignore")
            for i, n in enumerate(NEEDLES) if n in data]
    return (str(path), hits) if hits else None


if __name__ == "__main__":
    files = list((DATA / "StreamingAssets" / "aa").rglob("*.bundle"))
    files += [p for p in DATA.glob("*") if p.is_file() and p.suffix in (".assets", ".resS", "") and p.stat().st_size < 400_000_000]
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        for r in pool.imap_unordered(scan, files, chunksize=8):
            if r and not str(r[1]).startswith("ERR"):
                print(Path(r[0]).name, r[1], flush=True)
    print("DONE", len(files))
