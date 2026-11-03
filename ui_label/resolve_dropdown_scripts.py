"""Resolve script types on language Dropdown in 741042 bundle."""
import json
from pathlib import Path
import UnityPy

BUNDLE = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\741042f98eeaab65c8941174724e3496.bundle")
DROPDOWN_GO = -1538232607231808269
TMP_DROPDOWN = -7104408855834432269
EXTRA = [5402053862990179571, -8961996047486980877, 1640437448010788083]

env = UnityPy.load(str(BUNDLE))
by_id = {o.path_id: o for o in env.objects}

def script_name(pid):
    # m_Script on MonoBehaviour points to MonoScript
    return None

scripts = {}
for o in env.objects:
    if o.type.name == "MonoScript":
        try:
            t = o.read_typetree()
            scripts[o.path_id] = t.get("m_ClassName"), t.get("m_Namespace")
        except Exception:
            pass

def describe(pid):
    o = by_id.get(pid)
    if not o:
        return {"path_id": pid, "missing": True}
    rec = {"path_id": pid, "unity_type": o.type.name}
    if o.type.name == "MonoBehaviour":
        t = o.read_typetree()
        sp = t.get("m_Script", {}).get("m_PathID")
        rec["script"] = scripts.get(sp)
        rec["keys"] = [k for k in t.keys() if not k.startswith("m_font") and k not in ("references",)][:25]
        if "m_graph" in t:
            rec["has_graph"] = True
        if "m_Options" in t:
            rec["m_Options"] = t["m_Options"]
        if "m_text" in t:
            rec["m_text"] = t.get("m_text")
    return rec

out = {
    "dropdown_components": [describe(c["path_id"]) for c in [
        {"path_id": 6956434973078547699},
        {"path_id": 2712655708641848563},
        {"path_id": 1640437448010788083},
        {"path_id": TMP_DROPDOWN},
        {"path_id": 5402053862990179571},
        {"path_id": -8961996047486980877},
    ]],
}
Path(__file__).parent.joinpath("dropdown_scripts.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(out, ensure_ascii=False, indent=2))
