import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "catalog_tool"))

from catalog_data import Catalog  # noqa: E402
from serialization import key_to_display  # noqa: E402

CATALOG = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\catalog.json")
FONT_RE = re.compile(r"font|sdf|tmp|noto|mplus|\.ttf|\.otf|textmesh", re.I)
BUNDLE_PROVIDER = "UnityEngine.ResourceManagement.ResourceProviders.AssetBundleProvider"


def bundle_for_loc(cat, loc):
    if loc.provider_id == BUNDLE_PROVIDER:
        return Path(loc.internal_id.replace("\\", "/")).name
    dk = key_to_display(loc.dependency_key)
    if isinstance(dk, str) and ".bundle" in dk:
        return dk
    return ""


def main():
    cat = Catalog.load_json(str(CATALOG))
    hits = []
    for loc in cat.locations:
        parts = [str(loc.internal_id or ""), str(loc.primary_key or "")]
        text = " ".join(parts)
        if FONT_RE.search(text):
            hits.append(
                {
                    "primary": key_to_display(loc.primary_key),
                    "internal": loc.internal_id,
                    "bundle": bundle_for_loc(cat, loc),
                    "provider": loc.provider_id,
                }
            )
    print("font location hits:", len(hits))
    for h in hits[:100]:
        print(h)
    # unique internal paths
    paths = sorted({h["internal"] for h in hits if h["internal"]})
    print("\nunique internal paths:", len(paths))
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
