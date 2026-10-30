#!/usr/bin/env python3
"""Run the P89 poetry translation experiment.

The script builds prompts from data/poems.json + prompts/, calls an
OpenAI-compatible /v1/chat/completions endpoint, and appends every response
(including failures) to a JSONL file. No third-party packages are required.

Examples:
  python harness/run_experiment.py --dry-run --poems T01 --versions v0,v1,v2,v3
  python harness/run_experiment.py --poems T01 --versions v0,v1,v2,v3 \
      --out results/pilot/pilot_T01.jsonl
  python harness/run_experiment.py --split dev --reps 1 \
      --out results/main_dev.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prompts"))
from render import VERSIONS, build_prompt, load_poems, load_text  # noqa: E402

DEFAULT_MODEL = "deepseek-v4.1-flash-1017"
RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504}


def find_env(start: Path) -> Path | None:
    for parent in [start] + list(start.parents):
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def load_env(start: Path) -> dict:
    env = {}
    path = find_env(start)
    if path is not None:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    for name in ("BASE_URL", "API_KEY"):
        if name in os.environ:
            env[name] = os.environ[name]
    missing = [name for name in ("BASE_URL", "API_KEY") if not env.get(name)]
    if missing:
        raise SystemExit(f"missing API configuration: {', '.join(missing)}")
    return env


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def chat_once(env: dict, model: str, prompt: str, max_tokens: int,
              temperature: float, timeout: int = 180) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        env["BASE_URL"].rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + env["API_KEY"],
            "Content-Type": "application/json",
        },
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            message = data["choices"][0]["message"]
            return {
                "ok": True,
                "http_status": response.status,
                "model_returned": data.get("model"),
                "content": message.get("content"),
                "reasoning_content": message.get("reasoning_content"),
                "usage": data.get("usage"),
                "finish_reason": data["choices"][0].get("finish_reason"),
                "latency_sec": round(time.time() - started, 3),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:1200]
        return {
            "ok": False,
            "http_status": exc.code,
            "model_returned": None,
            "content": None,
            "reasoning_content": None,
            "usage": None,
            "finish_reason": None,
            "latency_sec": round(time.time() - started, 3),
            "error": f"HTTP {exc.code}: {body_text}",
        }
    except Exception as exc:  # URLError, timeout, JSON decode, etc.
        return {
            "ok": False,
            "http_status": None,
            "model_returned": None,
            "content": None,
            "reasoning_content": None,
            "usage": None,
            "finish_reason": None,
            "latency_sec": round(time.time() - started, 3),
            "error": repr(exc),
        }


def call_with_retries(env: dict, model: str, prompt: str, max_tokens: int,
                      temperature: float, retries: int = 3) -> dict:
    attempt_errors = []
    for attempt in range(1, retries + 1):
        result = chat_once(env, model, prompt, max_tokens, temperature)
        result["attempts"] = attempt
        if result["ok"]:
            result["attempt_errors"] = attempt_errors
            return result
        attempt_errors.append(result["error"])
        status = result.get("http_status")
        retryable = status is None or status in RETRYABLE
        if attempt == retries or not retryable:
            break
        time.sleep(min(2 ** (attempt - 1), 8) + random.random() * 0.5)
    result["attempt_errors"] = attempt_errors
    return result


def select_poems(poems: list[dict], poem_arg: str | None, split: str | None) -> list[dict]:
    if poem_arg:
        wanted = {item.strip() for item in poem_arg.split(",") if item.strip()}
        selected = [poem for poem in poems if poem["id"] in wanted]
        missing = wanted - {poem["id"] for poem in selected}
        if missing:
            raise SystemExit(f"unknown poem ids: {', '.join(sorted(missing))}")
        return selected
    if split:
        if split == "all":
            return poems
        selected = [poem for poem in poems if poem["split"] == split]
        if not selected:
            raise SystemExit(f"no poems for split: {split}")
        return selected
    return poems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poems", help="comma-separated poem ids, e.g. T01,T04")
    parser.add_argument("--split", choices=["dev", "test", "all"], help="select by split")
    parser.add_argument("--versions", default=",".join(VERSIONS), help="comma-separated: v0,v1,v2,v3")
    parser.add_argument("--reps", type=int, default=1, help="repetitions per poem x version")
    parser.add_argument("--out", default=str(ROOT / "results" / "run.jsonl"), help="output JSONL")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--order", choices=["random", "fixed"], default="random")
    parser.add_argument("--resume", action="store_true", help="skip run keys already in --out")
    parser.add_argument("--force", action="store_true", help="overwrite an existing --out")
    parser.add_argument("--dry-run", action="store_true", help="build prompts but do not call the API")
    parser.add_argument("--sleep", type=float, default=0.2, help="pause between calls (seconds)")
    args = parser.parse_args(argv)

    versions = [item.strip() for item in args.versions.split(",") if item.strip()]
    unknown = set(versions) - set(VERSIONS)
    if unknown:
        raise SystemExit(f"unknown versions: {', '.join(sorted(unknown))}")
    if args.reps < 1:
        raise SystemExit("--reps must be >= 1")

    data = load_poems()
    poems = select_poems(data["poems"], args.poems, args.split)
    base = load_text("base.txt")
    criteria = load_text("v1_criteria.txt")
    examples = load_text("v3_examples.txt")

    tasks = []
    for poem in poems:
        for version in versions:
            for rep in range(1, args.reps + 1):
                tasks.append({"poem": poem, "version": version, "rep": rep})
    if args.order == "random":
        random.Random(args.seed).shuffle(tasks)

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if out.exists() and not args.force and not args.resume:
        raise SystemExit(f"output exists: {out}; use --resume or --force")
    if out.exists() and args.resume:
        with open(out, encoding="utf-8") as f:
            for line in f:
                try:
                    existing.add(json.loads(line)["run_key"])
                except Exception:
                    continue

    env = None if args.dry_run else load_env(ROOT)

    config = {
        "started_at": now_iso(),
        "model_requested": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "retries": args.retries,
        "reps": args.reps,
        "seed": args.seed,
        "order": args.order,
        "poems": [poem["id"] for poem in poems],
        "versions": versions,
        "output": str(out),
        "argv": sys.argv,
        "gateway_host": None if env is None else urllib.parse.urlparse(env["BASE_URL"]).netloc,
        "prompt_hashes": {
            "base": sha256_text(base),
            "v1_criteria": sha256_text(criteria),
            "v3_examples": sha256_text(examples),
        },
        "data_sha256": sha256_file(ROOT / "data" / "poems.json"),
        "render_sha256": sha256_file(ROOT / "prompts" / "render.py"),
        "run_script_sha256": sha256_file(Path(__file__)),
    }
    config_path = out.parent / (out.stem + "_config.json")
    if not args.dry_run:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"tasks: {len(tasks)} | poems: {len(poems)} | versions: {len(versions)} | reps: {args.reps}")
    if args.dry_run:
        if tasks:
            first = tasks[0]
            prompt = build_prompt(first["poem"], first["version"], base, criteria, examples)
            print("\n--- first prompt (dry-run) ---")
            print(prompt)
            print(f"--- prompt chars: {len(prompt)} ---")
        print("dry-run: no API calls")
        return 0

    total = 0
    ok_count = 0
    with open(out, "a", encoding="utf-8") as f:
        for index, task in enumerate(tasks, start=1):
            poem = task["poem"]
            version = task["version"]
            rep = task["rep"]
            run_key = f"{poem['id']}-{version}-r{rep}"
            if run_key in existing:
                print(f"[{index}/{len(tasks)}] skip {run_key}")
                continue

            prompt = build_prompt(poem, version, base, criteria, examples)
            result = call_with_retries(
                env, args.model, prompt, args.max_tokens, args.temperature, args.retries
            )
            record = {
                "run_key": run_key,
                "run_id": f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}",
                "timestamp": now_iso(),
                "poem_id": poem["id"],
                "split": poem["split"],
                "version": version,
                "rep": rep,
                "model_requested": args.model,
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
                "prompt": prompt,
                "prompt_sha256": sha256_text(prompt),
                **result,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            total += 1
            if result["ok"]:
                ok_count += 1
                content = result.get("content") or ""
                print(
                    f"[{index}/{len(tasks)}] {run_key}: ok, {len(content)} chars, "
                    f"{result['latency_sec']}s, attempts={result['attempts']}"
                )
            else:
                print(f"[{index}/{len(tasks)}] {run_key}: FAILED {result['error']}")
            if args.sleep:
                time.sleep(args.sleep)

    print(f"wrote {total} records ({ok_count} ok) to {out}")
    print(f"config: {config_path}")
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())