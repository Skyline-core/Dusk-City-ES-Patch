#!/usr/bin/env python3
"""Patch misc serialized strings in Addressables bundles.

Reads translation/es_source_misc.json + translation/research/misc_refs.json,
writes patched bundles under translation/patch_en_slot/files/<relpath>/.
Chains from existing patched bundles in --out when present.
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "bundle_builder"))
sys.path.insert(0, str(ROOT / "catalog_tool"))

from crc_forge import Bundle, forge_file  # noqa: E402
from mt_common import read_string, write_string  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
DEFAULT_SOURCE = ROOT / "es_source_misc.json"
DEFAULT_REFS = ROOT / "research" / "misc_refs.json"
DEFAULT_OUT = ROOT / "patch_en_slot" / "files"
PACKER = "lz4"
JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


@dataclass
class PatchOp:
    text_id: int
    path_id: int
    path: list[Any]
    field: str
    en: str
    es: str


@dataclass
class BundleJob:
    relpath: str
    src: str
    dst: str
    target_crc: int
    patches: list[PatchOp] = field(default_factory=list)
    chained: bool = False


@dataclass
class BundleResult:
    relpath: str
    status: str
    texts: int = 0
    message: str = ""


def _normalize_references(tree: dict) -> None:
    refs = tree.get("references")
    if not isinstance(refs, dict):
        return
    ref_ids = refs.get("RefIds")
    if not isinstance(ref_ids, list):
        return
    refs["RefIds"] = [r for r in ref_ids if isinstance(r, dict) and "data" in r]


def _mono_by_path_id(env: UnityPy.Environment) -> dict[int, list[Any]]:
    out: dict[int, list[Any]] = defaultdict(list)
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            out[o.path_id].append(o)
    return out


def _pick_object(candidates: list[Any], ops: list[PatchOp], attr: str) -> Any:
    for obj in candidates or []:
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        ok = True
        for op in ops:
            cur = read_string(tree, op.path, op.field)
            want = getattr(op, attr)
            if cur != want:
                if attr == "en" and cur == op.es:
                    continue
                ok = False
                break
        if ok:
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
    n = 0
    for op in ops:
        cur = read_string(tree, op.path, op.field)
        if cur == op.es:
            continue
        if cur != op.en:
            raise RuntimeError(
                f"path_id {obj.path_id}: mismatch at {op.path!r}.{op.field!r}: "
                f"expected {op.en!r}, got {cur!r}"
            )
        write_string(tree, op.path, op.field, op.es)
        n += 1
    _normalize_references(tree)
    obj.save_typetree(tree)
    return n


def resolve_src(relpath: str, out_root: Path) -> tuple[str, bool]:
    dst = out_root / Path(relpath.replace("/", os.sep))
    vanilla = AA / Path(relpath.replace("/", os.sep))
    if dst.is_file():
        return str(dst), True
    return str(vanilla), False


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
        for ref in refs.get(str(sid)) or []:
            if not ref or len(ref) < 4:
                continue
            relpath, path_id, path, fld = ref[0], int(ref[1]), ref[2], str(ref[3])
            by_bundle[relpath].append(PatchOp(int(sid), path_id, path, fld, en, es))

    jobs: list[BundleJob] = []
    for relpath, patches in sorted(by_bundle.items()):
        meta = bundles_meta.get(relpath) or {}
        target_crc = int(meta.get("crc") or 0)
        if not target_crc:
            continue
        src, chained = resolve_src(relpath, out_root)
        dst = out_root / Path(relpath.replace("/", os.sep))
        jobs.append(
            BundleJob(
                relpath=relpath,
                src=src,
                dst=str(dst),
                target_crc=target_crc,
                patches=patches,
                chained=chained,
            )
        )
    return jobs


def process_bundle(job: BundleJob) -> BundleResult:
    src = Path(job.src)
    dst = Path(job.dst)
    if not src.is_file():
        return BundleResult(job.relpath, "error", 0, f"missing source: {src}")
    if not job.patches:
        return BundleResult(job.relpath, "skip", 0, "no patches")

    try:
        env = UnityPy.load(str(src))
        monos = _mono_by_path_id(env)
        by_pid: dict[int, list[PatchOp]] = defaultdict(list)
        for op in job.patches:
            by_pid[op.path_id].append(op)

        replaced = 0
        for pid, ops in by_pid.items():
            obj = _pick_object(monos.get(pid, []), ops, "en")
            if obj is None:
                raise RuntimeError(
                    f"path_id {pid}: no object matches English literals "
                    f"({len(monos.get(pid, []))} MonoBehaviour candidate(s))"
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

        msg = "chained" if job.chained else ""
        return BundleResult(job.relpath, "ok", replaced, msg)
    except Exception as e:
        return BundleResult(job.relpath, "error", 0, str(e))


def self_test_bundle(job: BundleJob, inv_before: list) -> list[str]:
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
        errs.append(f"{job.relpath}: object inventory changed ({len(diff)} diffs)")

    monos = _mono_by_path_id(env)
    by_pid: dict[int, list[PatchOp]] = defaultdict(list)
    for op in job.patches:
        by_pid[op.path_id].append(op)
    for pid, ops in by_pid.items():
        if _pick_object(monos.get(pid, []), ops, "es") is None:
            errs.append(f"{job.relpath}: path_id {pid}: no object contains Spanish literals")
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


def build_test_source(limit: int) -> tuple[dict[int, dict], dict[str, Any]]:
    src_path = DEFAULT_SOURCE
    refs_path = DEFAULT_REFS
    if not src_path.is_file() or not refs_path.is_file():
        raise FileNotFoundError("Run extract_misc_texts.py first")
    texts, refs = load_inputs(src_path, refs_path)
    bundles_meta = refs.get("_bundles") or {}

    by_bundle: dict[str, list[int]] = defaultdict(list)
    for tid in texts:
        for ref in refs.get(str(tid)) or []:
            by_bundle[ref[0]].append(tid)

    selected = [b for b in sorted(by_bundle.keys()) if b in bundles_meta][:limit]
    if not selected:
        raise RuntimeError("No catalog CRC entries in misc_refs _bundles (stale bundle paths?)")
    out_texts: dict[int, dict] = {}
    out_refs: dict[str, Any] = {"_bundles": {}}
    for relpath in selected:
        meta = bundles_meta.get(relpath)
        if not meta:
            continue
        out_refs["_bundles"][relpath] = meta
        for tid in by_bundle[relpath]:
            row = dict(texts[tid])
            en = row.get("en") or ""
            if JP.search(en):
                continue
            row["es"] = "ES: " + en
            out_texts[tid] = row
            out_refs[str(tid)] = refs[str(tid)]

    if not out_texts:
        raise RuntimeError("No English misc strings in selected bundles")
    return out_texts, out_refs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--use-test-source", action="store_true")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    args = ap.parse_args()

    if args.use_test_source:
        texts_map, refs = build_test_source(args.limit)
        texts = texts_map
    else:
        if not args.source.is_file():
            print(f"Missing {args.source}", file=sys.stderr)
            return 1
        if not args.refs.is_file():
            print(f"Missing {args.refs}", file=sys.stderr)
            return 1
        texts, refs = load_inputs(args.source, args.refs)

    jobs = build_jobs(texts, refs, args.out)
    if not jobs:
        print("No bundles to patch (no non-empty es translations).")
        return 0

    chained = sum(1 for j in jobs if j.chained)
    print(
        f"Patching {len(jobs)} bundle(s) ({chained} chained from --out), "
        f"{sum(len(j.patches) for j in jobs)} op(s)..."
    )

    results: list[BundleResult] = []
    with Pool(processes=args.workers, maxtasksperchild=4) as pool:
        for res in pool.imap_unordered(process_bundle, jobs, chunksize=1):
            results.append(res)
            if res.status == "ok":
                extra = f" [{res.message}]" if res.message else ""
                print(f"  OK {res.relpath} ({res.texts} texts){extra}")
            elif res.status == "error":
                print(f"  ERR {res.relpath}: {res.message}", file=sys.stderr)

    ok = [r for r in results if r.status == "ok"]
    err = [r for r in results if r.status == "error"]
    print(f"Done: {len(ok)} changed, {sum(r.texts for r in ok)} texts, {len(err)} error(s)")
    if err:
        return 1

    if args.self_test:
        ok_jobs = [j for j in jobs if any(r.relpath == j.relpath and r.status == "ok" for r in results)]
        return run_self_tests(ok_jobs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
