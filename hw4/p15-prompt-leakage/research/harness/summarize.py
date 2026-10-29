import json
import os
import sys
from collections import defaultdict
from pathlib import Path

path = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "results/pilot_L3.jsonl"
rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
rows = [r for r in rows if r.get("ok")]
print("rows", len(rows), "errors", sum(1 for l in open(path, encoding="utf-8") if l.strip()) - len(rows))

g = defaultdict(list)
for r in rows:
    g[(r["model"], r["attack"])].append(r)

attacks = [a for a in ["A_direct", "B_role", "C_translate", "D_repeat", "E_tools", "F_json", "G_code", "H_multiturn"]]
models = sorted({r["model"] for r in rows})


def pct(x, n):
    return f"{100*x/n:.0f}%" if n else "-"


print("\n## Per model / attack (answer-level)")
print("| model | attack | n | canary | verbatim | struct | any | refusal | avg s |")
print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
for m in models:
    for a in attacks:
        rs = g.get((m, a), [])
        if not rs:
            continue
        n = len(rs)
        can = sum(r["score"]["canary_answer"] for r in rs)
        ver = sum(r["score"]["verbatim_answer"] for r in rs)
        st = sum(r["score"]["struct_leak"] for r in rs)
        anyl = sum(r["score"]["canary_answer"] or r["score"]["verbatim_answer"] or r["score"]["struct_leak"] for r in rs)
        ref = sum(r["score"]["refusal"] for r in rs)
        sec = sum(r.get("sec", 0) for r in rs) / n
        print(f"| {m} | {a} | {n} | {pct(can,n)} | {pct(ver,n)} | {pct(st,n)} | {pct(anyl,n)} | {pct(ref,n)} | {sec:.1f} |")

print("\n## Per model summary (attacks only)")
print("| model | n | canary | verbatim | reasoning leak | struct | any | refusal |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for m in models:
    rs = [r for a in attacks for r in g.get((m, a), [])]
    n = len(rs)
    can = sum(r["score"]["canary_answer"] for r in rs)
    ver = sum(r["score"]["verbatim_answer"] for r in rs)
    rleak = sum(r["score"]["canary_reasoning"] or r["score"]["verbatim_reasoning"] for r in rs)
    st = sum(r["score"]["struct_leak"] for r in rs)
    anyl = sum(r["score"]["canary_answer"] or r["score"]["verbatim_answer"] or r["score"]["struct_leak"] for r in rs)
    ref = sum(r["score"]["refusal"] for r in rs)
    print(f"| {m} | {n} | {pct(can,n)} | {pct(ver,n)} | {pct(rleak,n)} | {pct(st,n)} | {pct(anyl,n)} | {pct(ref,n)} |")

print("\n## Controls")
print("| model | control | n | answered | refusal | struct |")
print("|---|---|---:|---:|---:|---:|")
for m in models:
    for c in ["C1_refund", "C2_support", "C3_policy"]:
        rs = g.get((m, c), [])
        if not rs:
            continue
        n = len(rs)
        ref = sum(r["score"]["refusal"] for r in rs)
        st = sum(r["score"]["struct_leak"] for r in rs)
        print(f"| {m} | {c} | {n} | {pct(n-ref,n)} | {pct(ref,n)} | {pct(st,n)} |")

print("\n## Errors by model")
err = defaultdict(int)
for line in open(path, encoding="utf-8"):
    try:
        r = json.loads(line)
    except Exception:
        continue
    if not r.get("ok"):
        err[r["model"]] += 1
print(dict(err))
