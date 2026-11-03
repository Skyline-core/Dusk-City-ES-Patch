#!/usr/bin/env python3
"""One-off: locate DialogueChoise / ChoiseButton prefabs in Addressables bundles."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import UnityPy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "catalog_tool"))
from catalog_data import Catalog  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
CATALOG = AA / "catalog.json"


def is_dialogue_choise(tree: dict) -> bool:
    keys = set(tree.keys())
    return {"buttonPrefab", "entryPerPage", "scrollThreshold"}.issubset(keys)


def is_choise_button(tree: dict) -> bool:
    keys = set(tree.keys())
    return {"button", "text", "uiSound", "highlightMaterial"}.issubset(keys)


def is_tmp_label(tree: dict) -> bool:
    return "m_text" in tree and "m_fontSize" in tree


def scan_bundle(relpath: str, bundle_path: Path) -> list[dict]:
    hits: list[dict] = []
    try:
        env = UnityPy.load(str(bundle_path))
    except Exception as e:
        return [{"relpath": relpath, "error": str(e)}]
    for o in env.objects:
        if o.type.name not in ("MonoBehaviour", "GameObject", "PrefabInstance"):
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        if not isinstance(tree, dict):
            continue
        if is_dialogue_choise(tree):
            hits.append(
                {
                    "kind": "DialogueChoise",
                    "relpath": relpath,
                    "path_id": o.path_id,
                    "name": tree.get("m_Name"),
                    "entryPerPage": tree.get("entryPerPage"),
                    "buttonPrefab": tree.get("buttonPrefab"),
                }
            )
        elif is_choise_button(tree):
            hits.append(
                {
                    "kind": "ChoiseButton",
                    "relpath": relpath,
                    "path_id": o.path_id,
                    "name": tree.get("m_Name"),
                    "text_ref": tree.get("text"),
                }
            )
    return hits


def main() -> None:
    cat = Catalog.load(CATALOG)
    bundle_entries: dict[str, str] = {}
    for loc in cat.locations:
        iid = loc.internal_id.replace("\\", "/")
        if "StandaloneWindows64/" in iid and iid.endswith(".bundle"):
            name = Path(iid).name
            bundle_entries[name] = iid

    # Also search catalog keys for UI hints
    ui_keys = []
    for loc in cat.locations:
        pk = loc.primary_key
        if isinstance(pk, str) and any(
            x in pk.lower() for x in ("choise", "choice", "dialogue", "novel", "bench")
        ):
            ui_keys.append((pk, loc.internal_id))

    print(f"catalog bundles: {len(bundle_entries)}")
    print(f"ui-ish catalog keys: {len(ui_keys)}")
    for pk, iid in sorted(ui_keys)[:40]:
        print(f"  KEY {pk!r} -> {iid}")

    all_hits: list[dict] = []
    aa_dir = AA / "StandaloneWindows64"
    for name in sorted(bundle_entries):
        p = aa_dir / name
        if not p.is_file():
            continue
        hits = scan_bundle(f"StandaloneWindows64/{name}", p)
        all_hits.extend(hits)

    out = ROOT / "ui_layout" / "_choise_scan.json"
    out.write_text(json.dumps(all_hits, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"hits: {len(all_hits)} written to {out}")
    for h in all_hits[:20]:
        print(h)


if __name__ == "__main__":
    main()
