#!/usr/bin/env python3
"""Aggregate blind ratings for the P89 experiment.

Inputs:
  --sf   ratings_sf.csv (one row per blind item)
  --key-sf key_sf.json
  --sr   ratings_sr.csv (optional)
  --key-sr key_sr.json (optional)
  --results main_dev.jsonl (for usage/latency)
  --out  scored_dev.md

The script writes a Markdown summary and an item-level CSV next to it.
Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Title-only terms are not scored in the body; see reports/评分细则_v1.md §2.2.
TITLE_ONLY_TERMS = {"T01-T1", "T02-T1"}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_scores(text: str) -> dict:
    scores = {}
    for part in (text or "").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        value = value.strip()
        if value:
            scores[key.strip()] = int(value)
    return scores


def parse_int(value, default=None):
    value = (value or "").strip()
    if value == "":
        return default
    return int(value)


def bootstrap_ci(values: list[float], rng: random.Random, n_boot: int = 2000) -> tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    means = []
    for _ in range(n_boot):
        sample = [rng.choice(values) for _ in values]
        means.append(statistics.mean(sample))
    means.sort()
    return means[int(0.025 * len(means))], means[int(0.975 * len(means)) - 1]


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", default=str(ROOT / "results" / "blind" / "ratings_sf.csv"))
    parser.add_argument("--key-sf", default=str(ROOT / "results" / "blind" / "key_sf.json"))
    parser.add_argument("--sr", default=str(ROOT / "results" / "blind" / "ratings_sr.csv"))
    parser.add_argument("--key-sr", default=str(ROOT / "results" / "blind" / "key_sr.json"))
    parser.add_argument("--results", default=str(ROOT / "results" / "main_dev.jsonl"))
    parser.add_argument("--out", default=str(ROOT / "results" / "scored_dev.md"))
    parser.add_argument("--label", default="开发集", help="标题用：开发集/测试集")
    parser.add_argument("--seed", type=int, default=20261029)
    args = parser.parse_args(argv)

    poems = {p["id"]: p for p in load_json(ROOT / "data" / "poems.json")["poems"]}
    key_sf = {item["blind_id"]: item for item in load_json(resolve(args.key_sf))["items"]}
    key_sr = {}
    sr_path = resolve(args.sr)
    key_sr_path = resolve(args.key_sr)
    if sr_path.exists() and key_sr_path.exists():
        key_sr = {item["blind_id"]: item for item in load_json(key_sr_path)["items"]}
    results = {row["run_key"]: row for row in load_jsonl(resolve(args.results))}

    with open(resolve(args.sf), encoding="utf-8") as f:
        sf_rows = list(csv.DictReader(f))

    sr_by_run = {}
    if key_sr and sr_path.exists():
        with open(sr_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = key_sr.get(row["blind_id"])
                if not key:
                    continue
                values = [
                    parse_int(row.get("s_r_core")),
                    parse_int(row.get("s_r_imagery")),
                    parse_int(row.get("s_r_poem")),
                    parse_int(row.get("s_r_misread")),
                ]
                if all(value is not None for value in values):
                    sr_by_run[key["run_key"]] = sum(values)

    items = []
    missing = []
    for row in sf_rows:
        key = key_sf.get(row["blind_id"])
        if not key:
            missing.append(f"unknown blind_id in SF ratings: {row['blind_id']}")
            continue
        poem = poems[key["poem_id"]]
        term_scores = parse_scores(row.get("term_scores", ""))
        relation_scores = parse_scores(row.get("relation_scores", ""))
        term_ids = [t["id"] for t in poem["terms"] if t["id"] not in TITLE_ONLY_TERMS]
        relation_ids = [r["id"] for r in poem["relations"]]
        if set(term_scores) != set(term_ids):
            missing.append(f"{key['run_key']}: term scores incomplete ({sorted(set(term_ids) - set(term_scores))})")
        if set(relation_scores) != set(relation_ids):
            missing.append(f"{key['run_key']}: relation scores incomplete ({sorted(set(relation_ids) - set(relation_scores))})")
        term_rate = sum(term_scores.get(i, 0) for i in term_ids) / (2 * len(term_ids))
        relation_rate = sum(relation_scores.get(i, 0) for i in relation_ids) / (2 * len(relation_ids))
        result = results.get(key["run_key"], {})
        usage = result.get("usage") or {}
        reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
        items.append({
            "run_key": key["run_key"],
            "poem_id": key["poem_id"],
            "version": key["version"],
            "rep": key["rep"],
            "term_rate": term_rate,
            "relation_rate": relation_rate,
            "term_scores": term_scores,
            "relation_scores": relation_scores,
            "term_zero": sum(1 for i in term_ids if term_scores.get(i, 0) == 0),
            "relation_zero": sum(1 for i in relation_ids if relation_scores.get(i, 0) == 0),
            "major_errors": parse_int(row.get("major_errors"), 0),
            "minor_errors": parse_int(row.get("minor_errors"), 0),
            "image_score": parse_int(row.get("image_score")),
            "emotion_score": parse_int(row.get("emotion_score")),
            "english_score": parse_int(row.get("english_score")),
            "format_pass": parse_int(row.get("format_pass")),
            "s_r_total": sr_by_run.get(key["run_key"]),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": reasoning,
            "latency_sec": result.get("latency_sec"),
        })

    if missing:
        print("WARNING:")
        for message in missing:
            print(" -", message)

    by_version = defaultdict(list)
    for item in items:
        by_version[item["version"]].append(item)

    def mean(values):
        values = [v for v in values if v is not None]
        return statistics.mean(values) if values else float("nan")

    lines = [f"# P89 {args.label}评分汇总", ""]
    lines.append(f"条目：{len(items)}；版本：{', '.join(sorted(by_version))}")
    lines.append("")
    lines.append("## 版本汇总（S_F 与成本）")
    lines.append("")
    lines.append("| 版本 | n | 术语正确率 | 关系保持率 | 关系0分 | 术语0分 | 重大错误 | 次要错误 | 意象 | 情感 | 英语 | 格式通过 | S_R（0–8） | prompt tok | completion tok | reasoning tok | 延迟秒 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for version in sorted(by_version):
        group = by_version[version]
        lines.append("| {} | {} | {:.2f} | {:.2f} | {} | {} | {} | {} | {:.2f} | {:.2f} | {:.2f} | {:.0f}% | {} | {:.0f} | {:.0f} | {:.0f} | {:.2f} |".format(
            version,
            len(group),
            mean([i["term_rate"] for i in group]),
            mean([i["relation_rate"] for i in group]),
            sum(i["relation_zero"] for i in group),
            sum(i["term_zero"] for i in group),
            sum(i["major_errors"] for i in group),
            sum(i["minor_errors"] for i in group),
            mean([i["image_score"] for i in group]),
            mean([i["emotion_score"] for i in group]),
            mean([i["english_score"] for i in group]),
            100 * mean([i["format_pass"] for i in group]),
            "—" if all(i["s_r_total"] is None for i in group) else "{:.2f}".format(mean([i["s_r_total"] for i in group])),
            mean([i["prompt_tokens"] for i in group]),
            mean([i["completion_tokens"] for i in group]),
            mean([i["reasoning_tokens"] for i in group]),
            mean([i["latency_sec"] for i in group]),
        ))

    lines.append("")
    lines.append("## 逐首配对（相对 V0）")
    lines.append("")
    lines.append("| 诗 | 版本 | Δ术语 | Δ关系 | Δ重大错误 | 关系改对 | 关系新增 | 术语改对 | 术语新增 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    by_poem = defaultdict(lambda: defaultdict(list))
    for item in items:
        by_poem[item["poem_id"]][item["version"]].append(item)
    rng = random.Random(args.seed)
    for poem_id in sorted(by_poem):
        base_items = by_poem[poem_id].get("v0", [])
        if not base_items:
            continue
        poem = poems[poem_id]
        base_by_rep = {item["rep"]: item for item in base_items}
        for version in sorted(by_poem[poem_id]):
            if version == "v0":
                continue
            item_items = by_poem[poem_id][version]
            item_by_rep = {item["rep"]: item for item in item_items}
            common_reps = sorted(set(base_by_rep) & set(item_by_rep))
            term_fixed = term_new = relation_fixed = relation_new = 0
            for rep in common_reps:
                base = base_by_rep[rep]
                item = item_by_rep[rep]
                for term in poem["terms"]:
                    before = base["term_scores"].get(term["id"], 0)
                    after = item["term_scores"].get(term["id"], 0)
                    if after > before:
                        term_fixed += 1
                    elif after < before:
                        term_new += 1
                for relation in poem["relations"]:
                    before = base["relation_scores"].get(relation["id"], 0)
                    after = item["relation_scores"].get(relation["id"], 0)
                    if after > before:
                        relation_fixed += 1
                    elif after < before:
                        relation_new += 1
            lines.append("| {} | {} | {:+.2f} | {:+.2f} | {:+.2f} | {} | {} | {} | {} |".format(
                poem_id, version,
                mean([i["term_rate"] for i in item_items]) - mean([i["term_rate"] for i in base_items]),
                mean([i["relation_rate"] for i in item_items]) - mean([i["relation_rate"] for i in base_items]),
                mean([i["major_errors"] for i in item_items]) - mean([i["major_errors"] for i in base_items]),
                relation_fixed, relation_new, term_fixed, term_new,
            ))

    lines.append("")
    lines.append("## 版本相对 V0 的平均差与 bootstrap 95% 区间（以诗为重采样单位）")
    lines.append("")
    lines.append("| 版本 | Δ关系（均值） | 95% 区间 | Δ术语（均值） | 95% 区间 | Δ重大错误（均值） |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for version in sorted(by_version):
        if version == "v0":
            continue
        poem_ids = sorted(by_poem)
        rel_diffs = []
        term_diffs = []
        major_diffs = []
        for poem_id in poem_ids:
            base_items = by_poem[poem_id].get("v0", [])
            item_items = by_poem[poem_id].get(version, [])
            if not base_items or not item_items:
                continue
            rel_diffs.append(
                mean([i["relation_rate"] for i in item_items])
                - mean([i["relation_rate"] for i in base_items])
            )
            term_diffs.append(
                mean([i["term_rate"] for i in item_items])
                - mean([i["term_rate"] for i in base_items])
            )
            major_diffs.append(
                mean([i["major_errors"] for i in item_items])
                - mean([i["major_errors"] for i in base_items])
            )
        if not rel_diffs:
            continue
        rel_ci = bootstrap_ci(rel_diffs, rng)
        term_ci = bootstrap_ci(term_diffs, rng)
        lines.append("| {} | {:+.3f} | [{:+.3f}, {:+.3f}] | {:+.3f} | [{:+.3f}, {:+.3f}] | {:+.2f} |".format(
            version,
            statistics.mean(rel_diffs), rel_ci[0], rel_ci[1],
            statistics.mean(term_diffs), term_ci[0], term_ci[1],
            statistics.mean(major_diffs),
        ))

    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 关系改对/新增、术语改对/新增按同一首诗、同一锚点、同一次重复配对后累计；多次重复的 Δ 是重复均值之差。重大错误的逐条 fixed/new 需要评分备注中的错误清单，本表先报净差。")
    lines.append("- S_R 只在有 `ratings_sr.csv` 时汇总；没有时显示 —。")
    lines.append("- n 很小（{}），bootstrap 区间只作描述，不作强推断。".format(args.label))

    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    csv_path = out.with_name(out.stem + "_items.csv")
    fieldnames = [
        "run_key", "poem_id", "version", "rep", "term_rate", "relation_rate",
        "term_scores", "relation_scores",
        "term_zero", "relation_zero", "major_errors", "minor_errors",
        "image_score", "emotion_score", "english_score", "format_pass",
        "s_r_total", "prompt_tokens", "completion_tokens", "reasoning_tokens",
        "latency_sec",
    ]
    csv_rows = []
    for item in items:
        row = dict(item)
        row["term_scores"] = ";".join(f"{key}:{value}" for key, value in item["term_scores"].items())
        row["relation_scores"] = ";".join(f"{key}:{value}" for key, value in item["relation_scores"].items())
        csv_rows.append(row)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"wrote {out}")
    print(f"wrote {csv_path}")
    print(f"items: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())