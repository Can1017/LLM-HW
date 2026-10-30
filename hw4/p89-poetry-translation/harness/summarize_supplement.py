#!/usr/bin/env python3
"""Merge the version-hidden review with frozen ablation outputs."""
from __future__ import annotations
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    d=ROOT/'results/supplement'
    rows={r['run_key']:r for r in map(json.loads,(d/'raw.jsonl').read_text(encoding='utf-8').splitlines())}
    keys=json.loads((d/'key.json').read_text(encoding='utf-8'))
    ratings=json.loads((d/'ratings_review.json').read_text(encoding='utf-8'))['items']
    assert len(rows)==len(keys)==len(ratings)==24
    items=[]
    for k in keys:
        raw=rows[k['run_key']];rt=ratings[k['blind_id']]
        assert len(rt['terms'])==len(rt['relations'])==3
        assert all(v in [0,1,2] for v in rt['terms']+rt['relations'])
        u=raw['usage'];reason=u.get('completion_tokens_details',{}).get('reasoning_tokens',0)
        pieces=re.split(r'\n\s*Notes\s*:?\s*\n',raw['content'],maxsplit=1,flags=re.I)
        item=dict(k,terms=sum(rt['terms'])/6,relations=sum(rt['relations'])/6,english=rt['english'],format=rt['format'],major=rt['major'],note=rt['note'],
                  prompt_tokens=u['prompt_tokens'],completion_tokens=u['completion_tokens'],reasoning_tokens=reason,
                  total_tokens=u['prompt_tokens']+u['completion_tokens'],visible_tokens_estimate=u['completion_tokens']-reason,
                  latency_sec=raw['latency_sec'],notes_present=int(len(pieces)>1),
                  notes_lines=sum(bool(s.strip()) for s in pieces[1].splitlines()) if len(pieces)>1 else 0)
        items.append(item)
    summaries={}
    for cohort in ['all','diagnostic','new']:
        groups=defaultdict(list)
        for item in items:
            if cohort=='all' or item['cohort']==cohort:groups[item['condition']].append(item)
        summary={}
        for cond,group in sorted(groups.items()):
            x={k:statistics.mean(i[k] for i in group) for k in ['terms','relations','english','format','notes_present','notes_lines']}
            x.update({k:sum(i[k] for i in group) for k in ['major','prompt_tokens','completion_tokens','reasoning_tokens','total_tokens','visible_tokens_estimate','latency_sec']})
            x['n']=len(group);x['poems']=len({i['poem_id'] for i in group});summary[cond]=x
        summaries[cohort]=summary
    result=dict(summaries=summaries,items=items)
    (d/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (d/'scored_items.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    lines=['# 单条注释消融汇总','','24条；4首×3条件×2次。D02/D09是诊断材料，N01/N02是本项目新增材料。评分由参与设计的AI完成，非独立专家双盲。','','|材料|条件|输出/诗数|术语|关系|英语0–2|输入token|completion含推理|total token|延迟秒|有尾注|平均尾注行|','|---|---|---|---|---|---|---|---|---|---|---|---|']
    for cohort,summary in summaries.items():
        for cond,s in summary.items():
            lines.append(f"|{cohort}|{cond}|{s['n']}/{s['poems']}|{s['terms']:.2f}|{s['relations']:.2f}|{s['english']:.3f}|{s['prompt_tokens']}|{s['completion_tokens']}|{s['total_tokens']}|{s['latency_sec']:.3f}|{s['notes_present']:.0%}|{s['notes_lines']:.2f}|")
    lines+=['','术语/关系全部满分，不能把未观察到收益解释为等效性已获证明。英语分差主要由D09两条生硬措辞与D02一条搭配产生，须经独立专家复核。A1并未证明更省或更好，成本以实测为准。']
    (d/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
