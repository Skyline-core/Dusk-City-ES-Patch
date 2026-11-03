"""Full dump of language-related objects in config UI bundle."""
import json
from pathlib import Path
import UnityPy

BUNDLE = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\741042f98eeaab65c8941174724e3496.bundle")

env = UnityPy.load(str(BUNDLE))
objects_by_id = {o.path_id: o for o in env.objects}

def ref_name(ref):
    if not isinstance(ref, dict):
        return ref
    pid = ref.get("m_PathID")
    if pid and pid in objects_by_id:
        o = objects_by_id[pid]
        try:
            if o.type.name == "GameObject":
                return o.read_typetree().get("m_Name")
            if o.type.name == "MonoBehaviour":
                t = o.read_typetree()
                return t.get("m_Name") or o.type.name
        except Exception:
            pass
    return ref

records = []
for o in env.objects:
    tname = o.type.name
    try:
        if tname == "GameObject":
            t = o.read_typetree()
            name = t.get("m_Name", "")
            comps = []
            for c in t.get("m_Component", []):
                pid = c.get("component", {}).get("m_PathID")
                if pid in objects_by_id:
                    co = objects_by_id[pid]
                    comps.append({"path_id": pid, "type": co.type.name})
            if any(k in name for k in ("Dropdown", "Language", "Localize", "Config", "Title", "Option")):
                records.append({"path_id": o.path_id, "type": "GameObject", "name": name, "components": comps})
        elif tname == "MonoBehaviour":
            t = o.read_typetree()
            blob = json.dumps(t, ensure_ascii=False, default=str)
            if any(k in blob for k in ("LocalizeManager", "Languages", "m_Options", "ScriptMachine", "graph", "SelectedLocale", "Option A", "TMP_Dropdown")):
                rec = {"path_id": o.path_id, "type": "MonoBehaviour", "name": t.get("m_Name"), "keys": list(t.keys())}
                if "m_Options" in t:
                    rec["m_Options"] = t["m_Options"]
                if "m_text" in t:
                    rec["m_text"] = t["m_text"]
                # script ref
                script = t.get("m_Script", {})
                spid = script.get("m_PathID") if isinstance(script, dict) else None
                rec["script_path_id"] = spid
                records.append(rec)
    except Exception as e:
        records.append({"path_id": o.path_id, "error": str(e)})

out = Path(__file__).parent / "inspect_741042.json"
out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(records), "->", out)
