"""Prepare a standalone Markdown report with GitHub-hosted assets."""
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
TITLE = '大语言模型后训练演进与强化学习代码研究'
REPO = 'https://github.com/Can1017/LLM-HW'
PREFIX = 'hw4/p226-posttraining'


def blob(relative):
    return REPO + '/blob/main/' + quote(PREFIX + '/' + relative, safe='/')


def raw(relative):
    return 'https://raw.githubusercontent.com/Can1017/LLM-HW/main/' + quote(PREFIX + '/' + relative, safe='/')


def main():
    path = ROOT / 'reports' / (TITLE + '.md')
    text = path.read_text(encoding='utf-8')
    intro = f'[GitHub 项目与复现材料]({REPO}/tree/main/{PREFIX})'
    if intro not in text:
        first, rest = text.split('\n', 1)
        text = first + '\n\n' + intro + '\n' + rest
    text = text.replace('<!-- PAGE -->\n\n', '')
    text = re.sub(r'^\\\[\s*$', '$$', text, flags=re.M)
    text = re.sub(r'^\\\]\s*$', '$$', text, flags=re.M)
    text = re.sub(r'!\[([^]]*)\]\(figures/([^)]+)\)',
                  lambda m: f'![{m[1]}]({raw("reports/figures/" + m[2])})', text)
    text = text.replace('完整SHA、文件行号及永久链接保存在附件和代码索引中。',
                        f'完整SHA、文件行号及永久链接保存在[详细分析附件]({blob("reports/" + TITLE + "-附件.md")})和[代码索引]({blob("reports/代码索引.md")})中。')
    text = text.replace('使用本机Python 3.11和PyTorch 2.5.1 CPU运行 `mechanism_lab.py`。',
                        f'使用本机Python 3.11和PyTorch 2.5.1 CPU运行[mechanism_lab.py]({blob("research/scripts/mechanism_lab.py")})。')
    text = text.replace('原始数据保存在 `mechanism_lab.json`。',
                        f'原始数据保存在[mechanism_lab.json]({blob("research/results/mechanism_lab.json")})。')

    aggregation = f'''\n\n![图4 不同损失聚合方式产生的样本梯度权重]({raw("reports/figures/05_损失聚合的样本权重.png")})

图4将同一损失矩阵按三种方式聚合。token平均下，长度为6的回答获得更大的总权重；序列平均使两条回答各占一半；固定分母则改变整体尺度。因而，比较算法时只对齐学习率和batch大小还不够，损失分母也是实际目标的一部分。
'''
    anchor = '这些检查提供可复查的程序证据，不能证明语言理解或推理能力提高。'
    if '不同损失聚合方式产生的样本梯度权重' not in text:
        text = text.replace(anchor, aggregation.strip() + '\n\n' + anchor)

    trust = f'''\n\n![图5 概率比率与散度信赖域的机制对照]({raw("reports/figures/07_概率比率与散度信赖域.png")})

图5左侧保持概率比率为1.5，观察不同旧概率对应的绝对变化；右侧来自本次合成张量实践。PPO比例阈值为0.2，DPPO的TV和KL阈值分别为0.1和0.01。阈值单位不同，这张图解释更新mask的机制，不构成模型效果或算法性能排名。
'''
    anchor = '**教师反馈的可见落点。**'
    if '概率比率与散度信赖域的机制对照' not in text:
        text = text.replace(anchor, trust.strip() + '\n\n' + anchor)

    resources = f'''## 7 代码与补充材料

本报告对应的代码、数据和补充文档集中保存在[GitHub 项目目录]({REPO}/tree/main/{PREFIX})。图片直接从GitHub在线加载，单独保存本Markdown文件也可以显示图表。

| 材料 | 内容 |
| --- | --- |
| [代码分析与研究记录]({blob("reports/" + TITLE + "-附件.md")}) | 三套源码深读、指定报告阅读位置、实践过程与边界 |
| [31个固定版本代码链接]({blob("reports/代码索引.md")}) | 从真实AST节点生成的文件位置与永久行号 |
| [CPU机制实践脚本]({blob("research/scripts/mechanism_lab.py")}) | 原函数体、配置适配、梯度检查和三动作策略更新 |
| [原始实践结果]({blob("research/results/mechanism_lab.json")}) | 17项检查、数值、梯度、环境和源码哈希 |
| [13篇文献核验记录]({blob("research/references-verified.json")}) | 版本、PDF哈希及阅读位置 |
| [图表生成脚本]({blob("research/scripts/generate_figures.py")})与[矢量图源]({REPO}/tree/main/{PREFIX}/reports/figures) | 本文五组图表的生成过程与SVG源码 |
| [10分钟汇报讲稿]({blob("reports/10分钟汇报讲稿.md")}) | 讲述顺序、演示提示和可能追问 |

复现机制实践需要Python、PyTorch CPU和NumPy，以及[来源清单]({blob("research/sources.json")})中固定提交的三套仓库；不需要GPU、预训练模型权重或启动Ray集群。具体准备方式见[项目README]({blob("README.md")})。

'''
    if '## 7 代码与补充材料' not in text:
        text = text.replace('## 参考文献', resources + '## 参考文献')
    numbering = {'01_': 1, '03_': 2, '07_': 3, '06_': 4, '05_': 5}
    def numbered_image(match):
        alt, target = match[1], match[2]
        number = next(n for prefix, n in numbering.items() if '/'+prefix in target)
        alt = re.sub(r'^图\d+\s*', '', alt)
        return f'![图{number} {alt}]({target})'
    text = re.sub(r'!\[([^]]*)\]\((https://raw.githubusercontent.com/[^)]+)\)', numbered_image, text)
    text = text.replace('图5左侧保持概率比率', '图3左侧保持概率比率')
    text = text.replace('图3左侧比较合成样例', '图4左侧比较合成样例')
    text = text.replace('图4将同一损失矩阵', '图5将同一损失矩阵')
    path.write_text(text, encoding='utf-8')
    print(path)
    print('Online images:', len(re.findall(r'!\[[^]]*\]\(https://raw.githubusercontent.com/', text)))

    annex = ROOT/'reports'/(TITLE+'-附件.md')
    data = annex.read_text(encoding='utf-8')
    data = re.sub(r'!\[([^]]*)\]\(figures/([^)]+)\)',
                  lambda m:f'![{m[1]}]({raw("reports/figures/"+m[2])})', data)
    data = data.replace('](代码索引.md)', ']('+blob('reports/代码索引.md')+')')
    annex.write_text(data, encoding='utf-8')


if __name__ == '__main__':
    main()
