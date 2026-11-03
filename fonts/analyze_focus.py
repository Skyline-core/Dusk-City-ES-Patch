"""Deep analysis of known font bundles and TMP settings."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import UnityPy
from UnityPy.enums import ClassIDType

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "catalog_tool"))
from catalog_data import Catalog  # noqa: E402
from serialization import key_to_display  # noqa: E402

GAME = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City")
DATA = GAME / "Dusk City_Data"
AA = DATA / "StreamingAssets" / "aa" / "StandaloneWindows64"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

SPANISH = "áéíóúüñÁÉÍÓÚÜÑ¿¡«»…—'\""
SPANISH_CPS = {ord(c): c for c in SPANISH}


def atlas_mode(v):
    return {0: "Static", 1: "Dynamic"}.get(v, f"?({v})")


def analyze_tmp_tree(tree: dict) -> dict:
    cps = set()
    for row in tree.get("m_CharacterTable") or []:
        if isinstance(row, dict) and "m_Unicode" in row:
            cps.add(int(row["m_Unicode"]))
    fallbacks = tree.get("m_FallbackFontAssetTable") or []
    fb = []
    for x in fallbacks:
        if isinstance(x, dict):
            fb.append(x.get("m_Name") or str(x.get("fileID")))
        else:
            fb.append(str(x))
    # source font embedded?
    src = tree.get("m_SourceFontFile") or tree.get("sourceFontFile")
    src_size = 0
    if isinstance(src, dict) and "m_SourceFontFileGUID" in tree:
        pass
    # check for byte array in typetree
    for key in ("m_SourceFontFile_EditorRef", "m_SourceFontFile"):
        v = tree.get(key)
        if isinstance(v, dict) and v.get("m_FileID"):
            src = v
    embedded_bytes = tree.get("m_SourceFontFile")  # sometimes list of bytes in newer TMP
    if isinstance(embedded_bytes, list) and embedded_bytes and isinstance(embedded_bytes[0], int):
        src_size = len(embedded_bytes)
    face = tree.get("m_FaceInfo") or {}
    family = face.get("m_FamilyName") if isinstance(face, dict) else ""
    return {
        "name": tree.get("m_Name"),
        "atlas_mode": atlas_mode(tree.get("m_AtlasPopulationMode")),
        "glyph_count": len(cps),
        "family": family,
        "spanish_present": "".join(c for c in SPANISH if ord(c) in cps),
        "spanish_missing": "".join(c for c in SPANISH if ord(c) not in cps),
        "fallbacks": fb,
        "has_source_font_bytes": src_size > 0,
        "creationSettings": tree.get("m_CreationSettings"),
    }


def check_ttf_bytes(data: bytes, name: str) -> dict:
    from fontTools.ttLib import TTFont
    import io

    tt = TTFont(io.BytesIO(data))
    cps = set()
    for table in tt["cmap"].tables:
        cps.update(table.cmap.keys())
    return {
        "name": name,
        "cmap_count": len(cps),
        "spanish_present": "".join(c for c in SPANISH if ord(c) in cps),
        "spanish_missing": "".join(c for c in SPANISH if ord(c) not in cps),
    }


def scan_env(path: str) -> list[dict]:
    out = []
    env = UnityPy.load(path)
    for obj in env.objects:
        tname = obj.type.name
        if tname == "Font":
            d = obj.read()
            fb = getattr(d, "m_FontData", b"") or b""
            info = {"type": "Font", "path": path, "path_id": obj.path_id, "name": d.m_Name, "size": len(fb)}
            if len(fb) > 200:
                try:
                    info.update(check_ttf_bytes(fb, d.m_Name))
                except Exception as e:
                    info["cmap_error"] = str(e)
            out.append(info)
        elif tname == "MonoBehaviour":
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            script = tree.get("m_Script") or {}
            sname = script.get("m_Name") if isinstance(script, dict) else ""
            if sname == "TMP_FontAsset" or ("m_CharacterTable" in tree and "m_FaceInfo" in tree):
                info = {"type": "TMP_FontAsset", "path": path, "path_id": obj.path_id}
                info.update(analyze_tmp_tree(tree))
                out.append(info)
            elif sname == "TMP_Settings":
                out.append(
                    {
                        "type": "TMP_Settings",
                        "path": path,
                        "path_id": obj.path_id,
                        "default_font": tree.get("m_defaultFontAsset"),
                        "fallback_fonts": tree.get("m_fallbackFontAssets"),
                        "dynamic_atlas": tree.get("m_enableDynamicAtlasSystem"),
                        "missing_glyph": tree.get("m_missingGlyphCharacter"),
                    }
                )
            elif sname in ("LocalizeTextFont", "LocalizeTMPFont", "LocalizeStringEvent"):
                out.append(
                    {
                        "type": sname,
                        "path": path,
                        "path_id": obj.path_id,
                        "keys": {k: tree[k] for k in tree if not k.startswith("m_Script") and k != "m_GameObject"},
                    }
                )
            elif "customFont" in tree or "oriFont" in tree or "m_fontAsset" in tree:
                if any(k in str(tree) for k in ("Font", "font", "TMP")):
                    out.append({"type": "FontRefMono", "script": sname, "path": path, "path_id": obj.path_id, "tree": tree})
    return out


def find_bundle_deps_for_fonts():
    cat = Catalog.load_json(str(DATA / "StreamingAssets" / "aa" / "catalog.json"))
    bundles = set()
    for loc in cat.locations:
        text = f"{loc.internal_id} {key_to_display(loc.primary_key)}"
        if any(x in text for x in ("Honoka", "Corporate", "Liberation", "SDF", "Fonts/")):
            dk = key_to_display(loc.dependency_key)
            if isinstance(dk, str) and dk.endswith(".bundle"):
                bundles.add(dk)
            if loc.provider_id.endswith("AssetBundleProvider"):
                bundles.add(Path(loc.internal_id.replace("\\", "/")).name)
    return sorted(b for b in bundles if b.endswith(".bundle"))


def main():
    targets = [
        str(DATA / "resources.assets"),
        str(DATA / "sharedassets0.assets"),
        str(AA / "ad133aaa6b7c43f15f99cf476d087942.bundle"),
        str(AA / "85bf13179bb6b147134bc8a1540a9b1d.bundle"),
    ]
    for b in find_bundle_deps_for_fonts():
        p = AA / b
        if p.is_file() and str(p) not in targets:
            targets.append(str(p))

    all_items = []
    for t in targets:
        if not Path(t).is_file():
            print("MISSING", t)
            continue
        print("Scan", t)
        all_items.extend(scan_env(t))

    with open(OUT / "font_focus.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False, default=str)

    for item in all_items:
        if item["type"] in ("TMP_FontAsset", "Font"):
            print(json.dumps(item, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
