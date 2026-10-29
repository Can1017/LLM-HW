# P15：泄露提示词与越狱方法研究

本题已完成。先阅读[研究报告](研究报告_泄露提示词与越狱.md)，再按附录定位研究过程和原始输出。

| 材料 | 位置 |
| --- | --- |
| 主报告 | [研究报告_泄露提示词与越狱.md](研究报告_泄露提示词与越狱.md) |
| 检索与初步分析 | [阶段 1](research/阶段1_资料检索与初步分析.md) |
| 结构与版本分析 | [阶段 2](research/阶段2_结构与版本分析.md) |
| 主实验与消融记录 | [阶段 3](research/阶段3_测试结果.md) |
| 新模型补充 | [阶段 3b](research/阶段3b_新模型补充.md) |
| 网页端手工测试 | [网页版测试卡](research/网页版测试卡.md) |
| 实验代码 | [harness](research/harness/) |
| 已保存原始结果与汇总 | [results](research/results/) |
| 第三方语料版本 | [sources.json](research/sources.json) |

## 离线复核

脚本仅使用 Python 标准库，建议 Python 3.10 或更新版本。在本目录执行：

```bash
python research/harness/stats.py
python research/harness/summarize.py research/results/pilot_L3.jsonl
python research/harness/summarize.py research/results/pilot_L3_new.jsonl
python research/harness/analyze.py research/results/pilot_L3.jsonl review-recomputed.md
```

`analyze.py` 的第二个参数指定复核切片的输出路径；省略时写入 `research/results/leaks_review.md`。不同统计脚本保留了原研究中的评分口径，解释见主报告和阶段记录。已有 JSONL 与汇总保留原样。

## 再次运行模型实验

将 `../.env.example` 复制为 `../.env`，填写自己的 `BASE_URL` 与 `API_KEY`，或设置同名环境变量。配置读取顺序为：从脚本目录向上查找最近的 `.env`，再用进程环境变量覆盖。离线统计和 `--help` 不需要 API 配置。

```bash
python research/harness/extract_experiment.py --help
python research/harness/extract_experiment.py --models gpt-5.4 --levels L3 --reps 2 --out research/results/pilot-rerun.jsonl
```

第二条命令会产生新的 API 请求。模型名称、接口支持与可用性以自己的接入服务为准；`api_probe.py`、`probe2.py`、`probe3.py`、`probe4.py` 保存了研究期间的协议探测过程，执行它们也会访问模型接口。

本题实测对象为自建 Aurora 合成客服提示词及其保密条款变体。第三方公开语料用于结构分析。语料克隆在本地 `research/repos/` 中，GitHub 仅保存来源与提交版本；如需恢复，可按 `sources.json` 中的地址克隆并检出对应提交。
