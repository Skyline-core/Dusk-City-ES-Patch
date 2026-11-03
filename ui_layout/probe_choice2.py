import os, sys, json
import UnityPy
g = os.environ.get("DUSK_GAME_PATH", r"G:\SteamLibrary\steamapps\common\Dusk City")
aa = os.path.join(g, "Dusk City_Data", "StreamingAssets", "aa", "StandaloneWindows64")
env = UnityPy.load(os.path.join(aa, sys.argv[1] + ".bundle"))

SKIP = {"m_ObjectHideFlags", "m_CorrespondingSourceObject", "m_PrefabInstance", "m_PrefabAsset", "m_Script"}


def show(af, pid, depth=0, seen=None):
    o = af.objects.get(pid)
    if not o:
        print(" " * depth, "?", pid)
        return
    t = o.read_typetree()
    ind = " " * depth
    if o.type.name == "GameObject":
        print(f"{ind}GO {pid} '{t['m_Name']}' active={t['m_IsActive']}")
        for c in t["m_Component"]:
            show(af, c["component"]["m_PathID"], depth + 2)
    elif o.type.name == "RectTransform":
        print(f"{ind}RectTransform {pid}", {k: t[k] for k in ("m_AnchorMin", "m_AnchorMax", "m_AnchoredPosition", "m_SizeDelta", "m_Pivot")},
              "children", len(t["m_Children"]), "father", t["m_Father"]["m_PathID"])
    elif o.type.name == "MonoBehaviour":
        d = {k: v for k, v in t.items() if k not in SKIP and not k.startswith("m_Corresp")}
        s = json.dumps(d, default=str)
        print(f"{ind}MB {pid} script={t['m_Script']['m_PathID']}", s[:900])
    else:
        print(f"{ind}{o.type.name} {pid}")


for mb in env.objects:
    if mb.type.name == "MonoBehaviour":
        try:
            t = mb.read_typetree()
        except Exception:
            continue
        if "highlightMaterial" in t:   # ChoiseButton
            af = mb.assets_file
            print("====== ChoiseButton MB", mb.path_id, "in", af.name)
            show(af, t["m_GameObject"]["m_PathID"])
            print("  -> text component:")
            show(af, t["text"]["m_PathID"], 4)
        if "bubbleViewController" in t:   # DialogueChoise
            af = mb.assets_file
            print("====== DialogueChoise MB", mb.path_id, "in", af.name, "entryPerPage", t["entryPerPage"])
            print("  parent:"); show(af, t["parent"]["m_PathID"], 4)
            if t["bubbleViewController"]["m_PathID"]:
                print("  bubble controller:"); show(af, t["bubbleViewController"]["m_PathID"], 4)
            print("  GO:"); show(af, t["m_GameObject"]["m_PathID"], 4)
