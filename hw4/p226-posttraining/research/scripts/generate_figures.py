"""Figures from primary-source milestones and the actual CPU lab output."""
import json
import re
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT/'reports/figures'
FIG.mkdir(exist_ok=True)
DATA = json.loads((ROOT/'research/results/mechanism_lab.json').read_text(encoding='utf-8'))['results']
plt.rcParams.update({'font.family':'sans-serif', 'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],
                     'axes.unicode_minus':False, 'figure.dpi':140, 'savefig.dpi':240,
                     'axes.spines.top':False, 'axes.spines.right':False})
BLUE, GREEN, ORANGE, PURPLE = '#245b9e', '#217a71', '#be7622', '#7854a5'

def save(fig, name):
    fig.savefig(FIG/f'{name}.png', bbox_inches='tight', facecolor='white')
    fig.savefig(FIG/f'{name}.svg', bbox_inches='tight', facecolor='white')
    plt.close(fig)

def timeline():
    fig, ax = plt.subplots(figsize=(12,4.1))
    ax.set(xlim=(-.6,4.6), ylim=(-.9,2.35)); ax.axis('off')
    years=['2022','2023','2024','2025','2026']
    titles=['指令与偏好','离线偏好优化','可验证推理','稳定更新与能力融合','长程协作与教师反馈']
    methods=['InstructGPT\nSFT → RM → PPO','DPO\n参考策略与偏好间隔',
             'DeepSeekMath\nGRPO\nDeepSeek-V3','R1 / DAPO / GSPO\nQwen3 / V3.2','DPPO\nKimi K2.5 / GLM-5']
    questions=['怎样遵循用户意图','能否简化训练闭环','怎样用结果反馈探索',
               '怎样控制长度和比率噪声','怎样归因并恢复阶段能力']
    colors=[BLUE,GREEN,ORANGE,PURPLE,BLUE]
    for x in range(5):
        ax.text(x,2.05,years[x],ha='center',fontsize=14,fontweight='bold',color=colors[x])
        ax.text(x,1.64,titles[x],ha='center',fontsize=9.5,color='#263746')
        ax.add_patch(FancyBboxPatch((x-.43,.12),.86,1.15,boxstyle='round,pad=0.025',
                           edgecolor=colors[x],facecolor='#f6f8fa',lw=1.4))
        ax.text(x,.70,methods[x],ha='center',va='center',fontsize=10,linespacing=1.8,color='#172734')
        ax.text(x,-.27,questions[x],ha='center',fontsize=8.4,color='#536473')
        if x<4:
            ax.add_patch(FancyArrowPatch((x+.47,.7),(x+.54,.7),arrowstyle='->',mutation_scale=12,color='#7e8b97'))
    ax.text(-.52,-.72,'按年份分组，间距不表示时长；算法路线持续并存。',fontsize=8.6,color='#536473')
    save(fig,'01_后训练技术演进路线')

def flow():
    lanes=[('TRL',BLUE,['prompt','generate','reward funcs','advantage','compute_loss','Trainer更新']),
           ('verl',ORANGE,['DataProto\nuid','rollout\nworkers','reward\nmanager','core_algos','ppo_loss\n注册分派','Engine更新\n参数同步']),
           ('ms-swift',PURPLE,['GRPOSample\nrequest_id','RolloutMixin','reward /\nenvironment','rl_core +\nteacher信号','GRPOTrainer\nloss','HF / Megatron\n更新'])]
    fig, ax=plt.subplots(figsize=(12,3.6))
    ax.set(xlim=(-1.5,6),ylim=(-.5,2.8)); ax.axis('off')
    for i,(name,color,nodes) in enumerate(lanes):
        y=2.25-i
        ax.text(-1.4,y,name,color=color,fontsize=12,weight='bold',va='center')
        for j,label in enumerate(nodes):
            ax.add_patch(FancyBboxPatch((j-.38,y-.24),.76,.48,boxstyle='round,pad=.02',
                                      edgecolor=color,facecolor='#f8fafb',lw=1.25))
            ax.text(j,y,label,ha='center',va='center',fontsize=8.4)
            if j<5:
                ax.add_patch(FancyArrowPatch((j+.41,y),(j+.60,y),arrowstyle='->',mutation_scale=10,color='#7e8b97'))
    save(fig,'03_三套代码执行链对照')

