from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

R=Path('results'); O=Path('paper_assets'); O.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8})

def architecture_figure():
    fig, ax = plt.subplots(figsize=(7.1, 3.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis('off')
    boxes = [
        (0.3, 3.25, 1.7, .8, 'Agent /\nworkflow'),
        (2.3, 3.25, 1.7, .8, 'Contract and\npolicy gate'),
        (4.3, 3.25, 1.7, .8, 'Service\nexecutor'),
        (6.3, 3.25, 1.7, .8, 'Trace and\nstate plane'),
        (8.3, 3.25, 1.4, .8, 'Terminal\nverifier'),
        (2.3, 1.25, 1.7, .8, 'Failure-belief\nengine'),
        (4.3, 1.25, 1.7, .8, 'Recovery\ngenerator'),
        (6.3, 1.25, 1.7, .8, 'SLO-constrained\nfrontier'),
    ]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.04',fc='#e8f0f7',ec='#1f4e79',lw=1.1))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8)
    arrows=[((2.0,3.65),(2.3,3.65)),((4.0,3.65),(4.3,3.65)),((6.0,3.65),(6.3,3.65)),((8.0,3.65),(8.3,3.65)),
            ((7.15,3.25),(3.15,2.05)),((4.0,1.65),(4.3,1.65)),((6.0,1.65),(6.3,1.65)),((7.15,2.05),(3.15,3.25))]
    for a,b in arrows:
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='->',mutation_scale=10,lw=1.0,color='#4c4c4c'))
    ax.text(5.15,.55,'Hard contract and authorization checks precede utility ranking',ha='center',fontsize=8,style='italic')
    fig.tight_layout(); fig.savefig(O/'architecture.png',dpi=300,bbox_inches='tight'); plt.close(fig)

def protocol_figure():
    fig, ax = plt.subplots(figsize=(7.1, 2.7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis('off')
    top=[('Ready',.4),('Intent\nrecorded',2.1),('Invoked',4.0),('Outcome\nknown',5.7),('Completed',7.8)]
    for label,x in top:
        ax.add_patch(FancyBboxPatch((x,2.55),1.35,.65,boxstyle='round,pad=.03',fc='#eef4f8',ec='#1f4e79'))
        ax.text(x+.675,2.875,label,ha='center',va='center',fontsize=8)
    for (_,x1),(_,x2) in zip(top,top[1:]):
        ax.add_patch(FancyArrowPatch((x1+1.35,2.875),(x2,2.875),arrowstyle='->',mutation_scale=9,color='#555'))
    lower=[('Ambiguous',2.1),('Reconcile',4.0),('Compensate',5.9),('Resume /\nescalate',7.8)]
    for label,x in lower:
        ax.add_patch(FancyBboxPatch((x,.75),1.35,.65,boxstyle='round,pad=.03',fc='#fff3df',ec='#b36b00'))
        ax.text(x+.675,1.075,label,ha='center',va='center',fontsize=8)
    for (_,x1),(_,x2) in zip(lower,lower[1:]):
        ax.add_patch(FancyArrowPatch((x1+1.35,1.075),(x2,1.075),arrowstyle='->',mutation_scale=9,color='#555'))
    ax.add_patch(FancyArrowPatch((4.675,2.55),(2.775,1.4),arrowstyle='->',mutation_scale=9,color='#b36b00'))
    ax.add_patch(FancyArrowPatch((8.475,1.4),(8.475,2.55),arrowstyle='->',mutation_scale=9,color='#b36b00'))
    fig.tight_layout(); fig.savefig(O/'protocol.png',dpi=300,bbox_inches='tight'); plt.close(fig)

architecture_figure()
protocol_figure()
h=pd.read_csv(R/'headline.csv')
fig,ax=plt.subplots(figsize=(6.8,3.0))
ax.scatter(h.unsafe*100,h.acceptable*100,s=55,color='#1f4e79')
offsets={'self_heal':(-27,13),'replan':(7,-13),'unconstrained':(7,11),
         'fa_mas':(4,3),'react':(4,3),'retry':(4,3),'static':(-26,4)}
for _,r in h.iterrows():
    ax.annotate(r.baseline.replace('_',' '),(r.unsafe*100,r.acceptable*100),
                xytext=offsets[r.baseline],textcoords='offset points',fontsize=7)
ax.set(xlabel='Unsafe outcomes (%) - lower is better',ylabel='Acceptable outcomes (%) - higher is better',title='Safety and acceptable-outcome frontier')
ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(O/'frontier.png',dpi=300); plt.close(fig)

a=pd.read_csv(R/'ablations.csv').sort_values('unsafe_side_effect')
fig,ax=plt.subplots(figsize=(6.8,3.0))
ax.barh(a.ablation.str.replace('_',' '),a.unsafe_side_effect*100,color='#4f81bd')
ax.set(xlabel='Unsafe outcomes (%)',title='FA-MAS ablation safety effects'); ax.grid(axis='x',alpha=.25)
fig.tight_layout(); fig.savefig(O/'ablations.png',dpi=300); plt.close(fig)

r=pd.read_csv(R/'runs.csv'); f=r[r.ablation.eq('full')]
p=f.groupby(['fault','baseline']).unsafe_side_effect.mean().unstack().loc[['infrastructure','protocol','semantic','agent','coordination','stateful','security']]
fig,ax=plt.subplots(figsize=(6.8,3.1))
p[['static','retry','self_heal','fa_mas']].plot(kind='bar',ax=ax,width=.78,color=['#999999','#7f8fa6','#d18f00','#1f4e79'])
ax.set(ylabel='Unsafe outcome rate',xlabel='Fault class',title='Unsafe outcomes by injected fault class'); ax.tick_params(axis='x',rotation=25); ax.legend(ncol=4,fontsize=7)
ax.grid(axis='y',alpha=.25); fig.tight_layout(); fig.savefig(O/'fault_safety.png',dpi=300); plt.close(fig)
print('figures',len(list(O.glob('*.png'))))
