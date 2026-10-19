from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
r=Path(__file__).resolve().parent
fig,ax=plt.subplots(figsize=(9,3.7));ax.set(xlim=(0,9),ylim=(0,3.7));ax.axis('off')
pos={'Ready':(.9,2.8),'IntentRecorded':(3,2.8),'Invoked':(5.1,2.8),'OutcomeKnown':(7.3,2.8),'Ambiguous':(5.1,1.6),'Reconciled':(3,1.6),'Compensating':(.9,1.6),'Resuming':(.9,.4),'Escalated':(3,.4),'Completed':(7.3,1.6),'SafelyTerminated':(7.3,.4)}
for name,(x,y) in pos.items():
 ax.add_patch(FancyBboxPatch((x-.78,y-.25),1.56,.5,boxstyle='round,pad=.03',facecolor='#eef4fa',edgecolor='#386084'));ax.text(x,y,name,ha='center',va='center',fontsize=8)
for a,b in [('Ready','IntentRecorded'),('IntentRecorded','Invoked'),('Invoked','OutcomeKnown'),('OutcomeKnown','Completed'),('Invoked','Ambiguous'),('Ambiguous','Reconciled'),('Reconciled','Compensating'),('Compensating','Resuming'),('Reconciled','Escalated'),('Ambiguous','SafelyTerminated')]:
 x,y=pos[a];u,v=pos[b];ax.annotate('',xy=(u,v),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='#ad7b30',shrinkA=32,shrinkB=32))
fig.tight_layout();fig.savefig(r/'figures/fig2_protocol.png',dpi=300);plt.close(fig)
