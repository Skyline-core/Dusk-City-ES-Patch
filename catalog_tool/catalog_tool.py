#!/usr/bin/env python3
"""CLI for Addressables catalog decode/encode and Spanish locale cloning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .catalog_data import (
        Catalog,
        catalog_file_md5,
        clone_locale,
        collect_en_mirror_locations,
        diff_catalog_patch_crc,
        patch_crc_hijack_en_bundles,
    )
    from .serialization import key_to_display
except ImportError:
    from catalog_data import (
        Catalog,
        catalog_file_md5,
        clone_locale,
        collect_en_mirror_locations,
        diff_catalog_patch_crc,
        patch_crc_hijack_en_bundles,
    )
    from serialization import key_to_display

import os

# Game folder: env var DUSK_GAME_PATH (set by build_all.ps1), else two levels above translation\.
_HERE = Path(__file__).resolve().parent
_GAME_ROOT = Path(os.environ.get("DUSK_GAME_PATH") or _HERE.parent.parent)
DEFAULT_CATALOG = _GAME_ROOT / "Dusk City_Data" / "StreamingAssets" / "aa" / "catalog.json"
OUT_DIR = _HERE / "out"
DEFAULT_PATCH_DIR = _HERE.parent / "patch_en_slot"
CATALOG_HASH_FILENAME = "catalog_2026.06.23.02.23.07.hash"


def cmd_roundtrip(args: argparse.Namespace) -> int:
    cat = Catalog.load_json(str(args.catalog))
    results = cat.verify_roundtrip_blobs()
    all_ok = all(results.values())
    for k, ok in results.items():
        print(f"{k}: {'IDENTICAL' if ok else 'DIFFER'}")
    return 0 if all_ok else 1


def _is_localization_text(s: str) -> bool:
    low = s.lower()
    return any(x in low for x in ("localize", "localization", "locali"))


def cmd_dump(args: argparse.Namespace) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cat = Catalog.load_json(str(args.catalog))
    out_path = OUT_DIR / "localization_locations.txt"

    lines: list[str] = []
    lines.append(f"Catalog: {args.catalog}")
    lines.append(f"Locations total: {len(cat.locations)}")
    lines.append(f"Buckets total: {len(cat.buckets)}")
    lines.append("")

    for bi, b in enumerate(cat.buckets):
        bk = key_to_display(b.key)
        if not _is_localization_text(bk):
            # also check locations in bucket
            if not any(_is_localization_text(cat.locations[i].internal_id) for i in b.entry_indices):
                continue
        lines.append(f"=== Bucket {bi} key={bk!r} entries={len(b.entry_indices)} ===")
        for ei in b.entry_indices:
            loc = cat.locations[ei]
            lines.append(f"  entry[{ei}] primary={key_to_display(loc.primary_key)!r}")
            lines.append(f"    internal_id={loc.internal_id!r}")
            lines.append(f"    provider={loc.provider_id!r}")
            lines.append(f"    dependency_key={key_to_display(loc.dependency_key)!r}")
            lines.append(f"    dep_hash={loc.dependency_hash}")
            if loc.resource_type:
                lines.append(f"    resource_type={loc.resource_type.class_name}")
            if loc.extra_data and isinstance(loc.extra_data, dict) and loc.extra_data.get("kind") == "AssetBundleRequestOptions":
                d = loc.extra_data.get("data") or {}
                lines.append(f"    bundle={d.get('m_BundleName')} crc={d.get('m_Crc')} hash={d.get('m_Hash')}")
        lines.append("")

    # *_EN TextAsset report
    lines.append("=== *_EN internalId locations (asset path keys) ===")
    en_assets = [loc for loc in cat.locations if "_EN" in loc.internal_id or loc.internal_id.endswith("_EN")]
    lines.append(f"Count: {len(en_assets)}")
    bundle_provider = "UnityEngine.ResourceManagement.ResourceProviders.AssetBundleProvider"
    for loc in en_assets[:5000]:
        bundle = ""
        if loc.provider_id == bundle_provider:
            bundle = loc.internal_id
        elif isinstance(loc.dependency_key, str) and ".bundle" in loc.dependency_key:
            bundle = loc.dependency_key
        lines.append(
            f"  primary={key_to_display(loc.primary_key)!r} internal={loc.internal_id!r} "
            f"provider={loc.provider_id.split('.')[-1]} bundle_dep={bundle!r}"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


def cmd_clone_locale(args: argparse.Namespace) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cat = Catalog.load_json(str(args.catalog))

    bundle_map: dict[str, str] = {}
    if args.bundle_map:
        bundle_map = json.loads(Path(args.bundle_map).read_text(encoding="utf-8"))

    # Default Spanish bundle placeholders (bundles built separately)
    runtime = "{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"
    defaults = {
        f"Assets/Localize/Spanish (es).asset": runtime + args.locales_bundle,
        f"Assets/Localize/Translation_es.asset": runtime + args.string_tables_bundle,
        f"Assets/Localize/Image_es.asset": runtime + args.asset_tables_bundle,
        runtime
        + "localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle": runtime
        + args.assets_bundle,
    }
    for k, v in defaults.items():
        bundle_map.setdefault(k, v)

    bundle_hashes = {}
    if args.bundle_hashes:
        bundle_hashes = json.loads(Path(args.bundle_hashes).read_text(encoding="utf-8"))

    cloned = clone_locale(
        cat,
        from_locale=args.from_locale,
        to_locale=args.to_locale,
        bundle_map=bundle_map,
        bundle_hashes=bundle_hashes,
        zero_crc_bundles=not args.keep_crc,
    )
    out_catalog = OUT_DIR / "catalog.json"
    cloned.save_json(str(out_catalog))
    print(f"Wrote {out_catalog}")

    # Verify es keys present
    markers = (
        "Locale-es",
        "Spanish (es)",
        "Translation_es",
        "Image_es",
        "spanish(es)",
        "_ES",
    )
    es_buckets = [
        b
        for b in cloned.buckets
        if isinstance(b.key, str) and any(m in b.key for m in markers)
    ]
    print(f"New Spanish locale buckets: {len(es_buckets)}")
    for b in sorted(es_buckets, key=lambda x: str(x.key))[:30]:
        print(f"  key={b.key!r} entries={len(b.entry_indices)}")
    if len(es_buckets) > 30:
        print(f"  ... and {len(es_buckets) - 30} more")

    mirror_path = OUT_DIR / "en_mirror_report.json"
    mirror_path.write_text(json.dumps(collect_en_mirror_locations(cat), indent=2), encoding="utf-8")
    print(f"Wrote en mirror report {mirror_path}")

    # Re-decode output
    cat2 = Catalog.load_json(str(out_catalog))
    es_locs = [loc for loc in cat2.locations if "Spanish (es)" in loc.internal_id or "_ES" in loc.internal_id]
    print(f"Re-decode: es-tagged locations: {len(es_locs)}")
    return 0


def cmd_patch_crc(args: argparse.Namespace) -> int:
    patch_root = args.patch_dir
    patch_root.mkdir(parents=True, exist_ok=True)
    aa_bundles = patch_root / "StandaloneWindows64"
    aa_bundles.mkdir(parents=True, exist_ok=True)

    cat = Catalog.load_json(str(args.catalog))
    patched = patch_crc_hijack_en_bundles(cat)
    diff = diff_catalog_patch_crc(cat, patched)
    if diff["changed_count"] != 4:
        print(f"patch-crc verify failed: {diff['changed_count']} locations changed", file=sys.stderr)
        return 1

    out_catalog = patch_root / "catalog.json"
    patched.save_json(str(out_catalog))

    cat2 = Catalog.load_json(str(out_catalog))
    diff2 = diff_catalog_patch_crc(cat, cat2)
    if diff2["changed_count"] != 4:
        print("Re-decode verify failed", file=sys.stderr)
        return 1

    for row in diff2["changed"]:
        before, after = row["before"], row["after"]
        if after["m_Crc"] != 0 or after["m_UseCrcForCachedBundles"] is not False:
            print(f"CRC flags not cleared at {row['internal_id']}", file=sys.stderr)
            return 1
        if before["m_Hash"] != after["m_Hash"] or before["m_BundleName"] != after["m_BundleName"]:
            print(
                f"Note: m_Hash/m_BundleName unchanged at {row['internal_id']!r} "
                f"(local AssetBundleProvider uses file path + optional CRC; "
                f"m_Hash is cache id / dependency key suffix, not re-verified when CRC=0)."
            )

    catalog_md5 = catalog_file_md5(str(out_catalog))
    hash_path = aa_bundles / CATALOG_HASH_FILENAME
    hash_path.write_bytes(catalog_md5.encode("ascii"))  # original .hash is 32 bytes, no newline

    orig_hash_path = (
        Path(args.catalog).parent / "StandaloneWindows64" / CATALOG_HASH_FILENAME
    )
    orig_hash = orig_hash_path.read_text(encoding="utf-8").strip() if orig_hash_path.exists() else ""
    print(f"Wrote {out_catalog}")
    print(f"Wrote {hash_path} (MD5 of catalog.json = {catalog_md5})")
    if orig_hash and orig_hash != catalog_md5:
        print(
            f"Original {CATALOG_HASH_FILENAME} was {orig_hash} (does not match MD5 of current "
            f"shipping catalog.json = {catalog_file_md5(str(args.catalog))}). "
            "Addressables compares this hash string to detect remote catalog updates; "
            "settings.json loads catalog from aa/catalog.json with dependency on this hash file. "
            "Patched hash must match patched catalog MD5 so local hash dependency stays consistent."
        )
    print("patch-crc OK: exactly 4 localization bundle CRC entries cleared (3 English + locales)")
    return 0


def cmd_list_en_mirror(args: argparse.Namespace) -> int:
    cat = Catalog.load_json(str(args.catalog))
    rows = collect_en_mirror_locations(cat)
    print(json.dumps(rows, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dusk City Addressables catalog tool")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Path to catalog.json (read-only)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_rt = sub.add_parser("roundtrip", help="Verify decode->encode blob identity (unchanged catalog)")
    p_rt.set_defaults(func=cmd_roundtrip)

    p_dump = sub.add_parser("dump", help="Dump localization-related catalog locations")
    p_dump.set_defaults(func=cmd_dump)

    p_clone = sub.add_parser("clone-locale", help="Clone English locale entries to Spanish in catalog")
    p_clone.add_argument("--from", dest="from_locale", default="en")
    p_clone.add_argument("--to", dest="to_locale", default="es")
    p_clone.add_argument("--bundle-map", type=Path, help="JSON map old_internal_id -> new bundle path")
    p_clone.add_argument("--bundle-hashes", type=Path, help="JSON map bundle name -> hash string")
    p_clone.add_argument("--locales-bundle", default="localization-locales-es_assets_all.bundle")
    p_clone.add_argument("--string-tables-bundle", default="localization-string-tables-spanish(es)_assets_all.bundle")
    p_clone.add_argument("--asset-tables-bundle", default="localization-asset-tables-spanish(es)_assets_all.bundle")
    p_clone.add_argument("--assets-bundle", default="localization-assets-spanish(es)_assets_all.bundle")
    p_clone.add_argument("--keep-crc", action="store_true", help="Do not zero CRC on bundle options")
    p_clone.set_defaults(func=cmd_clone_locale)

    p_en = sub.add_parser("list-en-mirror", help="List en bucket locations used as clone template")
    p_en.set_defaults(func=cmd_list_en_mirror)

    p_crc = sub.add_parser(
        "patch-crc",
        help="Zero CRC on 3 English localization bundles; write patch_en_slot catalog + hash",
    )
    p_crc.add_argument(
        "--patch-dir",
        type=Path,
        default=DEFAULT_PATCH_DIR,
        help="Patch staging root (writes catalog.json and StandaloneWindows64/*.hash)",
    )
    p_crc.set_defaults(func=cmd_patch_crc)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
