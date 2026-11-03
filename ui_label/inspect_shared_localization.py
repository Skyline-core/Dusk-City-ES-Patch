import json
from pathlib import Path
import UnityPy

base = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64")
patterns = [
    "localization-assets-shared*",
    "localization-string-tables-shared*",
    "*localization*",
]

records = []
for pat in patterns:
    for fp in sorted(base.glob(pat)):
        if not fp.name.endswith(".bundle"):
            continue
        try:
            env = UnityPy.load(str(fp))
        except Exception as e:
            records.append({"bundle": fp.name, "error": str(e)})
            continue
        for o in env.objects:
            if o.type.name != "MonoBehaviour":
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            name = t.get("m_Name", "")
            blob = json.dumps(t, ensure_ascii=False, default=str)
            if not any(k in blob for k in ["Selector", "PlayerPref", "LocalizationSettings", "Startup", "Locale", "English"]):
                continue
            records.append({"bundle": fp.name, "path_id": o.path_id, "name": name, "data": t})

out = Path(__file__).parent / "shared_localization_assets.json"
out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(records), "records ->", out)
