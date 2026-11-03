import json
from pathlib import Path
import UnityPy

path = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\globalgamemanagers.assets")
env = UnityPy.load(str(path))
records = []
for o in env.objects:
    if o.type.name != "MonoBehaviour":
        continue
    try:
        t = o.read_typetree()
    except Exception:
        continue
    name = t.get("m_Name", "")
    blob = json.dumps(t, ensure_ascii=False, default=str)
    if "LocalizationSettings" in blob or "PlayerPref" in blob or name == "Localization Settings":
        records.append({"path_id": o.path_id, "name": name, "data": t})

out = Path(__file__).parent / "global_localization_settings.json"
out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(records), "->", out)
