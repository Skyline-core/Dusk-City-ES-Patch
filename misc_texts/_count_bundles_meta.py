import json
from pathlib import Path

refs = json.loads(Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\misc_refs.json").read_text(encoding="utf-8"))
bundles = refs["_bundles"]
used = set()
for k, v in refs.items():
    if k.startswith("_"):
        continue
    for ref in v:
        used.add(ref[0])
print("crc meta", len(bundles), "used in refs", len(used), "missing crc", len(used - set(bundles.keys())))
