"""Build precise code permalinks and paper reading records from cached evidence."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research'
manifest=json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
papers=json.loads((DATA/'references-verified.json').read_text(encoding='utf-8'))
reading={
 '2203.02155':'PDF pp.6-9, sections 3.1 and 3.5',
 '2305.18290':'PDF sections 3-4, DPO derivation and objective',
 '2402.03300':'GRPO section, reward and group-relative objective',
 '2412.19437':'PDF pp.28-30,34, section 5',
 '2501.12948':'PDF pp.2-8, sections 2-3; v2 revised January 2026',
 '2503.14476':'PDF method section, Clip-Higher, Dynamic Sampling, Token-Level Policy Gradient and Overlong Reward Shaping',
 '2503.20783':'GRPO bias and Dr.GRPO objective',
 '2505.09388':'PDF pp.9-12 and20-21, section4 and distillation comparison',
 '2507.18071':'PDF pp.2-5, sections4.1-4.3, Eq.5-17',
 '2512.02556':'PDF pp.5-10, section3',
 '2602.02276':'PDF pp.4-6, section3 and section4.4',
 '2602.15763':'PDF pp.10-17, sections3-4',
 '2602.04879':'PDF pp.4-7, sections4-5 and AppendixB; v3 revised June2026'
}
for p in papers:
    text=(DATA/'papers'/(p['id']+'.txt')).read_text(encoding='utf-8')
    m=re.search(r'arXiv:'+re.escape(p['id'])+r'v(\d+)\s+\[.*?\]\s+([^\n]+)',text)
    if m:
        p['pdf_version']=int(m[1]); p['revision_date']=m[2].strip()
    p['url']=f"https://arxiv.org/abs/{p['id']}v{p['pdf_version']}"
    p['sections_read']=reading[p['id']]
    p['status']='primary PDF inspected; relevant methods read'
manifest['papers']=papers
(DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(DATA/'references-verified.json').write_text(json.dumps(papers,ensure_ascii=False,indent=2),encoding='utf-8')

specs={
 'trl':[
  ('trl/trainer/dpo_trainer.py','DPOTrainer','_precompute_ref_logps'),
  ('trl/trainer/dpo_trainer.py','DPOTrainer','_compute_loss'),
  ('trl/trainer/grpo_trainer.py','GRPOTrainer','_prepare_inputs'),
  ('trl/trainer/grpo_trainer.py','GRPOTrainer','_generate_and_score_completions'),
  ('trl/trainer/grpo_trainer.py','GRPOTrainer','_compute_loss')],
 'verl':[
  ('verl/trainer/main_ppo.py',None,'run_ppo'),
  ('verl/trainer/ppo/ray_trainer.py','RayPPOTrainer','fit'),
  ('verl/trainer/ppo/ray_trainer.py',None,'compute_advantage'),
  ('verl/trainer/ppo/ray_trainer.py','RayPPOTrainer','_update_actor'),
  ('verl/trainer/ppo/core_algos.py',None,'compute_gae_advantage_return'),
  ('verl/trainer/ppo/core_algos.py',None,'compute_grpo_outcome_advantage'),
  ('verl/trainer/ppo/core_algos.py',None,'agg_loss'),
  ('verl/trainer/ppo/core_algos.py',None,'compute_policy_loss_vanilla'),
  ('verl/trainer/ppo/core_algos.py',None,'compute_policy_loss_gspo'),
  ('verl/trainer/ppo/core_algos.py',None,'compute_policy_loss_dppo_tv'),
  ('verl/trainer/ppo/core_algos.py',None,'compute_policy_loss_dppo_kl'),
  ('verl/workers/utils/losses.py',None,'ppo_loss'),
  ('verl/workers/engine_workers.py','ActorRolloutRefWorker','update_actor'),
  ('verl/workers/engine_workers.py','TrainingWorker','train_mini_batch'),
  ('verl/workers/engine/base.py','BaseEngine','train_batch')],
 'ms-swift':[
  ('swift/pipelines/train/rlhf.py','SwiftRLHF','_get_trainer_kwargs'),
  ('swift/rlhf_trainers/rollout_mixin.py','RolloutTrainerMixin','_generate_and_score_completions'),
  ('swift/rlhf_trainers/rollout_mixin.py','RolloutTrainerMixin','_rollout'),
  ('swift/rlhf_trainers/grpo_trainer.py','GRPOTrainer','_score_completions'),
  ('swift/rlhf_trainers/grpo_trainer.py','GRPOTrainer','_postprocess_batch'),
  ('swift/rlhf_trainers/grpo_trainer.py','GRPOTrainer','_compute_advantages'),
  ('swift/rlhf_trainers/grpo_trainer.py','GRPOTrainer','_compute_loss_and_metrics'),
  ('swift/rl_core/advantage.py',None,'compute_advantages'),
  ('swift/rl_core/advantage.py',None,'compute_advantages_dynamic'),
  ('swift/rl_core/advantage.py',None,'expand_advantage_to_per_token'),
  ('swift/rl_core/advantage.py',None,'apply_rlsd_reweight')]
}
rows=[]
for (repo, entries), metadata in zip(specs.items(),manifest['repositories']):
    for relative,cls,func in entries:
        path=DATA/'repos'/repo/relative
        src=path.read_text(encoding='utf-8')
        tree=ast.parse(src)
        container=tree.body if cls is None else next(x.body for x in tree.body if isinstance(x,ast.ClassDef) and x.name==cls)
        node=next(x for x in container if isinstance(x,ast.FunctionDef) and x.name==func)
        rows.append(dict(repository=repo,commit=metadata['commit'],file=relative,
                         symbol=(cls+'.' if cls else '')+func,line=node.lineno,end_line=node.end_lineno,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         url=f"{metadata['url']}/blob/{metadata['commit']}/{relative}#L{node.lineno}"))
(DATA/'code-index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 锁定版本代码索引','','行号来自实际AST节点；SHA256对应本地源文件字节。URL固定到提交，不随main分支变化。','',
    '| 项目 | 函数 | 文件和行号 |','| --- | --- | --- |']
for r in rows:
    md.append(f"| {r['repository']} | {r['symbol']} | [{r['file']}:{r['line']}]({r['url']}) |")
(ROOT/'reports/代码索引.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(dict(papers=len(papers),code_entries=len(rows)),ensure_ascii=False))
