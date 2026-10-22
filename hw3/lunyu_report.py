"""Build figures and a report section from the completed Analects evaluation."""
from __future__ import annotations

import csv
import json

import matplotlib.pyplot as plt
import numpy as np

from prepare_data import ROOT, LABELS


def section():
    source = json.loads((ROOT / 'results/lunyu_source.json').read_text(encoding='utf-8'))
    results = json.loads((ROOT / 'results/news-bert_lunyu.json').read_text(encoding='utf-8'))
    fixed = {r['granularity']: r for r in results['experiments']
             if r['strategy'] == 'fixed' and r['batch_size'] == 8}
    assert results['checkpoint_sha256_before'] == results['checkpoint_sha256_after']
    figures = ROOT / 'figures'
    x = np.arange(7)
    fig, ax = plt.subplots(figsize=(9, 4))
    for granularity, name, offset, color in [('paragraphs', '逐条语录', -.19, '#285b90'),
                                             ('chapters', '整篇重叠切窗', .19, '#d18435')]:
        ax.bar(x + offset, [fixed[granularity]['metrics']['per_class'][c]['f1'] for c in LABELS[1:]],
               width=.36, color=color, label=name)
    ax.set(xticks=x, xticklabels=LABELS[1:], ylabel='F1', ylim=(0, 1), title='《论语》同一文字的两种输入粒度')
    ax.legend(frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(figures / '09_论语各类标点F1.png')
    plt.close(fig)
    with (figures / '09_论语各类标点F1.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['input_granularity', 'label', 'precision', 'recall', 'f1', 'support'])
        for granularity, record in fixed.items():
            for label in LABELS[1:]:
                writer.writerow([granularity, label] + [record['metrics']['per_class'][label][k]
                                                         for k in ['precision', 'recall', 'f1', 'support']])
    chapter_results = results['per_chapter']
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(range(20), [r['metrics']['punctuation_micro_f1'] for r in chapter_results], color='#285b90')
    ax.axhline(fixed['chapters']['metrics']['punctuation_micro_f1'], linestyle='--', color='#d18435',
               label='全书汇总微 F1')
    ax.set(xticks=range(20), xticklabels=[r['chapter'].removesuffix('篇') for r in chapter_results],
           ylabel='标点微平均 F1', ylim=(0, 1), title='《论语》20 篇专项结果（固定重叠窗口，batch=8）')
    ax.tick_params(axis='x', rotation=55)
    ax.legend(frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(figures / '10_论语逐篇结果.png')
    plt.close(fig)
    with (figures / '10_论语逐篇结果.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'chapter', 'characters', 'micro_f1', 'macro_f1', 'sentence_boundary_f1'])
        for r in chapter_results:
            writer.writerow([r['id'], r['chapter'], r['characters']] + [r['metrics'][k] for k in
                ['punctuation_micro_f1', 'punctuation_macro_f1', 'sentence_boundary_f1']])
    rows = '\n'.join(f"| {'512 条语录' if r['granularity'] == 'paragraphs' else '20 篇全文'} | "
                     f"{'固定重叠' if r['strategy'] == 'fixed' else '句号推进'} | {r['batch_size']} | "
                     f"{r['metrics']['punctuation_micro_f1']:.4f} | {r['metrics']['punctuation_macro_f1']:.4f} | "
                     f"{r['metrics']['sentence_boundary_f1']:.4f} |" for r in results['experiments'])
    p, c = fixed['paragraphs']['metrics'], fixed['chapters']['metrics']
    examples = []
    names = {'opening': '开篇语录', 'longest': '最长单条语录', 'lowest_f1': '低分语录'}
    for e in results['examples']:
        number = 11 + len(examples)
        examples.append(f"**{names[e['selection']]}（`{e['id']}`）**\n\n"
                        f"完整语录共{len(e['text'])}字，标点微F1为{e['metrics']['punctuation_micro_f1']:.4f}。\n\n"
                        f"![{names[e['selection']]}标点对照](figures/examples/lunyu_{e['selection']}.png)\n\n"
                        f"图 {number}　《论语》{names[e['selection']]}的参考标点与实际预测。")
    overlap = results['supervised_quotation_sensitivity']
    text = f'''## 7. 《论语》纯文言专项评测

### 7.1 文本来源与版本核查

补充数据取自 [chinese-poetry 项目的《论语》JSON](https://github.com/chinese-poetry/chinese-poetry/blob/{source['revision']}/%E8%AE%BA%E8%AF%AD/lunyu.json)，固定提交 `{source['revision']}`。原始 JSON、README 和 MIT 许可证分别保存字节指纹。本次使用全部 20 篇、512 条语录，共 {source['characters']:,} 个去标点正文字符；有效评分位置为 {p['scored_positions']:,} 个。

版本核查发现，上游 README 写“繁体分发”和“492章”，固定 JSON 实际为简体、512 条记录。本实验以实际文件为准，保留记录顺序和原字；该来源属于可追溯的开源电子文本，参考标点采用其固定版本。[中国哲学书电子化计划《学而》](https://ctext.org/analects/xue-er/zhs)用于开篇段落抽查，首条语录相符，第二条在“不好犯上”之后存在逗号差异。两版标点分别保留，本次未用抽查版本批量替换参考标签。

预处理将文件中的 5 个英文逗号、1 个英文问号和1个英文冒号映射为对应中文标点，计数保存到来源记录。引号和书名号按八类任务范围移除，两个连续主标点冲突位置采用与主实验相同的忽略规则。全部原始文字和原始标点保存在下载文件中。

### 7.2 同一模型的两种输入粒度

专项评测加载原新闻模型，模型权重在本次评测前后的 SHA-256 相同，新增训练步数为零。短输入按512条语录分别评价；长输入按电子文本原顺序将同篇语录合并为20篇，标题不进入正文。单条最长 {source['paragraph_max_characters']} 字，整篇最长 {source['chapter_max_characters']:,} 字，{source['chapter_over_510']} 篇超过510个正文字符。整篇是原有语录编排下的输入，文体属于语录集。

两种粒度覆盖同一套正文与标签，各自独立汇总分数。逐条输入保留发布文本给出的语录边界，整篇输入需要模型自行恢复内部标点；两组分数的差异同时受到边界提示及窗口上下文的影响。

| 输入粒度 | 方法 | Batch | 标点微 F1 | 七类宏 F1 | 句末边界 F1 |
|---|---|---:|---:|---:|---:|
{rows}

固定窗口 batch=8 时，逐条语录的 Precision 为 {p['punctuation_precision']:.4f}、Recall 为 {p['punctuation_recall']:.4f}，微 F1 为 {p['punctuation_micro_f1']:.4f}；整篇对应微 F1 为 {c['punctuation_micro_f1']:.4f}、Recall 为 {c['punctuation_recall']:.4f}。这些分数衡量与选定电子版本标点的一致性。

![论语各类标点](figures/09_论语各类标点F1.png)

图 9　《论语》逐条语录与整篇输入的各类标点 F1。

![论语逐篇结果](figures/10_论语逐篇结果.png)

图 10　《论语》20篇的固定窗口预测结果；虚线为全书汇总微 F1。

### 7.3 实际输出与结果解释

{(chr(10) * 2).join(examples)}

开篇预测能识别多数问句，仍漏掉“有朋自远方来”后的逗号。人物分类列举的低分样例中，模型将全部位置预测为无标点。分类指标显示冒号表现较好，顿号、叹号及分号较弱。较高的短条语录成绩没有消除整篇输入中的漏标和类型混淆，因此本轮模型适合提供标点初稿，整篇文言输出仍需要人工复核。

针对监督训练的原文重合检查，在新闻训练集中找到 {overlap['excluded_verbatim_paragraphs']} 条完整语录的文字匹配，长度8字。剔除该语录后的 {overlap['remaining_paragraphs']} 条微 F1 为 {overlap['metrics']['punctuation_micro_f1']:.4f}，接近全部语录结果。这个检查仅覆盖新闻监督训练文本的完整语录匹配；通用BERT的预训练材料可能包含常见经典文本，本实验不据此声称《论语》对预训练模型完全陌生。

本轮保留新闻训练、CCLUE混合文体迁移和《论语》纯文言专项结果，分别说明各自的数据范围。按本次实验决定，古文领域继续微调暂缓。

'''
    return text
