import json
from pathlib import Path

refs = json.loads(Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\dialogue_refs.json").read_text(encoding="utf-8"))
used = set()
for k, v in refs.items():
    if k.startswith("_"):
        continue
    for ref in v:
        used.add(ref[0])
print("dialogue crc meta", len(refs["_bundles"]), "used", len(used))
