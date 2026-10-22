"""Build the homework report and charts from completed training/evaluation artifacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from prepare_data import ROOT, LABELS
from public_links import file_url, publish_links, RELEASE, MODEL_DOWNLOAD


def read(name):
    return json.loads((ROOT / 'results' / name).read_text(encoding='utf-8'))


def save_table(name, headers, rows):
    path = ROOT / 'figures' / f'{name}.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--run', default='news-bert')
    args = p.parse_args()
    run = args.run
    # Requiring completion records prevents presenting partial training as a final run.
    completion = read(f'{run}_completion.json')
    history = read(f'{run}_history.json')
    evaluation = read(f'{run}_evaluation.json')
    benchmark = read(f'{run}_benchmark.json')
    data, environment = read('data_statistics.json'), read('environment.json')
    alignment = read('cclue_alignment.json')
    unknown_dev = sum(alignment['validation']['explicit_unknown_characters'].values())
    unknown_test = sum(alignment['test']['explicit_unknown_characters'].values())
    assert completion['epochs_completed'] == 3
    assert len(history) == 3
    assert len(evaluation['experiments']) == 8
    figdir = ROOT / 'figures'
    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
                         'axes.unicode_minus': False, 'font.size': 10, 'figure.dpi': 150})
    steps = [json.loads(line) for line in (ROOT / 'logs' / run / 'steps.jsonl').read_text().splitlines()]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].plot([s['optimizer_step'] for s in steps], [s['train_loss'] for s in steps], color='#285b90')
    axes[0].set(xlabel='优化器更新次数', ylabel='训练交叉熵', title='实际训练过程')
    axes[1].plot([h['epoch'] for h in history], [h['validation']['punctuation_micro_f1'] for h in history],
                 marker='o', color='#d18435', label='标点微平均 F1')
    axes[1].plot([h['epoch'] for h in history], [h['validation']['punctuation_macro_f1'] for h in history],
                 marker='s', color='#519781', label='标点宏平均 F1')
    axes[1].set(xlabel='Epoch', ylabel='F1', title='完整验证集评价', xticks=[1, 2, 3], ylim=(0, 1))
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(figdir / '04_训练与验证.png')
    plt.close(fig)
    save_table('04_训练与验证', ['epoch', 'validation_micro_f1', 'validation_macro_f1', 'validation_loss'],
               [[h['epoch']] + [h['validation'][k] for k in ['punctuation_micro_f1', 'punctuation_macro_f1', 'loss']]
                for h in history])
    save_table('04_训练损失', ['epoch', 'optimizer_step', 'train_loss', 'elapsed_seconds'],
               [[s[k] for k in ['epoch', 'optimizer_step', 'train_loss', 'elapsed_seconds']] for s in steps])
    final = {r['corpus']: r for r in evaluation['experiments'] if r['strategy'] == 'fixed' and r['batch_size'] == 8}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, corpus, title in zip(axes, ['news', 'cclue'], ['现代文留出集', 'CCLUE迁移测试集']):
        f1 = [final[corpus]['metrics']['per_class'][label]['f1'] for label in LABELS[1:]]
        ax.bar(LABELS[1:], f1, color='#285b90' if corpus == 'news' else '#d18435')
        ax.set(title=title, ylabel='F1', ylim=(0, 1))
        ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(figdir / '05_各类标点F1.png')
    plt.close(fig)
    save_table('05_各类标点F1', ['corpus', 'label', 'precision', 'recall', 'f1', 'support'],
               [[corpus, label] + [r['metrics']['per_class'][label][k] for k in ['precision', 'recall', 'f1', 'support']]
                for corpus, r in final.items() for label in LABELS[1:]])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, corpus, title in zip(axes, ['news', 'cclue'], ['现代文留出集', 'CCLUE迁移测试集']):
        cm = np.array(final[corpus]['metrics']['confusion_matrix'])
        normalized = np.divide(cm, cm.sum(1, keepdims=True), out=np.zeros_like(cm, dtype=float), where=cm.sum(1, keepdims=True) != 0)
        im = ax.imshow(normalized, vmin=0, vmax=1, cmap='Blues')
        ax.set(xticks=range(8), yticks=range(8), xticklabels=['无'] + LABELS[1:],
               yticklabels=['无'] + LABELS[1:], xlabel='预测标签', ylabel='真实标签', title=title)
        for i in range(8):
            for j in range(8):
                if normalized[i, j] >= .05:
                    ax.text(j, i, f'{normalized[i,j]:.2f}', ha='center', va='center',
                            color='white' if normalized[i,j] > .55 else 'black', fontsize=8)
    fig.colorbar(im, ax=axes, label='按真实类别归一化', shrink=.8)
    fig.savefig(figdir / '06_混淆矩阵.png', bbox_inches='tight')
    plt.close(fig)
    save_table('06_混淆矩阵', ['corpus', 'true_label', 'predicted_label', 'count'],
               [[corpus, LABELS[i], LABELS[j], r['metrics']['confusion_matrix'][i][j]]
                for corpus, r in final.items() for i in range(8) for j in range(8)])
    grouped = {}
    for r in benchmark['records']:
        if r.get('status') == 'cuda_oom':
            continue
        grouped.setdefault((r['workload'], r['strategy'], r['batch_size']), []).append(r)
    summary = []
    for (workload, strategy, batch), rs in sorted(grouped.items()):
        assert len(rs) == 5
        seconds = float(np.median([r['seconds'] for r in rs]))
        summary.append({'workload': workload, 'strategy': strategy, 'batch': batch,
                        'median_seconds': seconds, 'min_seconds': min(r['seconds'] for r in rs),
                        'max_seconds': max(r['seconds'] for r in rs),
                        'characters': rs[0]['original_characters'],
                        'characters_per_second': rs[0]['original_characters'] / seconds,
                        'model_forward_seconds': float(np.median([r['model_forward_seconds'] for r in rs])),
                        'tokenization_seconds': float(np.median([r['tokenization_seconds'] for r in rs])),
                        'largest_actual_batch': rs[0]['largest_actual_batch'],
                        'peak_mib': max(r['allocated_peak_mib'] for r in rs),
                        'micro_f1': rs[0]['metrics']['punctuation_micro_f1'],
                        'seam_f1': rs[0]['seam_metrics']['punctuation_micro_f1']})
    for key, ylabel, filename in [('characters_per_second', '原文字符 / 秒', '07_批量吞吐'),
                                  ('peak_mib', 'PyTorch 峰值分配显存 / MiB', '08_批量显存')]:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        for ax, workload, title in zip(axes, ['single_long_document', 'multiple_long_documents'], ['单篇长文', '多篇长文']):
            for strategy, label, color in [('adaptive', '预测句号推进', '#d18435'), ('fixed', '固定重叠切窗', '#285b90')]:
                rs = [r for r in summary if r['workload'] == workload and r['strategy'] == strategy]
                ax.plot([r['batch'] for r in rs], [r[key] for r in rs], marker='o', label=label, color=color)
            ax.set(xlabel='Batch 大小', ylabel=ylabel, title=title)
            ax.set_xscale('log', base=2)
            ax.set_xticks([1, 2, 4, 8, 16, 32], labels=['1', '2', '4', '8', '16', '32'])
            ax.spines[['top', 'right']].set_visible(False)
            ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(figdir / f'{filename}.png')
        plt.close(fig)
    save_table('07_批量吞吐', list(summary[0]), [list(r.values()) for r in summary])
    save_table('08_批量显存', ['workload', 'strategy', 'requested_batch', 'largest_actual_batch', 'peak_allocated_mib'],
               [[r[k] for k in ['workload', 'strategy', 'batch', 'largest_actual_batch', 'peak_mib']] for r in summary])
    quality_rows = '\n'.join(
        f"| {'现代文' if r['corpus'] == 'news' else 'CCLUE'} | {'句号推进' if r['strategy'] == 'adaptive' else '固定重叠'} | {r['batch_size']} | "
        f"{r['metrics']['punctuation_micro_f1']:.4f} | {r['metrics']['punctuation_macro_f1']:.4f} | "
        f"{r['metrics']['sentence_boundary_f1']:.4f} | {r['seconds']:.2f} |" for r in evaluation['experiments'])
    class_rows = '\n'.join(f"| {'现代文' if corpus == 'news' else 'CCLUE'} | {label} | "
                           f"{r['metrics']['per_class'][label]['precision']:.4f} | "
                           f"{r['metrics']['per_class'][label]['recall']:.4f} | "
                           f"{r['metrics']['per_class'][label]['f1']:.4f} | "
                           f"{r['metrics']['per_class'][label]['support']:,} |"
                           for corpus, r in final.items() for label in LABELS[1:])
    seam_rows = '\n'.join(f"| {'句号推进' if r['strategy']=='adaptive' else '固定重叠'} | "
                          f"{r['batch_size']} | {r['seam_metrics']['scored_positions']:,} | "
                          f"{r['seam_metrics']['punctuation_micro_f1']:.4f} | "
                          f"{r['metrics']['punctuation_micro_f1']:.4f} |"
                          for r in evaluation['experiments'] if r['corpus'] == 'news')
    speed_rows = '\n'.join(f"| {'单篇' if r['workload'] == 'single_long_document' else '多篇'} | "
                           f"{'句号推进' if r['strategy'] == 'adaptive' else '固定重叠'} | {r['batch']} | {r['median_seconds']:.3f} | "
                           f"{r['characters_per_second']:,.0f} | {r['peak_mib']:.1f} | {r['micro_f1']:.4f} |"
                           for r in summary)
    examples_text = []
    figure_number = 14
    titles = {'first_medium': '中等长度样例', 'first_question': '问号样例',
              'longest': '最长样例', 'lowest_f1_medium': '低分样例'}
    for corpus in ['news', 'cclue']:
        for e in read(f'{run}_{corpus}_examples.json'):
            key = corpus + '_' + e['selection']
            examples_text.append(f"### {'现代文' if corpus == 'news' else 'CCLUE'}：{titles[e['selection']]}\n\n"
                                 f"样例编号：`{e['id']}`；全文 {e['characters']:,} 字，全文标点微 F1 为 "
                                 f"{e['metrics']['punctuation_micro_f1']:.4f}。图中展示原位置上的字符与其后标点，"
                                 f"完整样例见[结果 JSON]({file_url(f'results/{run}_{corpus}_examples.json')})。\n\n"
                                 f"![{titles[e['selection']]}标点错误对照](figures/examples/{key}.png)\n\n"
                                 f"图 {figure_number}　{'现代文' if corpus == 'news' else 'CCLUE'}{titles[e['selection']]}的实际预测。")
            figure_number += 1
            if e['selection'] == 'longest' and e['seam_excerpts']:
                examples_text.append("![窗口接缝标点对照](figures/examples/news_seam.png)\n\n"
                                     f"图 {figure_number}　位置350前后各40字的接缝对照。")
                figure_number += 1
    best_epoch = evaluation['checkpoint_record']['epoch']
    speed_findings = []
    for workload, title in [('single_long_document', '单篇长文'), ('multiple_long_documents', '多篇长文')]:
        base = next(r for r in summary if r['workload'] == workload and r['strategy'] == 'fixed' and r['batch'] == 1)
        best = max((r for r in summary if r['workload'] == workload and r['strategy'] == 'fixed'),
                   key=lambda r: r['characters_per_second'])
        adaptive = next(r for r in summary if r['workload'] == workload and r['strategy'] == 'adaptive' and r['batch'] == 1)
        speed_findings.append(
            f"{title}中，固定窗口方案在 batch={best['batch']} 时取得本次组合内的最高吞吐 "
            f"{best['characters_per_second']:,.0f} 字/秒，相对相同窗口的 batch=1 加速 "
            f"{base['median_seconds']/best['median_seconds']:.2f} 倍；相对句号推进 batch=1 的整体加速为 "
            f"{adaptive['median_seconds']/best['median_seconds']:.2f} 倍。前一个比值反映批处理收益，"
            f"后一个比值同时包含窗口策略和批处理变化。该组合的标点微 F1 为 {best['micro_f1']:.4f}，"
            f"句号推进基线为 {adaptive['micro_f1']:.4f}。")
    comparison = []
    for corpus, title in [('news', '现代文'), ('cclue', 'CCLUE')]:
        r = final[corpus]
        comparison.append(f"{title}固定窗口 batch=8 相对 batch=1 有 "
                          f"{r['different_labels_from_fixed_batch1']:,} 个位置的预测标签不同，"
                          f"全量评分位置为 {r['metrics']['scored_positions']:,} 个。")
    report = f'''# 高效率 BERT 古文断句标点：微调与批量长文推理实验

## 摘要

本实验以课程提供的 1998 年半年人民日报带音语料构造字符后标点标签，微调预训练中文 BERT，并在独立现代文留出集及 CCLUE 标点测试集上评价。训练使用全部 {data['splits']['train']['articles']:,} 篇训练文章，完成三个 epoch；最佳验证模型来自第 {best_epoch} 轮。模型恢复无标点及七种常用标点。长文实验比较预测句号推进、多文章批处理及固定重叠窗口批处理，记录质量、端到端速度、显存与接缝表现。

固定窗口 batch=8 的现代文标点微 F1 为 {final['news']['metrics']['punctuation_micro_f1']:.4f}，CCLUE 迁移标点微 F1 为 {final['cclue']['metrics']['punctuation_micro_f1']:.4f}。两套数据独立报告。CCLUE 发布数据含文言与现代白话样例，其分数描述这套固定测试划分上的迁移表现。

## 1. 任务与实验设计

依据课程课件第68页，本实验完成预训练 BERT 的断句标点微调和超出上下文长度的批量推理。模型为 [google-bert/bert-base-chinese](https://huggingface.co/google-bert/bert-base-chinese)，使用 12 层、768 维 BERT 编码器及八类线性分类层。预训练权重固定版本 `8f23c25b06e129b6c986331a13d8d025a92cf0ea`，标点头从随机参数开始，全部模型参数参与微调。

## 2. 数据来源与处理

输入为课程提供的六个月 `2003版-带音` 文件，原始压缩包 SHA-256 为 `{data['archive_sha256']}`。解析文章段落编号、去除注音和分词空格，保留正文、数字与字母，全角数字转为半角。按无标点正文去除 {data['duplicate_articles_removed']} 篇重复文章；五个异常编码段落保存原字节并隔离。原始压缩包保持原样。

按月份分层、文章级独立划分训练 {data['splits']['train']['articles']:,} 篇、验证 {data['splits']['validation']['articles']:,} 篇、测试 {data['splits']['test']['articles']:,} 篇。每类标签表示字符后插入 `，。？！、：；` 中的一个符号或无标点。引号、括号、书名号按任务范围移除；省略号、破折号及多主标点冲突位置使用忽略标签。全文连续段落作为长文输入，缺失及隔离段落形成断点。

标题、署名、图片说明和正文都保留原有七类标点监督，段落拼接保持原标签，标题末尾和换段处沿用原文本中的标点状态。正文中的版面符号及特殊字仍按实际字符处理。该口径评价对发布文本标点的恢复，编辑标点习惯也是误差来源之一。

![数据划分](figures/01_数据划分.png)

图 1　文章级独立数据划分。

![标签分布](figures/02_标签分布.png)

图 2　训练集标签数量，采用对数纵轴。

![长度分布](figures/03_长文长度分布.png)

图 3　自然文章连续正文的长度分布。

外部标点评价采用 [CCLUE](https://github.com/Ethan-yt/CCLUE) 发布的固定测试划分，固定提交 `ed481c453c1c36397f86905a2bda625ecc5607e1`。上游经过简体转换、符号清理、书籍筛选和 1% 段落抽样。实际有效开发样本 4,074 条、测试样本 3,992 条。开发样本数与上游 README 的 4,075 相差一条，统计采用实际有效记录。本轮模型仅在新闻训练集上学习。

样例复核发现 CCLUE 固定测试集包含现代白话叙述，例如 `cclue-test-108-1964` 的开头“明妃正诧异的时候，一回头，见天皇满面怒容站在她身后”。本实验保留该样例及完整发布划分，明确采用混合文体测试集口径。由于发布记录未提供逐条来源路径，实验按实际记录编号呈现，整体分数与纯文言专项效果分别解释。

全量对齐发现古文开发集含 {unknown_dev} 个私用区等特殊字符位置，测试集含 {unknown_test} 个。这类字符在模型输入中显式映射为 `[UNK]`，保持原始文字、标签和评分位置；避免 tokenizer 默认清除字符后导致标签位移。普通词表外字按 BERT 的未知词处理。

## 3. 微调实现与真实运行

采用 Conda 环境 `hw3-bert`、Python {environment['python'].split()[0]}、PyTorch {environment['torch']}、CUDA {environment['cuda_runtime']}。GPU 为 {environment['gpu']}，显存约 {environment['gpu_memory_mib']:.0f} MiB。输入 400 字、步长 300 字，tokenizer 按字符对齐到最后一个子词；特殊位置及补齐位置使用 `-100`。实际最大输入长度 402 token，每个有效正文标签恰好进入一次监督。

模型输入去除目标标点后的文字，输出每个字符后的八类分数。交叉熵在有效监督位置上计算，推理取分数最高的类别并插回原文。这里的“解码”是一次前向中的并行序列标注，每个字符都得到预测结果。BERT 的双向注意力利用窗口中的左右上下文。

字符与子词的对齐使用 `word_ids()`。每个原始字符定位到最后一个子词，预测该字符之后的标点。以下为实现中的关键逻辑：

```python
for token_position, character_id in enumerate(batch.word_ids(row)):
    if character_id is not None:
        last[character_id] = token_position
for character_id in range(owned_start, owned_end):
    labels[last[character_id]] = gold[character_id]
```

AdamW 学习率 2e-5、权重衰减 0.01、线性 warmup 比例 0.1、三轮线性衰减。混合精度 FP16，实际训练 batch=4，梯度累积 4 次，名义有效 batch=16；固定种子 42。训练耗时 {completion['elapsed_seconds']/3600:.2f} 小时，包含完整验证和最佳模型保存。验证集标点微平均 F1 用于选模，测试集用于最终评价。

![训练验证](figures/04_训练与验证.png)

图 4　实际训练交叉熵与完整验证集 F1。

## 4. 批量长文推理方法

课件基线每次预测 400 字，在前 300 字中寻找最后一个预测句号，提交至该句号；没有句号时提交 300 字。剩余不足 400 字时一次提交完整尾部。下一起点依赖当前预测，因此单篇文章保留顺序依赖。多文章批处理将不同文章的当前窗口组成 batch。

固定重叠方案预先切出 400 字上下文、步长 300 字的窗口，记录全局位置。重叠区中点划分各窗口拥有的位置，首尾窗口覆盖文章边缘。所有窗口可提前组成 batch，再按全局位置恢复标签。每个正文字符最终输出一个预测标签，原文字符顺序保持一致。

固定窗口 batch=1 与 batch=8 使用相同上下文和拼接规则，比较批处理收益；与句号推进方法对照时，同时观察质量变化。测试时窗口构造与拼接只读取输入文字。

相邻上下文窗口如 `[0,400)` 和 `[300,700)`，中点边界为 350；前窗提交 `[0,350)`，后窗从 350 开始提交。这使重叠区两侧各保留约 50 字上下文。固定窗口拼接的核心实现为：

```python
for (document_id, (start, end, owned_start, owned_end)), pred in zip(tasks, output):
    result[document_id][owned_start:owned_end] = pred[owned_start-start:owned_end-start]
```

## 5. 完整测试评价

主指标采用排除无标点类别的标点微平均 F1、七类宏平均 F1。句末边界集合为 `。？！`。同位置错误标点类型同时形成一个假阳性和一个假阴性。表中时间为一次完整测试端到端运行，重复测速另见第 6 节。

| 语料 | 推进方法 | Batch | 标点微 F1 | 标点宏 F1 | 句末边界 F1 | 完整测试时间 / s |
|---|---|---:|---:|---:|---:|---:|
{quality_rows}

| 语料 | 标点 | Precision | Recall | F1 | 真实位置数 |
|---|---|---:|---:|---:|---:|
{class_rows}

{' '.join(comparison)} FP16 批处理可能改变少量临界分数处的最大类别，质量结论以实际统计为准。

![分类F1](figures/05_各类标点F1.png)

图 5　现代文测试与 CCLUE 迁移测试的各类标点 F1。

![混淆矩阵](figures/06_混淆矩阵.png)

图 6　按真实标签归一化的混淆矩阵。

## 6. 长文推理效率与显存

选取测试集中一篇最长连续文章作为单篇负载，从至少 2,000 字的真实测试文章中按种子 42 选取 24 篇作为多篇负载。每个组合预热后重复五次，计时包含分词、数据传输、前向预测、取最大类别和拼接，排除模型加载；GPU 在计时边界同步。吞吐分母采用原文字符数，重叠字符按原位置计算一次。

| 负载 | 方法 | Batch | 中位时间 / s | 原文字符 / s | 峰值分配显存 / MiB | 标点微 F1 |
|---|---|---:|---:|---:|---:|---:|
{speed_rows}

{chr(10).join(speed_findings)}

测速同时用 CUDA Event 累计模型前向时间，并用 CPU 时钟累计分词时间；完整时间仍包含传输、取最大类别和拼接。分阶段统计保存在图 7 对应 CSV，避免将纯模型时间与用户等待的总时间混用。

![批量吞吐](figures/07_批量吞吐.png)

图 7　相同长文负载上的批量推理吞吐。

![批量显存](figures/08_批量显存.png)

图 8　不同 batch 的 PyTorch 峰值分配显存；桌面进程和驱动显存另外占用设备容量。

接缝分析以固定窗口拥有区域的边界前后各 20 字为范围，指标及有效位置数保存在 benchmark JSON。CCLUE 发布段落均短于 400 字，该项测试衡量其固定短段落上的标点迁移质量；长文效率实验使用保持真实顺序的现代文文章。

| 方法 | Batch | 接缝评分位置数 | 接缝微 F1 | 全文微 F1 |
|---|---:|---:|---:|---:|
{seam_rows}

上表将全部方法放在相同的固定窗口接缝坐标上评价，能够比较这些位置的预测质量。单篇句号推进方法的实际 batch 始终为 1，因此仅提高请求 batch 对其吞吐的影响主要来自运行波动；固定切窗使同篇文章的多个窗口实际进入同一前向批次。

## 7. 实际预测与错误分析

样例规则固定为首个中等长度样例、首个含问号样例、最长样例，以及含至少五个标点的中等长度样例中微 F1 最低者。样例覆盖正常输出、少数类、长文与失败案例。完整逐字预测可从[实验归档]({RELEASE})下载，各样例图下附在线结果链接。

示例采用上下对齐的参考／预测图。绿色表示正确标点，橙色“×”表示漏标，红色表示多标，紫色表示类型错误，灰色“·”表示该位置按原实验规则不评分。图中的排版空白只用于对齐。颜色标记均由保存的逐字标签与预测直接生成。

**两个源字符的核查。** 人民日报原始段落 `19980304-02-002-001` 在标题中已经含有 `〓`，其 Unicode 为 U+3013，名称 GETA MARK，常用于缺字或不可表示字符的占位；原文件编码字节为 `A1 FE`。现有材料无法确认该标题位置原本代表什么字符，示例图用黄色方框保留位置并标注编码。

CCLUE 原始测试文件在“巴东朐”之后含 U+E583，属于 Unicode 私用区，缺少原配字库或映射表时没有可通用解释的字义。旧报告中的 `[U+E583]` 是该字符的可见编码说明。此次图中统一显示为黄色方框，注出 U+E583；源数据、模型输入处理、标签与既有分数均保持原样。完整核查记录见[字符核查结果]({file_url('results/source_character_audit.json')})。

{(chr(10) * 2).join(examples_text)}

## 8. 结果解释与复现

本实验完成新闻语料全量微调、完整留出集评价、CCLUE 固定划分迁移评价，以及单篇和多篇长文的批量效率对照。微平均反映主要标点的整体恢复，宏平均及每类支持数揭示问号、叹号等少数类别的行为。CCLUE 的混合文体、发布者预处理及版本标点习惯共同界定了迁移分数的解释范围。

错误矩阵显示两类具体问题：现代文中叹号和分号较多地混淆为句号或逗号，CCLUE 中大量真实逗号、句号和顿号被预测为无标点。新闻语料训练形成的标点习惯迁移到该集合时，整体召回下降。领域适配可作为下一组独立对照，先复核训练数据的文体和来源，再以独立开发集选模，保留本轮新闻模型与测试结果作为基线。

全部运行命令见[项目说明]({file_url('README.md')})。训练逐步日志、每轮验证、选模记录、来源版本、数据指纹、完整测试指标、五次重复测速及 PNG/CSV 构成复现实验产物。实验固定一个训练种子，测速的重复范围是相同模型推理运行。

**在线复核入口：**[数据统计]({file_url('results/data_statistics.json')}) · [三轮训练与验证]({file_url('results/news-bert_history.json')}) · [完整测试结果]({file_url('results/news-bert_evaluation.json')}) · [长文测速]({file_url('results/news-bert_benchmark.json')}) · [论语专项]({file_url('results/news-bert_lunyu.json')}) · [图表及CSV]({file_url('figures', True)}) · [训练模型下载]({MODEL_DOWNLOAD}) · [模型与完整预测归档]({RELEASE})。

## 参考文献与项目

1. Devlin J, Chang M W, Lee K, Toutanova K. [BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://aclanthology.org/N19-1423/). NAACL, 2019, 4171–4186.
2. [google-bert/bert-base-chinese 模型卡及配置](https://huggingface.co/google-bert/bert-base-chinese). 预训练权重与 tokenizer 来源。
3. [Hugging Face Transformers: Token classification](https://huggingface.co/docs/transformers/tasks/token_classification). 任务头、标签对齐和屏蔽损失的实现依据。
4. [CCLUE 古文语言理解测评基准](https://github.com/Ethan-yt/CCLUE). 古文标点标签、固定划分与数据构造说明。
5. [Chinese-Punctuation-Restoration-with-Bert-CNN-RNN](https://github.com/yuboona/Chinese-Punctuation-Restoration-with-Bert-CNN-RNN). 前期标点恢复实现调研参考。
6. 课程提供：`1998-上半年-带音.rar`，人民日报半年带音文件，版本以原文件字节指纹标识。
'''
    from lunyu_report import section
    report = report.replace('## 7. 实际预测与错误分析', section() + '## 8. 主实验实际预测与错误分析')
    report = report.replace('## 8. 结果解释与复现', '## 9. 结果解释与复现')
    lunyu = read(f'{run}_lunyu.json')
    special = {r['granularity']: r['metrics'] for r in lunyu['experiments']
               if r['strategy'] == 'fixed' and r['batch_size'] == 8}
    summary = (f"《论语》专项使用同一新闻模型，512条语录微F1为{special['paragraphs']['punctuation_micro_f1']:.4f}，"
               f"20篇全文输入微F1为{special['chapters']['punctuation_micro_f1']:.4f}。"
               "专项采用可追溯电子文本的参考标点，按原记录说明版本与处理差异。古文领域继续微调暂缓。")
    report = report.replace('## 1. 任务与实验设计', summary + '\n\n## 1. 任务与实验设计')
    report = report.replace('## 摘要', f'[GitHub 项目]({file_url("README.md")}) · [Word 报告]({file_url("高效率BERT古文断句标点微调与批量长文推理实验.docx")})\n\n## 摘要')
    report += '\n7. [chinese-poetry《论语》电子文本与版本说明](https://github.com/chinese-poetry/chinese-poetry/tree/b8594f81a89752241442f2ce267d6f66f96704ee/%E8%AE%BA%E8%AF%AD). MIT 许可证，专项参考标点来源。\n8. [中国哲学书电子化计划《论语·学而》](https://ctext.org/analects/xue-er/zhs). 开篇段落抽查与电子版本标点差异对照。\n'
    (ROOT / '作业报告.md').write_text(publish_links(report), encoding='utf-8')
    print('Completed report and measured charts generated.', flush=True)


if __name__ == '__main__':
    main()
