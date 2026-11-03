#!/usr/bin/env python3
"""Export every localized *_EN image (Texture2D) from the ACTIVE English localization bundle.

Read-only on game data. Writes:
  translation/images/original/<name>.png      (RGBA, upright)
  translation/images/manifest.json
  translation/images/CONTACT_SHEET_<group>.png (quick overview)

Game path: env DUSK_GAME_PATH, or asked on the console.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

import UnityPy
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ORIG = HERE / "original"


def game_path() -> Path:
    p = os.environ.get("DUSK_GAME_PATH")
    if not p:
        p = input("Ruta del juego (carpeta que contiene 'Dusk City.exe'): ").strip().strip('"')
    return Path(p)


def find_bundle(game: Path) -> Path:
    aa = game / "Dusk City_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
    hits = glob.glob(str(aa / "localization-assets-english*2226d8d2*.bundle"))
    if not hits:
        raise SystemExit(f"No se encontro el bundle de localizacion en {aa}")
    return Path(hits[0])


GROUPS = [
    ("tips", re.compile(r"^Tips")),
    ("creditos", re.compile(r"^(Credit_|StaffCredit)")),
    ("pesca_resultados", re.compile(r"^result_")),
    ("inventario", re.compile(r"^inventory_|^settei_|^save_bg|^Jyuumin")),
    ("popups", re.compile(r"pop|kounyuu|kaisou|rantan|baikyaku", re.I)),
    ("controles", re.compile(r"^(controller_)?Switch_|^return|^stop|^text_cancel|^turiageru|^subtitle")),
]


def group_of(name: str) -> str:
    for g, rx in GROUPS:
        if rx.search(name):
            return g
    return "otros"


def main() -> int:
    game = game_path()
    bundle = find_bundle(game)
    print("Bundle:", bundle.name)
    env = UnityPy.load(str(bundle))
    ORIG.mkdir(parents=True, exist_ok=True)

    sprites = {}
    for o in env.objects:
        if o.type.name == "Sprite":
            d = o.read()
            sprites[d.m_Name] = o.path_id

    manifest = []
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        d = o.read()
        name = d.m_Name
        img = d.image.convert("RGBA")
        out = ORIG / f"{name}.png"
        img.save(out)
        manifest.append(
            {
                "name": name,
                "file": f"original/{name}.png",
                "width": d.m_Width,
                "height": d.m_Height,
                "texture_format": int(d.m_TextureFormat),
                "mip_count": int(getattr(d, "m_MipCount", 1) or 1),
                "texture_path_id": o.path_id,
                "sprite_path_id": sprites.get(name),
                "group": group_of(name),
                "bundle": "StandaloneWindows64/" + bundle.name,
            }
        )
    manifest.sort(key=lambda m: (m["group"], m["name"]))
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Exportadas:", len(manifest))

    # contact sheets
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    by_group: dict[str, list] = {}
    for m in manifest:
        by_group.setdefault(m["group"], []).append(m)
    for g, items in by_group.items():
        cell_w, cell_h = 480, 300
        cols = 3
        # big images scaled to fit the cell
        pages = [items[i : i + 12] for i in range(0, len(items), 12)]
        for pi, page in enumerate(pages, 1):
            rows = (len(page) + cols - 1) // cols
            sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (60, 60, 70, 255))
            dr = ImageDraw.Draw(sheet)
            for i, m in enumerate(page):
                im = Image.open(HERE / m["file"]).convert("RGBA")
                im.thumbnail((cell_w - 10, cell_h - 30))
                x = (i % cols) * cell_w + 5
                y = (i // cols) * cell_h + 5
                sheet.alpha_composite(im, (x, y))
                dr.text((x, y + im.height + 4), f"{m['name']}  {m['width']}x{m['height']}", fill=(255, 255, 255, 255), font=font)
            suffix = f"_{pi}" if len(pages) > 1 else ""
            sheet.save(HERE / f"CONTACT_SHEET_{g}{suffix}.png")
    print("Hojas de contacto generadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
