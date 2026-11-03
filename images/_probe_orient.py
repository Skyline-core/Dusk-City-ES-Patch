"""One-off probe; safe to delete."""
import os
import sys
from pathlib import Path

import UnityPy

ROOT = Path(__file__).resolve().parent.parent
GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
bundles = sorted(AA.glob("localization-assets-english(en)_assets_all_2226*"))
print("bundles", bundles)
if not bundles:
    sys.exit(1)
env = UnityPy.load(str(bundles[0]))
names = {}
for o in env.objects:
    if o.type.name not in ("Texture2D", "Sprite"):
        continue
    d = o.read()
    n = getattr(d, "m_Name", "")
    if not n.endswith("_EN"):
        continue
    w = getattr(d, "m_Width", 0) or 0
    h = getattr(d, "m_Height", 0)
    key = (n, o.type.name)
    names.setdefault(n, []).append((o.type.name, o.path_id, w, h))

uniq = len(names)
print("unique names", uniq)
both = sum(1 for v in names.values() if len(v) > 1)
print("names with multiple objects", both)
for n in sorted(names)[:5]:
    print(n, names[n])

# orientation test on Tips_1_EN
for o in env.objects:
    d = o.read()
    if getattr(d, "m_Name", "") == "Tips_1_EN" and o.type.name == "Texture2D":
        img = d.image
        print("Tips_1_EN size", img.size, "mode", img.mode)
        img.save(Path(__file__).parent / "_probe_tips_raw.png")
        img.transpose(1).save(Path(__file__).parent / "_probe_tips_flip.png")  # FLIP_TOP_BOTTOM=1
        break
