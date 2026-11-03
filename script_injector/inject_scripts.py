#!/usr/bin/env python3
"""Patch GameScript string literals (m_commandDatas) in Addressables bundles.

Reads translation/es_source_scripts.json + translation/research/script_refs.json,
writes patched bundles under translation/patch_en_slot/files/<relpath under aa>/.
Forges each output bundle's CRC32 to the original catalog m_Crc (read-only game + catalog).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import UnityPy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "bundle_builder"))
sys.path.insert(0, str(ROOT / "catalog_tool"))
sys.path.insert(0, str(ROOT / "ui_layout"))

from layout_wrap import wrap_choice  # noqa: E402
from crc_forge import Bundle, forge_file  # noqa: E402
from catalog_data import Catalog  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
DEFAULT_SOURCE = ROOT / "es_source_scripts.json"
DEFAULT_REFS = ROOT / "research" / "script_refs.json"
DEFAULT_OUT = ROOT / "patch_en_slot" / "files"
SURVEY = ROOT / "research" / "gamescripts_survey.json"
CATALOG_PATH = AA / "catalog.json"

PACKER = "lz4"
JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
TEST_SUFFIX = " áéíóúñ¿¡"


@dataclass
class PatchOp:
    text_id: int
    path_id: int
    line: int
    tok: int
    en: str
    es: str


@dataclass
class BundleJob:
    relpath: str
    src: str
    dst: str
    target_crc: int
    patches: list[PatchOp] = field(default_factory=list)


@dataclass
class BundleResult:
    relpath: str
    status: str  # ok | skip | error
    texts: int = 0
    message: str = ""


def index_bundle_relpaths() -> dict[str, str]:
    """Map bundle file name -> path relative to aa (forward slashes)."""
    out: dict[str, str] = {}
    if not AA.is_dir():
        return out
    for p in AA.rglob("*.bundle"):
        rel = p.relative_to(AA).as_posix()
        name = p.name
        if name in out and out[name] != rel:
            raise RuntimeError(f"Ambiguous bundle name {name}: {out[name]!r} vs {rel!r}")
        out[name] = rel
    return out


def catalog_crc_by_filename(cat: Catalog) -> dict[str, tuple[int, str]]:
    """filename -> (m_Crc, internal_id)."""
    out: dict[str, tuple[int, str]] = {}
    for loc in cat.locations:
        d = loc.extra_data.get("data") if isinstance(loc.extra_data, dict) else None
        if not d or "m_Crc" not in d:
            continue
        iid = loc.internal_id.replace("\\", "/")
        fname = iid.rsplit("/", 1)[-1]
        if fname.endswith(".bundle"):
            out[fname] = (int(d["m_Crc"]), loc.internal_id)
    return out


def load_inputs(source_path: Path, refs_path: Path) -> tuple[dict[int, dict], dict[str, Any]]:
    with source_path.open(encoding="utf-8") as f:
        src = json.load(f)
    texts: dict[int, dict] = {}
    for row in src.get("texts", []):
        texts[int(row["id"])] = row
    with refs_path.open(encoding="utf-8") as f:
        refs = json.load(f)
    return texts, refs


def build_jobs(
    texts: dict[int, dict],
    refs: dict[str, Any],
    out_root: Path,
) -> list[BundleJob]:
    bundles_meta: dict[str, dict] = refs.get("_bundles") or {}
    by_bundle: dict[str, list[PatchOp]] = defaultdict(list)

    for sid, row in texts.items():
        es = (row.get("es") or "").strip()
        en = row.get("en") or ""
        if not es or es == en:
            continue
        if row.get("kind") == "choice":
            es = wrap_choice(es)   # keep the auto-sized choice menu inside the screen
        key = str(sid)
        for ref in refs.get(key) or []:
            if not ref or len(ref) < 4:
                continue
            relpath, path_id, line, tok = ref[0], int(ref[1]), int(ref[2]), int(ref[3])
            by_bundle[relpath].append(
                PatchOp(int(sid), path_id, line, tok, en, es)
            )

    jobs: list[BundleJob] = []
    for relpath, patches in sorted(by_bundle.items()):
        meta = bundles_meta.get(relpath) or {}
        target_crc = int(meta.get("crc") or 0)
        if not target_crc:
            raise RuntimeError(f"No catalog CRC in script_refs _bundles for {relpath!r}")
        src = AA / Path(relpath.replace("/", os.sep))
        dst = out_root / Path(relpath.replace("/", os.sep))
        jobs.append(
            BundleJob(
                relpath=relpath,
                src=str(src),
                dst=str(dst),
                target_crc=target_crc,
                patches=patches,
            )
        )
    return jobs


def _mono_by_path_id(env: UnityPy.Environment) -> dict[int, list[Any]]:
    """path_id is only unique per serialized file; a bundle can hold several (dependency CABs)."""
    out: dict[int, list[Any]] = defaultdict(list)
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            out[o.path_id].append(o)
    return out


def _literal_at(tree: dict, line: int, tok: int) -> str | None:
    cmds = tree.get("m_commandDatas")
    if not isinstance(cmds, list) or line >= len(cmds):
        return None
    toks = cmds[line].get("tokens") or []
    if tok >= len(toks):
        return None
    return toks[tok].get("Literal")


def _pick_object(candidates: list[Any], ops: list["PatchOp"], attr: str) -> Any:
    """Pick the GameScript MonoBehaviour whose literals match every op (attr = 'en' or 'es')."""
    for obj in candidates or []:
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if all(_literal_at(tree, op.line, op.tok) == getattr(op, attr) for op in ops):
            return obj
    return None


def _inventory(env: UnityPy.Environment) -> list[tuple[int, str, str]]:
    inv: list[tuple[int, str, str]] = []
    for o in env.objects:
        name = ""
        if o.type.name == "MonoBehaviour":
            try:
                name = o.read_typetree().get("m_Name") or ""
            except Exception:
                name = "?"
        inv.append((o.path_id, o.type.name, name))
    return sorted(inv)


def _normalize_references(tree: dict) -> None:
    """Drop placeholder RefIds entries UnityPy cannot round-trip (missing 'data')."""
    refs = tree.get("references")
    if not isinstance(refs, dict):
        return
    ref_ids = refs.get("RefIds")
    if not isinstance(ref_ids, list):
        return
    refs["RefIds"] = [r for r in ref_ids if isinstance(r, dict) and "data" in r]


def _verify_roundtrip(obj: Any) -> None:
    tree = obj.read_typetree()
    _normalize_references(tree)
    raw_before = bytes(obj.get_raw_data())
    obj.save_typetree(copy.deepcopy(tree))
    raw_after = bytes(obj.get_raw_data())
    if raw_before != raw_after:
        raise RuntimeError(
            f"path_id {obj.path_id}: save_typetree round-trip changed raw bytes "
            f"({len(raw_before)} -> {len(raw_after)})"
        )


def _apply_patches(obj: Any, ops: list[PatchOp]) -> int:
    tree = obj.read_typetree()
    _normalize_references(tree)
    cmds = tree.get("m_commandDatas")
    if not isinstance(cmds, list):
        raise RuntimeError(f"path_id {obj.path_id}: missing m_commandDatas")
    n = 0
    for op in ops:
        if op.line < 0 or op.line >= len(cmds):
            raise RuntimeError(f"path_id {obj.path_id}: line {op.line} out of range")
        toks = cmds[op.line].get("tokens") or []
        if op.tok < 0 or op.tok >= len(toks):
            raise RuntimeError(f"path_id {obj.path_id}: tok {op.tok} out of range at line {op.line}")
        tk = toks[op.tok]
        if tk.get("Type") != 46:
            raise RuntimeError(
                f"path_id {obj.path_id}: token {op.line}/{op.tok} Type={tk.get('Type')}, expected 46"
            )
        cur = tk.get("Literal") or ""
        if cur != op.en:
            raise RuntimeError(
                f"path_id {obj.path_id}: literal mismatch at {op.line}/{op.tok}: "
                f"expected {op.en!r}, got {cur!r}"
            )
        tk["Literal"] = op.es
        n += 1
    obj.save_typetree(tree)
    return n


def process_bundle(job: BundleJob) -> BundleResult:
    src = Path(job.src)
    dst = Path(job.dst)
    if not src.is_file():
        return BundleResult(job.relpath, "error", 0, f"missing source: {src}")
    if not job.patches:
        return BundleResult(job.relpath, "skip", 0, "no patches")

    try:
        env = UnityPy.load(str(src))
        inv_before = _inventory(env)
        by_pid: dict[int, list[PatchOp]] = defaultdict(list)
        for op in job.patches:
            by_pid[op.path_id].append(op)

        monos = _mono_by_path_id(env)
        replaced = 0
        for pid, ops in by_pid.items():
            obj = _pick_object(monos.get(pid, []), ops, "en")
            if obj is None:
                raise RuntimeError(
                    f"GameScript path_id {pid}: ningun objeto coincide con el texto original "
                    f"({len(monos.get(pid, []))} candidatos)"
                )
            _verify_roundtrip(obj)
            replaced += _apply_patches(obj, ops)

        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bundle") as tmp:
            tmp_path = Path(tmp.name)
        try:
            raw = env.file.save(packer=PACKER)
            tmp_path.write_bytes(raw)
            r = forge_file(tmp_path, dst, job.target_crc)
            if not r["ok"]:
                raise RuntimeError(f"CRC forge failed: {r}")
        finally:
            tmp_path.unlink(missing_ok=True)

        return BundleResult(job.relpath, "ok", replaced, "")
    except Exception as e:
        return BundleResult(job.relpath, "error", 0, str(e))


def self_test_bundle(
    job: BundleJob,
    inv_before: list,
) -> list[str]:
    errs: list[str] = []
    dst = Path(job.dst)
    if not dst.is_file():
        return [f"{job.relpath}: output missing"]
    b = Bundle(dst.read_bytes())
    if b.crc != (job.target_crc & 0xFFFFFFFF):
        errs.append(
            f"{job.relpath}: CRC {b.crc:08x} != target {job.target_crc & 0xFFFFFFFF:08x}"
        )
    env = UnityPy.load(str(dst))
    inv_after = _inventory(env)
    if inv_before != inv_after:
        diff = set(inv_before) ^ set(inv_after)
        errs.append(f"{job.relpath}: inventario de objetos cambio ({len(diff)} diferencias, ej. {sorted(diff)[:2]})")

    monos = _mono_by_path_id(env)
    by_pid: dict[int, list[PatchOp]] = defaultdict(list)
    for op in job.patches:
        by_pid[op.path_id].append(op)
    for pid, ops in by_pid.items():
        if _pick_object(monos.get(pid, []), ops, "es") is None:
            errs.append(f"{job.relpath}: path_id {pid}: ningun GameScript contiene los textos traducidos")
    return errs


def run_self_tests(jobs: list[BundleJob]) -> int:
    errs: list[str] = []
    for job in jobs:
        if not Path(job.dst).is_file():
            continue
        src = Path(job.src)
        if not src.is_file():
            continue
        env = UnityPy.load(str(src))
        inv = _inventory(env)
        errs.extend(self_test_bundle(job, inv))
    if errs:
        for e in errs[:30]:
            print("SELF-TEST:", e, file=sys.stderr)
        if len(errs) > 30:
            print(f"... and {len(errs) - 30} more", file=sys.stderr)
        return 1
    print(f"Self-test OK ({len(jobs)} bundle(s))")
    return 0


def build_synthetic_test_source(limit: int) -> tuple[dict[int, dict], dict[str, Any]]:
    """Build minimal es_source + script_refs from gamescripts_survey.json."""
    if not SURVEY.is_file():
        raise FileNotFoundError(f"Missing survey: {SURVEY}")
    survey = json.loads(SURVEY.read_text(encoding="utf-8"))
    name_to_rel = index_bundle_relpaths()
    if not name_to_rel:
        raise RuntimeError("Could not index bundles under aa (set DUSK_GAME_PATH)")

    cat = Catalog.load_json(str(CATALOG_PATH))
    crc_by_name = catalog_crc_by_filename(cat)

    texts: dict[int, dict] = {}
    refs: dict[str, Any] = {"_bundles": {}}
    next_id = 1
    bundles_used = 0

    for entry in survey:
        if bundles_used >= limit:
            break
        bname = entry.get("bundle") or ""
        relpath = name_to_rel.get(bname)
        if not relpath:
            continue
        crc_info = crc_by_name.get(bname)
        if not crc_info:
            continue
        scripts = entry.get("scripts") or []
        if not scripts:
            continue
        bundle_had = False
        for sc in scripts:
            path_id = sc.get("path_id")
            for lit in sc.get("literals") or []:
                text = lit.get("text") or ""
                if not text or JP.search(text):
                    continue
                if lit.get("cmd") not in ("say", "add_speaker", "choice", "item"):
                    continue
                if len(text) < 2:
                    continue
                tid = next_id
                next_id += 1
                es = "ES: " + text + TEST_SUFFIX
                texts[tid] = {
                    "id": tid,
                    "kind": "say",
                    "en": text,
                    "es": es,
                    "cmds": [lit.get("cmd")],
                    "uses": 1,
                }
                refs[str(tid)] = [[relpath, path_id, lit["line"], lit["tok"]]]
                bundle_had = True
        if bundle_had:
            crc, iid = crc_info
            refs["_bundles"][relpath] = {"crc": crc, "internal_id": iid}
            bundles_used += 1

    if bundles_used == 0:
        raise RuntimeError("No synthetic test bundles selected from survey")
    src_doc = {"meta": {"synthetic": True, "limit": limit}, "texts": list(texts.values())}
    return texts, refs | {"_source_doc": src_doc}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--use-test-source", action="store_true", help="Build test data from gamescripts_survey.json")
    ap.add_argument("--limit", type=int, default=3, help="With --use-test-source: max bundles to patch")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    args = ap.parse_args()

    if args.use_test_source:
        texts_map, refs = build_synthetic_test_source(args.limit)
        texts = texts_map
    else:
        if not args.source.is_file():
            print(f"Missing {args.source} (use --use-test-source for survey-based test)", file=sys.stderr)
            return 1
        if not args.refs.is_file():
            print(f"Missing {args.refs}", file=sys.stderr)
            return 1
        texts, refs = load_inputs(args.source, args.refs)

    jobs = build_jobs(texts, refs, args.out)
    if not jobs:
        print("No bundles to patch (no non-empty es translations).")
        return 0

    print(f"Patching {len(jobs)} bundle(s) with {sum(len(j.patches) for j in jobs)} text op(s)...")

    results: list[BundleResult] = []
    with Pool(processes=args.workers, maxtasksperchild=4) as pool:
        for res in pool.imap_unordered(process_bundle, jobs, chunksize=1):
            results.append(res)
            if res.status == "ok":
                print(f"  OK {res.relpath} ({res.texts} texts)")
            elif res.status == "error":
                print(f"  ERR {res.relpath}: {res.message}", file=sys.stderr)

    ok = [r for r in results if r.status == "ok"]
    err = [r for r in results if r.status == "error"]
    total_texts = sum(r.texts for r in ok)
    print(f"Done: {len(ok)} changed, {total_texts} texts replaced, {len(err)} error(s)")
    if err:
        return 1

    if args.self_test:
        ok_jobs = [j for j in jobs if any(r.relpath == j.relpath and r.status == "ok" for r in results)]
        return run_self_tests(ok_jobs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
