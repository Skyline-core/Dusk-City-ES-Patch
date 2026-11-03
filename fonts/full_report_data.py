"""Extract full font report data from all font-bearing containers."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import UnityPy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "catalog_tool"))
from catalog_data import Catalog  # noqa: E402
from serialization import key_to_display  # noqa: E402

DATA = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data")
AA = DATA / "StreamingAssets" / "aa" / "StandaloneWindows64"
OUT = Path(__file__).resolve().parent / "out"

SPANISH = "áéíóúüñÁÉÍÓÚÜÑ¿¡«»…—'\""
CONTAINERS = [
    DATA / "resources.assets",
    AA / "ad133aaa6b7c43f15f99cf476d087942.bundle",
    AA / "85bf13179bb6b147134bc8a1540a9b1d.bundle",
    AA / "7d1fbb8bac9eb574f5f021e9c38ee832.bundle",
    AA / "57cd5f06fa66144e14ab0ce0f58d3e01.bundle",
    AA / "7ff7bbb50d8963f8cfda64e43d946131.bundle",
    AA / "3a7b609e999f6d3fdc182498460fe62d.bundle",
]


def font_bytes(raw) -> bytes:
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if isinstance(raw, list):
        return bytes(raw)
    return b""


def cmap_report(data: bytes, name: str) -> dict:
    from fontTools.ttLib import TTFont
    import io

    tt = TTFont(io.BytesIO(data))
    cps = set()
    for table in tt["cmap"].tables:
        cps.update(table.cmap.keys())
    return {
        "name": name,
        "bytes": len(data),
        "cmap_count": len(cps),
        "spanish_present": "".join(c for c in SPANISH if ord(c) in cps),
        "spanish_missing": "".join(c for c in SPANISH if ord(c) not in cps),
    }


def tmp_report(tree: dict, container: str, path_id: int) -> dict:
    cps = set()
    for row in tree.get("m_CharacterTable") or []:
        if isinstance(row, dict) and "m_Unicode" in row:
            cps.add(int(row["m_Unicode"]))
    fallbacks = []
    for x in tree.get("m_FallbackFontAssetTable") or []:
        if isinstance(x, dict):
            fallbacks.append(x.get("m_Name") or f"fileID:{x.get('fileID')}")
        else:
            fallbacks.append(str(x))
    pop = tree.get("m_AtlasPopulationMode")
    cs = tree.get("m_CreationSettings") or {}
    face = tree.get("m_FaceInfo") or {}
    # dynamic atlas source embedded?
    src_list = tree.get("m_SourceFontFile")
    src_embedded = isinstance(src_list, list) and len(src_list) > 100
    return {
        "kind": "TMP_FontAsset",
        "name": tree.get("m_Name"),
        "container": container,
        "container_file": Path(container).name,
        "path_id": path_id,
        "atlas_mode": {0: "Static", 1: "Dynamic"}.get(pop, pop),
        "glyph_count": len(cps),
        "family": face.get("m_FamilyName") if isinstance(face, dict) else None,
        "spanish_present": "".join(c for c in SPANISH if ord(c) in cps),
        "spanish_missing": "".join(c for c in SPANISH if ord(c) not in cps),
        "fallbacks": fallbacks,
        "source_font_file_name": cs.get("sourceFontFileName"),
        "source_font_guid": cs.get("sourceFontFileGUID"),
        "character_set_mode": cs.get("characterSetSelectionMode"),
        "source_font_embedded_in_asset": src_embedded,
    }


def scan_container(path: Path) -> list[dict]:
    out = []
    env = UnityPy.load(str(path))
    for obj in env.objects:
        if obj.type.name == "Font":
            d = obj.read()
            fb = font_bytes(getattr(d, "m_FontData", b""))
            item = {"kind": "Font", "name": d.m_Name, "container": str(path), "container_file": path.name, "path_id": obj.path_id}
            if len(fb) > 200:
                item.update(cmap_report(fb, d.m_Name))
            out.append(item)
        elif obj.type.name == "MonoBehaviour":
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            script = (tree.get("m_Script") or {}).get("m_Name")
            if script == "TMP_Settings" or tree.get("m_Name") == "TMP Settings":
                out.append(
                    {
                        "kind": "TMP_Settings",
                        "container": str(path),
                        "container_file": path.name,
                        "path_id": obj.path_id,
                        "default_font": tree.get("m_defaultFontAsset"),
                        "fallback_fonts": tree.get("m_fallbackFontAssets"),
                        "enable_dynamic_atlas": tree.get("m_enableDynamicAtlasSystem"),
                        "missing_glyph_char": tree.get("m_missingGlyphCharacter"),
                    }
                )
            if script == "TMP_FontAsset" or ("m_CharacterTable" in tree and "m_FaceInfo" in tree):
                out.append(tmp_report(tree, str(path), obj.path_id))
            if script == "LocalizeTextFont":
                out.append({"kind": "LocalizeTextFont", "container": path.name, "tree": {k: tree[k] for k in tree if k not in ("m_Script",)}})
    return out


def catalog_font_usage():
    cat = Catalog.load_json(str(DATA / "StreamingAssets" / "aa" / "catalog.json"))
    rows = []
    for loc in cat.locations:
        pk = key_to_display(loc.primary_key)
        if any(x in pk for x in ("Honoka", "Corporate", "Liberation", "Roboto", "NotInter", "SDF", "TMP Settings")):
            rows.append({"primary": pk, "internal": loc.internal_id, "dep": key_to_display(loc.dependency_key), "provider": loc.provider_id})
    return rows


def main():
    all_items = []
    for c in CONTAINERS:
        if c.is_file():
            all_items.extend(scan_container(c))
    # dedupe TMP by name keeping richest glyph count
    tmp_by_name = {}
    for item in all_items:
        if item.get("kind") == "TMP_FontAsset":
            n = item["name"]
            if n not in tmp_by_name or item["glyph_count"] > tmp_by_name[n]["glyph_count"]:
                tmp_by_name[n] = item
    report = {
        "spanish_chars": SPANISH,
        "tmp_font_assets_unique": list(tmp_by_name.values()),
        "all_scanned": all_items,
        "catalog_font_refs": catalog_font_usage(),
    }
    OUT.mkdir(exist_ok=True)
    with open(OUT / "full_report_data.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    for t in sorted(tmp_by_name.values(), key=lambda x: x["name"] or ""):
        print(f"{t['name']}: {t['atlas_mode']} glyphs={t['glyph_count']} ES missing=[{t['spanish_missing']}] fb={t['fallbacks']} @ {t['container_file']}")
    print("\nTTF:")
    seen = set()
    for item in all_items:
        if item.get("kind") == "Font" and item.get("name") not in seen:
            seen.add(item["name"])
            print(f"  {item.get('name')}: cmap={item.get('cmap_count')} ES missing=[{item.get('spanish_missing')}] @ {item.get('container_file')}")
    for item in all_items:
        if item.get("kind") == "TMP_Settings":
            print("\nTMP_Settings:", json.dumps(item, indent=2, default=str))


if __name__ == "__main__":
    main()
