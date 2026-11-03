"""Validate clone-locale output against English template."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_data import (
    Catalog,
    EN_ASSET_TABLES_BUNDLE_KEY,
    EN_ASSETS_BUNDLE_KEY,
    EN_STRING_BUNDLE_KEY,
    clone_locale,
    collect_en_mirror_locations,
    make_es_string_mapper,
    _mapped_new_bucket_key,
)
from serialization import key_to_display

ORIG = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\catalog.json")
OUT = Path(__file__).resolve().parent / "out" / "catalog.json"


def main() -> int:
    cat = Catalog.load_json(str(ORIG))
    if not OUT.exists():
        clone_locale(cat).save_json(str(OUT))
    mod = Catalog.load_json(str(OUT))
    en_rows = collect_en_mirror_locations(cat)
    assert len(en_rows) > 200

    mapper = make_es_string_mapper(
        bundle_key_map={
            EN_ASSETS_BUNDLE_KEY: "localization-assets-spanish(es)_assets_all.bundle",
            EN_STRING_BUNDLE_KEY: "localization-string-tables-spanish(es)_assets_all.bundle",
            EN_ASSET_TABLES_BUNDLE_KEY: "localization-asset-tables-spanish(es)_assets_all.bundle",
        }
    )

    missing = 0
    for row in en_rows:
        if row["bucket_key"] == "Locale":
            continue
        for b in cat.buckets:
            if key_to_display(b.key) != row["bucket_key"]:
                continue
            target = _mapped_new_bucket_key(b.key, mapper)
            found = any(mb.key == target for mb in mod.buckets)
            if not found:
                missing += 1
                print("missing", row["bucket_key"], "->", key_to_display(target))
            break
    print("en mirror rows", len(en_rows), "missing es buckets", missing)
    assert missing == 0

    es_locale = [b for b in mod.buckets if b.key == "Locale-es"][0]
    assert len(es_locale.entry_indices) == 231
    print("Locale-es entries OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
