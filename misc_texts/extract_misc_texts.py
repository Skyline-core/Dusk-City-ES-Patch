#!/usr/bin/env python3
"""Extract misc player-visible strings from candidates.json (bundle locations only).

Writes:
  translation/es_source_misc.json
  translation/es_source_misc.original_vacio.json
  translation/research/misc_refs.json

Set DUSK_GAME_PATH to the game install root (read-only).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import UnityPy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "catalog_tool"))

from catalog_data import Catalog  # noqa: E402
from mt_common import (  # noqa: E402
    JP,
    build_script_map,
    classify_kind,
    has_localize_on_same_go,
    inclusion_decision,
    load_en_to_ja,
    load_translation_en_keys,
    read_string,
    split_field,
)

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
CATALOG_PATH = AA / "catalog.json"
CANDIDATES = ROOT / "research" / "remaining_text" / "candidates.json"
OUT_SOURCE = ROOT / "es_source_misc.json"
OUT_ORIGINAL = ROOT / "es_source_misc.original_vacio.json"
OUT_REFS = ROOT / "research" / "misc_refs.json"
ID_START = 200000


def catalog_bundle_index(cat: Catalog) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for loc in cat.locations:
        d = loc.extra_data.get("data") if isinstance(loc.extra_data, dict) else None
        if not d or "m_Crc" not in d:
            continue
        parts = loc.internal_id.split("\\")
        fname = parts[-1]
        if not fname.endswith(".bundle"):
            continue
        try:
            idx = next(i for i, p in enumerate(parts) if p == "StandaloneWindows64")
            start = idx - 1 if idx > 0 and parts[idx - 1] in ("DLC1", "DLC2") else idx
            relpath = "/".join(parts[start:])
        except StopIteration:
            relpath = fname
        out[fname] = {
            "relpath": relpath,
            "crc": int(d["m_Crc"]),
            "internal_id": loc.internal_id,
        }
    return out


def verify_location(
    env: UnityPy.Environment,
    script_map: dict[int, str],
    path_id: int,
    path: list[Any],
    field: str,
    expected: str,
    check_localize: bool,
) -> tuple[bool, str]:
    monos = [o for o in env.objects if o.type.name == "MonoBehaviour" and o.path_id == path_id]
    if not monos:
        return False, "missing_path_id"
    for o in monos:
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        cur = read_string(tree, path, field)
        if cur == expected:
            if check_localize and has_localize_on_same_go(env, script_map, path_id):
                return False, "localize_string_event"
            return True, ""
    return False, "literal_mismatch"


def main() -> int:
    if not CANDIDATES.is_file():
        print(f"Missing {CANDIDATES}", file=sys.stderr)
        return 1
    if not AA.is_dir():
        print(f"Missing aa: {AA} (set DUSK_GAME_PATH)", file=sys.stderr)
        return 1

    candidates: list[dict] = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    cat_idx: dict[str, dict[str, Any]] = {}
    if CATALOG_PATH.is_file():
        cat_idx = catalog_bundle_index(Catalog.load_json(str(CATALOG_PATH)))

    en_to_ja = load_en_to_ja(ROOT)
    tr_keys = load_translation_en_keys(ROOT)

    skipped: list[dict[str, str]] = []
    non_bundle: list[dict[str, str]] = []
    included_rows: list[dict[str, Any]] = []

    for entry in candidates:
        ok, reason = inclusion_decision(entry)
        if not ok:
            if reason == "non_bundle_asset":
                non_bundle.append(
                    {
                        "class": entry.get("class", ""),
                        "field": entry.get("field", ""),
                        "text": (entry.get("text") or "")[:80],
                        "reason": reason,
                    }
                )
            else:
                skipped.append(
                    {
                        "category": entry.get("category", ""),
                        "class": entry.get("class", ""),
                        "text": (entry.get("text") or "")[:80],
                        "reason": reason,
                    }
                )
            continue

        en = entry["text"]
        if en in tr_keys:
            skipped.append(
                {
                    "category": entry.get("category", ""),
                    "class": entry.get("class", ""),
                    "text": en[:80],
                    "reason": "translation_en_key",
                }
            )
            continue

        path, field = split_field(entry["field"])
        check_loc = entry.get("class") == "TMPro.TextMeshProUGUI" or entry.get("field") == "m_text"
        verified_refs: list[list[Any]] = []

        by_bundle: dict[str, list[dict]] = defaultdict(list)
        for loc in entry.get("locations") or []:
            by_bundle[loc["file"]].append(loc)

        env_cache: dict[str, UnityPy.Environment] = {}
        sm_cache: dict[str, dict[int, str]] = {}

        for relpath, locs in by_bundle.items():
            bpath = AA / Path(relpath.replace("/", os.sep))
            if not bpath.is_file():
                continue
            if relpath not in env_cache:
                env_cache[relpath] = UnityPy.load(str(bpath))
                sm_cache[relpath] = build_script_map(env_cache[relpath])
            env = env_cache[relpath]
            sm = sm_cache[relpath]
            for loc in locs:
                pid = int(loc["path_id"])
                good, why = verify_location(env, sm, pid, path, field, en, check_loc)
                if good:
                    verified_refs.append([relpath, pid, path, field])
                elif why == "localize_string_event":
                    skipped.append(
                        {
                            "category": entry.get("category", ""),
                            "class": entry.get("class", ""),
                            "text": en[:80],
                            "reason": "localize_string_event",
                        }
                    )
                    verified_refs = []
                    break

        if not verified_refs:
            if not any(s.get("text", "").startswith(en[:40]) and s.get("reason") == "localize_string_event" for s in skipped):
                skipped.append(
                    {
                        "category": entry.get("category", ""),
                        "class": entry.get("class", ""),
                        "text": en[:80],
                        "reason": "verify_failed",
                    }
                )
            continue

        included_rows.append(
            {
                "entry": entry,
                "path": path,
                "field": field,
                "refs": verified_refs,
            }
        )

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in included_rows:
        groups[row["entry"]["text"]].append(row)

    texts: list[dict] = []
    refs: dict[str, Any] = {"_bundles": {}}
    bundles_used: set[str] = set()
    next_id = ID_START

    for en in sorted(groups.keys(), key=lambda s: (classify_kind("", groups[s][0]["entry"].get("class", ""), ""), s.lower())):
        rows = groups[en]
        anchor = rows[0]
        ent = anchor["entry"]
        kind = classify_kind(ent["category"], ent["class"], ent["field"])
        all_refs: list[list[Any]] = []
        for r in rows:
            all_refs.extend(r["refs"])
        uses = len(all_refs)
        ctx = f"{ent['class']}.{ent['field']}"
        ja = en_to_ja.get(en, "")
        if not ja and JP.search(en):
            ja = en

        tid = next_id
        next_id += 1
        texts.append(
            {
                "id": tid,
                "kind": kind,
                "cmds": [ent["class"]],
                "uses": uses,
                "en": en,
                "ja": ja,
                "context": ctx,
                "es": "",
            }
        )
        refs[str(tid)] = all_refs
        for ref in all_refs:
            bundles_used.add(ref[0])

    for relpath in sorted(bundles_used):
        fname = Path(relpath).name
        meta = cat_idx.get(fname)
        if meta:
            refs["_bundles"][relpath] = {
                "crc": meta["crc"],
                "internal_id": meta["internal_id"],
            }

    no_crc = sorted(bundles_used - set(refs["_bundles"].keys()))
    skip_by_reason = Counter(s["reason"] for s in skipped)
    meta = {
        "note": "Fill 'es' for each entry. IDs start at 200000. Patch via inject_misc_texts.py.",
        "count": len(texts),
        "total_uses": sum(t["uses"] for t in texts),
        "bundles": len(bundles_used),
        "by_kind": dict(Counter(t["kind"] for t in texts)),
        "id_start": ID_START,
        "skipped_count": len(skipped),
        "skipped_by_reason": dict(skip_by_reason),
        "non_bundle_listed": len(non_bundle),
        "candidates_total": len(candidates),
        "bundles_without_catalog_crc": no_crc,
        "bundles_with_catalog_crc": len(refs["_bundles"]),
    }

    doc = {"meta": meta, "texts": texts}
    OUT_SOURCE.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_ORIGINAL.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_REFS.write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")

    report_path = HERE / "extract_report.json"
    report_path.write_text(
        json.dumps(
            {
                "skipped_sample": skipped[:120],
                "non_bundle": non_bundle,
                "meta": meta,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUT_SOURCE} ({len(texts)} unique, {meta['total_uses']} uses)")
    print(f"Wrote {OUT_REFS} ({len(bundles_used)} bundles)")
    print(f"By kind: {meta['by_kind']}")
    print(f"Skipped: {len(skipped)} ({dict(skip_by_reason)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
