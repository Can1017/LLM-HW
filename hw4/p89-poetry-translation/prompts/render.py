#!/usr/bin/env python3
"""Render the four prompt versions for the P89 poetry translation experiment.

V0: base instruction + poem
V1: base + task criteria + poem
V2: base + poem-specific reference notes + poem
V3: base + boundary examples + poem

Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "poems.json"
PROMPT_DIR = ROOT / "prompts"
VERSIONS = ("v0", "v1", "v2", "v3")
VERSION_LABELS = {
    "v0": "direct translation (base only)",
    "v1": "task criteria added",
    "v2": "reference notes added",
    "v3": "boundary examples added",
}


def load_poems(path: Path = DATA) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_text(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").rstrip() + "\n"


def poem_block(poem: dict) -> str:
    title = f"Title: {poem['title_zh']} ({poem['title_en']})"
    author = f"Author: {poem['author_zh']} ({poem['author_en']}), {poem['dynasty']}"
    body = "\n".join(poem["text"])
    return f"{title}\n{author}\n\n{body}"


def reference_block(poem: dict) -> str:
    lines = "\n".join(f"- {note}" for note in poem["reference_notes"])
    return f"Reference notes for this poem:\n{lines}"


def build_prompt(poem: dict, version: str, base: str, criteria: str, examples: str) -> str:
    if version not in VERSIONS:
        raise ValueError(f"unknown version: {version}")

    parts = [base.rstrip()]
    if version == "v1":
        parts.append(criteria.rstrip())
    elif version == "v2":
        parts.append(reference_block(poem).rstrip())
    elif version == "v3":
        parts.append(examples.rstrip())
    parts.append(poem_block(poem).rstrip())
    return "\n\n".join(parts) + "\n"


def build_all(poems: list[dict], base: str, criteria: str, examples: str) -> list[dict]:
    records = []
    for poem in poems:
        for version in VERSIONS:
            prompt = build_prompt(poem, version, base, criteria, examples)
            records.append({
                "poem_id": poem["id"],
                "split": poem["split"],
                "version": version,
                "version_label": VERSION_LABELS[version],
                "prompt": prompt,
                "prompt_chars": len(prompt),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            })
    return records


def check_examples(poems: list[dict], examples: str) -> list[str]:
    """Return any boundary-example Chinese line that also appears in a scored poem."""
    problems = []
    example_lines = []
    for line in examples.splitlines():
        m = re.match(r"^\s*\d+\.\s*(.+?)\s*$", line)
        if m and re.search(r"[\u4e00-\u9fff]", m.group(1)):
            example_lines.append(m.group(1))
    for ex in example_lines:
        for poem in poems:
            if ex in poem["text_plain"]:
                problems.append(f"example line appears in {poem['id']}: {ex}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poem", help="poem id, e.g. T01")
    parser.add_argument("--version", choices=VERSIONS, help="prompt version")
    parser.add_argument("--all", action="store_true", help="render all poem x version prompts")
    parser.add_argument("--out", help="write rendered prompts as JSONL")
    parser.add_argument("--check-examples", action="store_true", help="check example/test overlap")
    parser.add_argument("--list", action="store_true", help="list poem ids and splits")
    args = parser.parse_args(argv)

    data = load_poems()
    poems = data["poems"]
    base = load_text("base.txt")
    criteria = load_text("v1_criteria.txt")
    examples = load_text("v3_examples.txt")

    if args.list:
        for poem in poems:
            print(f"{poem['id']}\t{poem['split']}\t{poem['title_zh']}")
        return 0

    if args.check_examples:
        problems = check_examples(poems, examples)
        if problems:
            print("FAIL")
            for problem in problems:
                print(" -", problem)
            return 1
        print("OK: no boundary-example line appears in the scored poems")
        return 0

    if args.all:
        records = build_all(poems, base, criteria, examples)
        payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload, encoding="utf-8")
            print(f"wrote {len(records)} prompts to {out}")
        else:
            sys.stdout.write(payload)
        return 0

    if not args.poem or not args.version:
        parser.error("use --poem and --version, or --all, or --check-examples, or --list")

    by_id = {poem["id"]: poem for poem in poems}
    if args.poem not in by_id:
        parser.error(f"unknown poem id: {args.poem}")
    prompt = build_prompt(by_id[args.poem], args.version, base, criteria, examples)
    sys.stdout.write(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())