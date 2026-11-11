"""CPU mechanism lab using function bodies from pinned upstream repositories.

No pretrained model, Ray cluster, CUDA, network call or environment is needed.
The local ActorConfig adapter supplies configuration data only. Numerical
helpers and loss aggregation are extracted from verl rather than mocked.
"""
from __future__ import annotations

import ast
from collections import defaultdict
import hashlib
import json
import platform
from pathlib import Path
import subprocess
from types import SimpleNamespace
import typing

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
REPOS = ROOT / 'research' / 'repos'
OUT = ROOT / 'research' / 'results'
PROVENANCE = []
torch.set_default_dtype(torch.float64)
torch.manual_seed(7)


def extract(path, name, ns, class_name=None):
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    container = tree.body if class_name is None else next(
        n.body for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    node = next(n for n in container if isinstance(n, ast.FunctionDef) and n.name == name)
    PROVENANCE.append(dict(path=path.relative_to(ROOT).as_posix(), function=name,
                           line=node.lineno, end_line=node.end_lineno,
                           sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    node.decorator_list = []
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), ns)
    return ns[name]


class ActorConfig(SimpleNamespace):
    """Only values consumed by the extracted loss functions, not a trainer."""
    def __init__(self, clip_ratio=0.2, **kwargs):
        super().__init__(clip_ratio=clip_ratio, clip_ratio_low=None,
                         clip_ratio_high=None, clip_ratio_c=20.0,
                         global_batch_info={}, **kwargs)

    def get(self, key, default=None):
        return getattr(self, key, default)


def load_functions():
    ns = dict(torch=torch, np=np, defaultdict=defaultdict, F=F,
              ActorConfig=ActorConfig, AlgoConfig=type('AlgoConfig', (), {}))
    ns.update(vars(typing))
    helpers = REPOS/'verl/verl/utils/torch_functional.py'
    masked_sum = extract(helpers, 'masked_sum', ns)
    masked_mean = extract(helpers, 'masked_mean', ns)
    ns['verl_F'] = SimpleNamespace(masked_sum=masked_sum, masked_mean=masked_mean)
    core = REPOS/'verl/verl/trainer/ppo/core_algos.py'
    for name in ['agg_loss', 'compute_grpo_outcome_advantage', 'compute_policy_loss_vanilla',
                 'compute_policy_loss_gspo', 'compute_policy_loss_dppo_tv', 'compute_policy_loss_dppo_kl']:
        extract(core, name, ns)
    swift = REPOS/'ms-swift/swift/rl_core/advantage.py'
    for name in ['compute_advantages', 'compute_advantages_dynamic', 'apply_rlsd_reweight']:
        extract(swift, name, ns)
    return ns


def dpo_branch():
    path = REPOS/'trl/trl/trainer/dpo_trainer.py'
    src = path.read_text(encoding='utf-8')
    tree = ast.parse(src)
    sigmoid = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                   and ast.unparse(n.test) == "loss_type == 'sigmoid'")
    # Run the exact upstream sigmoid assignment. Preparation of delta_score is
    # explicit below, in the reverse-KL (ordinary DPO) case.
    module = ast.fix_missing_locations(ast.Module(body=sigmoid.body, type_ignores=[]))
    code = compile(module, str(path), 'exec')
    PROVENANCE.append(dict(path=path.relative_to(ROOT).as_posix(), function='DPO sigmoid branch',
                           line=sigmoid.lineno, end_line=sigmoid.body[-1].end_lineno,
                           sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

    def loss(probabilities, reference):
        p, r = probabilities.log(), reference.log()
        delta = (p[0]-r[0])-(p[1]-r[1])
        scope = dict(F=F, self=SimpleNamespace(beta=0.1), delta_score=delta)
        exec(code, scope)
        return scope['per_sequence_loss']
    return loss


def check_versions():
    manifest = json.loads((ROOT/'research/sources.json').read_text(encoding='utf-8'))
    commits = {}
    for repo, entry in zip(['trl', 'verl', 'ms-swift'], manifest['repositories']):
        got = subprocess.check_output(['git', '-C', str(REPOS/repo), 'rev-parse', 'HEAD'], text=True).strip()
        assert got == entry['commit'], (repo, got, entry['commit'])
        commits[repo] = got
    return commits


def main():
    versions = check_versions()
    ns = load_functions()
    results = {}
    checks = []
    def checked(name, condition):
        if not bool(condition):
            raise AssertionError(name)
        checks.append(name)

    rewards = torch.tensor([1., 0., 3., 1.])
    mask = torch.ones((4, 2))
    index = np.array(['a', 'a', 'b', 'b'])
    def verl_adv(r, ids, std=True):
        rt = torch.zeros((len(r), 2))
        rt[:, -1] = r  # terminal outcome reward only
        return ns['compute_grpo_outcome_advantage'](rt, mask, ids,
                                                    norm_adv_by_std_in_grpo=std)[0][:, 0]
    def swift_adv(r, scale='group'):
        return ns['compute_advantages'](r[:, None], torch.tensor([1.]), 2, scale_rewards=scale)[0]
    va, sa = verl_adv(rewards, index), swift_adv(rewards)
    checked('GRPO implementations agree within their epsilon difference', torch.allclose(va, sa, atol=2e-4))
    checked('Centered advantages are [-groupmean,+groupmean]', torch.allclose(
        verl_adv(rewards, index, False), torch.tensor([.5, -.5, 1., -1.])))
    zero = swift_adv(torch.ones(4))
    checked('Equal outcome rewards produce zero policy advantages', torch.equal(zero, torch.zeros(4)))
    order = torch.tensor([0, 2, 1, 3])
    pv = verl_adv(rewards[order], index[order.numpy()])
    ps = swift_adv(rewards[order])
    checked('UID grouping survives an interleaved permutation', torch.allclose(pv, va[order]))
    checked('Fixed contiguous grouping changes after interleaving', not torch.allclose(ps, sa[order], atol=2e-4))
    results['grouping'] = dict(rewards=rewards.tolist(), verl=va.tolist(), swift=sa.tolist(),
                               zero_std=zero.tolist(), permutation=order.tolist(),
                               shuffled_uid=pv.tolist(), shuffled_contiguous=ps.tolist())

    # Aggregation is part of the algorithm, not merely a logging operation.
    lm = torch.tensor([[1., 1., 0., 0., 0., 0.], [3., 3., 3., 3., 3., 3.]], requires_grad=True)
    mk = torch.tensor([[1., 1., 0., 0., 0., 0.], [1., 1., 1., 1., 1., 1.]])
    losses = {}
    for mode in ['token-mean', 'seq-mean-token-mean', 'seq-mean-token-sum-norm']:
        loss = ns['agg_loss'](lm, mk, mode, loss_scale_factor=8)
        grad, = torch.autograd.grad(loss, lm)
        losses[mode] = dict(loss=loss.item(), per_token_gradient=grad.tolist())
    checked('Token mean weights the longer sequence more', abs(losses['token-mean']['loss']-2.5)<1e-12)
    checked('Sequence mean gives equal sequence weight', abs(losses['seq-mean-token-mean']['loss']-2.0)<1e-7)
    results['aggregation'] = losses

    # GSPO-token and sequence GSPO coincide for constant within-sequence A.
    old = torch.log(torch.tensor([[.3, .4]]))
    def gspo_gradient(adv):
        lp = old.clone().requires_grad_(True)
        loss, _ = ns['compute_policy_loss_gspo'](old, lp, adv, torch.ones_like(lp), config=ActorConfig())
        g, = torch.autograd.grad(loss, lp)
        direct_lp = old.clone().requires_grad_(True)
        sequence_ratio = torch.exp((direct_lp-old).mean(-1, keepdim=True))
        direct_loss = -(sequence_ratio*adv).mean()
        dg, = torch.autograd.grad(direct_loss, direct_lp)
        return dict(token_loss=loss.item(), sequence_loss=direct_loss.item(),
                    token_gradient=g.tolist(), sequence_gradient=dg.tolist())
    constant = gspo_gradient(torch.tensor([[1., 1.]]))
    varying = gspo_gradient(torch.tensor([[1., -1.]]))
    checked('GSPO and GSPO-token constant-A gradients agree', np.allclose(constant['token_gradient'], constant['sequence_gradient']))
    checked('Same forward loss does not prove tokenwise gradient equivalence',
            abs(varying['token_loss']-varying['sequence_loss'])<1e-12
            and not np.allclose(varying['token_gradient'], varying['sequence_gradient']))
    results['gspo_gradients'] = dict(constant_advantage=constant, varying_advantage=varying)

    # Same ratio, different absolute probability movement. Thresholds are
    # illustrative and have different units; this is not a fair benchmark.
    op = torch.tensor([[.001, .5]])
    cp = torch.tensor([[.0015, .75]])
    losses = {}
    for name, fn, cfg in [('PPO ratio', 'compute_policy_loss_vanilla', ActorConfig(.2)),
                         ('DPPO binary TV', 'compute_policy_loss_dppo_tv', ActorConfig(.1)),
                         ('DPPO binary KL', 'compute_policy_loss_dppo_kl', ActorConfig(.01))]:
        lp = cp.log().requires_grad_(True)
        loss, metrics = ns[fn](op.log(), lp, torch.ones_like(lp), torch.ones_like(lp), config=cfg)
        g, = torch.autograd.grad(loss, lp)
        losses[name] = dict(loss=loss.item(), logp_gradient=g.tolist(), metrics=metrics)
    checked('PPO clips both positive-advantage tokens at ratio 1.5',
            np.allclose(losses['PPO ratio']['logp_gradient'], [[0., 0.]]))
    checked('DPPO-TV keeps the small probability shift in this example',
            np.allclose(losses['DPPO binary TV']['logp_gradient'], [[-.75, 0.]]))
    results['trust_region'] = dict(old_probabilities=op.tolist(), current_probabilities=cp.tolist(),
                                   ratio=(cp/op).tolist(), outcomes=losses)

    # Exact TRL sigmoid branch, plus a deliberately constructed counterexample.
    dpo = dpo_branch()
    ref = torch.tensor([.2, .1, .7])
    altered = torch.tensor([.15, .01, .84])
    initial, altered_loss = dpo(ref, ref), dpo(altered, ref)
    checked('DPO loss can fall while chosen absolute probability falls', altered_loss<initial and altered[0]<ref[0])
    logits = ref.log().clone().requires_grad_(True)
    optimizer = torch.optim.SGD([logits], lr=.1)
    trace = []
    for step in range(4):
        p = logits.softmax(-1)
        loss = dpo(p, ref)
        trace.append(dict(step=step, loss=loss.item(), probabilities=p.detach().tolist()))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    checked('A tiny categorical policy takes actual gradient update steps', trace[-1]['loss']<trace[0]['loss'])
    results['dpo'] = dict(reference=ref.tolist(), counterexample=altered.tolist(),
                          original_loss=initial.item(), counterexample_loss=altered_loss.item(),
                          optimizer_trace=trace)

    # Teacher reweighting without changing the sign of the outcome advantage.
    base = torch.tensor([1., -1.])
    completion_mask = torch.tensor([[1., 1., 0.], [1., 1., 0.]])
    teacher = torch.tensor([[-.1, -2., 0.], [-.1, -2., 0.]], requires_grad=True)
    student_old = torch.tensor([[-2., -.1, 0.], [-2., -.1, 0.]], requires_grad=True)
    ra = ns['apply_rlsd_reweight'](base, completion_mask, teacher, student_old,
                                  lam=.5, clip_range=.2)
    checked('RLSD reweight preserves the sign of outcome advantages',
            torch.all(torch.sign(ra[completion_mask.bool()])==torch.sign(base[:, None].expand_as(ra)[completion_mask.bool()])))
    checked('RLSD teacher and old policy gaps are detached', not ra.requires_grad)
    checked('Padding carries no advantage', torch.equal(ra[:, 2], torch.zeros(2)))
    results['teacher_reweight'] = dict(advantages=ra.tolist(), teacher_gap=(teacher-student_old).detach().tolist())

    # Request-ID deduplication matters for multi-turn trajectories.
    dyn, _ = ns['compute_advantages_dynamic'](torch.tensor([[1.], [1.], [0.]]),
        torch.tensor([1.]), ['p', 'p', 'p'], ['r1', 'r1', 'r2'], scale_rewards='none')
    checked('Repeated turns of one request receive the same deduplicated advantage',
            torch.allclose(dyn, torch.tensor([.5, .5, -.5])))
    results['request_deduplication'] = dict(request_ids=['r1','r1','r2'], advantages=dyn.tolist())

    payload = dict(scope='Local exact-source tensor functions and categorical optimizer only; no LLM training',
                   environment=dict(python=platform.python_version(), torch=torch.__version__,
                                    device='cpu', dtype='float64', seed=7),
                   commits=versions, checks=checks, check_count=len(checks),
                   results=results, provenance=PROVENANCE)
    OUT.mkdir(exist_ok=True)
    (OUT/'mechanism_lab.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(status='passed', checks=len(checks), device='cpu',
                          results=str(OUT/'mechanism_lab.json')), ensure_ascii=False))


if __name__ == '__main__':
    main()
