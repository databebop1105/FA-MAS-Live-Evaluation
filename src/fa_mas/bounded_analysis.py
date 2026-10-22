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
    def configuration_id(row):
        return row.get('model_configuration_id',row['model_class'])
    keys=[(r['task_id'],r['policy'],configuration_id(r)) for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate episode cells')
    models=manifest.get('models',[])
    model_map={m.get('configuration_id',m.get('class')):m for m in models if isinstance(m,dict)}
    expected={(t['task_id'],p,configuration_id) for t in held.values() for p in POLICIES for configuration_id in model_map}
    if set(keys)!=expected or not manifest.get('complete_matrix'):raise ValueError('Incomplete matrix: report launched outcomes descriptively; do not claim completed confirmatory comparison')
    for row in rows:
        configuration=model_map.get(configuration_id(row))
        if not configuration or row['model_id']!=configuration.get('model_id') or row['model_class']!=configuration.get('class'):
            raise ValueError('Model identity differs from manifest')
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
    frame['model_configuration_id']=frame.apply(configuration_id,axis=1)
    # Configuration-specific contrasts are primary. Pooled and service-specific
    # rows are descriptive sensitivities: neither turns nor configurations are
    # treated as independent populations.
    scopes=[(f'{configuration}_configuration',frame[frame.model_configuration_id==configuration])
            for configuration in model_map]
    scopes.extend((
        ('pooled_descriptive',frame),
        ('workflow_descriptive',frame[frame.service=='workflow']),
        ('inventory_descriptive',frame[frame.service=='inventory']),
    ))
    for scope,f in scopes:
        index=['task_id','model_configuration_id','service','fault']
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
    summary=frame.groupby(['service','policy','model_configuration_id','model_class'])[list(METRICS)+['safe_termination','total_tokens','tool_calls','wall_ms']].mean().reset_index()
    output.mkdir(parents=True,exist_ok=True);comparison.to_csv(output/'paired_comparisons.csv',index=False);summary.to_csv(output/'summary.csv',index=False)
    frame.groupby(['service','policy','model_configuration_id','model_class','status']).size().rename('episodes').reset_index().to_csv(output/'operational_status_counts.csv',index=False)
    primary=', '.join(f'{configuration}_configuration' for configuration in model_map)
    (output/'ANALYSIS_LIMITS.md').write_text(f'The primary row is {primary}. Pooled and service rows are descriptive sensitivities. The tasks and faults are authored local service tests. Bootstrap clusters are service/fault families, not variants, model responses, or turns. Intervals and supplementary sign tests describe this bank under exchangeability assumptions; they do not establish production rates. Provider failures and budget stops are retained. The study exercises one tool-using model at a time and does not test multi-agent coordination.\n')
    return {'rows':len(rows),'clusters':frame.service.str.cat(frame.fault,sep=':').nunique(),'evidence_class':'live_e2e_local_services'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',default='results/bounded_e2e/live_runs.jsonl');p.add_argument('--manifest',default='results/bounded_e2e/live_manifest.json');p.add_argument('--tasks',default='configs/bounded_tasks_v1.jsonl');p.add_argument('--output',default='results/bounded_e2e/analysis');a=p.parse_args()
    print(json.dumps(analyze(Path(a.runs),Path(a.manifest),Path(a.tasks),Path(a.output)),indent=2))
if __name__=='__main__':main()
