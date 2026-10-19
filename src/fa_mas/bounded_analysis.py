"""Strict live-only paired analysis for the bounded service workflow study."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from .bounded_e2e import load_tasks, POLICIES, digest, judge_workflow, judge_inventory
from .experiment import holm_adjust

METRICS=('task_success','acceptable_outcome','unsafe_outcome')

def analyze(runs,manifest_path,tasks_path,output):
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('evidence_class')!='live_e2e_local_services':raise ValueError('Reject non-live evidence')
    if hashlib.sha256(runs.read_bytes()).hexdigest()!=manifest['runs_sha256']:raise ValueError('Raw rows differ from saved manifest')
    rows=[json.loads(s) for s in runs.read_text().splitlines() if s.strip()]
    if not rows or {r.get('evidence_class') for r in rows}!={'live_e2e_local_services'}:raise ValueError('Reject non-live or mixed evidence')
    if {r['protocol_sha256'] for r in rows}!={manifest['protocol_sha256']}:raise ValueError('Mixed protocol locks')
    held={t['task_id']:t for t in load_tasks(tasks_path,'confirmatory')}
    keys=[(r['task_id'],r['policy'],r['model_class']) for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate episode cells')
    expected={(t,p,m) for t in held for p in POLICIES for m in ('hosted','open_weight')}
    if set(keys)!=expected or not manifest.get('complete_matrix'):raise ValueError('Incomplete matrix: report launched outcomes descriptively; do not claim completed confirmatory comparison')
    model_map={m['class']:m['model_id'] for m in manifest.get('models',[])}
    if set(model_map)!={'hosted','open_weight'}:raise ValueError('Manifest lacks pinned model identities')
    for row in rows:
        if row['model_id']!=model_map[row['model_class']]:raise ValueError('Model identity differs from manifest')
        if row['service']!=held[row['task_id']]['service'] or row['fault']!=held[row['task_id']]['fault']:raise ValueError('Task metadata mismatch')
        if row['trace_sha256']!=digest({'events':row['events'],'state':row['state']}):raise ValueError('Trace hash mismatch')
        if sum(row[m] for m in ('task_success','safe_termination','unsafe_outcome'))!=1:raise ValueError('Inconsistent terminal verdict')
        task=held[row['task_id']]
        if task['service']=='workflow':verdict=judge_workflow(task,row['state'])
        else:
            sku=task['requested_sku'];cap=task['capacity'];capacities={sku:cap,'sku-X':cap}
            initial={sku:cap if task['fault']=='capacity_exhausted' else 0,'sku-X':0}
            verdict=judge_inventory(task,row['state'],initial,capacities,task['task_id']+'-hold')
        if any(row[k]!=v for k,v in verdict.items()):raise ValueError('Terminal database judge differs from saved outcome')
    frame=pd.DataFrame(rows); contrasts=[];rng=np.random.default_rng(20261009)
    # Repeated instances/model classes are nested in service/fault families,
    # not treated as independent observations for uncertainty.
    for scope in ('pooled','workflow','inventory'):
        f=frame if scope=='pooled' else frame[frame.service==scope]
        index=['task_id','model_class','service','fault']
        fa=f[f.policy=='fa_mas'].set_index(index);base=f[f.policy=='feature_matched'].set_index(index)
        if len(fa)!=len(base) or set(fa.index)!=set(base.index):raise ValueError('Unpaired cells')
        base=base.reindex(fa.index)
        for metric in METRICS:
            differences=fa[metric].to_numpy()-base[metric].to_numpy()
            paired=pd.DataFrame({'difference':differences,'cluster':[a[2]+':'+a[3] for a in fa.index]})
            values=paired.groupby('cluster')['difference'].mean().to_numpy()
            effects=values[rng.integers(0,len(values),size=(10000,len(values)))].mean(axis=1)
            effect=float(values.mean()); lo,hi=np.quantile(effects,[.025,.975])
            # Exact sign randomization of cluster means: supplementary and
            # conditional on cluster exchangeability, not population proof.
            signs=1-2*((np.arange(2**len(values))[:,None]>>np.arange(len(values)))&1)
            p=float(np.mean(np.abs((signs*values).mean(axis=1))>=abs(effect)-1e-12))
            contrasts.append({'scope':scope,'metric':metric,'fa_minus_baseline':effect,'ci_low':float(lo),'ci_high':float(hi),
                              'cluster_sign_p':p,'clusters':len(values),'pairs':len(fa)})
    comparison=pd.DataFrame(contrasts);comparison['holm_p']=comparison.groupby('scope')['cluster_sign_p'].transform(lambda s:holm_adjust(s.to_numpy()))
    summary=frame.groupby(['service','policy','model_class'])[list(METRICS)+['safe_termination','total_tokens','tool_calls','wall_ms']].mean().reset_index()
    output.mkdir(parents=True,exist_ok=True);comparison.to_csv(output/'paired_comparisons.csv',index=False);summary.to_csv(output/'summary.csv',index=False)
    frame.groupby(['service','policy','model_class','status']).size().rename('episodes').reset_index().to_csv(output/'operational_status_counts.csv',index=False)
    (output/'ANALYSIS_LIMITS.md').write_text('The tasks and faults are authored local service tests. Bootstrap clusters are the 16 service/fault families, not variants or model responses. Intervals and supplementary sign tests describe this bank under exchangeability assumptions; they do not establish production rates. Provider failures and budget stops are retained. The study exercises one tool-using model at a time and does not test multi-agent coordination.\n')
    return {'rows':len(rows),'clusters':16,'evidence_class':'live_e2e_local_services'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',default='results/bounded_e2e/live_runs.jsonl');p.add_argument('--manifest',default='results/bounded_e2e/live_manifest.json');p.add_argument('--tasks',default='configs/bounded_tasks_v1.jsonl');p.add_argument('--output',default='results/bounded_e2e/analysis');a=p.parse_args()
    print(json.dumps(analyze(Path(a.runs),Path(a.manifest),Path(a.tasks),Path(a.output)),indent=2))
if __name__=='__main__':main()
