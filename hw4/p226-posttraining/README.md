# P226：大语言模型后训练技术演进与开源实现研究

本目录对应 `L3-part2.pptx` 第 226 页的“有基础的同学”作业。研究重点是后训练方法的演进、开源实现中的数据流与损失计算，以及有限算力下能够验证的机制性小实验。

## 研究范围

- 主线代码：Hugging Face TRL、字节跳动 `verl`、阿里 ModelScope `ms-swift`。
- 算法重点：DPO、GRPO，以及 DAPO、GSPO、Dr.GRPO、2026 年 DPPO 与教师逐 token 反馈。
- 实践范围：CPU 原函数与梯度检查、三动作策略更新；不包含语言模型训练。
- 代码版本：记录在 `research/sources.json`，以仓库提交哈希锁定。

## 当前报告

- [研究报告](reports/大语言模型后训练演进与强化学习代码研究.md)：按研究过程展开，包含方法演进、关键代码、反向传播解释、实际结果和研究收获。
- [31 个代码永久链接](reports/代码索引.md)：从真实 AST 节点生成的行号与固定提交链接。
- [机器可读结果](research/results/mechanism_lab.json)：17 项机制检查、数值、梯度和源码哈希。

## 实际完成的代码实践

[mechanism_lab.py](research/scripts/mechanism_lab.py) 从三个锁定仓库提取函数或目标分支，用 CPU 张量和三动作策略完成 17 项检查。结果及源码哈希保存在 [mechanism_lab.json](research/results/mechanism_lab.json)。原始检查、构造反例和实际 SGD 轨迹分开记录。

在本机已有的 Python 3.11、PyTorch 2.5.1 CPU、NumPy 环境中运行：

    python research/scripts/mechanism_lab.py

代码依赖本地浅克隆。恢复其他机器上的源码时，先克隆 sources.json 中的三个公开仓库，并检出所记录的完整 SHA。稀疏检出目录需覆盖 code-index.json 中的路径；不需要启动 Ray、vLLM 或下载模型。

图表生成：

    python research/scripts/generate_figures.py

需要 Matplotlib。三张自绘图分别表达技术演进、在线更新的数据流和本次机制结果，PNG用于在线展示，SVG保留为可编辑图源。

报告另引用Qwen3、GSPO、DPPO三张论文原图，页码、图号、裁切范围和PDF哈希记录在 [paper_sources.json](reports/figures/paper_sources.json)。取得对应版本的PDF后，可重新提取：

    python research/scripts/extract_paper_figures.py --paper-cache research/papers

该脚本需要 PyMuPDF，只做原图裁切与渲染，不重绘论文中的数据。

## 文献和证据

- [13 篇主来源核验记录](research/references-verified.json)：作者、版本、PDF 哈希和相关阅读位置。
- [代码结构化索引](research/code-index.json)：31 个方法及本地源文件字节哈希。
- [研究来源清单](research/sources.json)：课程位置、固定提交和论文。

本研究未进行预训练语言模型的实际训练与集群端到端复现。已运行的是原源码纯函数和小策略更新，不能当作语言模型能力实验。

## 目录

```text
research/
  repos/       本地浅克隆的开源仓库（不纳入提交）
  scripts/     来源整理、机制实践和图表生成脚本
  results/     核验结果与运行日志
  sources.json 论文、课件与代码版本清单
reports/
  大语言模型后训练演进与强化学习代码研究.md
  figures/     报告使用的图表和流程图
```

## 说明

报告把“论文中的算法”“仓库中的工程实现”和“本次基于代码的判断”分开记录。主报告已经包含必要的代码路径、版本、验证结果和复查入口，源码与机器可读结果保存在同一 GitHub 目录。
