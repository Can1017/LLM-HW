#!/usr/bin/env python3
"""Generate publication-grade report figures with human-readable labels (no internal IDs)."""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch

FONTPATH = Path('C:/Windows/Fonts/msyh.ttc')
if FONTPATH.exists():
    import matplotlib.font_manager as fm
    fm.fontManager.addfont(str(FONTPATH))
    plt.rcParams['font.family'] = FontProperties(fname=str(FONTPATH)).get_name()

plt.rcParams.update({
    'font.size': 9.5,
    'axes.unicode_minus': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.facecolor': 'white',
    'savefig.facecolor': 'white',
    'axes.labelcolor': '#1F2937',
    'xtick.color': '#374151',
    'ytick.color': '#374151',
    'svg.fonttype': 'none',
})

COLORS = ['#0072B2', '#D97706', '#059669', '#7C3AED']
DEST = ROOT / 'reports/figures'
DEST.mkdir(parents=True, exist_ok=True)

audit = json.loads((ROOT / 'results/audit/historical_audit.json').read_text(encoding='utf-8'))
supp = json.loads((ROOT / 'results/supplement/summary.json').read_text(encoding='utf-8'))
stab_rev = json.loads((ROOT / 'results/audit/stability_semantic_review.json').read_text(encoding='utf-8'))
poems_meta = {p['id']: p for p in json.loads((ROOT / 'data/poems.json').read_text(encoding='utf-8'))['poems']}


def save(fig, name: str) -> None:
    fig.savefig(DEST / f'{name}.png', dpi=260, bbox_inches='tight', pad_inches=0.14)
    fig.savefig(DEST / f'{name}.svg', bbox_inches='tight', pad_inches=0.14)
    plt.close(fig)


