"""Scan TMP_FontAsset objects for Spanish glyph coverage."""
import UnityPy, glob, os, json

ROOT = r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data"
SPANISH = "áéíóúñü¿¡ÁÉÍÓÚÑ"
SPANISH_CPS = sorted({ord(c) for c in SPANISH})

sources = [
    os.path.join(ROOT, "resources.assets"),
    os.path.join(ROOT, "sharedassets0.assets"),
    os.path.join(ROOT, "globalgamemanagers"),
]
sources += glob.glob(os.path.join(ROOT, "StreamingAssets", "aa", "StandaloneWindows64", "*.bundle"))

results = []

def check_font(name, obj_type, data):
    if obj_type != "MonoBehaviour":
        return
    try:
        t = obj.read_typetree()
    except Exception:
        return
    if t.get("m_Name") is None:
        return
    # TMP_FontAsset typetree keys
    if "m_AtlasPopulationMode" not in t and "atlasPopulationMode" not in str(t.keys()):
        # try nested
        if "m_fontInfo" not in t and "m_GlyphTable" not in t:
            return
    pop = t.get("m_AtlasPopulationMode", t.get("atlasPopulationMode"))
    glyph_table = t.get("m_GlyphTable") or t.get("glyphTable") or []
    char_table = t.get("m_CharacterTable") or t.get("characterTable") or []
    present = set()
    for entry in char_table:
        if isinstance(entry, dict):
            u = entry.get("m_Unicode") or entry.get("unicode")
            if u is not None:
                present.add(int(u))
    missing = [cp for cp in SPANISH_CPS if cp not in present]
    if missing or "Font" in name or pop is not None:
        results.append({
            "source": os.path.basename(src_path),
            "name": t.get("m_Name", name),
            "atlasPopulationMode": pop,
            "charCount": len(char_table),
            "missingSpanish": [chr(c) for c in missing],
            "hasFallback": bool(t.get("m_FallbackFontAssetTable") or t.get("fallbackFontAssets")),
        })

for src_path in sources:
    if not os.path.isfile(src_path):
        continue
    try:
        env = UnityPy.load(src_path)
    except Exception:
        continue
    for o in env.objects:
        check_font(o.path_id, o.type.name, o)

out = r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\fonts_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("fonts found", len(results), "->", out)
