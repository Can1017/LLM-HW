#!/usr/bin/env python3
"""Apply manually recorded ratings (JSON) to a blind ratings CSV.

The JSON is keyed by blind_id and contains either S_F fields
(term_scores, relation_scores, major_errors, ...) or S_R fields
(s_r_core, s_r_imagery, s_r_poem, s_r_misread).

Usage:
  python harness/apply_ratings.py --ratings results/blind/ratings_sf_manual.json --standard sf
  python harness/apply_ratings.py --ratings results/blind/ratings_sr_manual.json --standard sr
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLIND = ROOT / "results" / "blind"


def fill_scores(existing: str, scores: dict, label: str, blind_id: str) -> str:
    ids = [part.split(":", 1)[0] for part in (existing or "").split(";") if part.strip()]
    missing = [key for key in ids if key not in scores]
    if missing:
        raise SystemExit(f"{blind_id}: missing {label} scores for {missing}")
    extra = [key for key in scores if key not in ids]
    if extra:
        raise SystemExit(f"{blind_id}: unexpected {label} ids {extra}")
    return ";".join(f"{key}:{int(scores[key])}" for key in ids)


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--standard", choices=["sf", "sr", "rel"], required=True)
    parser.add_argument("--csv", help="default: results/blind/ratings_<standard>.csv")
    parser.add_argument("--out", help="default: same as --csv")
    args = parser.parse_args(argv)

    csv_path = resolve(args.csv) if args.csv else BLIND / f"ratings_{args.standard}.csv"
    out_path = resolve(args.out) if args.out else csv_path
    with open(resolve(args.ratings), encoding="utf-8") as f:
        ratings = json.load(f)
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    matched = 0
    for row in rows:
        blind_id = row["blind_id"]
        if blind_id not in ratings:
            continue
        entry = ratings[blind_id]
        matched += 1
        if args.standard == "sf":
            row["term_scores"] = fill_scores(row["term_scores"], entry["term_scores"], "term", blind_id)
            row["relation_scores"] = fill_scores(row["relation_scores"], entry["relation_scores"], "relation", blind_id)
            row["major_errors"] = str(entry["major_errors"])
            row["minor_errors"] = str(entry["minor_errors"])
            row["error_log"] = entry.get("error_log", "")
            row["image_score"] = str(entry["image_score"])
            row["emotion_score"] = str(entry["emotion_score"])
            row["english_score"] = str(entry["english_score"])
            row["format_pass"] = str(entry["format_pass"])
            row["notes"] = entry.get("notes", "")
        elif args.standard == "rel":
            row["term_scores"] = fill_scores(row["term_scores"], entry["term_scores"], "term", blind_id)
            row["relation_scores"] = fill_scores(row["relation_scores"], entry["relation_scores"], "relation", blind_id)
            row["major_errors"] = str(entry["major_errors"])
            row["minor_errors"] = str(entry["minor_errors"])
            row["notes"] = entry.get("notes", "")
        else:
            for field in ("s_r_core", "s_r_imagery", "s_r_poem", "s_r_misread"):
                row[field] = str(entry[field])
            row["notes"] = entry.get("notes", "")

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"matched {matched}/{len(rows)} rows -> {out_path}")
    missing = sorted(set(row["blind_id"] for row in rows) - set(ratings))
    if missing:
        print(f"not yet rated: {len(missing)} ({', '.join(missing[:8])}{'...' if len(missing) > 8 else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())