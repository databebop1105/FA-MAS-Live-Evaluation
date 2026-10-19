import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from fa_mas.core import POLICIES,run_trial
from fa_mas.experiment import bootstrap_diff,markdown_table
root=Path(__file__).resolve().parents[1]; config=root/'configs/matched_controls_v2.json';c=json.loads(config.read_text());out=root/'results/matched_controls_v2';out.mkdir(exist_ok=True)
rows=[]
for di,domain in enumerate(c['domains']):
 for fi,fault in enumerate(c['faults']):
  for intensity in ([0.] if fault=='none' else c['intensities']):
   for rep in range(c['repetitions']):
    seed=c['seed']+di*10000+fi*1000+int(intensity*100)*100000+rep
    for variant in c['variants']:
     policy=dict(POLICIES['fa_mas'],detect=c['detect'],localize=c['localize'])
     if variant=='no_gates':policy.update(contracts=False,security=False)
     if variant=='no_compensation':policy['compensate']=False
     row=run_trial(domain,fault,intensity,'fa_mas',seed,c['slo'],c['weights'],policy_override=policy,detection_bonus=False,selection='first' if variant=='first_feasible' else 'frontier',strict_terminal=True,recovery_semantics='effect_aware')
     row['variant']=variant;rows.append(row)
d=pd.DataFrame(rows);d.to_csv(out/'runs.csv',index=False);metrics=['task_success','acceptable_outcome','unsafe_side_effect','safe_termination','orphaned_effect']
summary=d.groupby('variant')[metrics].mean();summary.to_csv(out/'summary.csv')
keys=['domain','fault','intensity','seed'];fa=d[d.variant=='full'].set_index(keys);comparisons=[];rng=np.random.default_rng(c['seed'])
for variant in c['variants'][1:]:
 b=d[d.variant==variant].set_index(keys).reindex(fa.index)
 for metric in metrics[:3]:
  effect,lo,hi=bootstrap_diff(fa[metric],b[metric],rng,c['bootstrap_replicates'])
  comparisons.append({'baseline':variant,'metric':metric,'effect':effect,'ci_low':lo,'ci_high':hi,'pairs':len(fa)})
pd.DataFrame(comparisons).to_csv(out/'comparisons.csv',index=False)
(out/'manifest.json').write_text(json.dumps({'config':c,'rows':len(d),'protocol_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'core_sha256':hashlib.sha256((root/'src/fa_mas/core.py').read_bytes()).hexdigest(),'frontier_sha256':hashlib.sha256((root/'src/fa_mas/frontier.py').read_bytes()).hexdigest(),'evidence_class':'exploratory_authored_simulator_no_llm'},indent=2)+'\n')
(out/'REPORT.md').write_text('# Matched simulator sensitivity\n\nPost-audit defect-correction sensitivity; compensation requires an existing uncertain committed effect. This fixes a discovered simulator defect without modifying historical CSVs. Post-audit exploratory analysis, not independent preregistration or live-model evidence. Detection and localization are identical across variants; contract detection bonuses are disabled. The strict terminal judge counts unfinished workflows with active writes as unsafe. Non-gated recovery retains the same operations but relaxes gates. The finite-action frontier does not enumerate workflow subgraphs. Intervals quantify authored simulation uncertainty only.\n\n'+markdown_table(summary.reset_index(),4)+'\n')
print(summary.to_string());print('Rows',len(d))
