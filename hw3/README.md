# HW3：BERT 微调与批量长文断句标点

本实验依据 `L2-part2.pptx` 第 68 页开展，使用预训练中文 BERT 完成八类字符后标点预测，并比较顺序滑窗、多文章批处理与固定重叠切窗的推理效率。

[独立实验报告](https://github.com/Can1017/LLM-HW/blob/main/hw3/%E4%BD%9C%E4%B8%9A%E6%8A%A5%E5%91%8A.md) · [图表及标点错误对照图](https://github.com/Can1017/LLM-HW/tree/main/hw3/figures) · [训练模型与完整预测](https://github.com/Can1017/LLM-HW/releases/tag/hw3-news-bert-v1)

## 环境与运行

采用独立 Conda 环境 `hw3-bert`，Python 3.11。环境禁用用户级 site-packages，依赖统一安装在该 Conda 环境中。Windows 上按下面的顺序安装 CUDA 版 PyTorch 与实验依赖：

```powershell
conda create -n hw3-bert python=3.11 pip -y
conda env config vars set -n hw3-bert PYTHONNOUSERSITE=1 PYTHONUTF8=1
conda activate hw3-bert
python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
python -m pip install transformers==4.57.1 numpy==1.26.4 requests==2.32.5 matplotlib==3.10.8 pytest==8.4.2
```

在本目录运行：

```powershell
python prepare_data.py --archive "D:\PostGraduate\LLM\hw2\1998-上半年-带音.rar"
python fetch_assets.py model
python fetch_assets.py cclue
python -m pytest tests -q
python train.py cache
python train.py profile
python train.py train --batch-size 4 --accumulation 4 --eval-batch 8 --epochs 3 --run news-bert
.\run_post_training.ps1
```

硬件短试跑确定正式训练批大小、梯度累积和梯度检查点设置。`train.py train` 执行三个完整 epoch，使用完整验证集选择最佳模型。训练逐步日志保存在 `logs/`，每轮验证结果保存在 `results/`，模型保存在 `models/`。

原始人民日报压缩包使用课程提供的文件，运行 `--archive` 时填入该文件在本机的位置。HW3 不读取其他作业的划分或处理结果。预训练权重及外部评测集通过固定版本地址自动下载；`run_post_training.ps1` 完成现代文／CCLUE 全量评测、长文测速、《论语》专项与报告生成。模型训练和完整预测另有下方的已完成产物下载入口。

报告及示例图片可直接从已有结果重建：

```powershell
python audit_source_characters.py
python build_examples.py
python build_data_report.py
python build_report.py
```

重建示例图前先恢复下方的完整预测归档。`audit_source_characters.py` 读取课程压缩包和 `fetch_assets.py cclue` 下载的原文件；本轮核查结果已随仓库保存。

## 独立的数据处理

实验从用户指定的 `../hw2/1998-上半年-带音.rar` 直接读取原始字节，该路径仅标识输入文件位置。HW3 单独建立清洗规则、文章划分、标签、训练与评测产物。

原始压缩包 SHA-256：`30c4435bcce7d082c2175720a4549114f80656761df95d3c8b20f0ee48e5d7ab`。

处理规则如下：

1. 按 GB18030 严格解码；隔离五个异常段落并在 `data/quarantine.json` 保存原字节十六进制、编号、位置和原因。
2. 解析文章与段落编号，删除注音标记、分词空格；将全角数字转为半角数字，保留正文、数字、字母及姓名中的间隔号。
3. 标签依次为 `NONE，。？！、：；`，含“无标点”及七种常用标点。引号、括号、书名号按限定任务范围移除。省略号、破折号及同位置多个主标点的歧义位置使用 `-100`，单列统计。
4. 以无标点正文指纹去除重复文章，在每月内用固定种子划分约 80% 训练、10% 验证、10% 测试；同一文章的所有窗口属于同一划分。
5. 按原始段落编号顺序构造连续文章输入；缺失或隔离段落形成上下文断点。训练窗口长度 400 字、步长 300 字，重叠区按中点分配监督位置，每个正文位置只计一次损失。

`results/data_statistics.json` 记录清洗、划分和异常统计；`results/label_examples.json` 给出实际的字符、标签和目标文本。分词对齐检查另记录实际 token 长度和监督位置数量。

CCLUE 含 Unicode 私用区字符。模型输入将这类默认会被 tokenizer 清除的字符显式表示为 `[UNK]`，原始文字与标签位置完整保留。逐字符对齐检查与相关计数保存在 `results/cclue_alignment.json`。

## 古文迁移评价

CCLUE 固定版本为 `ed481c453c1c36397f86905a2bda625ecc5607e1`。本阶段下载其发布的开发、测试数据和构造说明，用于新闻模型的跨领域评价。发布者已做简体转换、符号清理、书籍筛选和段落抽样。开发集实际读取 4,074 个有效样本，测试集 3,992 个；开发集与上游 README 的 4,075 相差一条，统计采用实际有效记录。

样例复核确认发布测试集含文言与现代白话叙述，例如 `cclue-test-108-1964`。报告将该结果标为 CCLUE 固定划分上的迁移评价，并明确混合文体属性。

## 《论语》纯文言专项

按用户确认的方案，继续微调暂缓，专项评测采用本轮新闻模型。文本来自 `chinese-poetry/chinese-poetry` 固定提交 `b8594f81a89752241442f2ce267d6f66f96704ee` 的 `论语/lunyu.json`。原 JSON、README、MIT 许可证和字节指纹保存到 `data/lunyu/upstream/` 及 `results/lunyu_source.json`。

实际文件含20篇、512条语录、15,917个正文字符。README 的“繁体分发、492章”与当前 JSON 的简体文字、512条记录不同，专项使用实际文件并说明版本差异。英文逗号5处、问号1处、冒号1处显式映射为中文；两个主标点冲突位置按统一规则忽略。参考标点代表该电子版本。

固定窗口 batch=8：按512条语录分别输入的标点微F1为0.6488；按原顺序合并为20篇输入的微F1为0.6191。两者覆盖相同文字，独立报告。原新闻模型文件的评测前后字节指纹一致，完整预测保存在 `data/predictions/news-bert/lunyu_*.jsonl`。短语录全部短于400字，整篇最长1,339字，17篇超过510字。

监督训练原文重合检查找到1条8字语录匹配；剔除后其余511条微F1为0.6490。通用BERT预训练可能涉及常见经典文本，该检查只说明本次新闻微调数据中的完整语录匹配情况。

## 本轮实测结果

三个 epoch 全量训练耗时 4,770.3 秒，优化器更新 6,237 次，最佳模型来自第三轮。固定窗口 batch=8 的现代文测试标点微 F1 为 0.8172，CCLUE 固定测试集为 0.5994。实际运行记录见 `results/news-bert_completion.json`、`results/news-bert_evaluation.json`。

20 组长文测速各重复五次。固定窗口 batch=32 相对相同窗口 batch=1，单篇负载加速 1.95 倍，多篇负载加速 1.93 倍。相对课件句号推进 batch=1，整体加速分别为 2.18 倍和 2.11 倍。两种比值区分批处理收益与包含窗口策略变化的整体收益。

`python verify_results.py` 从保存的预测逐字重新计算测试指标，并核对原始文件指纹、文章划分、训练轮数、模型选择及重复测速记录。

## 为自己的长文恢复标点

下载[已训练模型](https://github.com/Can1017/LLM-HW/releases/download/hw3-news-bert-v1/hw3-news-bert.zip)，在 `hw3/` 目录解压，得到 `models/news-bert/`。如需逐字复核全部预测，下载[完整预测归档](https://github.com/Can1017/LLM-HW/releases/download/hw3-news-bert-v1/hw3-predictions.zip)并在同一目录解压。文件大小和 SHA-256 见[归档记录](https://github.com/Can1017/LLM-HW/blob/main/hw3/results/release_assets.json)。

将无标点文字保存为 UTF-8 文本，在已激活的 `hw3-bert` 环境中运行：

```powershell
python predict.py --input input.txt --output output.txt --batch-size 8
```

程序加载本轮已训练的 `models/news-bert`，使用 400 字上下文、300 字步长的固定重叠窗口批量推理。输出保留输入中的空白和换行，并恢复七种目标标点。`--batch-size 32` 对应本轮已完成测速的较大推理批次。

## 示例中的特殊字符

`〓` 是原人民日报标题中已有的 U+3013 GETA MARK，源编码为 GB18030 `A1 FE`，常作缺字或不可表示字符的占位；标题原意尚未确认。CCLUE 的 U+E583 是源文件中的私用区字符，缺少原字库映射时无法确定字义。示例图将两者标为黄色方框并注明编码，原始文本、模型处理与既有评分均保留。证据见[源字符核查](https://github.com/Can1017/LLM-HW/blob/main/hw3/results/source_character_audit.json)。

## 评价口径

主质量指标为排除 `NONE` 的标点微平均、宏平均 F1，并分别报告七种标点的 Precision、Recall、F1 和支持数。句末边界定义为 `。？！`。字符准确率作为辅助指标。

固定重叠切窗在相同模型、精度与切窗条件下比较不同 batch，并与课件的“400 字输入、前 300 字内最后一个预测句号结束、无句号则推进 300 字”方法对照。记录正文字符吞吐、端到端耗时、峰值显存和接缝附近质量。测速分母采用原文字符数。

## 来源

- 课程提供的人民日报半年带音语料；压缩包中包含六份 `1998-XX-2003版-带音.txt`，具体流转版本以原文件与字节指纹标识。
- [BERT 模型卡](https://huggingface.co/google-bert/bert-base-chinese)，预训练权重固定版本 `8f23c25b06e129b6c986331a13d8d025a92cf0ea`。
- Devlin et al. [BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://aclanthology.org/N19-1423/). NAACL 2019.
- [Transformers 序列标注指南](https://huggingface.co/docs/transformers/tasks/token_classification)，用于任务头、标签对齐和损失屏蔽的实现依据。
- [CCLUE 古文语言理解测评基准](https://github.com/Ethan-yt/CCLUE)，使用其 `punc_tags` 及固定开发/测试划分，保留来源与处理说明。
- [Chinese-Punctuation-Restoration-with-Bert-CNN-RNN](https://github.com/yuboona/Chinese-Punctuation-Restoration-with-Bert-CNN-RNN)，前期调研的参考项目。本实验主模型采用 BERT 与线性分类层。
- [chinese-poetry《论语》](https://github.com/chinese-poetry/chinese-poetry/tree/b8594f81a89752241442f2ce267d6f66f96704ee/%E8%AE%BA%E8%AF%AD)，固定版本的纯文言专项参考文本。
- [中国哲学书电子化计划《学而》](https://ctext.org/analects/xue-er/zhs)，开篇段落抽查；电子版本标点差异按原样记录。
