#!/usr/bin/env python3
"""Run the frozen A0/A1/A2 single-note ablation, preserving complete responses."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'harness'))
import run_experiment as api

def prompts(poem):
    base = (ROOT / 'prompts/base.txt').read_text(encoding='utf-8').strip()
    body = f"Title: {poem['title']}\nAuthor: {poem['author']}, {poem['dynasty']}\n\n" + '\n'.join(poem['text'])
    for condition in ['a0', 'a1', 'a2']:
        parts = [base]
        if condition != 'a0':
            notes = [poem['single_note']]
            if condition == 'a2':
                notes += poem['other_notes']
            parts.append('Reference notes for this poem:\n' + '\n'.join('- ' + s for s in notes))
        parts.append(body)
        yield condition, '\n\n'.join(parts) + '\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Call API; otherwise only freeze config and prompts')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    datafile = ROOT / 'data/supplement_v1.json'
    poems = json.loads(datafile.read_text(encoding='utf-8'))['poems']
    dest = ROOT / 'results/supplement'
    dest.mkdir(parents=True, exist_ok=True)
    tasks = []
    for p in poems:
        for cond, prompt in prompts(p):
            for rep in [1, 2]:
                tasks.append(dict(run_key=f"{p['id']}-{cond}-r{rep}", poem_id=p['id'], cohort=p['cohort'], condition=cond, rep=rep, prompt=prompt, prompt_sha256=api.sha256_text(prompt)))
    random.Random(2026102904).shuffle(tasks)
    config = dict(created_at=api.now_iso(), model=api.DEFAULT_MODEL, temperature=0.2, max_tokens=12000,
                  seed=2026102904, reps=2, calls=len(tasks), data_sha256=api.sha256_file(datafile),
                  plan_sha256=api.sha256_file(ROOT/'reports/复核与补充实验方案.md'),
                  script_sha256=api.sha256_file(Path(__file__)), conditions=['a0','a1','a2'])
    cf = dest/'config.json'
    if cf.exists():
        prev = json.loads(cf.read_text(encoding='utf-8'))
        for key in ['data_sha256','plan_sha256','script_sha256']:
            if prev[key] != config[key]:
                raise SystemExit(f'Frozen {key} changed; use a distinct study directory')
    else:
        cf.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        (dest/'prompts.jsonl').write_text('\n'.join(json.dumps(t, ensure_ascii=False) for t in tasks)+'\n', encoding='utf-8')
    if not args.run:
        print('FROZEN', len(tasks), 'calls; no API requests made')
        return
    out = dest/'raw.jsonl'
    existing = {}
    if out.exists():
        if not args.resume:
            raise SystemExit('Results exist; use --resume')
        existing = {r['run_key']:r for r in api.load_jsonl(out)} if hasattr(api,'load_jsonl') else {r['run_key']:r for r in map(json.loads,out.read_text(encoding='utf-8').splitlines())}
    env = api.load_env(ROOT)
    for t in tasks:
        if t['run_key'] in existing:
            continue
        row = dict(t, timestamp=api.now_iso(), model_requested=api.DEFAULT_MODEL, temperature=0.2, max_tokens=12000)
        row.update(api.call_with_retries(env, api.DEFAULT_MODEL, t['prompt'], 12000, 0.2, retries=1))
        with out.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False)+'\n')
        print(t['run_key'], 'ok='+str(row['ok']), 'finish='+str(row['finish_reason']), 'seconds='+str(row['latency_sec']), flush=True)
        if not row['ok'] or not row.get('content') or row['finish_reason'] != 'stop':
            raise SystemExit('Non-complete response retained; stop rather than substitute model')

if __name__ == '__main__':
    main()
