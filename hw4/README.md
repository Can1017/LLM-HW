# HW4：提示词研究与诗词英译实验

本作业依据 `L3-part1.pptx` 的实际第 15、89 页，按题目分别保存工作区。两页的课件页脚编号分别为 11/80、65/80。

| 题目 | 状态 | 工作区 |
| --- | --- | --- |
| P15：泄露提示词与越狱方法研究 | 已完成，含报告、研究记录、脚本和原始结果 | [第一题](p15-prompt-leakage/README.md) |
| P89：唐诗宋词英译提示对照实验 | 已完成，含最终报告、四阶段记录、脚本与原始结果 | [第二题](p89-poetry-translation/README.md) |

```text
hw4/
├── README.md
├── .env.example
├── materials/                 共享课件与提取文本（本地保存）
├── p15-prompt-leakage/
│   ├── README.md
│   ├── 研究报告_泄露提示词与越狱.md
│   └── research/
│       ├── 阶段*.md、网页版测试卡.md
│       ├── harness/           实验、统计与协议探测脚本
│       ├── results/           原始 JSONL 与已有汇总
│       ├── sources.json       第三方语料仓库的地址与提交版本
│       └── repos/             第三方仓库本地克隆（不上传）
└── p89-poetry-translation/
    ├── README.md
    ├── data/
    ├── prompts/
    ├── results/
    └── reports/
```

## 文件与配置

课程 PPT、提取文本、第三方仓库克隆、Python 缓存和实际 `.env` 配置保留在本地。GitHub 保存本作业的报告、代码、研究记录、原始实验结果以及第二题工作区。

第一题的原有 `research/` 内部结构保留，报告附录中的相对路径继续有效。脚本按文件位置定位结果目录，不依赖本机盘符。API 配置可放在本目录的 `.env` 中，字段见 `.env.example`；同名进程环境变量优先。
