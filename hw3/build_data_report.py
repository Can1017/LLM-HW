"""Render measured data statistics and label examples for the first experiment checkpoint."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from prepare_data import ROOT, LABELS
from core import load_samples
from public_links import publish_links


def main():
    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
                         'axes.unicode_minus': False, 'figure.dpi': 150, 'font.size': 10})
    out = ROOT / 'figures'
    out.mkdir(exist_ok=True)
    stats = json.loads((ROOT / 'results/data_statistics.json').read_text(encoding='utf-8'))
    splits = stats['splits']
    colors = ['#285b90', '#d18435', '#519781']
    names = ['train', 'validation', 'test']
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, key, title in zip(axes, ['articles', 'characters'], ['文章数量', '正文字符数量']):
        values = [splits[s][key] for s in names]
        ax.bar(['训练', '验证', '测试'], values, color=colors)
        ax.set_title(title)
        ax.set_ylim(0, max(values) * 1.18)
        for i, value in enumerate(values):
            ax.text(i, value, f'{value:,}', ha='center', va='bottom')
        ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / '01_数据划分.png')
    plt.close(fig)
    with (out / '01_数据划分.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['split', 'articles', 'characters', 'paragraphs'])
        for s in names:
            writer.writerow([s] + [splits[s][k] for k in ['articles', 'characters', 'paragraphs']])
    values = [splits['train']['labels'].get(s, 0) for s in LABELS]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(['无标点'] + LABELS[1:], values, color=['#7b8792'] + ['#285b90'] * 7)
    ax.set_yscale('log')
    ax.set_ylabel('训练位置数量（对数刻度）')
    ax.set_title('八类标签分布')
    ax.set_ylim(1000, max(values) * 3)
    for i, value in enumerate(values):
        ax.text(i, value * 1.08, f'{value:,}', ha='center', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / '02_标签分布.png')
    plt.close(fig)
    with (out / '02_标签分布.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['label', 'training_positions'])
        writer.writerows(zip(LABELS, values))
    lengths = {}
    fig, ax = plt.subplots(figsize=(9, 4))
    bins = np.geomspace(1, 50000, 40)
    for s, color in zip(names, colors):
        lengths[s] = [len(x['text']) for x in load_samples(s)]
        ax.hist(lengths[s], bins=bins, histtype='step', label=s, color=color, linewidth=1.5)
    ax.set_xscale('log')
    ax.axvline(400, linestyle='--', color='#999999', label='400 字窗口')
    ax.axvline(2000, linestyle=':', color='#999999', label='2,000 字')
    ax.set_xlabel('同篇文章连续正文长度（字）')
    ax.set_ylabel('连续正文数量')
    ax.legend(frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / '03_长文长度分布.png')
    plt.close(fig)
    with (out / '03_长文长度分布.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['split', 'run_index', 'characters'])
        for s in names:
            writer.writerows((s, i, n) for i, n in enumerate(lengths[s]))
    source = json.loads((ROOT / 'results/cclue_source.json').read_text(encoding='utf-8'))
    examples = json.loads((ROOT / 'results/label_examples.json').read_text(encoding='utf-8'))
    rows = '\n'.join(f"| {s} | {splits[s]['articles']:,} | {splits[s]['paragraphs']:,} | "
                     f"{splits[s]['characters']:,} | {sum(n > 2000 for n in lengths[s]):,} |" for s in names)
    examples_text = '\n\n'.join(f"**{e['split']}：`{e['id']}`**\n\n"
                              f"输入：{e['text']}\n\n八类目标文本：{e['reconstructed_target']}" for e in examples)
    report = f'''# HW3：数据准备与标签检查

## 1. 数据来源与清洗

本实验直接读取课程提供的人民日报半年带音压缩包，输入 SHA-256 为 `{stats['archive_sha256']}`。六个月共有 18,631 个原始文章编号，清洗后按无标点正文指纹去除 {stats['duplicate_articles_removed']} 篇重复文章。五个异常编码段落已隔离，原字节、段落编号和错误位置保存在 `data/quarantine.json`。处理前后压缩包字节指纹一致。

八类标签包括无标点及 `，。？！、：；`。清洗移除注音、分词空格和文章编号，保留正文、数字及字母；全角数字转换为半角。引号、括号和书名号按照本次标签范围移除。省略号、破折号和一个位置对应多个主标点的歧义标签使用忽略值，并在统计文件中单列计数。

## 2. 独立划分与长文输入

按月份分层，以文章为单位约 8∶1∶1 划分，种子固定为 42。训练、验证、测试的文章指纹互不交叉。同篇文章按原始编号连接连续段落，隔离或缺失段落形成上下文断点。

| 划分 | 文章数 | 原始有效段落数 | 正文字符数 | 超过 2,000 字的连续正文数 |
|---|---:|---:|---:|---:|
{rows}

![数据划分](figures/01_数据划分.png)

图 1　独立文章划分及各集合的正文字符规模。

![标签分布](figures/02_标签分布.png)

图 2　训练集八类标签分布；纵轴采用对数刻度。无标点占有效训练标签的 {values[0] / sum(values):.2%}，质量评价采用排除无标点类的 F1，并报告每类支持数。

![长文长度分布](figures/03_长文长度分布.png)

图 3　同篇文章连续正文的长度分布，虚线标出 400 字窗口和 2,000 字参考位置。

## 3. 实际标签样例

标签表示当前字符之后插入的符号。下列文本由真实标签直接重建，展示输入、标签目标与限定标点范围的对应关系。

{examples_text}

## 4. 古文外部评测集

采用 [CCLUE](https://github.com/Ethan-yt/CCLUE) 固定提交 `{source['revision']}` 的标点开发集与测试集。实际有效样本分别为 {source['splits']['validation']['samples']:,} 条和 {source['splits']['test']['samples']:,} 条；开发集比上游 README 的 4,075 条少一条，实验以实际读取的有效记录计数。

发布者对底层古籍做过简体转换、符号清理、书籍筛选及段落抽样。HW3 使用其已发布的 `punc_tags` 作为古文迁移评价标签，记录数据文件指纹和处理来源。当前阶段使用新闻语料训练，古文开发集用于了解迁移行为，测试集用于最终外部评价。

## 5. 下一阶段

使用预训练 `google-bert/bert-base-chinese` 加八类线性分类头进行完整微调。先测量 CUDA 环境下的实际显存和更新速度，据此确定正式批大小及训练设备。模型训练曲线、验证结果、测试预测和批量推理测速将在相应实验完成后生成。
'''
    report = report.replace('## 5. 下一阶段', '## 5. 完成状态')
    report = report.replace('使用预训练 `google-bert/bert-base-chinese` 加八类线性分类头进行完整微调。先测量 CUDA 环境下的实际显存和更新速度，据此确定正式批大小及训练设备。模型训练曲线、验证结果、测试预测和批量推理测速将在相应实验完成后生成。',
        '主实验与《论语》专项评测均已完成，训练、质量、效率与图示样例见[完整实验报告](作业报告.md)。')
    (ROOT / '数据准备与标签检查.md').write_text(publish_links(report), encoding='utf-8')
    print('Data report and three figures generated.', flush=True)


if __name__ == '__main__':
    main()
