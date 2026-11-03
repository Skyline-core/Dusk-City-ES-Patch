#!/usr/bin/env python3
"""
Patch the English locale display name in localization-locales_assets_all.bundle.

Read-only on game files; writes patched bundle to translation/ui_label/out/.
Does not modify catalog.json (see REPORT.md for CRC/hash interaction).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import UnityPy

import os

# Game folder: env var DUSK_GAME_PATH (set by build_all.ps1), else two levels above translation\.
_HERE = Path(__file__).resolve().parent
_GAME_ROOT = Path(os.environ.get("DUSK_GAME_PATH") or _HERE.parent.parent)
GAME_AA = _GAME_ROOT / "Dusk City_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
OUT_DIR = _HERE / "out"
LOCALES_GLOB = "localization-locales_assets_all.bundle"
EN_LOCALE_NAME = "English (en)"
EN_PATH_ID = -1395074884649563235
PACKER = "lz4"


def find_english_locale(env: UnityPy.Environment) -> tuple[int, dict]:
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        t = o.read_typetree()
        if t.get("m_Name") == EN_LOCALE_NAME or t.get("m_Identifier", {}).get("m_Code") == "en":
            return o.path_id, t
    raise RuntimeError(f"English locale asset ({EN_LOCALE_NAME!r}) not found in bundle")


def patch_locale_tree(t: dict, *, label: str, rename_asset: bool) -> dict:
    code = t.get("m_Identifier", {}).get("m_Code")
    if code != "en":
        raise RuntimeError(f"Refusing to patch non-en locale (code={code!r})")
    t["m_LocaleName"] = label
    if rename_asset:
        t["m_Name"] = label
    return t


def save_bundle(env: UnityPy.Environment, out_path: Path) -> bytes:
    data = env.file.save(packer=PACKER)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return data


def verify(out_path: Path, *, expected_label: str) -> dict:
    env = UnityPy.load(str(out_path))
    pid, t = find_english_locale(env)
    ok_name = t.get("m_LocaleName") == expected_label
    ok_code = t.get("m_Identifier", {}).get("m_Code") == "en"
    return {
        "path_id": pid,
        "m_LocaleName": t.get("m_LocaleName"),
        "m_Name": t.get("m_Name"),
        "m_Code": t.get("m_Identifier", {}).get("m_Code"),
        "ok": ok_name and ok_code,
    }


def catalog_meta() -> dict:
    """Known catalog ABRO for the locales bundle (from catalog_tool dump)."""
    return {
        "catalog_bucket_key": "localization-locales_assets_all_25f81ff8884b1f4fcb45a11eaa1625f7.bundle",
        "internal_id_suffix": LOCALES_GLOB,
        "m_BundleName": "4e9fbff37d7e4eef9b5131df960f6937",
        "shipped_m_Crc": 4043063053,
        "shipped_m_Hash": "25f81ff8884b1f4fcb45a11eaa1625f7",
        "note": "After edit: update m_Hash to md5(bundle bytes) and/or set m_Crc=0 via catalog_tool.serialization.abro_set_crc_zero",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--label",
        default="Español",
        help="New m_LocaleName for the en locale (default: Español)",
    )
    parser.add_argument(
        "--rename-asset",
        action="store_true",
        help="Also set m_Name to --label (keeps default: only m_LocaleName)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Override source locales bundle path",
    )
    args = parser.parse_args()

    src = args.source or (GAME_AA / LOCALES_GLOB)
    if not src.is_file():
        print(f"Source not found: {src}", file=sys.stderr)
        return 1

    env = UnityPy.load(str(src))
    pid, tree = find_english_locale(env)
    if pid != EN_PATH_ID:
        print(f"Warning: English locale path_id {pid} != expected {EN_PATH_ID}", file=sys.stderr)

    obj = next(o for o in env.objects if o.path_id == pid)
    patched = patch_locale_tree(tree, label=args.label, rename_asset=args.rename_asset)
    obj.save_typetree(patched)

    out_path = OUT_DIR / LOCALES_GLOB
    raw = save_bundle(env, out_path)
    digest = hashlib.md5(raw).hexdigest()

    check = verify(out_path, expected_label=args.label)
    report = {
        "source": str(src),
        "output": str(out_path),
        "bytes": len(raw),
        "md5": digest,
        "patch": {
            "path_id": pid,
            "fields": ["m_LocaleName"] + (["m_Name"] if args.rename_asset else []),
            "m_LocaleName": args.label,
            "m_Identifier.m_Code": "en",
        },
        "verify": check,
        "catalog": catalog_meta(),
    }
    meta_path = OUT_DIR / "patch_language_label_result.json"
    meta_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if check["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
