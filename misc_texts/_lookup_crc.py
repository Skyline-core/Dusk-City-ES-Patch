import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "catalog_tool"))
from catalog_data import Catalog

GAME = Path(os.environ.get("DUSK_GAME_PATH", r"G:\SteamLibrary\steamapps\common\Dusk City"))
cat = Catalog.load_json(str(GAME / "Dusk City_Data" / "StreamingAssets" / "aa" / "catalog.json"))
needle = "00876823e433c8400ecb7f3f8327b52a"
for loc in cat.locations:
    iid = loc.internal_id.replace("\\", "/")
    if needle in iid:
        d = loc.extra_data.get("data") if isinstance(loc.extra_data, dict) else None
        print("FOUND", iid, d.get("m_Crc") if d else None)
        break
else:
    print("not in catalog")
    # count by fname index
    idx = {}
    for loc in cat.locations:
        d = loc.extra_data.get("data") if isinstance(loc.extra_data, dict) else None
        if not d or "m_Crc" not in d:
            continue
        fname = iid.rsplit("/", 1)[-1] if (iid := loc.internal_id.replace("\\", "/")) else ""
        if fname.endswith(".bundle"):
            idx[fname] = int(d["m_Crc"])
    print("index size", len(idx))
    print("sample", needle + ".bundle" in idx)
