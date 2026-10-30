#!/usr/bin/env python3
"""Surface-level stability check for repeated samples.

For each poem x version, combine the main run (rep 1) with the stability run
(reps 1 and 2), then report length, line count, Notes presence, pairwise text
similarity, and obvious format problems. This is not a semantic rating; items
with low similarity are flagged for manual review.

Usage:
  python harness/stability.py --main results/main_dev.jsonl \
      --stability results/stability_dev.jsonl --out results/stability_dev.md
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def has_notes(text: str) -> bool:
    return bool(re.search(r"(?im)^\s*notes\s*$", text))


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", default=str(ROOT / "results" / "main_dev.jsonl"))
    parser.add_argument("--stability", default=str(ROOT / "results" / "stability_dev.jsonl"))
    parser.add_argument("--out", default=str(ROOT / "results" / "stability_dev.md"))
    args = parser.parse_args(argv)

    main_rows = [r for r in load_jsonl(resolve(args.main)) if r.get("ok")]
    stability_rows = [r for r in load_jsonl(resolve(args.stability)) if r.get("ok")]
    groups = defaultdict(list)
    for row in main_rows:
        groups[(row["poem_id"], row["version"])].append(("main-r1", row))
    for row in stability_rows:
        groups[(row["poem_id"], row["version"])].append((f"stab-r{row.get('rep')}", row))

    lines = ["# 稳定性检查（表层）", ""]
    lines.append("同一首诗、同一版本的三次采样：主实验 1 次 + 稳定性 2 次。")
    lines.append("相似度是文本层面的 `difflib` 比值，不是语义评分；低相似度项需要人工复核。")
    lines.append("")
    lines.append("| 诗 | 版本 | 样本 | 字符 | 行数 | Notes | 与主实验相似度 | 延迟秒 | 备注 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    flags = []
    for (poem_id, version) in sorted(groups):
        samples = groups[(poem_id, version)]
        base = next((row for label, row in samples if label == "main-r1"), None)
        base_text = (base or {}).get("content") or ""
        for label, row in samples:
            text = row.get("content") or ""
            sim = similarity(base_text, text) if base_text else float("nan")
            notes = "有" if has_notes(text) else "无"
            notes_flags = []
            if not text.strip():
                notes_flags.append("空正文")
            if len(text) < 40:
                notes_flags.append("过短")
            if sim == sim and sim < 0.60 and label != "main-r1":
                notes_flags.append("相似度低，需复核")
            if notes_flags:
                flags.append((poem_id, version, label, "；".join(notes_flags)))
            lines.append("| {} | {} | {} | {} | {} | {} | {:.2f} | {:.2f} | {} |".format(
                poem_id, version, label, len(text), line_count(text), notes, sim,
                row.get("latency_sec") or 0, "；".join(notes_flags) or "",
            ))
        lines.append("| — | — | — | — | — | — | — | — | — |")

    lines.append("")
    lines.append("## 需要人工复核的项")
    lines.append("")
    if flags:
        for poem_id, version, label, reason in flags:
            lines.append(f"- {poem_id} {version} {label}: {reason}")
    else:
        lines.append("- 无（仅表层检查；语义稳定性仍需评分）")

    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"groups: {len(groups)} | flags: {len(flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())