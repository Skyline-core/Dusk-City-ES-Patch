"""Validate a filled translation JSON against translation/es_source.json.

Usage: python validate_translation.py <translated.json> [--source es_source.json]
Checks: same ids/paths/voice, ja/en untouched, no empty 'es', markup tags preserved.
Exit code 0 = no blocking errors (warnings may remain).
"""
import argparse
import collections
import json
import os
import re
import sys

TAG_RE = re.compile(r"<[^>]*>|\{[^{}]*\}|\\n|\n|\r")


def tags(s):
    return collections.Counter(TAG_RE.findall(s))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("translated")
    ap.add_argument("--source", default=os.path.join(here, "es_source.json"))
    ap.add_argument("--show", type=int, default=8)
    a = ap.parse_args()

    src = json.load(open(a.source, encoding="utf-8"))
    tr = json.load(open(a.translated, encoding="utf-8"))
    errors, warns = [], []

    def cmp(kind, label, s, t):
        es = t.get("es", "")
        if not isinstance(es, str) or not es.strip():
            errors.append((kind, label, "es vacio", s.get("en", "")[:60]))
            return
        if s["en"] != t.get("en") or s["ja"] != t.get("ja"):
            warns.append((kind, label, "ja/en difiere del original", ""))
        ts, te = tags(s["en"]), tags(es)
        if ts != te:
            miss = ts - te
            extra = te - ts
            errors.append((kind, label, f"etiquetas: faltan {dict(miss)} sobran {dict(extra)}", es[:80]))
        if es == s["en"] and len(es) > 25:
            warns.append((kind, label, "identico al ingles", es[:50]))

    # strings
    sm = {x["id"]: x for x in src["strings"]}
    tm = {x["id"]: x for x in tr["strings"]}
    if set(sm) != set(tm):
        errors.append(("strings", "ids", f"faltan {len(set(sm)-set(tm))} sobran {len(set(tm)-set(sm))}", ""))
    for i, s in sm.items():
        if i in tm:
            cmp("string", f'{i} {s["key"][:20]}', s, tm[i])

    # scripts
    ss = {x["asset"]: x for x in src["scripts"]}
    ts_ = {x["asset"]: x for x in tr["scripts"]}
    if set(ss) != set(ts_):
        errors.append(("scripts", "assets", f"faltan {set(ss)-set(ts_)} sobran {set(ts_)-set(ss)}", ""))
    n_lines = 0
    for name, s in ss.items():
        if name not in ts_:
            continue
        se = {e["path"]: e for e in s["entries"]}
        te = {e["path"]: e for e in ts_[name]["entries"]}
        if set(se) != set(te):
            errors.append(("script", name, f"paths distintos: faltan {len(set(se)-set(te))} sobran {len(set(te)-set(se))}", ""))
        for p, e in se.items():
            if p in te:
                n_lines += 1
                if e["voice"] != te[p]["voice"]:
                    errors.append(("script", f"{name}:{p}", "voice distinto", ""))
                cmp("script", f"{name}:{p}", e, te[p])

    print(f"strings: {len(sm)} | lineas de voz: {n_lines}")
    print(f"ERRORES: {len(errors)} | AVISOS: {len(warns)}")
    for title, items in (("ERRORES", errors), ("AVISOS", warns)):
        by = collections.Counter(x[2].split(":")[0] if x[2].startswith("etiquetas") else x[2] for x in items)
        if by:
            print(f"-- {title} por tipo: {dict(by)}")
        for x in items[: a.show]:
            print("  ", x)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
