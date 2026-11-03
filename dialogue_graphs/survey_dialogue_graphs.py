#!/usr/bin/env python3
"""Scan all aa bundles for dialogue graphs; write dialogue_graph_survey.md + JSON stats."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import UnityPy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from dg_common import (  # noqa: E402
    classify_string,
    has_references_mono,
    is_dialogue_graph_tree,
    is_internal_string,
    walk_data_strings,
)

GAME = Path(os.environ.get("DUSK_GAME_PATH") or ROOT.parent)
AA = GAME / "Dusk City_Data" / "StreamingAssets" / "aa"
OUT_MD = ROOT / "research" / "dialogue_graph_survey.md"
OUT_JSON = ROOT / "research" / "dialogue_graph_survey_stats.json"


def main() -> int:
    if not AA.is_dir():
        print(f"Missing aa folder: {AA}", file=sys.stderr)
        return 1

    bundles = sorted(AA.rglob("*.bundle"))
    print(f"Scanning {len(bundles)} bundle(s)...")

    graph_count = 0
    other_ref_mono = 0
    node_class_counts: Counter[str] = Counter()
    field_by_class: dict[str, Counter[str]] = defaultdict(Counter)
    trans_by_class_field: Counter[tuple[str, str]] = Counter()
    nontrans_samples: dict[tuple[str, str], list[str]] = defaultdict(list)
    trans_samples: dict[tuple[str, str], list[str]] = defaultdict(list)
    graph_names: Counter[str] = Counter()
    bundle_graphs: Counter[str] = Counter()
    overlap_gamescript: list[str] = []

    for bp in bundles:
        relpath = bp.relative_to(AA).as_posix()
        try:
            env = UnityPy.load(str(bp))
        except Exception:
            continue
        has_gs = False
        for o in env.objects:
            if o.type.name != "MonoBehaviour":
                continue
            try:
                tree = o.read_typetree()
            except Exception:
                continue
            if isinstance(tree.get("m_commandDatas"), list):
                has_gs = True
            if not has_references_mono(tree):
                continue
            if is_dialogue_graph_tree(tree):
                graph_count += 1
                gname = str(tree.get("m_Name") or "")
                graph_names[gname] += 1
                bundle_graphs[relpath] += 1
                if has_gs:
                    overlap_gamescript.append(relpath)
                refs = tree["references"]["RefIds"]
                for entry in refs:
                    if not isinstance(entry, dict):
                        continue
                    t = entry.get("type") or {}
                    cls = str(t.get("class") or "?")
                    node_class_counts[cls] += 1
                    data = entry.get("data")
                    if not isinstance(data, dict):
                        continue
                    for field, text in walk_data_strings(data):
                        suf = field[5:] if field.startswith("data.") else field
                        field_by_class[cls][suf] += 1
                        kind = classify_string(cls, field, text)
                        if kind:
                            trans_by_class_field[(cls, suf)] += 1
                            if len(trans_samples[(cls, suf)]) < 5:
                                trans_samples[(cls, suf)].append(text[:120])
                        elif isinstance(text, str) and len(text) > 1 and not is_internal_string(text, field):
                            if len(nontrans_samples[(cls, suf)]) < 3:
                                nontrans_samples[(cls, suf)].append(text[:80])
            else:
                other_ref_mono += 1

    overlap_gamescript = sorted(set(overlap_gamescript))
    total_trans = sum(trans_by_class_field.values())
    by_kind: Counter[str] = Counter()
    for (cls, suf), n in trans_by_class_field.items():
        sample = trans_samples.get((cls, suf), [""])[0]
        k = classify_string(cls, f"data.{suf}", sample) or "?"
        by_kind[k] += n

    stats = {
        "bundles_scanned": len(bundles),
        "dialogue_graph_monos": graph_count,
        "distinct_graph_names": len(graph_names),
        "bundles_with_graphs": len(bundle_graphs),
        "other_mono_with_references": other_ref_mono,
        "overlap_bundles_gamescript_and_graph": overlap_gamescript,
        "node_instances_by_class": dict(node_class_counts.most_common()),
        "translatable_uses_by_class_field": {
            f"{c}.{f}": n for (c, f), n in trans_by_class_field.most_common()
        },
        "translatable_by_kind": dict(by_kind),
        "total_translatable_string_uses": total_trans,
    }
    OUT_JSON.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = [
        "# Dialogue graph survey (Dusk City)",
        "",
        f"Game root: `{GAME}`",
        f"Bundles scanned: **{len(bundles)}** under `StreamingAssets/aa` (incl. DLC1/DLC2).",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Dialogue graph `MonoBehaviour` assets | {graph_count} |",
        f"| Distinct graph `m_Name` values | {len(graph_names)} |",
        f"| Bundles containing ≥1 graph | {len(bundle_graphs)} |",
        f"| Translatable string field uses (RefIds `data`) | {total_trans} |",
        f"| Other `MonoBehaviour` with `references.RefIds` (not full graph) | {other_ref_mono} |",
        f"| Bundles with **both** GameScript + dialogue graph | {len(overlap_gamescript)} |",
        "",
        "### Translatable uses by kind",
        "",
    ]
    for k, n in by_kind.most_common():
        lines.append(f"- **{k}**: {n}")
    lines.extend(
        [
            "",
            "## Dialogue graph asset shape",
            "",
            "MonoBehaviours with typetree keys:",
            "`m_GameObject`, `m_Enabled`, `m_Script`, `m_Name`, `edges`, `nodes`, `labelNodes`, `labels`, `groups`, `references`.",
            "",
            "Node payloads live in `references.RefIds[i].data` with `references.RefIds[i].type.class` naming the node type",
            "(namespaces `StrayCatLab.DialogueGraph`, `StrayCatLab.Game`, etc.).",
            "",
            "Graph-level `labels[].labelName` (e.g. `Start`, `NewLabel`) is **editor-only** — not extracted.",
            "",
            "## Node classes (instance counts)",
            "",
            "| Class | Instances |",
            "|-------|----------:|",
        ]
    )
    for cls, n in node_class_counts.most_common(40):
        lines.append(f"| `{cls}` | {n} |")
    if len(node_class_counts) > 40:
        lines.append(f"| … | {sum(n for _, n in node_class_counts.most_common()[40:])} more classes |")

    lines.extend(["", "## String fields under `data` by class", ""])
    for cls in sorted(field_by_class.keys()):
        if cls == "?":
            continue
        lines.append(f"### `{cls}`")
        lines.append("")
        lines.append("| Field | Occurrences | Translatable? | Examples |")
        lines.append("|-------|------------:|:-------------:|----------|")
        for field, cnt in field_by_class[cls].most_common():
            key = (cls, field)
            is_tr = key in trans_by_class_field
            ex = trans_samples.get(key) or nontrans_samples.get(key) or []
            ex_s = "; ".join(f"`{e}`" for e in ex[:3]) or "—"
            note = "**Yes**" if is_tr else "No"
            if not is_tr and field in ("guid", "flagName", "interactableKey", "startlabel"):
                note = "No (internal id / flag / key)"
            elif not is_tr and field.startswith("entries"):
                note = "No (game variable key)"
            elif not is_tr and "scriptReference" in field or "prefabReference" in field:
                note = "No (asset reference)"
            lines.append(f"| `{field}` | {cnt} | {note} | {ex_s} |")
        lines.append("")

    lines.extend(["## Top graph names", ""])
    for name, n in graph_names.most_common(25):
        lines.append(f"- `{name}`: {n}")

    if overlap_gamescript:
        lines.extend(
            [
                "",
                "## GameScript overlap bundles",
                "",
                "These bundles contain both `m_commandDatas` GameScripts and dialogue graphs.",
                "When patching, load an already-patched bundle from the output dir if present (chain).",
                "",
            ]
        )
        for rel in overlap_gamescript[:30]:
            lines.append(f"- `{rel}`")
        if len(overlap_gamescript) > 30:
            lines.append(f"- … and {len(overlap_gamescript) - 30} more")

    lines.extend(
        [
            "",
            "## Trailing-space note",
            "",
            "Some choice strings differ only by trailing spaces (e.g. `'About the artifact '` vs `'About the artifact'`).",
            "Extraction treats exact strings as distinct ids.",
            "",
            f"Machine-readable stats: `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print(f"Graphs: {graph_count}, translatable uses: {total_trans}, overlap: {len(overlap_gamescript)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
