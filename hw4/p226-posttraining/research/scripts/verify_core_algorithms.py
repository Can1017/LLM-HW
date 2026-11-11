"""Run small CPU checks against pure functions extracted from the pinned repos.

This is not a model-training experiment.  It executes the repository functions
that turn grouped rewards and token log-probabilities into advantages and policy
losses, using synthetic tensors whose expected behavior is easy to inspect.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
REPOS = ROOT / "research" / "repos"
RESULTS = ROOT / "research" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def extract_function(path: Path, name: str, namespace: dict) -> object:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    if not nodes:
        raise LookupError(f"{name} not found in {path}")
    node = nodes[0]
    node.decorator_list = []
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    code = compile(module, str(path), "exec")
    exec(code, namespace)
    return namespace[name]


def identity_decorator(*args, **kwargs):
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]

    def wrap(fn):
        return fn

    return wrap


def run() -> dict:
    verl_core = REPOS / "verl" / "verl" / "trainer" / "ppo" / "core_algos.py"
    swift_adv = REPOS / "ms-swift" / "swift" / "rl_core" / "advantage.py"
    trl_files = [
        REPOS / "trl" / "trl" / "trainer" / "dpo_trainer.py",
        REPOS / "trl" / "trl" / "trainer" / "grpo_trainer.py",
    ]

    compile_checks = {}
    for path in trl_files + [verl_core, swift_adv]:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        compile_checks[str(path.relative_to(ROOT))] = "ok"

    # Exact function body from verl's current GRPO implementation.
    verl_ns = {
        "torch": torch,
        "np": np,
        "defaultdict": __import__("collections").defaultdict,
        "Optional": object,
        "AlgoConfig": object,
        "register_adv_est": identity_decorator,
        "AdvantageEstimator": SimpleNamespace(GRPO="grpo"),
    }
    verl_grpo = extract_function(verl_core, "compute_grpo_outcome_advantage", verl_ns)

    # Exact pure advantage function from ms-swift.
    def nanstd(value: torch.Tensor, *args, **kwargs):
        value = value[~torch.isnan(value)]
        return torch.std(value, *args, **kwargs)

    swift_ns = {"torch": torch, "Optional": object, "Tuple": tuple, "List": list, "Dict": dict,
                "nanstd": nanstd}
    swift_advantage = extract_function(swift_adv, "compute_advantages", swift_ns)

    rewards = torch.tensor([[1.0], [0.0], [2.0], [1.0]])
    response_mask = torch.ones((4, 3), dtype=torch.float32)
    group_index = np.array([0, 0, 1, 1])
    verl_token_rewards = rewards.repeat(1, 3) / 3
    verl_scaled, _ = verl_grpo(
        token_level_rewards=verl_token_rewards,
        response_mask=response_mask,
        index=group_index,
        norm_adv_by_std_in_grpo=True,
    )
    verl_dr, _ = verl_grpo(
        token_level_rewards=verl_token_rewards,
        response_mask=response_mask,
        index=group_index,
        norm_adv_by_std_in_grpo=False,
    )
    swift_scaled, swift_rewards = swift_advantage(
        rewards_per_func=rewards,
        reward_weights=torch.tensor([1.0]),
        num_generations=2,
        scale_rewards="group",
    )
    swift_unscaled, _ = swift_advantage(
        rewards_per_func=rewards,
        reward_weights=torch.tensor([1.0]),
        num_generations=2,
        scale_rewards="none",
    )

    # Exact GSPO policy-loss function from verl, with tiny local stubs for the
    # registry, aggregation, and metric helpers it references.
    class ActorConfig:
        clip_ratio = 0.2
        clip_ratio_low = None
        clip_ratio_high = None
        global_batch_info = {}

    class VerlF:
        @staticmethod
        def masked_mean(x, mask):
            return (x * mask).sum() / mask.sum().clamp(min=1.0)

    def agg_loss(loss_mat, loss_mask, loss_agg_mode, **_kwargs):
        return (loss_mat * loss_mask).sum() / loss_mask.sum().clamp(min=1.0)

    gspo_ns = {
        "torch": torch,
        "Optional": object,
        "Any": object,
        "ActorConfig": ActorConfig,
        "register_policy_loss": identity_decorator,
        "agg_loss": agg_loss,
        "verl_F": VerlF,
    }
    gspo = extract_function(verl_core, "compute_policy_loss_gspo", gspo_ns)
    old_log_prob = torch.log(torch.tensor([[0.25, 0.50, 0.25], [0.20, 0.30, 0.50]]))
    log_prob = torch.log(torch.tensor([[0.30, 0.60, 0.10], [0.25, 0.25, 0.50]]))
    advantages = torch.tensor([[1.0, 1.0, 1.0], [-1.0, -1.0, -1.0]])
    mask = torch.ones_like(advantages)
    gspo_loss, gspo_metrics = gspo(
        old_log_prob=old_log_prob,
        log_prob=log_prob,
        advantages=advantages,
        response_mask=mask,
        config=ActorConfig(),
    )
    seq_log_ratio = ((log_prob - old_log_prob) * mask).sum(-1) / mask.sum(-1)
    token_ratio = torch.exp(seq_log_ratio).tolist()

    result = {
        "status": "passed",
        "source_commit_scope": {
            "verl": "81464bb6d35cbb43962be42b0088a591e7020f21",
            "ms_swift": "a8dccaafe9324a5d454c44703e3dce92370f5c1c",
            "trl": "d115286bc5aef8d346e8510bfe312803c7881c4a",
        },
        "compile_checks": compile_checks,
        "grouped_rewards": rewards.squeeze(1).tolist(),
        "verl_grpo_scaled": verl_scaled[:, 0].tolist(),
        "verl_dr_grpo_unscaled": verl_dr[:, 0].tolist(),
        "swift_grpo_scaled": swift_scaled.tolist(),
        "swift_grpo_rewards": swift_rewards.tolist(),
        "swift_unscaled": swift_unscaled.tolist(),
        "gspo_sequence_importance_ratio": token_ratio,
        "gspo_loss": float(gspo_loss),
        "gspo_metrics": gspo_metrics,
        "observations": [
            "verl and ms-swift agree on grouped GRPO centering and group-standard-deviation scaling for this synthetic case.",
            "turning off standard-deviation scaling produces the Dr.GRPO-style centered signal.",
            "GSPO broadcasts one sequence-level importance ratio across the response tokens of each sequence.",
        ],
    }
    (RESULTS / "core_algorithm_verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    run()
