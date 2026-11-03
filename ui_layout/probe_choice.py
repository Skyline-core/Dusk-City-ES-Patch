import os, sys, glob, json
import UnityPy
g = os.environ.get("DUSK_GAME_PATH", r"G:\SteamLibrary\steamapps\common\Dusk City")
aa = os.path.join(g, "Dusk City_Data", "StreamingAssets", "aa", "StandaloneWindows64")
name = sys.argv[1]
f = os.path.join(aa, name + ".bundle")
env = UnityPy.load(f)
objs = {o.path_id: o for o in env.objects}
print("objects", len(objs))
types = {}
for o in env.objects:
    types[o.type.name] = types.get(o.type.name, 0) + 1
print(types)


def short(t, keys):
    return {k: t.get(k) for k in keys if k in t}


for o in env.objects:
    if o.type.name == "MonoBehaviour":
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if "highlightMaterial" in t or "bubbleViewController" in t or "buttonPrefab" in t:
            print("---- MB", o.path_id, t.get("m_Name"), "GO", t.get("m_GameObject"))
            print(json.dumps({k: v for k, v in t.items() if k not in ("edges", "nodes", "references")}, default=str)[:1500])
