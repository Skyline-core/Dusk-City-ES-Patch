"""Validate a filled GameScript translation JSON against translation/es_source_scripts.json.

Usage: python validate_scripts_translation.py <translated.json> [--source es_source_scripts.json]
Checks: same ids, 'en' untouched, no empty 'es', markup tags preserved.
Exit code 0 = no blocking errors (warnings may remain).
"""
import argparse
import collections
import json
import os
import re
import sys

TAG_RE = re.compile(r"<[^>]*>|\{[^{}]*\}|\\n|\n|\r|「|」|\u3000")


def tags(s):
    return collections.Counter(TAG_RE.findall(s))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("translated")
    ap.add_argument("--source", default=os.path.join(here, "es_source_scripts.json"))
    ap.add_argument("--show", type=int, default=8)
    a = ap.parse_args()

    src = json.load(open(a.source, encoding="utf-8"))
    tr = json.load(open(a.translated, encoding="utf-8"))
    errors, warns = [], []

    sm = {int(x["id"]): x for x in src["texts"]}
    tm = {int(x["id"]): x for x in tr["texts"]}
    if set(sm) != set(tm):
        errors.append(
            (
                "texts",
                "ids",
                f"faltan {len(set(sm) - set(tm))} sobran {len(set(tm) - set(sm))}",
                "",
            )
        )

    def cmp(kind, label, s, t):
        es = t.get("es", "")
        if not isinstance(es, str) or not es.strip():
            errors.append((kind, label, "es vacio", s.get("en", "")[:60]))
            return
        if s["en"] != t.get("en") or s.get("ja") != t.get("ja"):
            warns.append((kind, label, "ja/en difiere del original", ""))
        ts, te = tags(s["en"]), tags(es)
        if ts != te:
            miss = ts - te
            extra = te - ts
            errors.append(
                (
                    kind,
                    label,
                    f"etiquetas: faltan {dict(miss)} sobran {dict(extra)}",
                    es[:80],
                )
            )
        if es == s["en"] and len(es) > 25:
            warns.append((kind, label, "identico al ingles", es[:50]))

    for i, s in sm.items():
        if i in tm:
            cmp("script_text", f"{i} {s['kind']}", s, tm[i])

    print(f"texts: {len(sm)}")
    print(f"ERRORES: {len(errors)} | AVISOS: {len(warns)}")
    for title, items in (("ERRORES", errors), ("AVISOS", warns)):
        by = collections.Counter(
            x[2].split(":")[0] if x[2].startswith("etiquetas") else x[2] for x in items
        )
        if by:
            print(f"-- {title} por tipo: {dict(by)}")
        for x in items[: a.show]:
            print("  ", x)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
