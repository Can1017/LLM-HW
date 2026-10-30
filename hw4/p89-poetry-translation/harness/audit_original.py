#!/usr/bin/env python3
"""Recompute historical scores and explicit post-hoc sensitivity scenarios.

Does not edit the historical data, prompts, ratings, or summary files.
"""
from __future__ import annotations
import copy
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def jsonl(p):
    return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def load_items(split):
    folder, batch = ('blind','main_dev') if split == 'dev' else ('blind_test','test_holdout')
    runs = {r['run_key']:r for r in jsonl(ROOT/f'results/{batch}.jsonl')}
    keys = json.loads((ROOT/f'results/{folder}/key_sf.json').read_text(encoding='utf-8'))['items']
    ratings = json.loads((ROOT/f'results/{folder}/ratings_sf_manual.json').read_text(encoding='utf-8'))
    out = []
    for key in keys:
        rat = copy.deepcopy(ratings[key['blind_id']])
        row = dict(key, **rat)
        row['split'] = split
        row['term_scores'] = {k:v for k,v in row['term_scores'].items() if k not in ['T01-T1','T02-T1']}
        row['raw'] = runs[key['run_key']]
        for name in ['term_scores','relation_scores']:
            assert all(v in [0,1,2] for v in row[name].values())
        out.append(row)
    assert len(out) == len(runs)
    return out

def rate(item, field):
    values = item[field].values()
    return sum(values)/(2*len(item[field]))

def summarize(items):
    groups = defaultdict(list)
    for it in items:
        groups[it['version']].append(it)
    out = {}
    for name, group in sorted(groups.items()):
        def avg(k):return statistics.mean(i[k] for i in group)
        usage = [it['raw']['usage'] for it in group]
        prompt = sum(u['prompt_tokens'] for u in usage)
        completion = sum(u['completion_tokens'] for u in usage)
        reasoning = sum(u.get('completion_tokens_details',{}).get('reasoning_tokens',0) for u in usage)
        out[name] = dict(n=len(group), poems=len(set(i['poem_id'] for i in group)),
          term=statistics.mean(rate(i,'term_scores') for i in group),
          relation=statistics.mean(rate(i,'relation_scores') for i in group),
          english=avg('english_score'), imagery=avg('image_score'), emotion=avg('emotion_score'),
          major=sum(i['major_errors'] for i in group), minor=sum(i['minor_errors'] for i in group),
          format_pass=avg('format_pass'), prompt_tokens=prompt, completion_tokens=completion,
          reasoning_tokens=reasoning, visible_tokens_estimate=completion-reasoning,
          total_tokens=prompt+completion, latency_sec=sum(i['raw']['latency_sec'] for i in group))
    return out

def transitions(items):
    base={(i['poem_id'],i['rep']):i for i in items if i['version']=='v0'}
    counts=defaultdict(lambda:defaultdict(int))
    for i in items:
        if i['version']=='v0':continue
        b=base[(i['poem_id'],i['rep'])]
        for f in ['term_scores','relation_scores']:
            for k,v in i[f].items():
                before=b[f][k]
                if v != before:counts[i['version']][f'{f}:{before}->{v}']+=1
    return {k:dict(v) for k,v in counts.items()}

