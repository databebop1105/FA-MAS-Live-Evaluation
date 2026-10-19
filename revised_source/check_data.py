from pathlib import Path
import pandas as pd,json,hashlib
parent=Path(__file__).resolve().parents[1];r=parent if (parent/'results').exists() else parent/'fa_mas';out=Path(__file__).resolve().parent
v1=pd.read_csv(r/'results/matched_controls/runs.csv');v2=pd.read_csv(r/'results/matched_controls_v2/runs.csv');report={}
for arm in v1.variant.unique():
 a=v1[v1.variant==arm].reset_index(drop=True);b=v2[v2.variant==arm].reset_index(drop=True);cols=list(a.columns);d=a[cols]!=b[cols]
 report[arm]={'paired_rows':len(a),'changed_rows':int(d.any(axis=1).sum()),'changed_fields':{k:int(d[k].sum()) for k in cols if d[k].any()},'old_outcomes':a[['task_success','acceptable_outcome','unsafe_side_effect']].mean().to_dict(),'new_outcomes':b[['task_success','acceptable_outcome','unsafe_side_effect']].mean().to_dict()}
(out/'arm_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
allrows=[]
for study,d in [('historical',pd.read_csv(r/'results/runs.csv')),('matched',v1),('corrected',v2)]:
 if study=='historical':d=d[d.ablation=='full'];group='baseline'
 else:group='variant'
 g=d.groupby(group)[['task_success','acceptable_outcome','slo_attained','detected','localized','unsafe_side_effect']].mean()
 for policy,row in g.iterrows():allrows.append({'study':study,'policy':policy,**row.to_dict()})
pd.DataFrame(allrows).to_csv(out/'complete_outcomes.csv',index=False)
