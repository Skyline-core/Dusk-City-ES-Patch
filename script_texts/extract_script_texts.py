#!/usr/bin/env python3
"""Extract translatable GameScript literals from active Addressables bundles.

Read-only on game data. Writes:
  translation/es_source_scripts.json
  translation/research/script_refs.json

Requires DUSK_GAME_PATH (game root). Uses translation/research/gamescripts_survey.json
to find candidate bundles, filtered by aa/catalog.json.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import UnityPy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "catalog_tool"))
from catalog_data import Catalog  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
CATALOG_PATH = AA / "catalog.json"
SURVEY_PATH = ROOT / "research" / "gamescripts_survey.json"
OUT_SOURCE = ROOT / "es_source_scripts.json"
OUT_REFS = ROOT / "research" / "script_refs.json"

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
VOICE_ID = re.compile(r"^[a-z]{2,4}\d{3,5}$", re.I)
VOICE_ID_DLC = re.compile(r"^DLC\d+_[a-z]+\d+$", re.I)
KIND_ORDER = {"say": 0, "speaker": 1, "choice": 2, "item": 3, "other": 4}

# (cmd, tok) -> kind; tok None means "all string tokens matching rule"
RULES: list[tuple[str, int | None, str]] = [
    ("say", None, "say"),
    ("add_speaker", 4, "speaker"),
    ("set_speaker", 2, "speaker"),
    ("add_choice_option", 2, "choice"),
    ("itemName", 2, "item"),
]


def catalog_bundle_index(cat: Catalog) -> dict[str, dict[str, Any]]:
    """filename -> {relpath, crc, internal_id}."""
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


def index_bundle_paths() -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not AA.is_dir():
        return out
    for p in AA.rglob("*.bundle"):
        out[p.name] = p
    return out


def command_name(tokens: list[dict]) -> str:
    if not tokens:
        return ""
    return str(tokens[0].get("Literal") or "")


def is_voice_id(text: str) -> bool:
    return bool(VOICE_ID.match(text) or VOICE_ID_DLC.match(text))


def classify_literal(cmd: str, tok: int, text: str) -> str | None:
    if not text:
        return None
    for rule_cmd, rule_tok, kind in RULES:
        if cmd != rule_cmd:
            continue
        if rule_tok is not None and tok != rule_tok:
            continue
        if kind == "say":
            if is_voice_id(text):
                return None
            return "say"
        return kind
    return None


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
    script_name: str
    line: int
    tok: int
    cmd: str
    text: str
    kind: str


def extract_bundle(relpath: str, path: Path) -> list[Hit]:
    hits: list[Hit] = []
    env = UnityPy.load(str(path))
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        cmds = tree.get("m_commandDatas")
        if not isinstance(cmds, list):
            continue
        script_name = str(tree.get("m_Name") or "")
        for li, ln in enumerate(cmds):
            toks = ln.get("tokens") or []
            cmd = command_name(toks)
            for ti, tk in enumerate(toks):
                if tk.get("Type") != 46:
                    continue
                text = tk.get("Literal") or ""
                kind = classify_literal(cmd, ti, text)
                if not kind:
                    continue
                hits.append(
                    Hit(relpath, o.path_id, script_name, li, ti, cmd, text, kind)
                )
    return hits


def neighbour_context(cmds: list, line: int) -> str:
    parts: list[str] = []
    for off in (-1, 1):
        j = line + off
        if 0 <= j < len(cmds):
            toks = cmds[j].get("tokens") or []
            cmd = command_name(toks)
            if cmd == "say":
                for tk in toks:
                    if tk.get("Type") == 46 and not is_voice_id(tk.get("Literal") or ""):
                        parts.append((tk.get("Literal") or "")[:120])
                        break
    return " | ".join(parts)[:240]


def find_gamescript_tree(env: UnityPy.Environment, path_id: int) -> dict | None:
    """path_id repeats across dependency CABs; only the GameScript MonoBehaviour counts."""
    for o in env.objects:
        if o.type.name != "MonoBehaviour" or o.path_id != path_id:
            continue
        try:
            tree = o.read_typetree()
        except Exception:
            continue
        if isinstance(tree.get("m_commandDatas"), list):
            return tree
    return None


def verify_ref(path: Path, path_id: int, line: int, tok: int, expected: str) -> bool:
    env = UnityPy.load(str(path))
    tree = find_gamescript_tree(env, path_id)
    if tree is None:
        return False
    cmds = tree.get("m_commandDatas") or []
    if line >= len(cmds):
        return False
    toks = cmds[line].get("tokens") or []
    if tok >= len(toks):
        return False
    return (toks[tok].get("Literal") or "") == expected


def scan_other_mono_texts(paths: list[Path], limit_per_bundle: int = 40) -> dict[str, Any]:
    """Sample string fields outside m_commandDatas (report only)."""
    EN = re.compile(r"[A-Za-z]{4,}.*[ .!?]|[A-Za-z]{10,}")
    categories: Counter[str] = Counter()
    samples: list[dict] = []

    for path in paths:
        try:
            env = UnityPy.load(str(path))
        except Exception:
            continue
        n = 0
        for o in env.objects:
            if o.type.name not in ("MonoBehaviour", "GameObject"):
                continue
            try:
                tree = o.read_typetree()
            except Exception:
                continue
            if "m_commandDatas" in tree:
                continue

            def walk(obj: Any, prefix: str) -> None:
                nonlocal n
                if n >= limit_per_bundle:
                    return
                if isinstance(obj, str) and len(obj) > 2 and EN.search(obj):
                    if JP.search(obj):
                        return
                    cat = prefix.split(".")[0] if prefix else "str"
                    categories[cat] += 1
                    if len(samples) < 60:
                        samples.append(
                            {
                                "bundle": path.name,
                                "path_id": o.path_id,
                                "field": prefix,
                                "text": obj[:100],
                            }
                        )
                    n += 1
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == "m_commandDatas":
                            continue
                        walk(v, f"{prefix}.{k}" if prefix else k)
                elif isinstance(obj, list):
                    for i, v in enumerate(obj[:50]):
                        walk(v, f"{prefix}[{i}]")

            walk(tree, o.type.name)
    return {"categories": dict(categories), "samples": samples}


def command_classification_stats(hits: list[Hit]) -> dict[str, Any]:
    """Stats for README command table."""
    by_cmd_tok: Counter[tuple[str, int]] = Counter()
    trans_by_cmd: Counter[str] = Counter()
    for h in hits:
        by_cmd_tok[(h.cmd, h.tok)] += 1
        trans_by_cmd[h.cmd] += 1
    return {"by_cmd_tok": {f"{c}@{t}": n for (c, t), n in by_cmd_tok.most_common()}, "trans_by_cmd": dict(trans_by_cmd)}


def main() -> int:
    if not CATALOG_PATH.is_file():
        print(f"Missing catalog: {CATALOG_PATH}", file=sys.stderr)
        return 1
    if not SURVEY_PATH.is_file():
        print(f"Missing survey: {SURVEY_PATH}", file=sys.stderr)
        return 1

    cat = Catalog.load_json(str(CATALOG_PATH))
    cat_idx = catalog_bundle_index(cat)
    disk = index_bundle_paths()
    survey = json.loads(SURVEY_PATH.read_text(encoding="utf-8"))

    bundle_names = [b["bundle"] for b in survey if b["bundle"] in cat_idx and b["bundle"] in disk]
    bundle_names = sorted(set(bundle_names))
    print(f"Active GameScript bundles (catalog + on disk): {len(bundle_names)}")

    all_hits: list[Hit] = []
    for bname in bundle_names:
        meta = cat_idx[bname]
        relpath = meta["relpath"]
        path = disk[bname]
        all_hits.extend(extract_bundle(relpath, path))

    print(f"Translatable literal hits: {len(all_hits)}")

    en_to_ja = load_en_to_ja()

    # Dedupe by (kind, en)
    groups: dict[tuple[str, str], list[Hit]] = defaultdict(list)
    for h in all_hits:
        groups[(h.kind, h.text)].append(h)

    # Assign ids sorted by anchor script name
    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: (
            min(h.script_name.lower() for h in groups[k]),
            KIND_ORDER.get(k[0], 9),
            k[1],
        ),
    )

    texts: list[dict] = []
    refs: dict[str, Any] = {"_bundles": {}}
    bundles_used: set[str] = set()

    # Cache cmds per line for context (load on demand)
    script_cache: dict[tuple[str, int], list] = {}

    def get_cmds(relpath: str, path_id: int) -> list:
        key = (relpath, path_id)
        if key in script_cache:
            return script_cache[key]
        fname = Path(relpath).name
        path = disk[fname]
        env = UnityPy.load(str(path))
        tree = find_gamescript_tree(env, path_id)
        cmds = (tree.get("m_commandDatas") or []) if tree else []
        script_cache[key] = cmds
        return cmds

    next_id = 1
    verify_errors: list[str] = []

    for kind, en in sorted_keys:
        hits = groups[(kind, en)]
        cmds_set = sorted({h.cmd for h in hits})
        anchor = min(hits, key=lambda h: (h.script_name.lower(), h.line, h.tok))
        ctx = ""
        try:
            cmds = get_cmds(anchor.relpath, anchor.path_id)
            ctx = f"{anchor.script_name}: " + neighbour_context(cmds, anchor.line)
        except Exception:
            ctx = anchor.script_name

        ja = en_to_ja.get(en, "")
        if not ja and JP.search(en):
            ja = en

        tid = next_id
        next_id += 1
        texts.append(
            {
                "id": tid,
                "kind": kind,
                "cmds": cmds_set,
                "uses": len(hits),
                "en": en,
                "ja": ja,
                "context": ctx.strip(),
                "es": "",
            }
        )

        ref_list: list[list[Any]] = []
        for h in hits:
            fname = Path(h.relpath).name
            path = disk[fname]
            if not verify_ref(path, h.path_id, h.line, h.tok, en):
                verify_errors.append(
                    f"id {tid} {h.relpath} pid={h.path_id} {h.line}/{h.tok}"
                )
            ref_list.append([h.relpath, h.path_id, h.line, h.tok])
            bundles_used.add(h.relpath)
        refs[str(tid)] = ref_list

    for relpath in sorted(bundles_used):
        fname = Path(relpath).name
        meta = cat_idx[fname]
        refs["_bundles"][relpath] = {
            "crc": meta["crc"],
            "internal_id": meta["internal_id"],
        }

    meta = {
        "note": "Fill 'es' for each entry. Keep markup/tags identical to 'en'. "
        "Kinds: say (dialogue), speaker (add_speaker/set_speaker display names), "
        "choice (add_choice_option), item (itemName). Voice ids in say() are excluded.",
        "count": len(texts),
        "total_uses": len(all_hits),
        "bundles": len(bundles_used),
        "by_kind": dict(Counter(t["kind"] for t in texts)),
    }

    OUT_SOURCE.write_text(
        json.dumps({"meta": meta, "texts": texts}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    OUT_REFS.write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Wrote {OUT_SOURCE} ({len(texts)} unique texts, {len(all_hits)} uses, {len(bundles_used)} bundles)")
    print(f"Wrote {OUT_REFS}")
    print(f"By kind: {meta['by_kind']}")

    if verify_errors:
        print(f"VERIFY ERRORS: {len(verify_errors)}", file=sys.stderr)
        for e in verify_errors[:20]:
            print(" ", e, file=sys.stderr)
        return 1

    # Sample scan for non-GameScript English (first 80 bundles)
    sample_paths = [disk[n] for n in bundle_names[:80]]
    other = scan_other_mono_texts(sample_paths)
    sidecar = HERE / "other_text_scan.json"
    sidecar.write_text(json.dumps(other, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Other-text sample scan -> {sidecar} categories={other['categories']}")

    stats = command_classification_stats(all_hits)
    (HERE / "extraction_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
