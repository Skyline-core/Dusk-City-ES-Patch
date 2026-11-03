import json
from pathlib import Path
import UnityPy

fp = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\localization-assets-shared_assets_all.bundle")
env = UnityPy.load(str(fp))
records = []
for o in env.objects:
    if o.type.name != "MonoBehaviour":
        continue
    try:
        t = o.read_typetree()
    except Exception:
        continue
    name = t.get("m_Name", "")
    records.append({"path_id": o.path_id, "name": name, "keys": list(t.keys())})
    if "m_StartupSelectors" in t or "Startup" in name or "Settings" in name:
        records[-1]["data"] = t

out = Path(__file__).parent / "loc_shared_list.json"
out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(records), "->", out)
