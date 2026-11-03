import json
from pathlib import Path
import UnityPy

BUNDLE = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\741042f98eeaab65c8941174724e3496.bundle")
PID = -7104408855834432269

env = UnityPy.load(str(BUNDLE))
for o in env.objects:
    if o.path_id == PID:
        t = o.read_typetree()
        print(json.dumps({"m_OnValueChanged": t.get("m_OnValueChanged"), "m_Value": t.get("m_Value")}, indent=2, ensure_ascii=False))
        break
