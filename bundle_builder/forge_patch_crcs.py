"""Make every patched bundle under patch_en_slot\\files pass the ORIGINAL catalog CRC.

Reads the original m_Crc for each bundle from the game's catalog.json (read-only) and appends a
4-byte forged block (see crc_forge.py) when the patched CRC does not already match. The game's
catalog / .hash are NOT modified.
Game folder: env DUSK_GAME_PATH (set by build_all.ps1) or two levels above translation\\.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "catalog_tool"))

from catalog_data import Catalog  # noqa: E402
from crc_forge import Bundle, forge_file  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or HERE.parent.parent)
CATALOG = GAME / "Dusk City_Data" / "StreamingAssets" / "aa" / "catalog.json"
PATCH_FILES = HERE.parent / "patch_en_slot" / "files"


def crc_by_bundle_filename(cat: Catalog) -> dict[str, int]:
    out: dict[str, int] = {}
    for loc in cat.locations:
        d = loc.extra_data.get("data") if isinstance(loc.extra_data, dict) else None
        if not d or "m_Crc" not in d:
            continue
        iid = loc.internal_id.replace("\\", "/")
        fname = iid.rsplit("/", 1)[-1]
        if fname.endswith(".bundle"):
            out[fname] = int(d["m_Crc"])
    return out


def main():
    if not PATCH_FILES.is_dir():
        print("ERROR: no existe", PATCH_FILES)
        return 1
    bundles = sorted(PATCH_FILES.rglob("*.bundle"))
    if not bundles:
        print("ERROR: no hay .bundle en", PATCH_FILES)
        return 1
    cat = Catalog.load_json(str(CATALOG))
    crcs = crc_by_bundle_filename(cat)
    ok_all = True
    for p in bundles:
        name = p.name
        target = crcs.get(name)
        if not target:
            print(f"WARN: sin CRC en catalogo para {p.relative_to(PATCH_FILES)} — omitido")
            continue
        cur = Bundle(p.read_bytes())
        if cur.crc == (target & 0xFFFFFFFF):
            rel = p.relative_to(PATCH_FILES)
            print(f"{str(rel)[:58]:58} crc ya OK ({cur.crc:08x})")
            continue
        r = forge_file(p, p, target)
        rel = p.relative_to(PATCH_FILES)
        print(
            f"{str(rel)[:58]:58} crc {r['before']:08x} -> {r['after']:08x} "
            f"(objetivo {r['target']:08x}) {'OK' if r['ok'] else 'FALLO'}"
        )
        ok_all &= r["ok"]
    # remove stale catalog/hash from old staging layout
    patch_root = PATCH_FILES.parent
    for stale in (
        patch_root / "catalog.json",
        patch_root / "StandaloneWindows64" / "catalog_2026.06.23.02.23.07.hash",
        PATCH_FILES / "catalog_2026.06.23.02.23.07.hash",
    ):
        if stale.exists():
            stale.unlink()
            print("eliminado del staging (ya no se usa):", stale.name)
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
