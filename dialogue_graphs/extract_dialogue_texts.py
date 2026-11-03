#!/usr/bin/env python3
"""Extract translatable dialogue-graph strings from Addressables bundles.

Read-only on game data. Writes:
  translation/es_source_dialogues.json
  translation/research/dialogue_refs.json

Set DUSK_GAME_PATH to the game install root.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import UnityPy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "catalog_tool"))
from catalog_data import Catalog  # noqa: E402
from dg_common import classify_string, is_dialogue_graph_tree, iter_graph_text_hits  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
CATALOG_PATH = AA / "catalog.json"
OUT_SOURCE = ROOT / "es_source_dialogues.json"
OUT_REFS = ROOT / "research" / "dialogue_refs.json"
ID_START = 100000

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
KIND_ORDER = {"choice": 0, "say": 1, "message": 2, "other": 3}


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


def load_en_to_ja() -> dict[str, str]:
    src_path = ROOT / "es_source.json"
    if not src_path.is_file():
        return {}
    data = json.loads(src_path.read_text(encoding="utf-8"))
    m: dict[str, str] = {}
    for sc in data.get("scripts") or []:
        for e in sc.get("entries") or []:
            en = e.get("en") or ""
            ja = e.get("ja") or ""
            if en and ja and en not in m:
                m[en] = ja
    return m


@dataclass
class Hit:
    relpath: str
    path_id: int
    graph_name: str
    rid: int
    field: str
    node_class: str
    text: str
    kind: str


def find_dialogue_graph_tree(env: UnityPy.Environment, path_id: int) -> dict | None:
    for o in env.objects:
        if o.type.name != "MonoBehaviour" or o.path_id != path_id:
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        if is_dialogue_graph_tree(tree):
            return tree
    return None


def neighbour_choice_context(tree: dict, rid: int) -> str:
    texts: list[str] = []
    refs = tree.get("references") or {}
    for entry in refs.get("RefIds") or []:
        if not isinstance(entry, dict):
            continue
        cls = (entry.get("type") or {}).get("class") or ""
        data = entry.get("data")
        if not isinstance(data, dict):
            continue
        t = data.get("text")
        if isinstance(t, str) and t.strip():
            texts.append(t.strip()[:80])
    if not texts:
        return ""
    # show a few options from same graph
    uniq = list(dict.fromkeys(texts))
    sample = uniq[:4]
    return " | ".join(sample)[:240]


def extract_bundle(relpath: str, path: Path) -> tuple[list[Hit], int]:
    hits: list[Hit] = []
    n_graphs = 0
    env = UnityPy.load(str(path))
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        if not is_dialogue_graph_tree(tree):
            continue
        n_graphs += 1
        gname = str(tree.get("m_Name") or "")
        for h in iter_graph_text_hits(tree, gname):
            hits.append(
                Hit(
                    relpath,
                    o.path_id,
                    gname,
                    h["rid"],
                    h["field"],
                    h["node_class"],
                    h["text"],
                    h["kind"],
                )
            )
    return hits, n_graphs


def verify_ref(path: Path, path_id: int, rid: int, field: str, expected: str) -> bool:
    env = UnityPy.load(str(path))
    tree = find_dialogue_graph_tree(env, path_id)
    if tree is None:
        return False
    ref_ids = (tree.get("references") or {}).get("RefIds") or []
    if rid >= len(ref_ids):
        return False
    entry = ref_ids[rid]
    if not isinstance(entry, dict):
        return False
    data = entry.get("data")
    if not isinstance(data, dict):
        return False
    cur = data.get(field)
    if field == "text" and isinstance(cur, str):
        return cur == expected
    # nested fields stored flat in hits as suffix only
    return cur == expected


def main() -> int:
    if not AA.is_dir():
        print(f"Missing aa: {AA} (set DUSK_GAME_PATH)", file=sys.stderr)
        return 1

    cat_idx: dict[str, dict[str, Any]] = {}
    if CATALOG_PATH.is_file():
        cat = Catalog.load_json(str(CATALOG_PATH))
        cat_idx = catalog_bundle_index(cat)

    bundle_paths: dict[str, Path] = {}
    for p in AA.rglob("*.bundle"):
        bundle_paths[p.relative_to(AA).as_posix()] = p

    all_hits: list[Hit] = []
    graph_monos = 0
    for relpath, path in sorted(bundle_paths.items()):
        hits, ng = extract_bundle(relpath, path)
        graph_monos += ng
        all_hits.extend(hits)

    print(f"Dialogue graph MonoBehaviours: {graph_monos}")
    print(f"Translatable field hits: {len(all_hits)}")

    en_to_ja = load_en_to_ja()
    groups: dict[tuple[str, str], list[Hit]] = defaultdict(list)
    for h in all_hits:
        groups[(h.kind, h.text)].append(h)

    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: (
            min(x.graph_name.lower() for x in groups[k]),
            KIND_ORDER.get(k[0], 9),
            k[1],
        ),
    )

    texts: list[dict] = []
    refs: dict[str, Any] = {"_bundles": {}}
    bundles_used: set[str] = set()
    tree_cache: dict[tuple[str, int], dict] = {}

    def get_tree(relpath: str, path_id: int) -> dict | None:
        key = (relpath, path_id)
        if key in tree_cache:
            return tree_cache[key]
        path = bundle_paths[relpath]
        env = UnityPy.load(str(path))
        tree = find_dialogue_graph_tree(env, path_id)
        if tree:
            tree_cache[key] = tree
        return tree

    next_id = ID_START
    trailing_pairs: list[tuple[str, str]] = []

    for kind, en in sorted_keys:
        hits = groups[(kind, en)]
        node_classes = sorted({h.node_class for h in hits})
        anchor = min(hits, key=lambda h: (h.graph_name.lower(), h.rid))
        ctx = f"{anchor.graph_name} ({anchor.node_class}.{anchor.field})"
        try:
            tree = get_tree(anchor.relpath, anchor.path_id)
            if tree:
                nb = neighbour_choice_context(tree, anchor.rid)
                if nb:
                    ctx += ": " + nb
        except Exception:
            pass

        ja = en_to_ja.get(en, "")
        if not ja and JP.search(en):
            ja = en

        tid = next_id
        next_id += 1
        texts.append(
            {
                "id": tid,
                "kind": kind,
                "cmds": node_classes,
                "uses": len(hits),
                "en": en,
                "ja": ja,
                "context": ctx.strip(),
                "es": "",
            }
        )

        ref_list: list[list[Any]] = []
        for h in hits:
            ref_list.append([h.relpath, h.path_id, h.rid, h.field])
            bundles_used.add(h.relpath)
        refs[str(tid)] = ref_list

    # trailing-space pairs hint
    en_set = {t["en"] for t in texts}
    for t in texts:
        en = t["en"]
        if en != en.rstrip() and en.rstrip() in en_set:
            trailing_pairs.append((en.rstrip(), en))
        if en != en.lstrip() and en.lstrip() in en_set:
            trailing_pairs.append((en.lstrip(), en))

    for relpath in sorted(bundles_used):
        fname = Path(relpath).name
        meta = cat_idx.get(fname)
        if meta:
            refs["_bundles"][relpath] = {
                "crc": meta["crc"],
                "internal_id": meta["internal_id"],
            }

    no_crc = sorted(r for r in bundles_used if r not in refs["_bundles"])

    meta = {
        "note": "Fill 'es' for each entry. Keep markup/tags identical to 'en'. "
        "Kinds: choice (ChoiseOptionNode / DialogueBenchChoiseOption text), "
        "message (SendGlobalEventDialogueNode). IDs start at 100000 to avoid collision with es_source_scripts.json.",
        "count": len(texts),
        "total_uses": len(all_hits),
        "bundles": len(bundles_used),
        "graph_monobehaviours": graph_monos,
        "by_kind": dict(Counter(t["kind"] for t in texts)),
        "id_start": ID_START,
        "trailing_space_pairs": trailing_pairs[:20],
        "bundles_without_catalog_crc": no_crc,
    }

    OUT_SOURCE.write_text(
        json.dumps({"meta": meta, "texts": texts}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    OUT_REFS.write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Wrote {OUT_SOURCE} ({len(texts)} unique, {len(all_hits)} uses)")
    print(f"Wrote {OUT_REFS}")
    print(f"By kind: {meta['by_kind']}")
    if trailing_pairs:
        print(f"Note: {len(trailing_pairs)} trailing/leading space variant pairs (see meta)")
    if no_crc:
        print(f"WARNING: {len(no_crc)} bundle(s) lack catalog CRC", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
