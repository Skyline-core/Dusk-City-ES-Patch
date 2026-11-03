"""CRC32 forging for UnityFS bundles.

Unity's AssetBundle CRC (the Addressables `m_Crc`) is the CRC32 of the *uncompressed* data stream
(concatenation of all decompressed blocks). A patched bundle therefore fails CRC validation against
the original catalog. This module appends one extra 4-byte block, computed so that the CRC32 of the
whole uncompressed stream equals the original value. No node is modified, so Unity simply ignores
the unreferenced trailing bytes.

CLI: python crc_forge.py <in.bundle> <out.bundle> <target_crc_decimal_or_hex>
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import lz4.block
from UnityPy.helpers import CompressionHelper as CH

# --- CRC32 tables -----------------------------------------------------------
_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if _c & 1 else _c >> 1
    _TABLE.append(_c)
_REV = {t >> 24: i for i, t in enumerate(_TABLE)}


def forge_suffix(prefix_crc: int, target_crc: int) -> bytes:
    """Return 4 bytes b such that crc32(prefix + b) == target_crc (prefix given by its crc32)."""
    s0 = prefix_crc ^ 0xFFFFFFFF
    t = target_crc ^ 0xFFFFFFFF
    idx = [0, 0, 0, 0]
    cur = t
    for k in (3, 2, 1, 0):
        i = _REV[cur >> 24]
        idx[k] = i
        cur = ((cur ^ _TABLE[i]) << 8) & 0xFFFFFFFF
    out = bytearray()
    s = s0
    for k in range(4):
        b = idx[k] ^ (s & 0xFF)
        out.append(b)
        s = _TABLE[(s ^ b) & 0xFF] ^ (s >> 8)
    assert s == t, "forge failed"
    return bytes(out)


# --- UnityFS parsing / writing ---------------------------------------------
def _dec(raw: bytes, mode: int, usize: int) -> bytes:
    if mode == 0:
        return raw
    if mode == 1:
        return CH.decompress_lzma(raw, usize)
    if mode in (2, 3):
        return lz4.block.decompress(raw, usize)
    raise ValueError(f"unsupported compression {mode}")


def _comp_bi(raw: bytes, mode: int) -> bytes:
    if mode == 0:
        return raw
    if mode in (2, 3):
        return lz4.block.compress(raw, mode="high_compression", store_size=False)
    raise ValueError(f"unsupported blocksinfo compression {mode}")


class Bundle:
    def __init__(self, data: bytes):
        self.raw = data
        p = 0

        def cstr():
            nonlocal p
            e = data.index(b"\0", p)
            s = data[p:e]
            p = e + 1
            return s

        assert cstr() == b"UnityFS"
        self.version = struct.unpack(">I", data[p:p + 4])[0]
        p += 4
        self.player = cstr()
        self.engine = cstr()
        self.size, self.csz, self.usz, self.flags = struct.unpack(">qIII", data[p:p + 20])
        p += 20
        if self.version >= 7:
            p = (p + 15) & ~15
        self.bi_at_end = bool(self.flags & 0x80)
        if self.bi_at_end:
            self.bi = _dec(data[len(data) - self.csz:], self.flags & 0x3F, self.usz)
        else:
            self.bi = _dec(data[p:p + self.csz], self.flags & 0x3F, self.usz)
            p += self.csz
            if self.flags & 0x200:
                p = (p + 15) & ~15
        n = struct.unpack(">i", self.bi[16:20])[0]
        self.blocks = []
        q = 20
        for _ in range(n):
            u, c, f = struct.unpack(">IIH", self.bi[q:q + 10])
            q += 10
            self.blocks.append((u, c, f))
        self.bi_tail = self.bi[q:]  # node table etc.
        self.data_start = p
        self.crc = 0
        self.total = 0
        for u, c, f in self.blocks:
            d = _dec(data[p:p + c], f & 0x3F, u)
            self.crc = zlib.crc32(d, self.crc)
            self.total += len(d)
            p += c

    def with_forged_crc(self, target: int) -> bytes:
        suffix = forge_suffix(self.crc, target)
        blocks = self.blocks + [(4, 4, 0)]
        bi = (
            self.bi[:16]
            + struct.pack(">i", len(blocks))
            + b"".join(struct.pack(">IIH", *b) for b in blocks)
            + self.bi_tail
        )
        mode = self.flags & 0x3F
        bi_c = _comp_bi(bi, mode)
        body = self.raw[self.data_start:self.data_start + sum(c for _, c, _ in self.blocks)] + suffix

        head = b"UnityFS\0" + struct.pack(">I", self.version) + self.player + b"\0" + self.engine + b"\0"
        fixed_len = 20
        pos = len(head) + fixed_len
        pad1 = ((pos + 15) & ~15) - pos if self.version >= 7 else 0
        if self.bi_at_end:
            total = pos + pad1 + len(body) + len(bi_c)
            out = (
                head
                + struct.pack(">qIII", total, len(bi_c), len(bi), self.flags)
                + b"\0" * pad1
                + body
                + bi_c
            )
        else:
            pos2 = pos + pad1 + len(bi_c)
            pad2 = ((pos2 + 15) & ~15) - pos2 if self.flags & 0x200 else 0
            total = pos2 + pad2 + len(body)
            out = (
                head
                + struct.pack(">qIII", total, len(bi_c), len(bi), self.flags)
                + b"\0" * pad1
                + bi_c
                + b"\0" * pad2
                + body
            )
        assert len(out) == total
        return out


def forge_file(src: Path, dst: Path, target: int) -> dict:
    b = Bundle(Path(src).read_bytes())
    before = b.crc
    out = b.with_forged_crc(target)
    Path(dst).write_bytes(out)
    check = Bundle(out)
    ok = check.crc == (target & 0xFFFFFFFF)
    return {"before": before, "after": check.crc, "target": target & 0xFFFFFFFF, "ok": ok, "bytes": len(out)}


if __name__ == "__main__":
    src, dst, tgt = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
    r = forge_file(Path(src), Path(dst), tgt)
    print(r)
    sys.exit(0 if r["ok"] else 1)