def fig01_workflow() -> None:
    fig, ax = plt.subplots(figsize=(11.2, 4.9))
    ax.axis('off')
    ax.set_xlim(0, 11.2)
    ax.set_ylim(0, 4.9)

    banner1 = FancyBboxPatch((0.2, 2.70), 10.8, 2.00, boxstyle='round,pad=0.08,rounding_size=0.12',
                             facecolor='#F0F7FF', edgecolor='#93C5FD', lw=1.2)
    banner2 = FancyBboxPatch((0.2, 0.20), 10.8, 2.00, boxstyle='round,pad=0.08,rounding_size=0.12',
                             facecolor='#F0FDF4', edgecolor='#86EFAC', lw=1.2)
    ax.add_patch(banner1)
    ax.add_patch(banner2)

    ax.text(0.42, 4.45, '第一部分：四类提示改动的同批对照与留出集独立检验（72 次正式调用 + 9 次试跑校准）',
            fontsize=10.5, fontweight='bold', color='#1E3A8A', va='center')
    ax.text(0.42, 1.95, '第二部分：文学评价口径敏感性分析与注释粒度消融实验（24 次补充消融调用）',
            fontsize=10.5, fontweight='bold', color='#065F46', va='center')

    top_boxes = [
        (0.40, 2.90, 2.35, 1.30, '1. 语料构建与参数校准\n12 首诗词（8 开发 + 4 测试）\n逐首设定文化词与诗学关系点\n试跑 9 次锁定输出上限 12000'),
        (3.08, 2.90, 2.38, 1.30, '2. 开发集四方案同批对照\n直接译 / 任务标准 / 参考注 / 示例\n开发集 32 次 + 稳定性采样 24 次\n固定同一模型与解码温度 0.2'),
        (5.79, 2.90, 2.35, 1.30, '3. 双视角匿名盲评与选型\n忠实文学译介 + 自由改写双视角\n参考注释版术语分最高（0.969）\n任务标准版散文化且耗时翻倍淘汰'),
        (8.47, 2.90, 2.33, 1.30, '4. 留出测试集独立验证\n《枫桥夜泊》《春晓》等 4 首留出诗\n直接翻译与参考注释各重复 2 次\n术语同为满分，按最简胜出留基线'),
    ]
    bot_boxes = [
        (0.40, 0.40, 2.35, 1.30, '5. 词义与歧义评价口径分析\n区分完全误译（0次）与局部润色\n检验接纳功能对等异译的得分变化\n统一《枫桥夜泊》歧义句评判标准'),
        (3.08, 0.40, 2.38, 1.30, '6. 注释粒度三条件消融设计\n无注释 / 单条核心注 / 完整词表注\n完整词表严格包含单条核心注释\n隔离注释内容质量与词条数量效应'),
        (5.79, 0.40, 2.35, 1.30, '7. 诊断名篇与拓展新诗检验\n复测《登鹳雀楼》与《枫桥夜泊》\n拓展《商山早行》与《竹里馆》\n每首每条件重复 2 次（共 24 次）'),
        (8.47, 0.40, 2.33, 1.30, '8. 成本拆解与最终方法裁决\n三条件术语与关系分均达 1.00\n完整词表诱发尾注增至 3.88 行/首\n确立“最简基线 + 按需单条注释”'),
    ]

    for x, y, w, h, text in top_boxes:
        card = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.04,rounding_size=0.08',
                              facecolor='white', edgecolor='#3B82F6', lw=1.1)
        ax.add_patch(card)
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=8.2, linespacing=1.45, color='#1F2937')

    for x, y, w, h, text in bot_boxes:
        card = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.04,rounding_size=0.08',
                              facecolor='white', edgecolor='#10B981', lw=1.1)
        ax.add_patch(card)
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=8.2, linespacing=1.45, color='#1F2937')

    for i in range(3):
        x1 = top_boxes[i][0] + top_boxes[i][2]
        x2 = top_boxes[i + 1][0]
        ax.annotate('', xy=(x2 - 0.03, 3.55), xytext=(x1 + 0.03, 3.55),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#2563EB'))
        ax.annotate('', xy=(x2 - 0.03, 1.05), xytext=(x1 + 0.03, 1.05),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#059669'))

    ax.annotate('', xy=(5.6, 2.24), xytext=(5.6, 2.66),
                arrowprops=dict(arrowstyle='->', lw=1.6, color='#4B5563'))
    ax.text(5.78, 2.45, '针对留出集天花板效应与局部注释假设展开深度消融（总计 96 次正式调用）',
            ha='left', va='center', fontsize=8.8, fontweight='bold', color='#374151')

    save(fig, '01_实验设计与证据层次')


def fig02_dev_quality() -> None:
    orig = audit['original']['dev']
    sr_scores = {'v0': 7.625, 'v1': 7.625, 'v2': 8.000, 'v3': 7.875}

    dev_items = {}
    with (ROOT / 'results/scored_dev_items.csv').open(encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            dev_items[(r['poem_id'], r['version'])] = (
                float(r['term_rate']),
                float(r['relation_rate']),
                float(r['english_score']),
            )

    fig = plt.figure(figsize=(11.8, 4.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.25], wspace=0.38)

    ax1 = fig.add_subplot(gs[0, 0])
    metrics = [
        ('术语保持分', [orig[f'v{i}']['term'] for i in range(4)]),
        ('关系保持分', [orig[f'v{i}']['relation'] for i in range(4)]),
        ('英语表达 (/2)', [orig[f'v{i}']['english'] / 2.0 for i in range(4)]),
        ('自由改写视角 (/8)', [sr_scores[f'v{i}'] / 8.0 for i in range(4)]),
    ]
    x = np.arange(len(metrics)) * 1.15
    width = 0.21
    v_names = ['直接翻译基线', '加入任务标准', '加入参考注释', '加入边界示例']
    for idx, v_label in enumerate(v_names):
        vals = [m[1][idx] for m in metrics]
        offset = (idx - 1.5) * width
        bars = ax1.bar(x + offset, vals, width=width * 0.92, color=COLORS[idx], label=v_label, edgecolor='white', lw=0.5)
        for b, val in zip(bars, vals):
            dy = 0.010 if idx % 2 == 0 else 0.024
            ax1.text(b.get_x() + b.get_width() / 2, val + dy, f'{val:.2f}',
                     ha='center', va='bottom', fontsize=7.3, color=COLORS[idx], fontweight='bold')

    ax1.set_xticks(x, [m[0] for m in metrics], fontsize=8.8)
    ax1.set_ylim(0.65, 1.11)
    ax1.set_ylabel('归一化得分（纵轴自 0.65 起以放大差异）', fontsize=9)
    ax1.set_title('(a) 开发集四种提示方案的多维质量均值对比', fontsize=10.2, fontweight='bold', pad=10)
    ax1.grid(axis='y', alpha=0.2)
    ax1.set_axisbelow(True)
    ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), frameon=False, fontsize=8.2, ncol=4)

    ax2 = fig.add_subplot(gs[0, 1])
    poem_ids = [f'T0{i}' for i in range(1, 9)]
    poem_labels = [
        f"{poems_meta[pid]['author_zh']}《{poems_meta[pid]['title_zh'].split('·')[0]}》"
        for pid in poem_ids
    ]
    versions = ['v0', 'v1', 'v2', 'v3']
    mat = np.zeros((len(poem_ids), len(versions)))
    for r_i, pid in enumerate(poem_ids):
        for c_i, ver in enumerate(versions):
            t_sc, r_sc, e_sc = dev_items[(pid, ver)]
            mat[r_i, c_i] = (t_sc + r_sc + e_sc / 2.0) / 3.0

    im = ax2.imshow(mat, cmap='YlGnBu', vmin=0.72, vmax=1.02, aspect='auto')
    ax2.set_xticks(np.arange(4), ['直接翻译', '任务标准', '参考注释', '边界示例'], fontsize=9)
    ax2.set_yticks(np.arange(8), poem_labels, fontsize=8.8)
    ax2.set_title('(b) 逐首质量剖面矩阵（格内：术语 / 关系 / 英语分）', fontsize=10.2, fontweight='bold', pad=10)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    for r_i, pid in enumerate(poem_ids):
        for c_i, ver in enumerate(versions):
            t_sc, r_sc, e_sc = dev_items[(pid, ver)]
            txt = f'{t_sc:.2f}/{r_sc:.2f}/{int(e_sc)}'
            is_diff = (t_sc < 1.0 or r_sc < 1.0 or e_sc < 2.0)
            color = 'white' if mat[r_i, c_i] > 0.93 else '#111827'
            weight = 'bold' if is_diff else 'normal'
            ax2.text(c_i, r_i, txt, ha='center', va='center', fontsize=8.2, color=color, fontweight=weight)

    cbar = fig.colorbar(im, ax=ax2, fraction=0.035, pad=0.03)
    cbar.ax.tick_params(labelsize=8)
    cbar.set_label('三维综合均值', fontsize=8.5)

    save(fig, '02_原开发集质量对比')


def fig03_cost_breakdown() -> None:
    orig_dev = audit['original']['dev']
    orig_test = audit['original']['test']
    supp_all = supp['summaries']['all']

    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.6), gridspec_kw={'width_ratios': [1.28, 0.82, 1.05]})
    panels = [
        (axes[0], orig_dev, ['v0', 'v1', 'v2', 'v3'], ['直接翻译', '任务标准', '参考注释', '边界示例'], '(a) 开发集（每方案 8 次）'),
        (axes[1], orig_test, ['v0', 'v2'], ['直接翻译', '参考注释'], '(b) 测试集（每方案 8 次）'),
        (axes[2], supp_all, ['a0', 'a1', 'a2'], ['无注释', '单条注释', '完整注释'], '(c) 注释消融（每条件 8 次）'),
    ]

    for ax, data, keys, labels, title in panels:
        x = np.arange(len(keys))
        bottom = np.zeros(len(keys))
        layers = [
            ('prompt_tokens', '#0072B2', '输入提示词 (Prompt)'),
            ('reasoning_tokens', '#93C5FD', '内部思维链推理 (Reasoning)'),
            ('visible_tokens_estimate', '#D97706', '可见译文与尾注 (Visible)'),
        ]
        for key, col, lab in layers:
            vals = np.array([data[k][key] for k in keys]) / 1000.0
            ax.bar(x, vals, bottom=bottom, color=col, label=lab, width=0.55, edgecolor='white', lw=0.5)
            bottom += vals

        for j, k in enumerate(keys):
            tot_k = bottom[j]
            lat_avg = data[k]['latency_sec'] / data[k]['n']
            reason_pct = data[k]['reasoning_tokens'] / data[k]['completion_tokens'] * 100
            ax.text(j, tot_k + max(bottom) * 0.025, f'{tot_k:.2f}k\n({lat_avg:.1f}s/次)',
                    ha='center', va='bottom', fontsize=8.0, linespacing=1.2)
            r_val = data[k]['reasoning_tokens'] / 1000.0
            p_val = data[k]['prompt_tokens'] / 1000.0
            if r_val > 1.8:
                ax.text(j, p_val + r_val / 2, f'推理占输出\n{reason_pct:.0f}%',
                        ha='center', va='center', fontsize=7.3, color='#1E3A8A', fontweight='bold')

        ax.set_xticks(x, labels, fontsize=8.8)
        ax.set_ylim(0, max(bottom) * 1.26)
        ax.set_title(title, fontsize=10, fontweight='bold', pad=8)
        ax.grid(axis='y', alpha=0.2)
        ax.set_axisbelow(True)

    axes[0].set_ylabel('累计消耗（千 Token）', fontsize=9.5)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.04),
               ncol=3, frameon=False, fontsize=9)
    fig.tight_layout(w_pad=1.8, rect=(0, 0.05, 1, 1))
    save(fig, '03_输入推理与可见输出成本')


