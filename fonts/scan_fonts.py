"""Scan Unity game assets for fonts and Spanish glyph coverage."""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import UnityPy
from UnityPy.enums import ClassIDType

GAME_ROOT = Path(r"E:\Users\ah_3m\Documents\gits\Dusk City")
DATA = GAME_ROOT / "Dusk City_Data"
OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SPANISH_CHARS = "áéíóúüñÁÉÍÓÚÜÑ¿¡«»…—'\""  # noqa: W605
SPANISH_CODEPOINTS = {ord(c): c for c in SPANISH_CHARS}

FONT_KEY_RE = re.compile(
    r"font|sdf|tmp|noto|mplus|\.ttf|\.otf|textmesh|glyph",
    re.I,
)


def catalog_font_bundles(catalog_path: Path) -> dict[str, list[str]]:
    """Map bundle file name -> list of internal asset paths matching font patterns."""
    with open(catalog_path, encoding="utf-8") as f:
        data = json.load(f)

    # Addressables JSON catalog: m_LocatorId + serialized buckets in m_LocationLists etc.
    # Use raw string search on internal IDs from decoded structure if available.
    bundle_hits: dict[str, set[str]] = {}

    def walk(obj: Any, ctx: dict | None = None) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, ctx)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, ctx)
        elif isinstance(obj, str):
            if FONT_KEY_RE.search(obj) and (".bundle" in obj.lower() or "assets/" in obj.lower()):
                if "assets/" in obj.lower() and FONT_KEY_RE.search(obj):
                    # will pair with bundle via separate pass
                    pass

    # Parse via catalog_tool if present
    sys.path.insert(0, str(GAME_ROOT / "translation" / "catalog_tool"))
    try:
        from catalog_data import load_catalog_json  # type: ignore

        catalog = load_catalog_json(catalog_path)
        for loc in catalog.locations:
            internal = loc.internal_id or ""
            primary = str(loc.primary_key) if loc.primary_key is not None else ""
            text = f"{internal} {primary}"
            if not FONT_KEY_RE.search(text):
                continue
            # resolve bundle from dependency
            dep = loc.dependency_key
            bundle_name = ""
            if isinstance(dep, str) and dep.endswith(".bundle"):
                bundle_name = dep
            elif isinstance(dep, dict):
                bundle_name = str(dep.get("m_BundleName", "") or dep.get("bundle", ""))
            if not bundle_name and "bundle" in internal.lower():
                bundle_name = Path(internal.replace("\\", "/")).name
            if bundle_name:
                bundle_hits.setdefault(bundle_name, set()).add(internal or primary)
    except Exception as e:
        print(f"catalog_data load failed: {e}", file=sys.stderr)
        # fallback: grep catalog json strings
        raw = json.dumps(data)
        for m in re.finditer(r'"internal_id"\s*:\s*"([^"]+)"', raw):
            s = m.group(1)
            if FONT_KEY_RE.search(s):
                bundle_hits.setdefault("(unknown)", set()).add(s)

    return {k: sorted(v) for k, v in bundle_hits.items()}


def static_asset_files() -> list[Path]:
    paths: list[Path] = []
    for pattern in [
        "globalgamemanagers*",
        "resources.assets",
        "sharedassets*.assets",
        "sharedassets*.resource",
    ]:
        paths.extend(DATA.glob(pattern))
    return sorted(set(paths))


def bundle_paths_from_catalog(catalog_path: Path) -> list[Path]:
    aa = DATA / "StreamingAssets" / "aa"
    bundles: set[Path] = set()
    # named bundles from font catalog hits
    hits = catalog_font_bundles(catalog_path)
    for name in hits:
        if name == "(unknown)":
            continue
        for base in [aa / "StandaloneWindows64", aa / "DLC1" / "StandaloneWindows64"]:
            p = base / name
            if p.is_file():
                bundles.add(p)
                break
            # hash-only name
            stem = name.replace(".bundle", "")
            if len(stem) == 32 and all(c in "0123456789abcdef" for c in stem.lower()):
                p2 = base / name
                if p2.is_file():
                    bundles.add(p2)
    # Also scan bundle filenames containing font keywords (fast filename filter)
    for base in [aa / "StandaloneWindows64", aa / "DLC1" / "StandaloneWindows64"]:
        if not base.is_dir():
            continue
        for p in base.glob("*.bundle"):
            if FONT_KEY_RE.search(p.name):
                bundles.add(p)
        for p in base.glob("*font*.bundle"):
            bundles.add(p)
        for p in base.glob("*sdf*.bundle"):
            bundles.add(p)
    return sorted(bundles)


