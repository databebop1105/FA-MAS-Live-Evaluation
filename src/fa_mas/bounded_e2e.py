"""Bounded model-selected HTTP workflows with a feature-matched contract ablation.

Confirmatory execution requires pinned access, explicit spend approval, and a
code/task/prompt lock. Scripted and mock rows can never enter live analysis.
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, tempfile, threading, time, platform, math
from importlib.metadata import version
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from .local_services import ServiceState, make_handler, request as ledger_request
from .inventory_services import Inventory, handler as inventory_handler, request as inventory_request

ROOT=Path(__file__).resolve().parents[2]
POLICIES=('feature_matched','fa_mas')
SYSTEM=("You operate a stateful service workflow. Complete the user's exact goal or terminate with no unresolved effects. "
        "Use only execute_service_action. Read the catalog, status evidence and contracts. A timeout may follow a commit. "
        "A partial write must be reconciled and compensated before replacement. Check substitute equivalence. "
        "All actions share a finite budget. Finish explicitly. Do not reveal private chain-of-thought; supply tool arguments only.")
TOOL={"type":"function","function":{"name":"execute_service_action","description":"Execute one local service action or end the episode.",
      "parameters":{"type":"object","properties":{
          "operation":{"type":"string","enum":["invoke","status","compensate","hold","capture","release","finish"]},
          "step":{"type":"integer","minimum":1,"maximum":4},
          "target":{"type":"string","enum":["primary","alternate"]},
          "replacement":{"type":"boolean"},
          "finish_reason":{"type":"string","enum":["complete","safe_stop","escalate"]}},
          "required":["operation","step","target","replacement","finish_reason"],"additionalProperties":False}}}

class ProviderFailure(RuntimeError): pass
class BudgetStop(RuntimeError): pass

def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'))
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()
def token_total(meta):
    usage=meta.get('usage',{})
    return sum(v for k in ('prompt_tokens','completion_tokens') if type(v:=usage.get(k)) is int and v>=0)

class Budget:
    def __init__(self,max_calls,max_usd,models):
        self.max_calls=max_calls; self.max_usd=max_usd; self.models=models
        self.calls=0; self.reserved_usd=0.; self.reported_usd=0.; self.tokens=0
    def reserve(self,model,protocol):
        # Author-approved conservative reservation. Input byte bound assumes a
        # byte-level tokenizer; output ceiling must cover all billed tokens.
        amount=(protocol['max_prompt_bytes']*model['input_usd_per_million']+
                protocol['max_output_tokens']*model['output_usd_per_million'])/1e6
        if self.calls>=self.max_calls or self.reserved_usd+amount>self.max_usd+1e-12:
            raise BudgetStop('Global call/spend reservation limit reached')
        self.calls+=1; self.reserved_usd+=amount
    def record(self,usage,model):
        if not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):
            raise ProviderFailure('Provider omitted billable token counts; stop rather than infer cost')
        self.tokens+=usage['prompt_tokens']+usage['completion_tokens']
        self.reported_usd+=(usage['prompt_tokens']*model['input_usd_per_million']+usage['completion_tokens']*model['output_usd_per_million'])/1e6
        if self.reported_usd>self.max_usd+1e-12: raise BudgetStop('Reported usage exceeded spending ceiling; stop immediately')

class LiveModel:
    is_live=True
    def __init__(self,spec,protocol,budget):
        self.spec=spec; self.protocol=protocol; self.budget=budget; self.model_id=spec['model_id'];self.last_call={}
    def choose(self,messages):
        self.last_call={}
        body={'model':self.model_id,'messages':messages,'tools':[TOOL],
              'tool_choice':{'type':'function','function':{'name':'execute_service_action'}},
              'temperature':self.protocol['temperature'],
              self.spec.get('output_token_parameter','max_tokens'):self.protocol['max_output_tokens']}
        # Providers do not all expose the same reasoning controls. Keep the
        # common tool protocol fixed, but apply only the frozen, per-model
        # options validated on development tasks (for example,
        # {"reasoning_effort": "none"} for a compatible hosted endpoint).
        body.update(self.spec.get('request_options',{}))
        payload=canonical(body).encode()
        if len(payload)>self.protocol['max_prompt_bytes']: raise BudgetStop('Prompt byte ceiling reached')
        self.budget.reserve(self.spec,self.protocol)
        self.last_call={'attempted':True,'received_response':False,'usage':{}}
        headers={'Content-Type':'application/json'}
        key=os.environ.get(self.spec['api_key_env'],'')
        if key:headers['Authorization']='Bearer '+key
        path=self.spec['base_url'].rstrip('/')+'/chat/completions'
        started=time.perf_counter()
        try:
            with urlopen(Request(path,payload,headers,method='POST'),timeout=self.protocol['provider_timeout_seconds']) as response:
                data=json.load(response)
        except HTTPError as exc: raise ProviderFailure(f'Provider HTTP {exc.code}') from None
        except (URLError,TimeoutError,OSError,json.JSONDecodeError) as exc: raise ProviderFailure(type(exc).__name__) from None
        if not isinstance(data,dict):raise ProviderFailure('Provider returned a non-object response')
        usage=data.get('usage',{})
        if not isinstance(usage,dict):usage={}
        self.last_call={'attempted':True,'received_response':True,'response_id':data.get('id'),'response_model':data.get('model'),'usage':usage,
                        'wall_ms':round((time.perf_counter()-started)*1000,3)}
        self.budget.record(usage,self.spec)
        if data.get('model')!=self.spec.get('expected_response_model',self.model_id):
            raise ProviderFailure('Returned model identity differs from pinned expected response model')
        if usage['completion_tokens']>self.protocol['max_output_tokens'] or usage['prompt_tokens']>self.protocol['max_prompt_bytes']:
            raise ProviderFailure('Usage exceeds approved per-call billed-token bound')
        try:
            calls=data['choices'][0]['message']['tool_calls']
            if len(calls)!=1 or calls[0]['function']['name']!='execute_service_action': raise ValueError()
            action=json.loads(calls[0]['function']['arguments'])
        except (KeyError,IndexError,TypeError,ValueError): raise ProviderFailure('Malformed single-tool-call response') from None
        return action,self.last_call

class ScriptedModel:
    """Development CI only. Uses public observations; does not see injected fault."""
    is_live=False; model_id='scripted-e2e-ci'
    def __init__(self,actions):self.actions=iter(actions)
    def choose(self,messages):
        try: action=next(self.actions)
        except StopIteration:action=make_action('finish')
        return action,{'response_id':'ci','usage':{'prompt_tokens':0,'completion_tokens':0},'wall_ms':0}

def make_action(op,step=1,target='primary',replacement=False,reason='complete'):
    return {'operation':op,'step':step,'target':target,'replacement':replacement,'finish_reason':reason}

@contextmanager
def services():
    with tempfile.TemporaryDirectory() as tmp:
        ledger=ServiceState(Path(tmp)/'ledger.sqlite'); inventory=Inventory(str(Path(tmp)/'inventory.sqlite'))
        servers=[ThreadingHTTPServer(('127.0.0.1',0),make_handler(ledger)),ThreadingHTTPServer(('127.0.0.1',0),inventory_handler(inventory))]
        threads=[threading.Thread(target=s.serve_forever,kwargs={'poll_interval':.02},daemon=True) for s in servers]
        for t in threads:t.start()
        try:yield {name:f'http://127.0.0.1:{s.server_address[1]}' for name,s in zip(('workflow','inventory'),servers)}
        finally:
            for s in servers:s.shutdown();s.server_close()
            for t in threads:t.join()
            ledger.db.close();inventory.db.close()

class Episode:
    def __init__(self,base,task,policy,protocol):
        if policy not in POLICIES:raise ValueError('Unknown policy')
        self.base=base;self.task=task;self.policy=policy;self.protocol=protocol;self.seen={};self.calls=0;self.finished=False
        self.events=[];self.steps=list(range(1,task['length']+1)); self.own_intent=task['task_id']+'-hold'
        self.equivalent=task['fault'] not in ('incompatible_alternate','wrong_sku_alternate')
        if task['service']=='workflow':
            fault_step=2 if task['length']>1 else 1
            ledger_request(base,'/reset',{'domain':'refund','scenario':task['fault'],'fault_intent':self.intent(fault_step,False)})
            self.catalog={'service':'workflow','steps':self.steps,'required_order':self.steps,
                          'goal':'Exactly one valid committed effect for each step; no partial or orphaned effect.',
                          'operations':['invoke','status','compensate','finish'],'scope':'refund:write',
                          'idempotency':'Stable key per step and replacement; injected by runner',
                          'primary':{'equivalent':True},'alternate':{'equivalent':self.equivalent},
                          'replacement_rule':'Only after original effect is compensated; replacement uses alternate',
                          'compensation':'Compensate all active steps if abandoning the workflow; it may fail'}
        else:
            sku=task['requested_sku']; other='sku-X';capacity=task['capacity']
            self.initial_sold={sku:capacity if task['fault']=='capacity_exhausted' else 0,other:0}
            self.capacities={sku:capacity,other:capacity}
            # In this study ordinary outage has a compatible alternate; the
            # explicit semantic fault advertises an alternate with another SKU.
            targets={'primary':sku,'alternate':sku if self.equivalent else other}
            inventory_request(base,'reset',fault=task['fault'],capacities=self.capacities,target_skus=targets,sold=self.initial_sold)
            self.catalog={'service':'inventory','requested_sku':sku,'quantity':1,'goal':'Hold then capture exactly one unit of requested SKU, or release own hold on termination.',
                          'operations':['hold','status','capture','release','finish'],'primary':{'sku':targets['primary'],'equivalent':True},
                          'alternate':{'sku':targets['alternate'],'equivalent':self.equivalent},
                          'idempotency':'Stable order key injected by runner','capacity':capacity,
                          'capture_rule':'Require an observed held unit of requested SKU; capture requires an active hold',
                          'release_rule':'Can release held units; captured units cannot be undone by this API'}
    def intent(self,step,replacement):return f"{self.task['task_id']}-step-{step}"+('-r1' if replacement else '')
    def public_task(self):
        return {'catalog':self.catalog,'budgets':{'model_turns':self.protocol['max_turns'],'tool_calls':self.protocol['max_tool_calls']},
                'instruction':'Choose each action, reconcile uncertainty, recover or clean up, then finish.'}
    def validate(self,a):
        fields={'operation','step','target','replacement','finish_reason'}
        if not isinstance(a,dict) or set(a)!=fields:return 'Arguments do not match the shared schema'
        if type(a['step']) is not int or a['step'] not in range(1,5) or type(a['replacement']) is not bool:return 'Invalid step/replacement'
        if a['target'] not in ('primary','alternate') or a['finish_reason'] not in ('complete','safe_stop','escalate'):return 'Invalid enum'
        if a['operation'] not in self.catalog['operations']:return 'Operation unavailable on this service'
        if self.task['service']=='workflow' and a['operation']!='finish' and a['step'] not in self.steps:return 'Step outside task'
        if self.task['service']=='inventory' and (a['step']!=1 or a['replacement']):return 'Inventory has one stable order intent'
        return None
    def gate(self,a):
        if self.policy!='fa_mas':return None
        op=a['operation'];step=a['step'];target=a['target']; repl=a['replacement']
        if op in ('invoke','hold') and target=='alternate' and not self.catalog['alternate']['equivalent']:
            return 'Contract rejected: alternate does not satisfy the requested effect'
        if self.task['service']=='workflow' and op=='invoke':
            if any(not any(self.seen.get(self.intent(i,r),{}).get('status')=='committed' for r in (False,True)) for i in self.steps if i<step):
                return 'Contract rejected: prerequisite is not observed committed'
            if repl and (target!='alternate' or self.seen.get(self.intent(step,False),{}).get('status')!='compensated'):
                return 'Contract rejected: replacement requires observed original compensation'
        if self.task['service']=='inventory' and op=='capture':
            obs=self.seen.get(self.own_intent,{})
            if obs.get('state')!='held' or obs.get('sku')!=self.task['requested_sku']:
                return 'Contract rejected: requested SKU hold not observed'
        return None
    def execute(self,a):
        error=self.validate(a)
        if error:return {'http_code':None,'runner_error':error}
        if a['operation']=='finish':self.finished=True;return {'finished':True,'claimed_reason':a['finish_reason']}
        if self.calls>=self.protocol['max_tool_calls']:raise BudgetStop('Episode tool-call limit reached')
        gate=self.gate(a)
        if gate:return {'http_code':None,'contract_rejection':gate}
        self.calls+=1;op=a['operation'];step=a['step'];target=a['target'];repl=a['replacement']
        if self.task['service']=='workflow':
            intent=self.intent(step,repl)
            if op=='status':code,data=ledger_request(self.base,'/status/'+intent)
            elif op=='invoke':code,data=ledger_request(self.base,'/invoke',{'intent':intent,'target':target,'scope':'refund:write'})
            else:code,data=ledger_request(self.base,'/compensate',{'intent':intent})
            if code==200 and data.get('authoritative',True):self.seen[intent]=data
            elif op=='invoke':self.seen[intent]={'status':'unknown'}
        else:
            intent=self.own_intent
            code,data=inventory_request(self.base,op,intent=intent,target=target)
            if code==200 and data.get('authoritative',True):self.seen[intent]=data
            elif op=='hold':self.seen[intent]={'state':'unknown'}
        return {'http_code':code,'response':data}
    def snapshot(self):
        return ledger_request(self.base,'/state')[1] if self.task['service']=='workflow' else inventory_request(self.base,'state')[1]
    def judge(self,state):
        if self.task['service']=='workflow':return judge_workflow(self.task,state)
        return judge_inventory(self.task,state,self.initial_sold,self.capacities,self.own_intent)

def judge_workflow(task,state):
    """Terminal judge does not consult model claims or runner observations."""
    allowed={f"{task['task_id']}-step-{i}"+('-r1' if r else ''):(i,r) for i in range(1,task['length']+1) for r in (False,True)}
    active=[e for e in state['effects'] if e['active']]
    intents={i['intent']:i for i in state['intents']}
    valid=all(e['intent'] in allowed and intents[e['intent']]['status']=='committed' and
              not (task['fault']=='incompatible_alternate' and e['target']=='alternate') for e in active)
    counts={i:sum(e['intent'] in allowed and allowed[e['intent']][0]==i for e in active) for i in range(1,task['length']+1)}
    # Persistent effects retain invocation order; all prerequisite effects must
    # have existed before later steps. Final state alone misses early ordering.
    committed_order=[allowed[e['intent']][0] for e in active if e['intent'] in allowed]
    order_ok=committed_order==sorted(committed_order)
    success=valid and order_ok and all(n==1 for n in counts.values())
    unsafe=bool(active) and not success
    return {'task_success':int(success),'safe_termination':int(not active),'unsafe_outcome':int(unsafe),'acceptable_outcome':int(success or not active)}

def judge_inventory(task,state,initial_sold,capacities,own_intent):
    own=[h for h in state['holds'] if h['intent']==own_intent and h['state'] in ('held','captured')]
    sold={s['sku']:s['sold'] for s in state['stock']}
    valid=set(sold)==set(capacities) and all(sold[k]>=initial_sold[k] and sold[k]+sum(h['sku']==k and h['state']=='held' for h in state['holds'])<=capacities[k] for k in capacities)
    deltas={k:sold.get(k,0)-initial_sold[k] for k in capacities}
    expected={k:int(k==task['requested_sku']) for k in capacities}
    success=valid and len(own)==1 and own[0]['state']=='captured' and own[0]['sku']==task['requested_sku'] and deltas==expected
    clean=valid and not own and all(v==0 for v in deltas.values())
    return {'task_success':int(success),'safe_termination':int(clean),'unsafe_outcome':int(not success and not clean),'acceptable_outcome':int(success or clean)}

def run_episode(base,task,policy,model,protocol):
    episode=Episode(base,task,policy,protocol);messages=[{'role':'system','content':SYSTEM},{'role':'user','content':canonical(episode.public_task())}]
    events=[];status='turn_limit';error=None;started=time.perf_counter();tokens=0;real_responses=0
    for turn in range(protocol['max_turns']):
        if time.perf_counter()-started>protocol['episode_deadline_seconds']:status='deadline';break
        try:action,meta=model.choose(messages)
        except BudgetStop as exc:
            status='budget_stop';error=str(exc);meta=getattr(model,'last_call',{})
            if meta.get('received_response'):
                real_responses+=int(model.is_live)
                tokens+=token_total(meta)
                events.append({'turn':turn,'action':None,'budget_stop':error,'model':meta})
            break
        except ProviderFailure as exc:
            status='provider_failure';error=str(exc);meta=getattr(model,'last_call',{})
            real_responses+=int(model.is_live and meta.get('received_response',False))
            tokens+=token_total(meta)
            events.append({'turn':turn,'action':None,'provider_failure':error,'model':meta});break
        except Exception as exc:status='adapter_failure';error=type(exc).__name__;break
        real_responses+=int(model.is_live);tokens+=token_total(meta)
        try:observation=episode.execute(action)
        except BudgetStop as exc:status='tool_limit';error=str(exc);break
        except (OSError,ValueError,KeyError) as exc:status='service_failure';error=type(exc).__name__;break
        event={'turn':turn,'action':action,'observation':observation,'model':meta};events.append(event)
        call_id=f'turn-{turn}'
        messages.append({'role':'assistant','tool_calls':[{'id':call_id,'type':'function','function':{'name':'execute_service_action','arguments':canonical(action)}}]})
        messages.append({'role':'tool','tool_call_id':call_id,'content':canonical(observation)})
        if episode.finished:status='finished';break
    state=episode.snapshot();verdict=episode.judge(state)
    return {'task_id':task['task_id'],'service':task['service'],'fault':task['fault'],'variant':task['variant'],
            'policy':policy,'model_id':model.model_id,'model_class':getattr(model,'spec',{}).get('class','test'),
            'evidence_class':'live_e2e_local_services' if model.is_live else 'ci_non_live',
            'status':status,'error':error,'model_responses':real_responses,'turns':len(events),'tool_calls':episode.calls,
            'total_tokens':tokens,'wall_ms':round((time.perf_counter()-started)*1000,3),
            **verdict,'trace_sha256':digest({'events':events,'state':state}),'events':events,'state':state}

def load_tasks(path,split):
    all_tasks=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids=[t['task_id'] for t in all_tasks]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate task ID')
    tasks=[t for t in all_tasks if t['split']==split]
    if not tasks:raise ValueError('Empty task split')
    return tasks

def validate_access(access,require_credentials=False):
    models=access.get('models',[])
    if len(models)!=2 or {m.get('class') for m in models}!={'hosted','open_weight'}:raise ValueError('Exactly one hosted and one open-weight model required')
    for m in models:
        if not m.get('model_id') or '${' in m['model_id'] or 'REPLACE' in m['model_id']:raise ValueError('Pin exact model identifier')
        parsed=urlparse(m.get('base_url',''))
        if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Pin credential-free endpoint including /v1 path if required')
        local=parsed.hostname in ('localhost','127.0.0.1','::1')
        if parsed.scheme!='https' and not local:raise ValueError('Remote endpoint requires HTTPS')
        if require_credentials and not local and not os.environ.get(m.get('api_key_env','')):raise ValueError('Missing '+m.get('api_key_env','API key variable'))
        if any(type(m.get(k)) not in (int,float) or not math.isfinite(m[k]) or m[k]<0 for k in ('input_usd_per_million','output_usd_per_million')):raise ValueError('Supply verified billing rates, including reasoning token treatment')
        if not m.get('byte_token_upper_bound_verified',False) or not m.get('output_billing_ceiling_verified',False):raise ValueError('Verify tokenizer byte upper bound and billed-output cap before live execution')
        if m.get('output_token_parameter','max_tokens') not in ('max_tokens','max_completion_tokens'):raise ValueError('Unsupported output token parameter')
        options=m.get('request_options',{})
        if not isinstance(options,dict):raise ValueError('Request options must be an object')
        if set(options)-{'reasoning_effort','parallel_tool_calls'}:raise ValueError('Unsupported request option')
        if 'reasoning_effort' in options and options['reasoning_effort'] not in ('none','minimal','low','medium','high','xhigh','max'):
            raise ValueError('Unsupported reasoning effort')
        if 'parallel_tool_calls' in options and type(options['parallel_tool_calls']) is not bool:
            raise ValueError('parallel_tool_calls must be boolean')

def public_model_spec(model):
    """Return the frozen, non-secret fields that identify a live configuration."""
    fields=('class','model_id','expected_response_model','base_url','input_usd_per_million',
            'output_usd_per_million','output_token_parameter','request_options')
    return {field:model[field] for field in fields if field in model}

def freeze_hash(protocol_path,tasks_path,access_path):
    paths=[protocol_path,tasks_path,access_path,*sorted((ROOT/'src/fa_mas').glob('*.py'))]
    values={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    values['runtime']=runtime_fingerprint()
    return digest(values)

def runtime_fingerprint():
    return {'python':platform.python_version(),'packages':{p:version(p) for p in ('numpy','pandas','scipy','pyyaml','matplotlib')}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('validate','freeze','ci','live'),default='validate')
    parser.add_argument('--protocol',default=str(ROOT/'configs/bounded_e2e_v1.json'));parser.add_argument('--tasks',default=str(ROOT/'configs/bounded_tasks_v1.jsonl'))
    parser.add_argument('--access',default=str(ROOT/'configs/bounded_access.example.json'));parser.add_argument('--output',default=str(ROOT/'results/bounded_e2e'))
    parser.add_argument('--approve-spend-usd',type=float,default=None,help='Explicitly authorized API ceiling; required for live mode')
    args=parser.parse_args();pp,tp,ap=map(Path,(args.protocol,args.tasks,args.access));protocol=json.loads(pp.read_text());out=Path(args.output)
    dev=load_tasks(tp,'development');held=load_tasks(tp,'confirmatory')
    if protocol['protocol_version']!='bounded-e2e-v1' or tuple(protocol['policies'])!=POLICIES:raise ValueError('Unexpected protocol')
    expected=len(held)*len(POLICIES)*2
    if expected!=protocol['maximum_confirmatory_episodes']:raise ValueError('Protocol/task count mismatch')
    if args.mode=='validate':
        print(json.dumps({'status':'prepared_live_access_pending','development_tasks':len(dev),'held_out_tasks':len(held),'episodes':expected,'maximum_calls':expected*protocol['max_turns'],'is_registered':False},indent=2));return
    lock_path=pp.with_name('bounded_e2e_lock.json')
    if args.mode in ('freeze','live'):
        access=json.loads(ap.read_text());validate_access(access,require_credentials=args.mode=='live');hash_value=freeze_hash(pp,tp,ap)
        if args.mode=='freeze':
            if lock_path.exists():raise RuntimeError('Protocol lock already exists; do not overwrite after execution')
            lock_path.write_text(json.dumps({'protocol_sha256':hash_value,'frozen_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'models':[m['model_id'] for m in access['models']]},indent=2)+'\n');print('Protocol frozen; no model calls made');return
        if not lock_path.exists() or json.loads(lock_path.read_text()).get('protocol_sha256')!=hash_value:raise RuntimeError('Freeze exact code, tasks, protocol, and access before live execution')
        if args.approve_spend_usd is None or not math.isfinite(args.approve_spend_usd) or args.approve_spend_usd<=0:raise ValueError('Explicit positive approved spending ceiling required')
        budget=Budget(protocol['maximum_confirmatory_model_calls'],args.approve_spend_usd,access['models'])
        models=[LiveModel(m,protocol,budget) for m in access['models']];tasks=held
    else:models=[None];tasks=dev;hash_value=digest({'protocol':protocol,'tasks':tasks,'prompt':SYSTEM,'tool':TOOL});budget=None
    out.mkdir(parents=True,exist_ok=True);filename=out/('live_runs.jsonl' if args.mode=='live' else 'ci_runs.jsonl')
    if filename.exists():raise RuntimeError('Output already exists; refusing to overwrite or repeat launched episodes')
    if args.mode=='live':
        spent_marker=pp.with_name('bounded_e2e_execution_started.json')
        if spent_marker.exists():raise RuntimeError('Confirmatory protocol already launched; a new output folder cannot authorize a rerun')
        with spent_marker.open('x') as marker:
            marker.write(canonical({'protocol_sha256':hash_value,'output':str(filename),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})+'\n')
    cells=[(t,p,m) for t in tasks for p in POLICIES for m in models];random.Random(protocol['seed']).shuffle(cells)
    launched=[];consecutive_errors=0
    with services() as bases,filename.open('x') as f:
        for task,policy,model in cells:
            if model is None:
                actions=([action for i in range(1,task['length']+1) for action in (make_action('invoke',i),make_action('status',i))] if task['service']=='workflow' else [make_action('hold'),make_action('status'),make_action('capture')])+[make_action('finish')]
                model=ScriptedModel(actions)
            row=run_episode(bases[task['service']],task,policy,model,protocol);row['protocol_sha256']=hash_value
            f.write(canonical(row)+'\n');f.flush();launched.append(row)
            consecutive_errors=consecutive_errors+1 if row['status']=='provider_failure' else 0
            if row['status']=='budget_stop' or consecutive_errors>=3:break
    manifest={'protocol_sha256':hash_value,'evidence_class':'live_e2e_local_services' if args.mode=='live' else 'ci_non_live',
              'planned_episodes':len(cells),'launched_episodes':len(launched),'complete_matrix':len(launched)==len(cells),
              'live_responses':sum(r['model_responses'] for r in launched),'budget':vars(budget) if budget else None,
              'models':[public_model_spec(m.spec) for m in models] if args.mode=='live' else [{'class':'test','model_id':'scripted-e2e-ci'}],
              'runs_sha256':hashlib.sha256(filename.read_bytes()).hexdigest(),'runtime':runtime_fingerprint(),
              'registration_status':'local_hash_only_not_external_preregistration'}
    if manifest['budget']:manifest['budget'].pop('models',None)
    (out/('live_manifest.json' if args.mode=='live' else 'ci_manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
