"""Direct public-tool recovery checks, NOT a tau-bench conversational evaluation."""
import argparse,copy,hashlib,json,os,sys,types
from pathlib import Path


def run(source, output):
    # Namespace only the orchestration-heavy parents. Business tool/data modules
    # and utility code below are executed unmodified from the pinned checkout.
    os.environ['TAU2_DATA_DIR']=str(source/'data')
    os.environ['PYTHON_DOTENV_DISABLED']='1'
    for name in ['tau2','tau2.domains','tau2.environment','tau2.domains.retail','tau2.domains.airline']:
        module=types.ModuleType(name);module.__path__=[str(source/'src'/name.replace('.','/'))];sys.modules[name]=module
    from loguru import logger
    logger.remove()
    from tau2.domains.retail.data_model import RetailDB
    from tau2.domains.retail.tools import RetailTools
    from tau2.domains.airline.data_model import FlightDB
    from tau2.domains.airline.tools import AirlineTools
    output.mkdir(parents=True,exist_ok=True)
    rows=[]; selected=[]
    specs=[('retail',RetailDB,RetailTools,'cancel_pending_order','orders','order_id'),
           ('airline',FlightDB,AirlineTools,'cancel_reservation','reservations','reservation_id')]
    for domain,DB,Tools,operation,table,idfield in specs:
        tasks=json.loads((source/f'data/tau2/domains/{domain}/tasks.json').read_text())
        tasks=[t for t in tasks if t['initial_state'] is None and any(a['name']==operation for a in t['evaluation_criteria']['actions'])]
        base_db=DB.load(source/f'data/tau2/domains/{domain}/db.json')
        for task in tasks:
            action=next(a for a in task['evaluation_criteria']['actions'] if a['name']==operation)
            selected.append({'domain':domain,'task_id':task['id'],'operation':operation,'arguments':action['arguments']})
            initial=base_db
            expected=initial.model_copy(deep=True)
            getattr(Tools(expected),operation)(**action['arguments'])
            reference_hash=hashlib.sha256(expected.model_dump_json().encode()).hexdigest()
            def snapshot(database):
                entity=getattr(database,table)[action['arguments'][idfield]]
                return {'entity':entity.model_dump(),'user':database.users[entity.user_id].model_dump()}
            initial_subject=snapshot(initial);expected_subject=snapshot(expected)
            for fault in ['clean','before_commit','lost_reply']:
                for policy in ['feature_matched','fa_mas']:
                    db=initial.model_copy(deep=True);tools=Tools(db);events=[];injected=False
                    def invoke():
                        nonlocal injected
                        first=not injected;injected=True
                        if first and fault=='before_commit':
                            events.append({'action':'write','outcome':'transport_failure_before_commit'});raise TimeoutError('Injected before commit')
                        getattr(tools,operation)(**action['arguments'])
                        if first and fault=='lost_reply':
                            events.append({'action':'write','outcome':'response_lost_after_commit'});raise TimeoutError('Injected lost reply')
                        events.append({'action':'write','outcome':'returned'})
                    def reconciled():
                        status=getattr(db,table)[action['arguments'][idfield]].status
                        events.append({'action':'read_status','status':status})
                        return status=='cancelled'
                    try:invoke()
                    except TimeoutError:
                        if policy=='fa_mas' and reconciled():pass
                        else:
                            try:invoke()
                            except ValueError as error:
                                events.append({'action':'write','outcome':'rejected','error':str(error)});reconciled()
                    actual=snapshot(db);reference=expected_subject
                    full_hash=hashlib.sha256(db.model_dump_json().encode()).hexdigest()
                    ok=full_hash==reference_hash
                    row={'domain':domain,'task_id':task['id'],'fault':fault,'policy':policy,
                         'task_success':int(ok),'unsafe_outcome':int(not ok),
                         'evidence_class':'public_upstream_tools_reference_actions_no_llm',
                         'events':events,'initial_state':initial_subject,'expected_state':reference,'terminal_state':actual,
                         'whole_database_sha256':full_hash,'expected_whole_database_sha256':reference_hash}
                    row['terminal_sha256']=hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest()
                    rows.append(row)
    files={}
    for module in list(sys.modules.values()):
        p=getattr(module,'__file__',None)
        if p and str(p).startswith(str(source/'src')):
            path=Path(p);files[path.relative_to(source).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    for p in [source/'LICENSE']+[source/f'data/tau2/domains/{d}/{f}' for d in ['retail','airline'] for f in ['db.json','tasks.json','policy.md']]:
        files[p.relative_to(source).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    provenance=json.loads((source/'SOURCE.json').read_text()) if (source/'SOURCE.json').exists() else {}
    manifest={'source':provenance,'selected_tasks':selected,'rows':len(rows),'files':files,
              'selection':'All retail/airline tasks with null initial_state and an expected cancellation action; 18 retail and 7 airline at the pinned revision.',
              'limits':'Reference actions supplied directly; no model or user simulation, no full official reward, no HTTP or production calls. Faults and wrappers are authored. Oracle clean-state equality is not independent semantic adjudication.'}
    (output/'traces.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    summary=[]
    for d in ['retail','airline']:
        for f in ['clean','before_commit','lost_reply']:
            for p in ['feature_matched','fa_mas']:
                subset=[r for r in rows if (r['domain'],r['fault'],r['policy'])==(d,f,p)]
                summary.append({'domain':d,'fault':f,'policy':p,'runs':len(subset),'complete':sum(r['task_success'] for r in subset),'unsafe':sum(r['unsafe_outcome'] for r in subset)})
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('third_party/tau2'));p.add_argument('--output',type=Path,default=Path('results/external_services'));a=p.parse_args();run(a.source.resolve(),a.output)