def fig04_sensitivity_and_stability() -> None:
    orig_dev = audit['original']['dev']
    sens_dev = audit['sensitivity']['dev_accept_reasonable_translations']
    orig_test = audit['original']['test']
    sens_test = audit['sensitivity']['test_consistent_ambiguity']

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.6), gridspec_kw={'width_ratios': [1.18, 0.88, 1.22]})

    # Panel A: Dev term sensitivity
    ax = axes[0]
    x = np.arange(4) * 1.1
    w = 0.36
    orig_t = [orig_dev[f'v{i}']['term'] for i in range(4)]
    sens_t = [sens_dev[f'v{i}']['term'] for i in range(4)]
    ax.bar(x - w / 2, orig_t, width=w * 0.9, color='#94A3B8', label='严格字面匹配口径')
    ax.bar(x + w / 2, sens_t, width=w * 0.9, color='#0072B2', label='接纳功能对等异译')
    for j in range(4):
        ax.text(x[j] - w / 2, orig_t[j] + 0.006, f'{orig_t[j]:.3f}', ha='center', fontsize=7.2, color='#475569')
        dy = 0.019 if abs(sens_t[j] - orig_t[j]) < 0.01 else 0.006
        ax.text(x[j] + w / 2, sens_t[j] + dy, f'{sens_t[j]:.3f}', ha='center', fontsize=7.2, color='#0072B2', fontweight='bold')
    ax.set_xticks(x, ['直接翻译', '任务标准', '参考注释', '边界示例'], fontsize=8.6)
    ax.set_ylim(0.75, 1.07)
    ax.set_ylabel('归一化得分（纵轴自 0.75 起）', fontsize=9)
    ax.set_title('(a) 开发集术语分对异译口径的敏感性', fontsize=10, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, fontsize=7.8)
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)

    # Panel B: Test relation sensitivity
    ax = axes[1]
    xx = np.arange(2)
    w2 = 0.32
    old_r = [orig_test[k]['relation'] for k in ['v0', 'v2']]
    new_r = [sens_test[k]['relation'] for k in ['v0', 'v2']]
    ax.bar(xx - w2 / 2, old_r, width=w2 * 0.92, color='#94A3B8', label='单一解读扣分口径')
    ax.bar(xx + w2 / 2, new_r, width=w2 * 0.92, color='#059669', label='合理单一解读满分')
    for j in range(2):
        ax.text(xx[j] - w2 / 2, old_r[j] + 0.007, f'{old_r[j]:.3f}', ha='center', fontsize=7.8, color='#475569')
        ax.text(xx[j] + w2 / 2, new_r[j] + 0.007, f'{new_r[j]:.3f}', ha='center', fontsize=7.8, color='#059669', fontweight='bold')
    ax.set_xticks(xx, ['直接翻译基线', '加入参考注释'], fontsize=8.8)
    ax.set_ylim(0.75, 1.07)
    ax.set_title('(b) 测试集关系分随歧义标准统一持平', fontsize=10, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, fontsize=7.8)
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)

    # Panel C: Stability 3-rep comparison
    ax = axes[2]
    main_scores = {
        'T01': {'v0': 1, 'v1': 1, 'v2': 1, 'v3': 1},
        'T04': {'v0': 1, 'v1': 2, 'v2': 2, 'v3': 2},
        'T07': {'v0': 1, 'v1': 2, 'v2': 2, 'v3': 2},
    }
    poems_stab = [('T01', '《鹿柴》\n“返景”词义'), ('T04', '《夜雨寄北》\n时间嵌套'), ('T07', '《声声慢》\n“将息”词义')]
    x3 = np.arange(len(poems_stab)) * 1.18
    bw = 0.21
    v_short = ['直接翻译', '任务标准', '参考注释', '边界示例']
    for idx, ver in enumerate(['v0', 'v1', 'v2', 'v3']):
        means, mins, maxs = [], [], []
        for pid, _ in poems_stab:
            s_main = main_scores[pid][ver]
            s_r1 = stab_rev['items'][f'{pid}-{ver}-r1']['target']
            s_r2 = stab_rev['items'][f'{pid}-{ver}-r2']['target']
            arr = [s_main, s_r1, s_r2]
            means.append(np.mean(arr) / 2.0)
            mins.append(min(arr) / 2.0)
            maxs.append(max(arr) / 2.0)
        pos = x3 + (idx - 1.5) * bw
        ax.bar(pos, means, width=bw * 0.9, color=COLORS[idx], label=v_short[idx], alpha=0.88)
        for p_x, mn, mx, m_val in zip(pos, mins, maxs, means):
            if mx > mn:
                ax.plot([p_x, p_x], [mn, mx], color='#111827', lw=1.3)
                ax.scatter([p_x, p_x], [mn, mx], color='#111827', s=11, zorder=5)
            dy = 0.025 if idx % 2 == 0 else 0.065
            ax.text(p_x, max(mx, m_val) + dy, f'{m_val:.2f}', ha='center', fontsize=6.9, color=COLORS[idx], fontweight='bold')

    ax.set_xticks(x3, [p[1] for p in poems_stab], fontsize=8.4)
    ax.set_ylim(0.0, 1.18)
    ax.set_ylabel('关键项得分（3 次采样均值与极差）', fontsize=8.5)
    ax.set_title('(c) 3 次重复采样的均值与波动范围', fontsize=10, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, fontsize=7.4, ncol=2)
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)

    fig.tight_layout(w_pad=1.6)
    save(fig, '04_争议评分敏感性')


