#!/usr/bin/env python3
"""Build a small re-rating packet for rater consistency.

Selects N items per version from an already rated run (stratified), assigns new
random IDs, and writes a fresh packet + CSV. The key maps the new IDs back to
the original run/blind_id; it should stay closed until re-rating is done.

Usage:
  python harness/make_reliability_packet.py --results results/main_dev.jsonl \
      --ratings-sf results/blind/ratings_sf.csv --key-sf results/blind/key_sf.json \
      --tag dev --per-version 2
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE_ONLY_TERMS = {"T01-T1", "T02-T1"}


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--ratings-sf", required=True)
    parser.add_argument("--key-sf", required=True)
    parser.add_argument("--tag", default="dev")
    parser.add_argument("--per-version", type=int, default=2)
    parser.add_argument("--selection", choices=["first", "rotate"], default="rotate",
                        help="first: 每版取排序前 N 条；rotate: 按版本轮换，覆盖不同诗")
    parser.add_argument("--seed", type=int, default=20261031)
    parser.add_argument("--out-dir", default=str(ROOT / "results" / "reliability"))
    args = parser.parse_args(argv)

    poems = {p["id"]: p for p in load_json(ROOT / "data" / "poems.json")["poems"]}
    key_by_blind = {item["blind_id"]: item for item in load_json(resolve(args.key_sf))["items"]}
    records = {row["run_key"]: row for row in load_jsonl(resolve(args.results))}
    with open(resolve(args.ratings_sf), encoding="utf-8") as f:
        ratings = list(csv.DictReader(f))

    rated_runs = set()
    for row in ratings:
        key = key_by_blind.get(row["blind_id"])
        if key and row.get("relation_scores") and row.get("major_errors") != "":
            rated_runs.add(key["run_key"])

    by_version = defaultdict(list)
    for key in key_by_blind.values():
        if key["run_key"] in rated_runs:
            by_version[key["version"]].append(key)

    selected = []
    for version_index, version in enumerate(sorted(by_version)):
        items = sorted(by_version[version], key=lambda item: item["poem_id"])
        if not items:
            continue
        if args.selection == "first":
            chosen = items[: args.per_version]
        else:
            start = (version_index * args.per_version) % len(items)
            chosen = [items[(start + offset) % len(items)] for offset in range(args.per_version)]
        selected.extend(chosen)
    random.Random(args.seed).shuffle(selected)

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = []
    rows = []
    key_items = []
    header = f"""# P89 二次盲评（一致性检查，{args.tag}）

> 目的：检查同一评分者在换编号、换顺序后，术语/关系/重大错误是否稳定。
> 本包不含版本名；对应关系在 `key_reliability_{args.tag}.json`，评完前不要打开。
> 评分写入 `ratings_reliability_{args.tag}.csv`。
> 只评术语（0–2）、关系（0–2）、重大/次要错误数；不评意象/情感/英语/格式。

"""
    for index, key in enumerate(selected, start=1):
        rid = f"R{index:03d}"
        poem = poems[key["poem_id"]]
        record = records[key["run_key"]]
        terms = "\n".join(
            f"- {t['id']} {t['zh']}：{t['gloss']}"
            for t in poem["terms"] if t["id"] not in TITLE_ONLY_TERMS
        )
        relations = "\n".join(f"- {r['id']} {r['type']}：{r['description']}" for r in poem["relations"])
        blocks.append(f"""## {rid} · {poem['id']} {poem['title_zh']}

**原文**

```text
{poem['text_plain']}
```

**术语锚点**

{terms}

**关系锚点**

{relations}

**译文**

```text
{(record.get('content') or '').strip()}
```

---
""")
        rows.append({
            "blind_id": rid,
            "poem_id": key["poem_id"],
            "term_scores": ";".join(f"{t['id']}:" for t in poem["terms"] if t["id"] not in TITLE_ONLY_TERMS),
            "relation_scores": ";".join(f"{r['id']}:" for r in poem["relations"]),
            "major_errors": "",
            "minor_errors": "",
            "notes": "",
        })
        key_items.append({
            "rid": rid,
            "original_blind_id": key["blind_id"],
            "run_key": key["run_key"],
            "poem_id": key["poem_id"],
            "version": key["version"],
        })

    packet = out_dir / f"packet_reliability_{args.tag}.md"
    packet.write_text(header + "\n".join(blocks), encoding="utf-8")
    csv_path = out_dir / f"ratings_reliability_{args.tag}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    key_path = out_dir / f"key_reliability_{args.tag}.json"
    key_path.write_text(json.dumps({"tag": args.tag, "seed": args.seed, "items": key_items}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(rows)} items -> {packet}")
    print(f"ratings -> {csv_path}")
    print(f"key -> {key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())