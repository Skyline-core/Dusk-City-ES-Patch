"""Survey every GameScript (m_commandDatas) in the Addressables bundles. Read-only.
Outputs research/gamescripts_survey.json: per bundle, per script, every string literal (Type 46)
with the command name, and whether it contains Japanese characters / is already a key of the
Translation table (es_source.json 'strings')."""
import json
import os
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import UnityPy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "bundle_builder"))
from crc_forge import Bundle, _dec  # noqa: E402

GAME = Path(os.environ.get("DUSK_GAME_PATH") or HERE.parent.parent.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
NEEDLE = b"m_commandDatas"
JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def has_needle(path):
    try:
        raw = Path(path).read_bytes()
        b = Bundle(raw)
        p = b.data_start
        for u, c, f in b.blocks:
            if NEEDLE in _dec(raw[p:p + c], f & 0x3F, u):
                return str(path)
            p += c
    except Exception:
        return None
    return None


def survey(path):
    out = []
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        cmds = t.get("m_commandDatas")
        if not isinstance(cmds, list):
            continue
        lits = []
        for li, ln in enumerate(cmds):
            toks = ln.get("tokens") or []
            if not toks:
                continue
            fn = toks[0].get("Literal", "")
            for ti, tk in enumerate(toks):
                if tk.get("Type") == 46 and tk.get("Literal"):
                    lits.append({"line": li, "tok": ti, "cmd": fn, "text": tk["Literal"]})
        out.append({"path_id": o.path_id, "name": t.get("m_Name"), "literals": lits})
    return {"bundle": Path(path).name, "scripts": out}


if __name__ == "__main__":
    files = list((AA / "StandaloneWindows64").glob("*.bundle")) + list((AA / "DLC1").rglob("*.bundle")) + list((AA / "DLC2").rglob("*.bundle"))
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        cands = [x for x in pool.imap_unordered(has_needle, files, chunksize=8) if x]
        print("bundles con m_commandDatas:", len(cands), flush=True)
        res = pool.map(survey, cands)
    keys = set()
    src = HERE.parent / "es_source.json"
    if src.exists():
        d = json.load(open(src, encoding="utf-8"))
        keys = {e["key"] for e in d["strings"]} | {e["ja"] for e in d["strings"]}
    tot = nonjp = nonjp_nokey = 0
    for b in res:
        for s in b["scripts"]:
            for l in s["literals"]:
                tot += 1
                l["jp"] = bool(JP.search(l["text"]))
                l["in_table"] = l["text"] in keys
                nonjp += not l["jp"]
                nonjp_nokey += (not l["jp"] and not l["in_table"])
    json.dump(res, open(HERE / "gamescripts_survey.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("scripts:", sum(len(b["scripts"]) for b in res), "| literales:", tot, "| sin kanji/kana:", nonjp, "| sin kanji y fuera de tabla:", nonjp_nokey)