def fig05_supplement_ablation() -> None:
    s_all = supp['summaries']['all']
    s_diag = supp['summaries']['diagnostic']
    s_new = supp['summaries']['new']

    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.5))
    conds = ['a0', 'a1', 'a2']
    cond_labels = ['无注释', '单条核心注释', '完整词表注释']
    x = np.arange(3)

    # Panel A
    ax = axes[0]
    w = 0.25
    ax.bar(x - w, [s_all[c]['terms'] for c in conds], width=w * 0.92, color='#0072B2', label='术语保持分（全集）')
    ax.bar(x, [s_all[c]['relations'] for c in conds], width=w * 0.92, color='#059669', label='关系保持分（全集）')
    ax.bar(x + w, [s_all[c]['english'] / 2.0 for c in conds], width=w * 0.92, color='#D97706', label='英语表达分/2（全集）')
    for j, c in enumerate(conds):
        ax.text(j - w, 1.015, '1.00', ha='center', fontsize=7.4, color='#0072B2', fontweight='bold')
        ax.text(j, 1.055, '1.00', ha='center', fontsize=7.4, color='#059669', fontweight='bold')
        ev = s_all[c]['english'] / 2.0
        ax.text(j + w, ev + 0.015, f'{ev:.3f}', ha='center', fontsize=7.4, color='#B45309', fontweight='bold')
    ax.set_xticks(x, cond_labels, fontsize=8.8)
    ax.set_ylim(0, 1.18)
    ax.set_ylabel('归一化得分', fontsize=9)
    ax.set_title('(a) 注释消融：术语与关系均达满分', fontsize=10, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, fontsize=7.6)
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)

    # Panel B
    ax = axes[1]
    w2 = 0.30
    diag_tok = [s_diag[c]['total_tokens'] / 1000.0 for c in conds]
    new_tok = [s_new[c]['total_tokens'] / 1000.0 for c in conds]
    ax.bar(x - w2 / 2, diag_tok, width=w2, color='#6366F1', label='《登鹳雀楼》《枫桥夜泊》')
    ax.bar(x + w2 / 2, new_tok, width=w2, color='#14B8A6', label='《商山早行》《竹里馆》')
    for j in range(3):
        ax.text(j - w2 / 2, diag_tok[j] + 0.15, f'{diag_tok[j]:.2f}k', ha='center', fontsize=8)
        ax.text(j + w2 / 2, new_tok[j] + 0.15, f'{new_tok[j]:.2f}k', ha='center', fontsize=8)
    ax.set_xticks(x, cond_labels, fontsize=8.8)
    ax.set_ylim(0, 7.2)
    ax.set_ylabel('总 Token 消耗（千 Token）', fontsize=9)
    ax.set_title('(b) 两组诗词的 Token 消耗对比', fontsize=10, fontweight='bold')
    ax.legend(loc='upper left', frameon=True, fontsize=7.6)
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)

    # Panel C
    ax = axes[2]
    presence = [s_all[c]['notes_present'] for c in conds]
    lines_avg = [s_all[c]['notes_lines'] / 4.0 for c in conds]
    ax.bar(x - w2 / 2, presence, width=w2, color='#0284C7', label='附带尾注 (Notes) 比例')
    ax.bar(x + w2 / 2, lines_avg, width=w2, color='#EC4899', label='平均尾注行数 (÷4 归一化)')
    for j, c in enumerate(conds):
        ax.text(j - w2 / 2, presence[j] + 0.03, f"{presence[j]*100:.0f}%", ha='center', fontsize=8, fontweight='bold')
        raw_l = s_all[c]['notes_lines']
        ax.text(j + w2 / 2, lines_avg[j] + 0.03, f'{raw_l:.2f}行', ha='center', fontsize=8, color='#BE185D', fontweight='bold')
    ax.set_xticks(x, cond_labels, fontsize=8.8)
    ax.set_ylim(0, 1.24)
    ax.set_ylabel('比例 / 归一化行数', fontsize=9)
    ax.set_title('(c) 尾注触发率与尾注行数膨胀', fontsize=10, fontweight='bold')
    ax.legend(loc='upper left', frameon=True, fontsize=7.6)
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)

    fig.tight_layout(w_pad=1.6)
    save(fig, '05_单条注释消融结果')


def main() -> None:
    fig01_workflow()
    fig02_dev_quality()
    fig03_cost_breakdown()
    fig04_sensitivity_and_stability()
    fig05_supplement_ablation()
    print('Generated 5 human-readable PNG + 5 SVG figures in', DEST)


if __name__ == '__main__':
    main()
