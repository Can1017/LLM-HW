"""Render explanatory diagrams and measured local mechanism results.

No paper curves or model-performance numbers are reconstructed. Paper excerpts
are rendered separately by extract_paper_figures.py with explicit provenance.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / 'reports' / 'figures'
FIG.mkdir(exist_ok=True)
DATA = json.loads((ROOT/'research/results/mechanism_lab.json').read_text(encoding='utf-8'))['results']
BLUE, TEAL, ORANGE, PURPLE = '#245B85', '#197C72', '#B9792C', '#7B5B99'
INK, MUTED, GRID = '#192C3B', '#5E7180', '#E3EAF0'
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'font.size': 10.5,
    'axes.titleweight': 'bold',
    'axes.labelcolor': INK,
    'text.color': INK,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 140,
    'savefig.dpi': 230,
    'svg.fonttype': 'path',
})


def save(fig, stem):
    for suffix in ['png', 'svg']:
        path=FIG/f'{stem}.{suffix}'
        fig.savefig(path, bbox_inches='tight', facecolor='white')
        if suffix=='svg':
            text=path.read_text(encoding='utf-8')
            path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n',encoding='utf-8')
    plt.close(fig)


def node(ax, x, y, w, h, title, detail, color=BLUE):
    ax.add_patch(FancyBboxPatch((x,y), w,h, boxstyle='round,pad=.025,rounding_size=.09',
                 facecolor='#F6F9FB', edgecolor=color, linewidth=1.35))
    ax.text(x+w/2, y+h*.66, title, ha='center', va='center',
            fontsize=11, weight='bold', color=color)
    ax.text(x+w/2, y+h*.30, detail, ha='center', va='center',
            fontsize=9, linespacing=1.45)


def arrow(ax, start, end, color=MUTED, connection='arc3'):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=12,
                 linewidth=1.3,color=color,connectionstyle=connection))


def evolution():
    fig, ax = plt.subplots(figsize=(12.6,5.4))
    ax.set(xlim=(-.6,4.6),ylim=(-2.2,1.9))
    ax.axis('off')
    colors=[BLUE,BLUE,TEAL,ORANGE,PURPLE]
    methods=['InstructGPT','DPO','DeepSeekMath / GRPO','DAPO / Dr.GRPO / GSPO','DPPO']
    focus=['示范、排序与在线优化','离线偏好间隔','同题候选的相对奖励','有效采样、长度与序列比率','概率散度与更新范围']
    ax.plot([0,4],[.5,.5],color='#AABAC6',lw=2,zorder=1)
    for i in range(5):
        ax.plot(i,.5,'o',color=colors[i],ms=12,mec='white',mew=2,zorder=3)
        ax.text(i,1.35,str(2022+i),ha='center',fontsize=18,weight='bold',color=colors[i])
        ax.text(i,.93,methods[i].replace(' / ','\n') if i>=2 else methods[i],
                ha='center',va='center',fontsize=10.7,linespacing=1.3)
        ax.text(i,.10,focus[i],ha='center',va='top',fontsize=9.5)
    ax.text(-.52,-.62,'训练组织的变化',fontsize=11.5,weight='bold',color=INK)
    ax.plot([-.52,4.45],[-.82,-.82],color=GRID,lw=1)
    orgs=[
        ('2022—2023','SFT → RM → PPO\n或离线偏好训练'),
        ('2024','可验证任务\n与推理轨迹'),
        ('2025','R1 冷启动与筛选\nQwen3 模式融合与蒸馏'),
        ('2025—2026','V3.2 混合 RL\nKimi 并行与 GLM 跨阶段蒸馏')]
    for x,(date,label) in zip([.0,1.3,2.6,3.9],orgs):
        ax.text(x,-1.08,date,ha='center',fontsize=10,weight='bold',color=MUTED)
        ax.text(x,-1.45,label,ha='center',va='top',fontsize=9.7,linespacing=1.6)
    save(fig,'evolution')


def training_loop():
    fig, ax=plt.subplots(figsize=(13,6.2))
    ax.set(xlim=(-.5,12.7),ylim=(.0,6.2)); ax.axis('off')
    ax.text(-.2,5.95,'一次在线更新的数据主干',fontsize=14,weight='bold')
    xs=[0,2.05,4.10,6.15,8.20,10.25]; y=4.2; w=1.7; h=1.15
    stages=[
        ('prompt + uid','保留同题身份',BLUE),
        ('rollout','生成同题候选',BLUE),
        ('reward','规则 / 模型 / 环境',TEAL),
        ('advantage','分组、中心化、缩放',TEAL),
        ('policy loss','比率、mask、聚合',ORANGE),
        ('optimizer','反向传播与参数更新',ORANGE)]
    for x,(title,detail,color) in zip(xs,stages):
        node(ax,x,y,w,h,title,detail,color)
    for x in xs[:-1]:
        arrow(ax,(x+w+.04,y+h/2),(x+2.05-.06,y+h/2))
    ax.text(-.2,3.5,'损失还依赖哪些信息',fontsize=11.5,weight='bold')
    node(ax,.0,1.9,2.35,1.05,'采样策略','rollout log-prob\n数据实际来自的分布',BLUE)
    node(ax,2.7,1.9,2.35,1.05,'旧策略','old log-prob\n近端比率的固定锚点',BLUE)
    node(ax,5.4,1.9,2.35,1.05,'当前策略','current log-prob\n保留梯度的前向',ORANGE)
    node(ax,8.1,1.9,3.3,1.05,'可选旁路','ref：偏离约束  /  teacher：额外反馈',PURPLE)
    arrow(ax,(6.6,3.0),(8.7,4.1),ORANGE)
    arrow(ax,(3.9,3.0),(8.45,4.12),BLUE,connection='arc3,rad=-.08')
    arrow(ax,(9.8,3.0),(9.25,4.1),PURPLE)
    ax.text(.1,1.25,'旧策略、参考策略与采样策略用途不同；并不意味着必须驻留四份模型。',fontsize=9.8,color=MUTED)
    ax.plot([11.1,11.1,2.9],[5.37,5.67,5.67],color=ORANGE,lw=1.3)
    arrow(ax,(2.9,5.67),(2.9,5.37),ORANGE)
    ax.text(7.0,5.85,'更新参数同步给后续 rollout',ha='center',fontsize=9.5,color=ORANGE)
    save(fig,'training_loop')


def mechanism():
    fig,axes=plt.subplots(2,2,figsize=(12.2,8.7))
    for ax in axes.flat:
        ax.set_facecolor('#FCFDFE'); ax.set_axisbelow(True)
    ax=axes[0,0]
    adv=np.array(DATA['grouping']['verl'])
    rewards=np.array(DATA['grouping']['rewards'])
    ax.bar(range(4),adv,color=[TEAL if v>0 else '#B65757' for v in adv],width=.58,zorder=3)
    for x,(a,r) in enumerate(zip(adv,rewards)):
        ax.text(x,a+(0.06 if a>0 else -.06),f'r={r:g}, A={a:+.3f}',
                fontsize=9,ha='center',va='bottom' if a>0 else 'top')
    ax.axhline(0,color=MUTED,lw=.8)
    ax.set(xticks=range(4),xticklabels=['G1-a','G1-b','G2-a','G2-b'],
           ylim=(-1.02,1.02),ylabel='组内优势')
    ax.set_title('A  不同奖励差距可被标准差缩放为相同优势',loc='left',fontsize=11)
    ax.grid(axis='y',color=GRID,lw=.7)

    ax=axes[0,1]
    modes=['token-mean','seq-mean-token-mean','seq-mean-token-sum-norm']
    matrix=np.array([[sum(abs(v) for v in row) for row in
        DATA['aggregation'][mode]['per_token_gradient']] for mode in modes])
    ax.imshow(matrix,cmap='Blues',vmin=0,vmax=.8,aspect='auto')
    ax.set(xticks=[0,1],xticklabels=['2-token回答','6-token回答'],yticks=range(3),
           yticklabels=['token mean','sequence mean','fixed norm'])
    for (i,j),v in np.ndenumerate(matrix):
        ax.text(j,i,f'{v:.3f}',ha='center',va='center',fontsize=12,weight='bold',
                color='white' if v>.38 else INK)
    ax.set_title('B  各回答的总梯度权重取决于聚合分母',loc='left',fontsize=11)

    ax=axes[1,0]
    d=DATA['gspo_gradients']['varying_advantage']
    matrix=np.array([d['sequence_gradient'][0],d['token_gradient'][0]])
    ax.imshow(matrix,cmap='RdBu_r',vmin=-.55,vmax=.55,aspect='auto')
    ax.set(xticks=[0,1],xticklabels=['token 1','token 2'],yticks=[0,1],
           yticklabels=['sequence objective','GSPO-token'])
    for (i,j),v in np.ndenumerate(matrix):
        ax.text(j,i,f'{v:+.2f}',ha='center',va='center',fontsize=13,weight='bold',
                color='white' if abs(v)>.3 else INK)
    ax.set_title('C  优势 [1, −1] 时，同值 loss 对应不同梯度',loc='left',fontsize=11)
    ax.set_xlabel('数值为 ∂loss / ∂log π；两条路径的前向 loss 均为0',fontsize=9.5,labelpad=12)

    ax=axes[1,1]
    d=DATA['dpo']
    matrix=np.array([d['reference'],d['counterexample']])
    left=np.zeros(2)
    for j,(name,color) in enumerate([('chosen',BLUE),('rejected','#B65757'),('其他回答','#CAD5DE')]):
        ax.barh([1,0],matrix[:,j],left=left,color=color,label=name,height=.46)
        for i,v in enumerate(matrix[:,j]):
            if v>=.025:
                ax.text(left[i]+v/2,1-i,f'{v:.2f}',ha='center',va='center',fontsize=10,
                        color='white' if j<2 else INK,weight='bold')
        left+=matrix[:,j]
    ax.set(yticks=[1,0],yticklabels=['reference / 初始','构造的另一分布'],
           xlim=(0,1),ylim=(-.7,2),xlabel='三个候选的概率')
    ax.text(.98,1.43,f"loss = {d['original_loss']:.4f}",ha='right',fontsize=10)
    ax.text(.98,.42,f"loss = {d['counterexample_loss']:.4f}",ha='right',fontsize=10)
    ax.annotate('0.01',xy=(.155,0),xytext=(.29,-.40),ha='center',fontsize=9,
                arrowprops=dict(arrowstyle='-',color=MUTED,lw=.8))
    ax.set_title('D  这是两个分布的反例，不是训练时间序列',loc='left',fontsize=11)
    ax.legend(loc='lower left',ncol=3,fontsize=9,frameon=False,bbox_to_anchor=(0,-.28))
    ax.spines['left'].set_visible(False)
    fig.subplots_adjust(left=.16,right=.98,top=.95,bottom=.17,wspace=.45,hspace=.55)
    fig.text(.16,.03,'数据：mechanism_lab.json。合成张量只检验局部机制；不表示语言模型能力或论文复现结果。',
             fontsize=9,color=MUTED)
    save(fig,'mechanism_results')


if __name__=='__main__':
    evolution()
    training_loop()
    mechanism()
    print('Rendered evolution, training loop and measured mechanism panels.')
