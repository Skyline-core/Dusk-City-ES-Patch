#!/usr/bin/env python3
"""Replace localized *_EN textures with translated PNGs.

Input : translation/images/translated/<name>.png  (same name & EXACT same pixel size as original/)
Output: translation/patch_en_slot/files/StandaloneWindows64/<localization-assets-english...2226d8d2...bundle>
        (chain-aware: if that file already exists in the output dir it is used as input, so the
        string-table/voice-line translation already inside it is preserved; build_all.ps1's
        forge_patch_crcs.py step then restores the ORIGINAL catalog CRC).

Options: --game PATH (else env DUSK_GAME_PATH / prompt)  --out DIR  --use-test-source  --self-test
Textures keep their original TextureFormat when it is uncompressed (RGBA32/RGB24). Compressed ones
(DXT/BC) are rewritten as RGBA32, which is lossless and always valid (bundle gets bigger, CRC is forged).
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import tempfile
from pathlib import Path

import UnityPy
from PIL import Image, ImageDraw
from UnityPy.enums import TextureFormat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "bundle_builder"))
sys.path.insert(0, str(ROOT / "catalog_tool"))
from crc_forge import Bundle, forge_file  # noqa: E402

TRANSLATED = HERE / "translated"
ORIGINAL = HERE / "original"
DEFAULT_OUT = ROOT / "patch_en_slot" / "files"


def game_path(arg: str | None) -> Path:
    p = arg or os.environ.get("DUSK_GAME_PATH")
    if not p:
        p = input("Ruta del juego (carpeta que contiene 'Dusk City.exe'): ").strip().strip('"')
    return Path(p)


def find_bundle(game: Path) -> Path:
    aa = game / "Dusk City_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
    hits = glob.glob(str(aa / "localization-assets-english*2226d8d2*.bundle"))
    if not hits:
        raise SystemExit(f"No se encontro el bundle de localizacion en {aa}")
    return Path(hits[0])


def catalog_crc(game: Path, fname: str) -> int:
    from catalog_data import Catalog

    cat = Catalog.load_json(str(game / "Dusk City_Data" / "StreamingAssets" / "aa" / "catalog.json"))
    for loc in cat.locations:
        d = loc.extra_data.get("data") if isinstance(loc.extra_data, dict) else None
        if d and "m_Crc" in d and loc.internal_id.replace("\\", "/").rsplit("/", 1)[-1] == fname:
            return int(d["m_Crc"])
    raise SystemExit(f"{fname} no esta en el catalogo activo")


def make_test_pngs(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(ORIGINAL.glob("*.png")):
        im = Image.open(p).convert("RGBA")
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, min(im.width, 60), min(im.height, 24)], fill=(255, 0, 255, 255))
        dr.text((3, 5), "ES", fill=(255, 255, 255, 255))
        im.save(dst / p.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--use-test-source", action="store_true", help="genera PNG de prueba (cuadro magenta 'ES')")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    src_dir = TRANSLATED
    tmp = None
    if args.use_test_source:
        tmp = tempfile.TemporaryDirectory()
        src_dir = Path(tmp.name)
        make_test_pngs(src_dir)

    pngs = {p.stem: p for p in sorted(src_dir.glob("*.png"))}
    if not pngs:
        print("No hay PNG en", src_dir, "- nada que hacer.")
        return 0

    game = game_path(args.game)
    vanilla = find_bundle(game)
    rel = Path("StandaloneWindows64") / vanilla.name
    dst = args.out / rel
    src = dst if dst.is_file() else vanilla
    print(f"Entrada: {'(encadenado) ' if src == dst else ''}{src.name}")

    env = UnityPy.load(str(src))
    done, errors = [], []
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        d = o.read()
        p = pngs.get(d.m_Name)
        if not p:
            continue
        im = Image.open(p).convert("RGBA")
        if im.size != (d.m_Width, d.m_Height):
            errors.append(f"{d.m_Name}: tamano {im.size} != original {(d.m_Width, d.m_Height)}")
            continue
        fmt = d.m_TextureFormat
        if fmt not in (TextureFormat.RGBA32, TextureFormat.RGB24):
            d.m_TextureFormat = TextureFormat.RGBA32
            if hasattr(d, "m_CompleteImageSize"):
                d.m_CompleteImageSize = im.width * im.height * 4
        d.m_MipCount = 1
        d.image = im
        d.save()
        done.append(d.m_Name)

    missing = sorted(set(pngs) - set(done) - {e.split(":")[0] for e in errors})
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    if missing:
        print("AVISO: PNG sin textura con ese nombre:", ", ".join(missing), file=sys.stderr)
    if errors:
        return 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bundle") as t:
        tp = Path(t.name)
    try:
        tp.write_bytes(env.file.save(packer="lz4"))
        r = forge_file(tp, dst, catalog_crc(game, vanilla.name))
        if not r["ok"]:
            print("ERROR: no se pudo ajustar el CRC", r, file=sys.stderr)
            return 1
    finally:
        tp.unlink(missing_ok=True)
    print(f"OK: {len(done)} imagen(es) reemplazadas -> {dst}")

    if args.self_test:
        b = Bundle(dst.read_bytes())
        assert b.crc == (catalog_crc(game, vanilla.name) & 0xFFFFFFFF), "CRC distinto"
        env2 = UnityPy.load(str(dst))
        bad = 0
        for o in env2.objects:
            if o.type.name == "Texture2D":
                d = o.read()
                if d.m_Name in done:
                    got = d.image.convert("RGBA")
                    exp = Image.open(pngs[d.m_Name]).convert("RGBA")
                    if list(got.getdata()) != list(exp.getdata()):
                        bad += 1
                        print("DIFERENTE tras recarga:", d.m_Name, file=sys.stderr)
        print("Self-test:", "OK" if not bad else f"{bad} diferencias")
        return 1 if bad else 0
    if tmp:
        tmp.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
