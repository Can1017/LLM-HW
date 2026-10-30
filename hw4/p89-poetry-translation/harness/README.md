# 运行脚本

`run_experiment.py` 负责渲染提示、调用 OpenAI 兼容的 `/v1/chat/completions`、写 JSONL。仅用 Python 标准库。

## 配置

脚本从自身位置向上查找最近的 `.env`（本仓库为 `D:\PostGraduate\LLM\.env`），读取 `BASE_URL` 与 `API_KEY`；同名进程环境变量优先。不要把密钥写进结果或报告。

默认模型：`deepseek-v4.1-flash-1017`
默认温度：`0.2`
默认 `max_tokens`：`12000`（四版相同；pilot 的配置发现见下）

## 命令

在 `p89-poetry-translation/` 下执行：

```bash
# 只渲染，不调用接口
python harness/run_experiment.py --dry-run --poems T01 --versions v0,v1,v2,v3

# pilot：1 首 × 4 版
python harness/run_experiment.py --poems T01 --versions v0,v1,v2,v3 \
    --reps 1 --order fixed --max-tokens 12000 \
    --out results/pilot/pilot_T01_final.jsonl

# 开发集主实验：8 首 × 4 版
python harness/run_experiment.py --split dev --versions v0,v1,v2,v3 \
    --reps 1 --max-tokens 12000 --out results/main_dev.jsonl

# 稳定性：3 首 × 4 版 × 2 次重复（与主实验分开文件，避免 run_key 冲突）
python harness/run_experiment.py --poems T01,T04,T07 --versions v0,v1,v2,v3 \
    --reps 2 --max-tokens 12000 --out results/stability_dev.jsonl
```

注意：`--resume` 按 `run_key`（诗-版本-重复序号）跳过已有记录；不同批次请用不同 `--out`，否则同一 `run_key` 会被当成已完成。

## 记录内容

每条 JSONL：

- `run_key`、`run_id`、`timestamp`
- `poem_id`、`split`、`version`、`rep`
- `model_requested`、`temperature`、`max_tokens`
- 完整 `prompt` 与 `prompt_sha256`
- `ok`、`http_status`、`model_returned`
- 原始 `content`、`reasoning_content`、`usage`、`finish_reason`
- `latency_sec`、`attempts`、`attempt_errors`、`error`

配置快照写到同目录的 `<out>_config.json`，包含模板/数据/脚本的 SHA-256、网关 host（不含密钥）与命令行。

## pilot 的配置发现

- `max_tokens=2000` 时，V1 的推理 token 占满 2000，`finish_reason=length`，正文为空。
- `max_tokens=8000` 时 V1 正常产出；最终统一用 `12000`，四版相同。
- 最初输出会重复标题/作者；在共同底座加入“不要重复标题/作者”后，pilot 输出为干净的四行译文。

## 后续脚本

- `make_blind_packet.py`：从结果 JSONL 生成盲评包与评分 CSV；版本映射另存 `key_*.json`，评分完成前不要打开。
- `score.py`：合并 S_F/S_R 评分与运行记录，按版本汇总术语/关系/错误/成本，给出逐首配对与 bootstrap 区间。
- `stability.py`：比较同一格 3 次采样的文本相似度、行长、Notes 与格式，标出需人工复核的项。

```bash
# 盲评包（开发集）
python harness/make_blind_packet.py --results results/main_dev.jsonl --standard sf
python harness/make_blind_packet.py --results results/main_dev.jsonl --standard sr

# 填完 ratings_sf.csv / ratings_sr.csv 后汇总
python harness/score.py --sf results/blind/ratings_sf.csv --key-sf results/blind/key_sf.json \
    --sr results/blind/ratings_sr.csv --key-sr results/blind/key_sr.json \
    --results results/main_dev.jsonl --out results/scored_dev.md

# 稳定性表层检查
python harness/stability.py --main results/main_dev.jsonl \
    --stability results/stability_dev.jsonl --out results/stability_dev.md

# 二次盲评：开发集用 --selection first（本报告实际抽样为 T01/T02）；
# 测试集实际抽样覆盖 T09/T10 共 4 条
python harness/make_reliability_packet.py --results results/main_dev.jsonl \
    --ratings-sf results/blind/ratings_sf.csv --key-sf results/blind/key_sf.json \
    --tag dev --selection first
python harness/agreement.py --key results/reliability/key_reliability_dev.json \
    --ratings results/reliability/ratings_reliability_dev.csv \
    --orig-ratings results/blind/ratings_sf.csv --orig-key results/blind/key_sf.json \
    --out results/reliability/agreement_dev.md

# 阶段 II：历史评分口径审计、单条注释消融汇总与报告图表生成
python harness/audit_original.py
python harness/summarize_supplement.py
python harness/make_report_figures.py
```

盲评包只含诗、锚点与译文，不含版本名；`key_*.json` 保存 `blind_id -> run_key/version`，评分完成后再打开。`score.py` 的 `--label` 用于标题（开发集/测试集），测试集需显式传 `--sf/--key-sf/--sr/--key-sr/--results/--out` 指向 `results/blind_test/` 与 `results/test_holdout.jsonl`。