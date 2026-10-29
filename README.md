# LLM 课程作业

各目录独立保存代码、实验配置、报告、图表与必要结果。

```text
LLM-HW/
├── README.md
├── hw1/    n-gram、KenLM 与 Stupid Backoff
├── hw2/    Gensim、FastText 与新闻版面分类
├── hw3/    BERT 微调、断句标点与批量长文推理
└── hw4/    泄露提示词研究与唐诗宋词英译提示实验
```

| 作业 | 项目说明 | 实验报告 |
| --- | --- | --- |
| HW1 | [环境与运行](https://github.com/Can1017/LLM-HW/blob/main/hw1/README.md) | [n-gram 实验报告](https://github.com/Can1017/LLM-HW/blob/main/hw1/作业报告.md) |
| HW2 | [环境与运行](https://github.com/Can1017/LLM-HW/blob/main/hw2/README.md) | [Gensim 与 FastText 实验报告](https://github.com/Can1017/LLM-HW/blob/main/hw2/docs/P137实验报告.md) |
| HW3 | [环境与运行](https://github.com/Can1017/LLM-HW/blob/main/hw3/README.md) | [BERT 断句标点实验报告](https://github.com/Can1017/LLM-HW/blob/main/hw3/作业报告.md) |
| HW4 | [题目与工作区](https://github.com/Can1017/LLM-HW/blob/main/hw4/README.md) | [P15 泄露提示词研究报告](https://github.com/Can1017/LLM-HW/blob/main/hw4/p15-prompt-leakage/研究报告_泄露提示词与越狱.md)；[P89 诗词英译工作区](https://github.com/Can1017/LLM-HW/tree/main/hw4/p89-poetry-translation) |

获取完整代码及 KenLM 子模块：

```bash
git clone --recurse-submodules https://github.com/Can1017/LLM-HW.git
cd LLM-HW
```

运行作业时进入对应的 `hw1/`、`hw2/`、`hw3/` 或 `hw4/`，再按相应 README 配置环境与数据。实验报告中的项目链接指向 GitHub，图片使用完整在线地址，单独保存报告后仍可通过网络访问。HW3 的已训练模型和完整预测见 [GitHub Release](https://github.com/Can1017/LLM-HW/releases/tag/hw3-news-bert-v1)。