def gradients():
    d=DATA['gspo_gradients']['varying_advantage']
    fig, axes=plt.subplots(1,2,figsize=(10.8,3.8),gridspec_kw={'width_ratios':[1,1.6]})
    axes[0].bar(['序列级目标','GSPO-token'],[d['sequence_loss'],d['token_loss']],color=[BLUE,GREEN],width=.48)
    axes[0].set(ylim=(-.15,.5),ylabel='前向loss',title='逐token优势为 [1, −1]')
    for x in [0,1]: axes[0].text(x,.025,'0.0000',ha='center',fontsize=10)
    x=np.arange(2); w=.30
    axes[1].bar(x-w/2,d['sequence_gradient'][0],w,label='序列级目标',color=BLUE)
    axes[1].bar(x+w/2,d['token_gradient'][0],w,label='GSPO-token',color=GREEN)
    axes[1].set(xticks=x,xticklabels=['token 1','token 2'],ylabel='∂loss / ∂log π',ylim=(-.65,.8),title='相同loss不保证相同梯度')
    axes[1].legend(frameon=False,fontsize=9)
    for ax in axes:
        ax.axhline(0,color='#8394a3',lw=.8); ax.grid(axis='y',color='#e1e6ea',lw=.6); ax.set_axisbelow(True)
    fig.tight_layout(w_pad=3)
    save(fig,'06_相同损失不同梯度')

def aggregation():
    modes=['token-mean','seq-mean-token-mean','seq-mean-token-sum-norm']
    labels=['token平均','序列平均','固定分母']
    fig, ax=plt.subplots(figsize=(8.6,3.9)); x=np.arange(2); w=.24
    for i,(m,label,color) in enumerate(zip(modes,labels,[BLUE,GREEN,ORANGE])):
        gradients=DATA['aggregation'][m]['per_token_gradient']
        totals=[sum(abs(x) for x in row) for row in gradients]
        ax.bar(x+(i-1)*w,totals,w,label=label,color=color)
    ax.set(xticks=x,xticklabels=['2-token回答','6-token回答'],ylabel='各回答梯度绝对值之和',ylim=(0,.95))
    ax.legend(ncol=3,frameon=False,fontsize=9); ax.grid(axis='y',color='#e1e6ea'); ax.set_axisbelow(True)
    fig.tight_layout(); save(fig,'05_损失聚合的样本权重')

def trust_region():
    fig, axes=plt.subplots(1,2,figsize=(10.8,3.8)); p=np.geomspace(.0002,.6,180); q=np.minimum(1.5*p,.999)
    axes[0].plot(p,q-p,color=BLUE,lw=2,label='概率增量（ratio恒为1.5）')
    axes[0].axhline(.1,color=ORANGE,ls='--',label='TV示意阈值 0.1')
    axes[0].set(xscale='log',xlabel='旧策略中动作概率',ylabel='新旧概率差'); axes[0].legend(frameon=False,fontsize=8)
    outcome=DATA['trust_region']['outcomes']; names=['PPO ratio','DPPO binary TV','DPPO binary KL']
    grad=np.array([outcome[n]['logp_gradient'][0] for n in names]); x=np.arange(3); w=.3
    axes[1].bar(x-w/2,abs(grad[:,0]),w,color=BLUE,label='低概率token')
    axes[1].bar(x+w/2,abs(grad[:,1]),w,color=GREEN,label='高概率token')
    axes[1].set(xticks=x,xticklabels=['PPO','DPPO-TV','DPPO-KL'],ylabel='|∂loss / ∂log π|')
    axes[1].legend(frameon=False,fontsize=8)
    for ax in axes: ax.grid(axis='y',color='#e1e6ea',lw=.6); ax.set_axisbelow(True)
    fig.tight_layout(w_pad=3); save(fig,'07_概率比率与散度信赖域')

def equations():
    source=(ROOT/'reports/大语言模型后训练演进与强化学习代码研究.md').read_text(encoding='utf-8')
    blocks=re.findall(r'\\\[(.*?)\\\]',source,re.S) or re.findall(r'\$\$(.*?)\$\$',source,re.S)
    for i, equation in enumerate(blocks,1):
        fig,ax=plt.subplots(figsize=(10,.65))
        ax.axis('off')
        latex=' '.join(equation.split())
        ax.text(.5,.5,'$'+latex+'$',ha='center',va='center',fontsize=15)
        fig.savefig(FIG/f'equation-{i}.png',bbox_inches='tight',pad_inches=.03,facecolor='white')
        plt.close(fig)

if __name__=='__main__':
    timeline(); flow(); gradients(); aggregation(); trust_region(); equations()
    for stem in ['02_方法依赖结构对照','04_优势计算数值验证','05_损失聚合与信赖域机制']:
        for suffix in ['.png','.svg']: (FIG/(stem+suffix)).unlink(missing_ok=True)
    print('Generated five figures with SVG sources and PNG exports.')
