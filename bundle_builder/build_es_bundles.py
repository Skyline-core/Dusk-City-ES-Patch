#!/usr/bin/env python3
"""Build Spanish (es) Unity Addressables localization bundles from English templates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import UnityPy

# Game folder: set env var DUSK_GAME_PATH (build_all.ps1 does this); falls back to the
# folder two levels above translation\ (i.e. the translation folder lives inside the game folder).
ROOT = Path(__file__).resolve().parent
GAME_ROOT = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent.parent)
GAME_AA = GAME_ROOT / "Dusk City_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
DEFAULT_OUT = ROOT / "out"
DEFAULT_HIJACK_OUT = ROOT.parent / "patch_en_slot" / "files" / "StandaloneWindows64"
DEFAULT_SOURCE = ROOT.parent / "es_source.json"

RUNTIME_PREFIX = (
    "{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"
)

OUT_LOCALES = "localization-locales-es_assets_all.bundle"
OUT_STRINGS = "localization-string-tables-spanish(es)_assets_all.bundle"
OUT_ASSET_TABLES = "localization-asset-tables-spanish(es)_assets_all.bundle"
OUT_ASSETS = "localization-assets-spanish(es)_assets_all.bundle"

# English slot hijack: same on-disk names as shipped game / catalog internalId paths
HIJACK_STRINGS = "localization-string-tables-english(en)_assets_all.bundle"
HIJACK_ASSET_TABLES = "localization-asset-tables-english(en)_assets_all.bundle"
HIJACK_ASSETS = (
    "localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle"
)

EN_ASSETS_GLOB = "localization-assets-english(en)_assets_all_2226*"
EN_STRINGS_GLOB = "localization-string-tables-english*"
EN_ASSET_TABLES_GLOB = "localization-asset-tables-english*"
EN_LOCALES_GLOB = "localization-locales*"

# Catalog GUID bucket keys (32-char hex) for English locale / tables
CATALOG_GUID_EN = {
    "locale": "c536477e6c44c4e4282656fff6794ef7",
    "translation_table": "cfbb05c60dd549047979885a5188ce7d",
    "image_table": "6962848bf289d644199b1a228eb7615d",
}

PACKER = "lz4"


def _glob_one(pattern: str) -> Path:
    matches = sorted(GAME_AA.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one match for {pattern!r}, got {matches}")
    return matches[0]


def _serialized_file(env: UnityPy.Environment) -> Any:
    bf = env.file
    if bf is None:
        raise RuntimeError("No bundle file on environment")
    files = bf.files
    if len(files) != 1:
        raise RuntimeError(f"Expected one cab file, got {len(files)}")
    return next(iter(files.values()))


def _es_guid_from_en(en_hex: str) -> str:
    return hashlib.md5(f"es:{en_hex}".encode()).hexdigest()


def _internal_bundle_name(logical_name: str) -> str:
    """Deterministic AssetBundle.m_Name stem (no .bundle suffix in catalog m_BundleName)."""
    return hashlib.md5(f"es-internal:{logical_name}".encode()).hexdigest()


def _catalog_hash_for_bytes(data: bytes) -> str:
    """Hash128 string for catalog m_Hash (MD5 of bundle bytes; use with --keep-crc off)."""
    return hashlib.md5(data).hexdigest()


def load_translation_source(path: Path) -> tuple[dict[int, str], dict[tuple[str, str], str], dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    strings: dict[int, str] = {}
    for row in data.get("strings", []):
        sid = int(row["id"])
        es = (row.get("es") or "").strip()
        strings[sid] = es if es else row.get("en", "")

    scripts: dict[tuple[str, str], str] = {}
    for script in data.get("scripts", []):
        asset = script["asset"]
        for entry in script.get("entries", []):
            es = (entry.get("es") or "").strip()
            text = es if es else entry.get("en", "")
            scripts[(asset, entry["path"])] = text
    return strings, scripts, data


def make_test_source(src: Path, dest: Path) -> None:
    with src.open(encoding="utf-8") as f:
        data = json.load(f)
    suffix = " áéíóúñ¿¡"
    for row in data.get("strings", []):
        row["es"] = "ES: " + row.get("en", "") + suffix
    for script in data.get("scripts", []):
        for entry in script.get("entries", []):
            entry["es"] = "ES: " + entry.get("en", "") + suffix
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Wrote test source {dest}")


def collect_text_nodes(node: Any, path: str = "") -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    if isinstance(node, dict):
        if "text" in node and isinstance(node["text"], str):
            out.append((path, node))
        for k, v in node.items():
            child = f"{path}/{k}" if path else k
            out.extend(collect_text_nodes(v, child))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(collect_text_nodes(v, f"{path}/{i}"))
    return out


def patch_textasset_json(raw: str, asset_base: str, scripts: dict[tuple[str, str], str]) -> str:
    obj = json.loads(raw)
    for path, node in collect_text_nodes(obj):
        key = (asset_base, path)
        if key in scripts:
            node["text"] = scripts[key]
    text = json.dumps(obj, ensure_ascii=False, indent=4)
    return text.replace("\n", "\r\n")


def rename_en_to_es(name: str) -> str:
    if name.endswith("_EN"):
        return name[:-3] + "_ES"
    return name.replace("_EN.", "_ES.")


def map_asset_path(path: str) -> str:
    return path.replace("_EN.json", "_ES.json").replace("_EN.png", "_ES.png")


def _internal_bundle_stem(env: UnityPy.Environment) -> str:
    for o in env.objects:
        if o.type.name == "AssetBundle":
            name = o.read_typetree().get("m_Name", "")
            return name.replace(".bundle", "")
    raise RuntimeError("No AssetBundle object in environment")


def save_bundle(
    env: UnityPy.Environment,
    out_path: Path,
    internal_stem: str | None,
) -> tuple[bytes, str, str]:
    stem = internal_stem if internal_stem is not None else _internal_bundle_stem(env)
    if internal_stem is not None:
        for o in env.objects:
            if o.type.name == "AssetBundle":
                ab = o.read_typetree()
                ab["m_Name"] = f"{internal_stem}.bundle"
                o.save_typetree(ab)
                break
    data = env.file.save(packer=PACKER)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    catalog_hash = _catalog_hash_for_bytes(data)
    return data, stem, catalog_hash


def build_locales_bundle(out_dir: Path) -> dict[str, Any]:
    env = UnityPy.load(str(_glob_one(EN_LOCALES_GLOB)))
    sf = _serialized_file(env)
    remove_pids: list[int] = []
    for pid, o in sf.objects.items():
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            if t.get("m_Name") != "English (en)":
                remove_pids.append(pid)
    for pid in remove_pids:
        del sf.objects[pid]

    for o in sf.objects.values():
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            t["m_Name"] = "Spanish (es)"
            t["m_Identifier"] = {"m_Code": "es"}
            t["m_LocaleName"] = "Spanish (es)"
            t["m_SortOrder"] = 10000
            o.save_typetree(t)
        elif o.type.name == "AssetBundle":
            ab = o.read_typetree()
            new_cont = []
            for path, meta in ab.get("m_Container", []):
                if path == "Assets/Localize/English (en).asset":
                    new_cont.append(("Assets/Localize/Spanish (es).asset", meta))
            ab["m_Container"] = new_cont
            ab["m_Dependencies"] = []
            o.save_typetree(ab)

    out_path = out_dir / OUT_LOCALES
    _, internal, catalog_hash = save_bundle(env, out_path, _internal_bundle_name(OUT_LOCALES))
    return {
        "file": OUT_LOCALES,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": len(list(env.objects)),
    }


def build_string_tables_bundle(out_dir: Path, strings: dict[int, str]) -> dict[str, Any]:
    env = UnityPy.load(str(_glob_one(EN_STRINGS_GLOB)))
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            if t.get("m_Name") != "Translation_en":
                continue
            t = copy.deepcopy(t)
            t["m_Name"] = "Translation_es"
            t["m_LocaleId"] = {"m_Code": "es"}
            for row in t.get("m_TableData", []):
                sid = int(row["m_Id"])
                row["m_Localized"] = strings.get(sid, row.get("m_Localized", ""))
            o.save_typetree(t)
        elif o.type.name == "AssetBundle":
            ab = o.read_typetree()
            ab["m_Container"] = [
                (map_asset_path(p) if "Translation_en" in p else p, m)
                for p, m in ab.get("m_Container", [])
            ]
            o.save_typetree(ab)

    out_path = out_dir / OUT_STRINGS
    _, internal, catalog_hash = save_bundle(env, out_path, _internal_bundle_name(OUT_STRINGS))
    return {
        "file": OUT_STRINGS,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": len(list(env.objects)),
    }


def build_asset_tables_bundle(out_dir: Path) -> dict[str, Any]:
    """Image_es: locale metadata only; m_Localized GUIDs kept from Image_en (English catalog keys).

    Unity loads localized sprites via Addressables GUID buckets that still point at *_EN.png
    for unchanged art. Separate *_ES assets in the es assets bundle satisfy Locale-es / name
    lookups; the asset table continues to reference the same English GUID strings.
    """
    env = UnityPy.load(str(_glob_one(EN_ASSET_TABLES_GLOB)))
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            if t.get("m_Name") != "Image_en":
                continue
            t = copy.deepcopy(t)
            t["m_Name"] = "Image_es"
            t["m_LocaleId"] = {"m_Code": "es"}
            o.save_typetree(t)
        elif o.type.name == "AssetBundle":
            ab = o.read_typetree()
            ab["m_Container"] = [
                (p.replace("Image_en", "Image_es"), m) for p, m in ab.get("m_Container", [])
            ]
            o.save_typetree(ab)

    out_path = out_dir / OUT_ASSET_TABLES
    _, internal, catalog_hash = save_bundle(env, out_path, _internal_bundle_name(OUT_ASSET_TABLES))
    return {
        "file": OUT_ASSET_TABLES,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": len(list(env.objects)),
        "image_table_guid_policy": "keep_english_asset_guids_in_m_Localized",
    }


def build_assets_bundle(out_dir: Path, scripts: dict[tuple[str, str], str]) -> dict[str, Any]:
    env = UnityPy.load(str(_glob_one(EN_ASSETS_GLOB)))
    en_counts = Counter(o.type.name for o in env.objects)

    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            old_name = d.m_Name
            if not old_name.endswith("_EN"):
                continue
            base = old_name[: -len("_EN")]
            new_name = base + "_ES"
            raw = d.m_Script
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8-sig")
            new_raw = patch_textasset_json(raw, base, scripts)
            d.m_Name = new_name
            d.m_Script = new_raw
            d.save()
        elif o.type.name in ("Texture2D", "Sprite"):
            d = o.read()
            if d.m_Name.endswith("_EN"):
                d.m_Name = rename_en_to_es(d.m_Name)
                d.save()
        elif o.type.name == "AssetBundle":
            ab = o.read_typetree()
            ab["m_Container"] = [(map_asset_path(p), m) for p, m in ab.get("m_Container", [])]
            ab["m_Dependencies"] = []
            o.save_typetree(ab)

    out_path = out_dir / OUT_ASSETS
    _, internal, catalog_hash = save_bundle(env, out_path, _internal_bundle_name(OUT_ASSETS))
    es_counts = Counter(o.type.name for o in UnityPy.load(str(out_path)).objects)
    return {
        "file": OUT_ASSETS,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": sum(es_counts.values()),
        "type_counts_en": dict(en_counts),
        "type_counts_es": dict(es_counts),
    }


def build_hijack_string_tables_bundle(out_dir: Path, strings: dict[int, str]) -> dict[str, Any]:
    env = UnityPy.load(str(_glob_one(EN_STRINGS_GLOB)))
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        t = o.read_typetree()
        if t.get("m_Name") != "Translation_en":
            continue
        for row in t.get("m_TableData", []):
            sid = int(row["m_Id"])
            row["m_Localized"] = strings.get(sid, row.get("m_Localized", ""))
        o.save_typetree(t)

    out_path = out_dir / HIJACK_STRINGS
    _, internal, catalog_hash = save_bundle(env, out_path, internal_stem=None)
    return {
        "file": HIJACK_STRINGS,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": len(list(env.objects)),
    }


def build_hijack_asset_tables_bundle(out_dir: Path) -> dict[str, Any]:
    """Re-save Image_en bundle unchanged (locale metadata stays English)."""
    env = UnityPy.load(str(_glob_one(EN_ASSET_TABLES_GLOB)))
    out_path = out_dir / HIJACK_ASSET_TABLES
    _, internal, catalog_hash = save_bundle(env, out_path, internal_stem=None)
    return {
        "file": HIJACK_ASSET_TABLES,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": len(list(env.objects)),
    }


def build_hijack_assets_bundle(out_dir: Path, scripts: dict[tuple[str, str], str]) -> dict[str, Any]:
    env = UnityPy.load(str(_glob_one(EN_ASSETS_GLOB)))
    en_counts = Counter(o.type.name for o in env.objects)

    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            old_name = d.m_Name
            if not old_name.endswith("_EN"):
                continue
            base = old_name[: -len("_EN")]
            raw = d.m_Script
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8-sig")
            d.m_Script = patch_textasset_json(raw, base, scripts)
            d.save()

    out_path = out_dir / HIJACK_ASSETS
    _, internal, catalog_hash = save_bundle(env, out_path, internal_stem=None)
    out_counts = Counter(o.type.name for o in UnityPy.load(str(out_path)).objects)
    return {
        "file": HIJACK_ASSETS,
        "path": str(out_path),
        "internal_bundle_name": internal,
        "catalog_hash": catalog_hash,
        "object_count": sum(out_counts.values()),
        "type_counts_en": dict(en_counts),
        "type_counts_out": dict(out_counts),
    }


def _compare_texture_sprite_raw(en_env: UnityPy.Environment, out_env: UnityPy.Environment) -> list[str]:
    errors: list[str] = []
    en_by = {(o.path_id, o.type.name): o for o in en_env.objects if o.type.name in ("Texture2D", "Sprite")}
    out_by = {(o.path_id, o.type.name): o for o in out_env.objects if o.type.name in ("Texture2D", "Sprite")}
    if en_by.keys() != out_by.keys():
        errors.append(f"Texture/Sprite path_id set mismatch en={len(en_by)} out={len(out_by)}")
        return errors
    for key, o_en in en_by.items():
        o_out = out_by[key]
        if o_en.read().m_Name != o_out.read().m_Name:
            errors.append(f"{key} name mismatch")
        if o_en.get_raw_data() != o_out.get_raw_data():
            errors.append(f"{key} raw bytes differ")
    return errors


def self_test_hijack(out_dir: Path, source_path: Path, use_test_strings: bool) -> int:
    errors: list[str] = []
    strings, scripts, _ = load_translation_source(source_path)

    pairs = [
        (EN_STRINGS_GLOB, HIJACK_STRINGS, {"MonoBehaviour": 1, "MonoScript": 1, "AssetBundle": 1}),
        (EN_ASSET_TABLES_GLOB, HIJACK_ASSET_TABLES, {"MonoBehaviour": 1, "MonoScript": 1, "AssetBundle": 1}),
        (EN_ASSETS_GLOB, HIJACK_ASSETS, {"TextAsset": 53, "Texture2D": 88, "Sprite": 88, "AssetBundle": 1}),
    ]

    for en_pat, out_name, expected in pairs:
        en_env = UnityPy.load(str(_glob_one(en_pat)))
        out_env = UnityPy.load(str(out_dir / out_name))
        en_c = Counter(o.type.name for o in en_env.objects)
        out_c = Counter(o.type.name for o in out_env.objects)
        if sum(en_c.values()) != sum(out_c.values()):
            errors.append(f"{out_name}: object count {sum(out_c.values())} != {sum(en_c.values())}")
        for typ, count in expected.items():
            if out_c.get(typ, 0) != count:
                errors.append(f"{out_name}: {typ} count {out_c.get(typ)} != {count}")

        if out_name == HIJACK_STRINGS:
            for o in out_env.objects:
                if o.type.name != "MonoBehaviour":
                    continue
                t = o.read_typetree()
                if t.get("m_Name") != "Translation_en":
                    errors.append(f"expected Translation_en, got {t.get('m_Name')!r}")
                if t.get("m_LocaleId") != {"m_Code": "en"}:
                    errors.append("Translation_en locale id must stay en")
                sample = t["m_TableData"][0]["m_Localized"]
                if use_test_strings and not sample.startswith("ES: "):
                    errors.append(f"string patch failed: {sample[:40]!r}")
                ref = strings.get(int(t["m_TableData"][0]["m_Id"]), "")
                if t["m_TableData"][0]["m_Localized"] != ref:
                    errors.append("string table id0 mismatch source")

        if out_name == HIJACK_ASSET_TABLES:
            for o in out_env.objects:
                if o.type.name == "MonoBehaviour":
                    t = o.read_typetree()
                    if t.get("m_Name") != "Image_en":
                        errors.append(f"expected Image_en, got {t.get('m_Name')!r}")
                    if t.get("m_LocaleId") != {"m_Code": "en"}:
                        errors.append("Image_en locale id must stay en")

        if out_name == HIJACK_ASSETS:
            tas = [o.read().m_Name for o in out_env.objects if o.type.name == "TextAsset"]
            if not all(n.endswith("_EN") for n in tas):
                errors.append(f"TextAsset names not all _EN: {tas[:3]}")
            if use_test_strings:
                found = False
                for o in out_env.objects:
                    if o.type.name == "TextAsset":
                        raw = o.read().m_Script
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8-sig")
                        if "áéíóúñ" in raw:
                            found = True
                            break
                if not found:
                    errors.append("no Spanish accents found in TextAsset JSON")
            errors.extend(_compare_texture_sprite_raw(en_env, out_env))

        for o in out_env.objects:
            if o.type.name == "AssetBundle":
                en_name = None
                for o2 in en_env.objects:
                    if o2.type.name == "AssetBundle":
                        en_name = o2.read_typetree().get("m_Name")
                        break
                out_name_ab = o.read_typetree().get("m_Name")
                if en_name != out_name_ab:
                    errors.append(f"{out_name}: AssetBundle m_Name {out_name_ab!r} != {en_name!r}")

    if errors:
        print("HIJACK SELF-TEST FAILED:")
        for e in errors:
            print(" ", e)
        return 1
    print("HIJACK SELF-TEST OK")
    return 0


def build_all_hijack(out_dir: Path, source_path: Path) -> int:
    strings, scripts, _ = load_translation_source(source_path)
    meta = [
        build_hijack_string_tables_bundle(out_dir, strings),
        build_hijack_asset_tables_bundle(out_dir),
        build_hijack_assets_bundle(out_dir, scripts),
    ]
    print("Built hijack-en bundles (English identity, Spanish payload):")
    for m in meta:
        print(
            f"  {m['file']} objects={m['object_count']} "
            f"hash={m['catalog_hash']} internal={m['internal_bundle_name']}"
        )
    return 0


def write_bundle_map(out_dir: Path) -> None:
    en_assets_key = (
        "localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle"
    )
    mapping = {
        "Assets/Localize/Spanish (es).asset": RUNTIME_PREFIX + OUT_LOCALES,
        "Assets/Localize/Translation_es.asset": RUNTIME_PREFIX + OUT_STRINGS,
        "Assets/Localize/Image_es.asset": RUNTIME_PREFIX + OUT_ASSET_TABLES,
        RUNTIME_PREFIX + en_assets_key: RUNTIME_PREFIX + OUT_ASSETS,
    }
    path = out_dir / "bundle_map.json"
    path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path}")


def write_bundle_hashes(out_dir: Path, meta: list[dict[str, Any]]) -> None:
    hashes = {m["internal_bundle_name"]: m["catalog_hash"] for m in meta}
    path = out_dir / "bundle_hashes.json"
    path.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(f"Wrote {path}")


def write_guid_map(out_dir: Path) -> None:
    guid_map = {
        "notes": (
            "Catalog Hash128 buckets for en locale/tables use 32-char hex string keys. "
            "clone-locale adds Spanish (es) / Translation_es / Image_es string buckets; "
            "Hash128 dict keys use md5('es:'+enGuid) only when the en bucket key is kind Hash128. "
            "These English hex keys are what Image_en m_Localized GUID strings match. "
            "Image_es keeps those English GUIDs so unchanged sprites resolve via existing en buckets."
        ),
        "english_catalog_guids": CATALOG_GUID_EN,
        "spanish_placeholder_guids_md5_es_prefix": {
            k: _es_guid_from_en(v) for k, v in CATALOG_GUID_EN.items()
        },
        "table_assets": {
            "Translation_es": {"address": "Translation_es", "path": "Assets/Localize/Translation_es.asset"},
            "Image_es": {"address": "Image_es", "path": "Assets/Localize/Image_es.asset"},
        },
        "locale_asset": {
            "address": "Spanish (es)",
            "path": "Assets/Localize/Spanish (es).asset",
            "code": "es",
        },
    }
    path = out_dir / "guid_map.json"
    path.write_text(json.dumps(guid_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path}")


def self_test(out_dir: Path, source_path: Path, use_test_strings: bool) -> int:
    errors: list[str] = []
    strings, scripts, _ = load_translation_source(source_path)

    pairs = [
        (EN_LOCALES_GLOB, OUT_LOCALES, {"MonoBehaviour": 1, "MonoScript": 1, "AssetBundle": 1}),
        (EN_STRINGS_GLOB, OUT_STRINGS, {"MonoBehaviour": 1, "MonoScript": 1, "AssetBundle": 1}),
        (EN_ASSET_TABLES_GLOB, OUT_ASSET_TABLES, {"MonoBehaviour": 1, "MonoScript": 1, "AssetBundle": 1}),
        (EN_ASSETS_GLOB, OUT_ASSETS, {"TextAsset": 53, "Texture2D": 88, "Sprite": 88, "AssetBundle": 1}),
    ]

    for en_pat, out_name, expected in pairs:
        en_env = UnityPy.load(str(_glob_one(en_pat)))
        es_env = UnityPy.load(str(out_dir / out_name))
        en_c = Counter(o.type.name for o in en_env.objects)
        es_c = Counter(o.type.name for o in es_env.objects)
        for typ, count in expected.items():
            if es_c.get(typ, 0) != count:
                errors.append(f"{out_name}: {typ} count {es_c.get(typ)} != {count}")
        if out_name == OUT_LOCALES:
            names = [o.read_typetree().get("m_Name") for o in es_env.objects if o.type.name == "MonoBehaviour"]
            if names != ["Spanish (es)"]:
                errors.append(f"{out_name}: locale names {names}")
        if out_name == OUT_STRINGS:
            for o in es_env.objects:
                if o.type.name == "MonoBehaviour":
                    t = o.read_typetree()
                    if t.get("m_Name") == "Translation_es":
                        if t.get("m_LocaleId") != {"m_Code": "es"}:
                            errors.append("Translation_es locale id")
                        sample = t["m_TableData"][0]["m_Localized"]
                        if use_test_strings and not sample.startswith("ES: "):
                            errors.append(f"string patch failed: {sample[:40]!r}")
                        if use_test_strings and "á" not in sample:
                            errors.append("accent round-trip failed on string table")
                        ref = strings.get(int(t["m_TableData"][0]["m_Id"]), "")
                        if t["m_TableData"][0]["m_Localized"] != ref:
                            errors.append("string table id0 mismatch source")
        if out_name == OUT_ASSET_TABLES:
            for o in es_env.objects:
                if o.type.name == "MonoBehaviour":
                    t = o.read_typetree()
                    if t.get("m_Name") == "Image_es":
                        en_t = None
                        for o2 in en_env.objects:
                            if o2.type.name == "MonoBehaviour":
                                en_t = o2.read_typetree()
                                if en_t.get("m_Name") == "Image_en":
                                    break
                        if en_t and t["m_TableData"][0]["m_Localized"] != en_t["m_TableData"][0]["m_Localized"]:
                            errors.append("Image_es GUID should match Image_en entry0")
        if out_name == OUT_ASSETS:
            tas = [o.read().m_Name for o in es_env.objects if o.type.name == "TextAsset"]
            if not all(n.endswith("_ES") for n in tas):
                errors.append(f"TextAsset names not all _ES: {tas[:3]}")
            if len(tas) != 53:
                errors.append(f"TextAsset count {len(tas)}")
            # JSON accent check
            if use_test_strings:
                for o in es_env.objects:
                    if o.type.name == "TextAsset":
                        raw = o.read().m_Script
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8-sig")
                        if "áéíóúñ" in raw:
                            break
                else:
                    errors.append("no Spanish accents found in TextAsset JSON")

    if errors:
        print("SELF-TEST FAILED:")
        for e in errors:
            print(" ", e)
        return 1
    print("SELF-TEST OK")
    return 0


def build_all(out_dir: Path, source_path: Path) -> int:
    strings, scripts, _ = load_translation_source(source_path)
    meta = [
        build_locales_bundle(out_dir),
        build_string_tables_bundle(out_dir, strings),
        build_asset_tables_bundle(out_dir),
        build_assets_bundle(out_dir, scripts),
    ]
    write_bundle_map(out_dir)
    write_bundle_hashes(out_dir, meta)
    write_guid_map(out_dir)
    print("Built bundles:")
    for m in meta:
        print(f"  {m['file']} objects={m['object_count']} hash={m['catalog_hash']} internal={m['internal_bundle_name']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Spanish localization AssetBundles for Dusk City")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="es_source.json path")
    parser.add_argument(
        "--write-test-source",
        action="store_true",
        help=f"Write {DEFAULT_OUT / 'es_source_test.json'} and exit",
    )
    parser.add_argument(
        "--use-test-source",
        action="store_true",
        help="Build using out/es_source_test.json (implies --write-test-source first if missing)",
    )
    parser.add_argument("--self-test", action="store_true", help="Verify output bundles after build")
    parser.add_argument(
        "--hijack-en",
        action="store_true",
        help="Write Spanish into English-named bundles (phase-1 en slot patch)",
    )
    args = parser.parse_args(argv)

    if args.hijack_en and args.out == DEFAULT_OUT:
        args.out = DEFAULT_HIJACK_OUT

    test_source = args.out / "es_source_test.json"
    if args.write_test_source:
        make_test_source(args.source, test_source)
        if not args.use_test_source and not args.self_test:
            return 0

    source = args.source
    if args.use_test_source:
        if not test_source.exists():
            make_test_source(args.source, test_source)
        source = test_source

    if args.hijack_en:
        rc = build_all_hijack(args.out, source)
        if args.self_test:
            rc = self_test_hijack(args.out, source, use_test_strings=args.use_test_source) or rc
    else:
        rc = build_all(args.out, source)
        if args.self_test:
            rc = self_test(args.out, source, use_test_strings=args.use_test_source) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
