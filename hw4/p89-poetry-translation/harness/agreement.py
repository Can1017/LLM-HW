#!/usr/bin/env python3
"""Compare original and re-rating scores for the reliability subset.

Usage:
  python harness/agreement.py --key results/reliability/key_reliability_dev.json \
      --ratings results/reliability/ratings_reliability_dev.csv \
      --orig-ratings results/blind/ratings_sf.csv \
      --orig-key results/blind/key_sf.json --out results/reliability/agreement_dev.md
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_scores(text: str) -> dict:
    scores = {}
    for part in (text or "").split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            if value.strip():
                scores[key.strip()] = int(value)
    return scores


def parse_int(value, default=None):
    value = (value or "").strip()
    if not value:
        return default
    return int(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True)
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--orig-ratings", required=True)
    parser.add_argument("--orig-key", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    key_items = load_json(resolve(args.key))["items"]
    orig_key_by_blind = {item["blind_id"]: item for item in load_json(resolve(args.orig_key))["items"]}
    with open(resolve(args.orig_ratings), encoding="utf-8") as f:
        orig_by_run = {}
        for row in csv.DictReader(f):
            key = orig_key_by_blind.get(row["blind_id"])
            if key:
                orig_by_run[key["run_key"]] = row
    with open(resolve(args.ratings), encoding="utf-8") as f:
        new_by_rid = {row["blind_id"]: row for row in csv.DictReader(f)}

    term_total = term_exact = term_within1 = 0
    rel_total = rel_exact = rel_within1 = 0
    major_exact = major_total = 0
    minor_exact = 0
    rows = []
    disagreements = []
    for item in key_items:
        rid = item["rid"]
        orig = orig_by_run.get(item["run_key"])
        new = new_by_rid.get(rid)
        if not orig or not new:
            continue
        oterm = parse_scores(orig.get("term_scores", ""))
        nterm = parse_scores(new.get("term_scores", ""))
        orel = parse_scores(orig.get("relation_scores", ""))
        nrel = parse_scores(new.get("relation_scores", ""))
        term_ids = sorted(set(oterm) | set(nterm))
        rel_ids = sorted(set(orel) | set(nrel))
        te = tw = 0
        for key in term_ids:
            if oterm.get(key) == nterm.get(key):
                term_exact += 1
                te += 1
            if abs(oterm.get(key, -9) - nterm.get(key, -9)) <= 1:
                term_within1 += 1
                tw += 1
            if oterm.get(key) != nterm.get(key):
                disagreements.append((rid, item["poem_id"], "term", key, oterm.get(key), nterm.get(key)))
        re = rw = 0
        for key in rel_ids:
            if orel.get(key) == nrel.get(key):
                rel_exact += 1
                re += 1
            if abs(orel.get(key, -9) - nrel.get(key, -9)) <= 1:
                rel_within1 += 1
                rw += 1
            if orel.get(key) != nrel.get(key):
                disagreements.append((rid, item["poem_id"], "relation", key, orel.get(key), nrel.get(key)))
        term_total += len(term_ids)
        rel_total += len(rel_ids)
        omaj = parse_int(orig.get("major_errors"))
        nmaj = parse_int(new.get("major_errors"))
        if omaj is not None and nmaj is not None:
            major_total += 1
            if omaj == nmaj:
                major_exact += 1
            if omaj != nmaj:
                disagreements.append((rid, item["poem_id"], "major", "-", omaj, nmaj))
        omin = parse_int(orig.get("minor_errors"))
        nmin = parse_int(new.get("minor_errors"))
        if omin is not None and nmin is not None and omin == nmin:
            minor_exact += 1
        rows.append({
            "rid": rid,
            "poem_id": item["poem_id"],
            "version": item["version"],
            "term_exact": f"{te}/{len(term_ids)}",
            "relation_exact": f"{re}/{len(rel_ids)}",
            "major_orig": "" if omaj is None else omaj,
            "major_new": "" if nmaj is None else nmaj,
        })

    lines = ["# 二次盲评一致性", ""]
    lines.append(f"条目：{len(rows)}")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 项目 | 完全一致 | 相差 ≤1 | 总数 | 完全一致率 |")
    lines.append("| --- | --- | --- | --- | --- |")
    lines.append(f"| 术语 | {term_exact} | {term_within1} | {term_total} | {100*term_exact/term_total:.1f}% |" if term_total else "| 术语 | 0 | 0 | 0 | — |")
    lines.append(f"| 关系 | {rel_exact} | {rel_within1} | {rel_total} | {100*rel_exact/rel_total:.1f}% |" if rel_total else "| 关系 | 0 | 0 | 0 | — |")
    lines.append(f"| 重大错误数 | {major_exact} | — | {major_total} | {100*major_exact/major_total:.1f}% |" if major_total else "| 重大错误数 | 0 | — | 0 | — |")
    lines.append("")
    lines.append("## 逐条")
    lines.append("")
    lines.append("| RID | 诗 | 版本 | 术语一致 | 关系一致 | 重大错误（原/重） |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in rows:
        lines.append(f"| {row['rid']} | {row['poem_id']} | {row['version']} | {row['term_exact']} | {row['relation_exact']} | {row['major_orig']}/{row['major_new']} |")
    lines.append("")
    lines.append("## 分歧")
    lines.append("")
    if disagreements:
        for rid, poem, kind, anchor, before, after in disagreements:
            lines.append(f"- {rid} {poem} {kind} {anchor}: 原评 {before} → 重评 {after}")
    else:
        lines.append("- 无")

    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"items {len(rows)} | term exact {term_exact}/{term_total} | relation exact {rel_exact}/{rel_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())