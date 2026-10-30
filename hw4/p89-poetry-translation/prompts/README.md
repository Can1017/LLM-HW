# 提示版本（V0–V3）

本目录保存 P89 实验的提示模板与渲染脚本。所有版本共用同一输出契约；版本之间只增加一种信息。

| 文件 | 用途 |
| --- | --- |
| `base.txt` | 共同底座：翻译指令 + 输出契约 |
| `v1_criteria.txt` | V1 追加的任务标准（受众、目的、关系/术语要求） |
| `v3_examples.txt` | V3 追加的边界示例（来自非计分诗） |
| `render.py` | 读取 `data/poems.json`，渲染四个版本 |

## 版本

| 版本 | 内容 | 对应假设 |
| --- | --- | --- |
| V0 | 底座 + 原诗 | 最简基线 |
| V1 | 底座 + 任务标准 + 原诗 | H1：关系错误减少 |
| V2 | 底座 + 该首诗的参考注释 + 原诗 | H2：术语错误减少，关系未必改善 |
| V3 | 底座 + 4 组边界示例 + 原诗 | H3：示例主要帮助同类现象，迁移有限 |

## 共同输出契约

```text
Output: the English translation. If you add endnotes for culture-specific
terms, place them after the translation under a short "Notes" heading.
Do not repeat the title or author in the output. Do not add any other
commentary.
```

- 四版逐字相同，避免把“格式要求”误当成版本差异。
- V1 的任务标准不再重复格式要求；它只补受众、目的与内容判据。
- V2 的注释在该首诗运行前已写入 `data/poems.json` 的 `reference_notes`；测试集注释也在看到任何模型输出之前完成。
- V3 的示例来自李白、杜甫的四首诗，均不在 12 首计分材料内；`--check-examples` 会检查示例句是否误入计分诗。

## 渲染

在 `p89-poetry-translation/` 下执行：

```bash
python prompts/render.py --list
python prompts/render.py --poem T01 --version v0
python prompts/render.py --all --out results/prompts_all.jsonl
python prompts/render.py --check-examples
```

`--all` 生成 12 首 × 4 版 = 48 条提示；每条带 `prompt_sha256`，便于核对运行后是否改过模板。

## 冻结规则

- pilot 可以调整共同底座（例如输出契约）。
- 开发集主实验开始后，不再修改 `base.txt`、`v1_criteria.txt`、`v3_examples.txt` 与 `data/poems.json` 的术语/关系锚点；运行脚本会把模板与数据的 SHA-256 写入配置快照。
- 若必须修改，另存新版本并重跑，不把新旧输出混在同一比较里。