def main():
    dest=ROOT/'results/audit';dest.mkdir(parents=True,exist_ok=True)
    dev,test=load_items('dev'),load_items('test')
    # Check recomputation against the existing item CSVs rather than trusting prose.
    for items,tag in [(dev,'dev'),(test,'test')]:
        with (ROOT/f'results/scored_{tag}_items.csv').open(encoding='utf-8',newline='') as f:
            expected={r['run_key']:r for r in csv.DictReader(f)}
        for i in items:
            e=expected[i['run_key']]
            assert abs(float(e['term_rate'])-rate(i,'term_scores'))<1e-10
            assert abs(float(e['relation_rate'])-rate(i,'relation_scores'))<1e-10
    minimal=copy.deepcopy(test)
    for i in minimal:
        if i['poem_id']=='T09' and i['version']=='v0':
            i['relation_scores']['T09-R3']=2
            i['minor_errors']=max(0,i['minor_errors']-1)
    generous=copy.deepcopy(dev)
    changes=[]
    for i in generous:
        if i['poem_id']=='T02':
            for k,v in i['term_scores'].items():
                if v<2:changes.append(dict(run_key=i['run_key'],anchor=k,before=v,after=2,reason='功能对等异译可接受，不按词典逐字匹配'))
                i['term_scores'][k]=2
            if i['relation_scores']['T02-R2']<2:
                changes.append(dict(run_key=i['run_key'],anchor='T02-R2',before=1,after=2,reason='thousand li 本身不是把夸张误作精确测量的证据'))
                i['relation_scores']['T02-R2']=2
            i['minor_errors']=0
        if i['poem_id']=='T04' and i['version']=='v0':
            for k in ['T04-R1','T04-R3']:
                changes.append(dict(run_key=i['run_key'],anchor=k,before=i['relation_scores'][k],after=2,reason='When shall we 的范围可覆盖 and talk；承认合理未来回忆读法'))
                i['relation_scores'][k]=2
            i['minor_errors']=0
    checks=[]
    all_runs=[]
    for batch,expected_n in [('main_dev',32),('stability_dev',24),('test_holdout',16)]:
        runs=jsonl(ROOT/f'results/{batch}.jsonl');assert len(runs)==expected_n
        assert len({r['run_key'] for r in runs})==len(runs)
        conf=json.loads((ROOT/f'results/{batch}_config.json').read_text(encoding='utf-8'))
        integrity = {
          'data':hashlib.sha256((ROOT/'data/poems.json').read_bytes()).hexdigest()==conf['data_sha256'],
          'render':hashlib.sha256((ROOT/'prompts/render.py').read_bytes()).hexdigest()==conf['render_sha256'],
          'run_script':hashlib.sha256((ROOT/'harness/run_experiment.py').read_bytes()).hexdigest()==conf['run_script_sha256'],
        }
        for r in runs:
            assert r['ok'] and r['content'] and r['finish_reason']=='stop'
            assert hashlib.sha256(r['prompt'].encode('utf-8')).hexdigest()==r['prompt_sha256']
            assert r['temperature']==0.2 and r['max_tokens']==12000
        all_runs+=runs
        checks.append(dict(batch=batch,n=len(runs),prompt_hashes_valid=True,config_hashes=integrity))
    coverage={}
    for split in ['dev','test']:
        keys=json.loads((ROOT/f'results/reliability/key_reliability_{split}.json').read_text(encoding='utf-8'))['items']
        coverage[split]=dict(n=len(keys),poems=sorted({i['poem_id'] for i in keys}))
    payload=dict(checks=checks,coverage=coverage,
       original=dict(dev=summarize(dev),test=summarize(test)),
       sensitivity=dict(test_consistent_ambiguity=summarize(minimal),dev_accept_reasonable_translations=summarize(generous)),
       transitions=dict(dev=transitions(dev),test=transitions(test)),
       changes=changes,
       totals=dict(calls=len(all_runs),prompt=sum(r['usage']['prompt_tokens'] for r in all_runs),
                   completion=sum(r['usage']['completion_tokens'] for r in all_runs),
                   reasoning=sum(r['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0) for r in all_runs),
                   latency_sec=sum(r['latency_sec'] for r in all_runs)))
    write_json(dest/'historical_audit.json',payload)
    lines=['# 原始结果核算与评分敏感性分析','','历史数据与评分未覆盖；下表的敏感性列属于事后分析。','',
      '|数据与口径|版本|术语归一化分|关系归一化分|英语0–2|重大/次要|', '|---|---|---|---|---|---|']
    for label,summary in [('开发原评分',payload['original']['dev']),('开发合理异译敏感性',payload['sensitivity']['dev_accept_reasonable_translations']),('测试原评分',payload['original']['test']),('测试统一歧义口径',payload['sensitivity']['test_consistent_ambiguity'])]:
        for v,s in summary.items():
            lines.append(f"|{label}|{v}|{s['term']:.4f}|{s['relation']:.4f}|{s['english']:.3f}|{s['major']}/{s['minor']}|")
    lines += ['', '## 核查结果', '',f"正式原始调用 {len(all_runs)} 条；逐条提示哈希与生成状态通过核对。配置文件的数据、渲染脚本、运行脚本哈希匹配见 JSON。",'',
      f"开发重评实际覆盖 {coverage['dev']['poems']}；测试重评实际覆盖 {coverage['test']['poems']}。测试重评并未覆盖4首。",'',
      '原术语/关系均无0分。因此历史“改对”应称得分上升（主要1→2），不能称完全错误修复。分数下降也不一律等于新增严重误译。', '',
      'T09严格复现原细则“合理单一解读可满分”后，两版关系均为1.00。英语原分保留，避免同时改多个维度。', '',
      '开发敏感性分析仅展示T02功能对等异译与T04时间读法争议对结论的影响，不宣称重新建立文学翻译金标准。', '',
      '满分测试表示未观察到额外收益；不能排除更难材料上的注释价值。T08 terrace保留原部分得分，其可接受程度应由独立专家进一步判断。']
    (dest/'historical_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(checks=checks,coverage=coverage,original=payload['original'],sensitivity=payload['sensitivity'],transitions=payload['transitions']),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