def atlas_mode_name(v: int | None) -> str:
    # TMP_AtlasPopulationMode: Static=0, Dynamic=1
    if v == 0:
        return "Static"
    if v == 1:
        return "Dynamic"
    return f"Unknown({v})"


def get_typetree_field(tree: dict, *names: str) -> Any:
    for n in names:
        if n in tree:
            return tree[n]
    return None


def extract_char_codepoints(tree: dict) -> set[int]:
    cps: set[int] = set()
    table = get_typetree_field(tree, "m_CharacterTable")
    if isinstance(table, list):
        for row in table:
            if isinstance(row, dict):
                u = row.get("m_Unicode")
                if u is not None:
                    cps.add(int(u))
    return cps


def is_tmp_font_asset(obj) -> bool:
    if obj.type.name == "MonoBehaviour":
        try:
            tree = obj.read_typetree()
            sn = tree.get("m_Script", {})
            if isinstance(sn, dict):
                name = sn.get("m_Name") or sn.get("name") or ""
                if name == "TMP_FontAsset":
                    return True
            # fallback: has m_CharacterTable
            if "m_CharacterTable" in tree and "m_FaceInfo" in tree:
                return True
        except Exception:
            pass
    if obj.type.name == "TMP_FontAsset":
        return True
    return False


def analyze_container(container_path: str) -> list[dict]:
    results: list[dict] = []
    try:
        env = UnityPy.load(container_path)
    except Exception as e:
        return [{"error": str(e), "container": container_path}]

    for obj in env.objects:
        try:
            if obj.type == ClassIDType.Font:
                data = obj.read()
                name = getattr(data, "m_Name", "") or obj.read_typetree().get("m_Name", "")
                font_bytes = getattr(data, "m_FontData", b"") or b""
                results.append(
                    {
                        "kind": "Font",
                        "name": name,
                        "container": container_path,
                        "path_id": obj.path_id,
                        "font_data_size": len(font_bytes),
                    }
                )
            elif is_tmp_font_asset(obj):
                tree = obj.read_typetree()
                name = tree.get("m_Name", "")
                pop = get_typetree_field(tree, "m_AtlasPopulationMode")
                if pop is None:
                    pop = get_typetree_field(tree, "atlasPopulationMode")
                source = get_typetree_field(tree, "m_SourceFontFileGUID", "sourceFontFileGUID")
                source_name = get_typetree_field(tree, "m_SourceFontFile", "sourceFontFile")
                embedded = get_typetree_field(tree, "m_SourceFontFile_EditorRef", "sourceFontFile_EditorRef")
                cps = extract_char_codepoints(tree)
                fallbacks = get_typetree_field(tree, "m_FallbackFontAssetTable", "fallbackFontAssets")
                fb_names: list[str] = []
                if isinstance(fallbacks, list):
                    for fb in fallbacks:
                        if isinstance(fb, dict):
                            fb_names.append(str(fb.get("m_Name") or fb.get("name") or fb))
                        else:
                            fb_names.append(str(fb))
                missing = {c: cp for cp, c in SPANISH_CODEPOINTS.items() if cp not in cps}
                results.append(
                    {
                        "kind": "TMP_FontAsset",
                        "name": name,
                        "container": container_path,
                        "path_id": obj.path_id,
                        "atlas_mode": atlas_mode_name(pop if isinstance(pop, int) else None),
                        "atlas_population_mode_raw": pop,
                        "glyph_count": len(cps),
                        "spanish_missing": "".join(missing[c] for c in SPANISH_CHARS if ord(c) in missing),
                        "spanish_present": "".join(c for c in SPANISH_CHARS if ord(c) in cps),
                        "fallbacks": fb_names,
                        "source_font_hint": str(source_name or source or embedded or ""),
                    }
                )
            elif obj.type.name == "MonoBehaviour":
                tree = obj.read_typetree()
                sn = tree.get("m_Script", {})
                script_name = ""
                if isinstance(sn, dict):
                    script_name = sn.get("m_Name") or ""
                if script_name in ("TMP_Settings", "TextMeshProSettings"):
                    results.append(
                        {
                            "kind": "TMP_Settings",
                            "name": script_name,
                            "container": container_path,
                            "path_id": obj.path_id,
                            "tree_keys": list(tree.keys())[:30],
                            "default_font": tree.get("m_defaultFontAsset") or tree.get("defaultFontAsset"),
                            "fallback_fonts": tree.get("m_fallbackFontAssets") or tree.get("fallbackFontAssets"),
                        }
                    )
        except Exception:
            continue
    return results


