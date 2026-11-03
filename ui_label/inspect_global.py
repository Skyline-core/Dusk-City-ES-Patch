"""Inspect globalgamemanagers.assets for embedded language UI."""
import json
from pathlib import Path
import UnityPy

path = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\globalgamemanagers.assets")
NEEDLES = ["English", "Japanese", "Chinese", "日本語", "简体中文", "m_Options", "LocalizeManager", "dropdown"]

env = UnityPy.load(str(path))
out = []
for o in env.objects:
    if o.type.name not in ("MonoBehaviour", "GameObject"):
        continue
    try:
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            blob = json.dumps(t, ensure_ascii=False, default=str)
            if not any(n in blob for n in NEEDLES):
                continue
            rec = {"path_id": o.path_id, "type": "MonoBehaviour", "name": t.get("m_Name"), "keys": list(t.keys())}
            if "m_Options" in t:
                rec["m_Options"] = t["m_Options"]
            out.append(rec)
        else:
            t = o.read_typetree()
            name = t.get("m_Name", "")
            if any(n in name for n in NEEDLES):
                out.append({"path_id": o.path_id, "type": "GameObject", "name": name, "components": t.get("m_Component")})
    except Exception as e:
        pass

p = Path(__file__).parent / "inspect_global.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(out), "hits ->", p)
