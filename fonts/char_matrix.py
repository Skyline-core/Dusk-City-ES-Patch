import UnityPy
from pathlib import Path

SPANISH = "áéíóúüñÁÉÍÓÚÜÑ¿¡«»…—'\""
paths = {
    "Honoka_Shin_Mincho_L SDF": Path(
        r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\7d1fbb8bac9eb574f5f021e9c38ee832.bundle"
    ),
    "Corporate-Mincho-ver2 SDF": Path(
        r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\ad133aaa6b7c43f15f99cf476d087942.bundle"
    ),
    "LiberationSans SDF": Path(
        r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\57cd5f06fa66144e14ab0ce0f58d3e01.bundle"
    ),
    "Roboto-Italic-VariableFont_wdth,wght SDF": Path(
        r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\3a7b609e999f6d3fdc182498460fe62d.bundle"
    ),
}
for fname, p in paths.items():
    for obj in UnityPy.load(str(p)).objects:
        if obj.type.name != "MonoBehaviour":
            continue
        t = obj.read_typetree()
        if t.get("m_Name") != fname:
            continue
        cps = {int(r["m_Unicode"]) for r in t.get("m_CharacterTable", []) if isinstance(r, dict)}
        marks = " ".join(f"{c}:{'Y' if ord(c) in cps else 'N'}" for c in SPANISH)
        print(fname)
        print(marks)
