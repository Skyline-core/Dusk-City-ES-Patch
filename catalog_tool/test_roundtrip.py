"""Run round-trip validation from translation/catalog_tool directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_data import Catalog

CATALOG = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\catalog.json")


def main() -> int:
    cat = Catalog.load_json(str(CATALOG))
    assert len(cat.locations) > 0
    assert len(cat.buckets) > 0
    results = cat.verify_roundtrip_blobs()
    for k, ok in results.items():
        print(f"{k}: {'OK' if ok else 'FAIL'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