def check_ttf_cmap(font_bytes: bytes, name: str) -> dict:
    try:
        from fontTools.ttLib import TTFont
        import io

        tt = TTFont(io.BytesIO(font_bytes))
        cps: set[int] = set()
        for table in tt["cmap"].tables:
            cps.update(table.cmap.keys())
        missing = {c: ord(c) for c in SPANISH_CHARS if ord(c) not in cps}
        return {
            "ttf_name": name,
            "cmap_size": len(cps),
            "spanish_missing": "".join(missing.keys()),
            "spanish_present": "".join(c for c in SPANISH_CHARS if ord(c) in cps),
        }
    except Exception as e:
        return {"ttf_name": name, "error": str(e)}


def main() -> None:
    catalog_path = DATA / "StreamingAssets" / "aa" / "catalog.json"
    print("Catalog font bundles...")
    cat_hits = catalog_font_bundles(catalog_path)
    with open(OUT_DIR / "catalog_font_hits.json", "w", encoding="utf-8") as f:
        json.dump(cat_hits, f, indent=2, ensure_ascii=False)
    print(f"  {len(cat_hits)} bundle keys with font-like assets")

    containers: list[str] = [str(p) for p in static_asset_files()]
    bundles = bundle_paths_from_catalog(catalog_path)
    print(f"  {len(bundles)} candidate bundles (+ {len(containers)} static containers)")

    # dedupe: also add bundles referenced in catalog hits by full name search
    aa_dirs = [
        DATA / "StreamingAssets" / "aa" / "StandaloneWindows64",
        DATA / "StreamingAssets" / "aa" / "DLC1" / "StandaloneWindows64",
    ]
    for bname in cat_hits:
        if bname == "(unknown)":
            continue
        for base in aa_dirs:
            cand = base / bname
            if cand.is_file() and str(cand) not in containers:
                containers.append(str(cand))
    for b in bundles:
        if str(b) not in containers:
            containers.append(str(b))

    print(f"Scanning {len(containers)} containers...")
    all_results: list[dict] = []
    # Process in chunks with multiprocessing
    workers = min(8, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyze_container, c): c for c in containers}
        done = 0
        for fut in as_completed(futs):
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(containers)}")
            all_results.extend(fut.result())

    fonts = [r for r in all_results if r.get("kind") == "Font"]
    tmps = [r for r in all_results if r.get("kind") == "TMP_FontAsset"]
    settings = [r for r in all_results if r.get("kind") == "TMP_Settings"]
    errors = [r for r in all_results if "error" in r and "kind" not in r]

    print(f"Found Font={len(fonts)} TMP_FontAsset={len(tmps)} TMP_Settings={len(settings)}")

    # TTF cmap from embedded Font objects
    ttf_reports: list[dict] = []
    for c in containers:
        try:
            env = UnityPy.load(c)
        except Exception:
            continue
        for obj in env.objects:
            if obj.type != ClassIDType.Font:
                continue
            try:
                data = obj.read()
                fb = getattr(data, "m_FontData", b"") or b""
                if len(fb) < 100:
                    continue
                name = getattr(data, "m_Name", "") or "Font"
                rep = check_ttf_cmap(fb, name)
                rep["container"] = c
                rep["path_id"] = obj.path_id
                ttf_reports.append(rep)
            except Exception:
                pass

    summary = {
        "spanish_test_chars": SPANISH_CHARS,
        "catalog_font_bundle_count": len(cat_hits),
        "containers_scanned": len(containers),
        "font_objects": fonts,
        "tmp_font_assets": tmps,
        "tmp_settings": settings,
        "ttf_cmap": ttf_reports,
        "scan_errors": errors[:50],
    }
    with open(OUT_DIR / "font_scan_raw.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Print concise table
    print("\n=== TMP_FontAsset ===")
    for t in sorted(tmps, key=lambda x: x.get("name", "")):
        print(
            f"{t.get('name')}\t{t.get('atlas_mode')}\tglyphs={t.get('glyph_count')}\t"
            f"missing=[{t.get('spanish_missing')}]\tfb={t.get('fallbacks')}\t{t.get('container')}"
        )
    print("\n=== TTF Font ===")
    for t in ttf_reports:
        print(
            f"{t.get('ttf_name')}\tcmap={t.get('cmap_size')}\tmissing=[{t.get('spanish_missing')}]\t{t.get('container')}"
        )
    print("\n=== TMP_Settings ===")
    for s in settings:
        print(json.dumps(s, indent=2, default=str)[:2000])


if __name__ == "__main__":
    main()
