#!/usr/bin/env python3
"""Build blind rating packets from a run JSONL.

The packet contains the poem, the scoring anchors (S_F only), and the
translation, but never the version name. The blind_id -> version mapping is
written to a separate key file that should not be opened until rating is done.

Usage:
  python harness/make_blind_packet.py --results results/main_dev.jsonl --standard sf
  python harness/make_blind_packet.py --results results/main_dev.jsonl --standard sr
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "poems.json"
# Terms that occur only in the title. The shared output contract forbids
# repeating the title, so they cannot be scored as body terms.
TITLE_ONLY_TERMS = {"T01-T1", "T02-T1"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_records(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("ok") and (record.get("content") or "").strip():
                records.append(record)
    return records


def sf_block(index: int, record: dict, poem: dict) -> str:
    terms = "\n".join(
        f"- {t['id']} {t['zh']}：{t['gloss']}"
        for t in poem["terms"] if t["id"] not in TITLE_ONLY_TERMS
    )
    relations = "\n".join(f"- {r['id']} {r['type']}：{r['description']}" for r in poem["relations"])
    return f"""## B{index:03d} · {poem['id']} {poem['title_zh']}

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
{record['content'].strip()}
```

---
"""


def sr_block(index: int, record: dict, poem: dict) -> str:
    return f"""## B{index:03d} · {poem['id']} {poem['title_zh']}

**原文**

```text
{poem['text_plain']}
```

**译文**

```text
{record['content'].strip()}
```

---
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=str(ROOT / "results" / "main_dev.jsonl"))
    parser.add_argument("--standard", choices=["sf", "sr"], required=True)
    parser.add_argument("--out-dir", default=str(ROOT / "results" / "blind"))
    parser.add_argument("--seed", type=int, default=20261029)
    args = parser.parse_args(argv)

    results_path = Path(args.results)
    if not results_path.is_absolute():
        results_path = ROOT / results_path
    with open(DATA, encoding="utf-8") as f:
        poems = json.load(f)["poems"]
    by_id = {poem["id"]: poem for poem in poems}

    records = load_records(results_path)
    if not records:
        raise SystemExit(f"no successful records in {results_path}")
    random.Random(args.seed).shuffle(records)

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    key_items = []
    rows = []
    blocks = []
    for index, record in enumerate(records, start=1):
        blind_id = f"B{index:03d}"
        poem = by_id[record["poem_id"]]
        key_items.append({
            "blind_id": blind_id,
            "run_key": record.get("run_key"),
            "poem_id": record["poem_id"],
            "version": record.get("version"),
            "rep": record.get("rep"),
            "content_sha256": sha256_text(record.get("content") or ""),
        })
        if args.standard == "sf":
            blocks.append(sf_block(index, record, poem))
            rows.append({
                "blind_id": blind_id,
                "poem_id": record["poem_id"],
                "term_scores": ";".join(f"{t['id']}:" for t in poem["terms"] if t["id"] not in TITLE_ONLY_TERMS),
                "relation_scores": ";".join(f"{r['id']}:" for r in poem["relations"]),
                "major_errors": "",
                "minor_errors": "",
                "error_log": "",
                "image_score": "",
                "emotion_score": "",
                "english_score": "",
                "format_pass": "",
                "notes": "",
            })
        else:
            blocks.append(sr_block(index, record, poem))
            rows.append({
                "blind_id": blind_id,
                "poem_id": record["poem_id"],
                "s_r_core": "",
                "s_r_imagery": "",
                "s_r_poem": "",
                "s_r_misread": "",
                "notes": "",
            })

    if args.standard == "sf":
        header = """# P89 盲评包：S_F（忠实文学译介）

> 评分依据：`../reports/评分细则_v1.md` 的 S_F 部分。
> 本包不含版本名；`blind_id` 与版本/运行的对应关系在 `key_sf.json`，评分完成前不要打开。
> 评分写入 `ratings_sf.csv`；不要在这一份 Markdown 上直接改分。
> 先读原文与术语/关系锚点，再读译文；先评含义/术语/关系，再评意象/情感/英语/格式。

"""
    else:
        header = """# P89 盲评包：S_R（自由改写视角）

> 评分依据：`../reports/评分细则_v1.md` 的 S_R 部分。
> 把每条译文当作“受原诗启发的英语诗”来评；允许重组、增删意象、改变行序，不惩罚有意的改写。
> 本包不含版本名；对应关系在 `key_sr.json`，评分完成前不要打开。
> 评分写入 `ratings_sr.csv`。

"""

    packet_path = out_dir / f"packet_{args.standard}.md"
    packet_path.write_text(header + "\n".join(blocks), encoding="utf-8")

    csv_path = out_dir / f"ratings_{args.standard}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    key_path = out_dir / f"key_{args.standard}.json"
    key_path.write_text(json.dumps({
        "standard": args.standard,
        "seed": args.seed,
        "results": str(results_path),
        "results_sha256": sha256_text(results_path.read_text(encoding="utf-8")),
        "items": key_items,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(rows)} items -> {packet_path}")
    print(f"ratings -> {csv_path}")
    print(f"key (do not open while rating) -> {key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())