"""Independent HTTP/SQLite stock-and-hold conformance service.

Authored cases, deterministic policies, synthetic inventory; no model calls.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sqlite3, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

FAULTS = ('clean','lost_after_hold','lost_before_hold','stale_read','primary_outage','wrong_sku_alternate','capture_denied_release_unavailable')
POLICIES = ('static','stable_retry','verify_retry','feature_matched','fa_mas')

class Inventory:
    def __init__(self, path):
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.lock=threading.RLock(); self.fault='clean'; self.fired=False; self.reads=0; self.events=[]
        self.db.executescript('CREATE TABLE stock(sku TEXT PRIMARY KEY, capacity INT, sold INT); CREATE TABLE holds(intent TEXT PRIMARY KEY, sku TEXT, state TEXT);')
        self.reset('clean')
    def reset(self, fault, capacities=None, target_skus=None, sold=None):
        with self.lock:
            self.db.execute('DELETE FROM holds'); self.db.execute('DELETE FROM stock')
            capacities=capacities or {'sku-A':1,'sku-B':1}
            sold=sold or {}
            self.db.executemany('INSERT INTO stock VALUES (?,?,?)', [(sku,cap,sold.get(sku,0)) for sku,cap in capacities.items()])
            self.target_skus=target_skus or {'primary':'sku-A','alternate':'sku-B'}
            self.db.commit(); self.fault=fault; self.fired=False; self.reads=0; self.events=[]
    def snapshot(self):
        with self.lock:
            stock=[dict(zip(('sku','capacity','sold'),x)) for x in self.db.execute('SELECT * FROM stock ORDER BY sku')]
            holds=[dict(zip(('intent','sku','state'),x)) for x in self.db.execute('SELECT * FROM holds ORDER BY intent')]
            return {'stock':stock,'holds':holds,'events':list(self.events)}
    def action(self, op, data):
        with self.lock:
            intent=data.get('intent','order-1'); target=data.get('target','primary')
            sku=self.target_skus[target]
            if op=='reset':
                self.reset(data['fault'],data.get('capacities'),data.get('target_skus'),data.get('sold'))
                return 200,{'ok':True}
            if op=='state': return 200,self.snapshot()
            if op=='status':
                self.reads+=1
                if self.fault=='stale_read' and self.reads==1: return 200,{'state':'unknown','authoritative':False}
                row=self.db.execute('SELECT sku,state FROM holds WHERE intent=?',(intent,)).fetchone()
                return 200,{'state':row[1] if row else 'absent','sku':row[0] if row else None,'authoritative':True}
            if op=='hold':
                if self.fault in ('primary_outage','wrong_sku_alternate') and target=='primary':
                    self.events.append({'op':op,'result':'outage','target':target}); return 503,{'error':'unavailable'}
                if self.fault=='lost_before_hold' and not self.fired:
                    self.fired=True; self.events.append({'op':op,'result':'lost_before'}); return 504,{'error':'timeout'}
                old=self.db.execute('SELECT sku,state FROM holds WHERE intent=?',(intent,)).fetchone()
                if old:
                    if old[0]!=sku: return 409,{'error':'intent_target_mismatch'}
                    return 200,{'state':old[1],'sku':sku,'replay':True}
                available=self.db.execute("SELECT capacity-sold-(SELECT count(*) FROM holds WHERE sku=? AND state='held') FROM stock WHERE sku=?",(sku,sku)).fetchone()[0]
                if available<=0: return 409,{'error':'capacity'}
                self.db.execute("INSERT INTO holds VALUES (?, ?, 'held')",(intent,sku)); self.db.commit()
                self.events.append({'op':op,'result':'held','sku':sku})
                if self.fault in ('lost_after_hold','stale_read') and not self.fired:
                    self.fired=True; return 504,{'error':'reply_lost'}
                return 200,{'state':'held','sku':sku}
            if op=='capture':
                row=self.db.execute('SELECT sku,state FROM holds WHERE intent=?',(intent,)).fetchone()
                if not row or row[1]!='held': return 409,{'error':'no_active_hold'}
                if self.fault=='capture_denied_release_unavailable':
                    self.events.append({'op':op,'result':'denied'}); return 403,{'error':'capture_denied'}
                self.db.execute("UPDATE holds SET state='captured' WHERE intent=?",(intent,))
                self.db.execute('UPDATE stock SET sold=sold+1 WHERE sku=?',(row[0],)); self.db.commit()
                self.events.append({'op':op,'result':'captured','sku':row[0]}); return 200,{'state':'captured'}
            if op=='release':
                if self.fault=='capture_denied_release_unavailable':
                    self.events.append({'op':op,'result':'release_failed'}); return 503,{'error':'release_unavailable'}
                self.db.execute("UPDATE holds SET state='released' WHERE intent=? AND state='held'",(intent,)); self.db.commit()
                self.events.append({'op':op,'result':'released'}); return 200,{'state':'released'}
            return 404,{'error':'unknown_operation'}

def handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            size=int(self.headers.get('Content-Length','0')); data=json.loads(self.rfile.read(size) or b'{}')
            code,out=state.action(self.path.strip('/'),data)
            payload=json.dumps(out).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
    return Handler

def request(base,op,**data):
    req=Request(base+'/'+op,json.dumps(data).encode(),{'Content-Type':'application/json'})
    try: response=urlopen(req,timeout=3)
    except HTTPError as exc: response=exc
    with response: return response.status,json.loads(response.read())

def run_case(base,fault,policy):
    request(base,'reset',fault=fault)
    intent='order-1'; calls=0
    def hold(target='primary'):
        nonlocal calls
        calls+=1; return request(base,'hold',intent=intent,target=target)
    code,out=hold(); held=code==200
    if not held and policy=='stable_retry': held=hold()[0]==200
    if not held and policy in ('verify_retry','feature_matched','fa_mas'):
        _,obs=request(base,'status',intent=intent)
        if obs['state']=='unknown' and policy in ('feature_matched','fa_mas'):
            _,obs=request(base,'status',intent=intent)
        if obs['state']=='held': held=True
        elif obs['state']=='absent' and obs['authoritative']:
            held=hold()[0]==200
            if not held and policy in ('feature_matched','fa_mas'):
                if policy=='feature_matched':
                    if fault=='wrong_sku_alternate':
                        calls+=1; held=request(base,'hold',intent='alternate-order',target='alternate')[0]==200
                    else: held=hold('alternate')[0]==200
    capture_intent='alternate-order' if fault=='wrong_sku_alternate' and policy=='feature_matched' else intent
    capture_code=0
    if held: capture_code=request(base,'capture',intent=capture_intent)[0]
    if capture_code!=200 and policy in ('feature_matched','fa_mas'):
        state=request(base,'state')[1]
        for h in state['holds']:
            if h['state']=='held': request(base,'release',intent=h['intent'])
    state=request(base,'state')[1]
    verdict=judge(state)
    success=verdict['task_success']; unsafe=verdict['unsafe_outcome']; safe=verdict['safe_termination']
    return {'fault':fault,'policy':policy,'task_success':int(success),'safe_termination':int(safe),'unsafe_outcome':int(unsafe),
            'acceptable_outcome':int(success or safe),'hold_calls':calls,'trace_sha256':hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest(),
            'evidence_class':'engineered_distinct_inventory_http_sqlite_no_llm','ledger':state}

def judge(state):
    """Read only the terminal database snapshot; never trust controller outcome."""
    active=[h for h in state['holds'] if h['state'] in ('held','captured')]
    sold={s['sku']:s['sold'] for s in state['stock']}
    invariant=all(s['sold']+sum(h['sku']==s['sku'] and h['state']=='held' for h in active)<=s['capacity'] for s in state['stock'])
    success=len(active)==1 and active[0]['sku']=='sku-A' and active[0]['state']=='captured' and sold=={'sku-A':1,'sku-B':0} and invariant
    unsafe=not invariant or bool(active and not success) or sold['sku-B']!=0
    safe=not success and not unsafe
    return {'task_success':int(success),'safe_termination':int(safe),'unsafe_outcome':int(unsafe)}

def run_study(path):
    path.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        service=Inventory(str(Path(directory)/'inventory.sqlite'))
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(service)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base=f'http://127.0.0.1:{server.server_address[1]}'
        try: rows=[run_case(base,f,p) for f in FAULTS for p in POLICIES]
        finally: server.shutdown(); server.server_close(); thread.join(); service.db.close()
    (path/'inventory_traces.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    with (path/'inventory_runs.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,[k for k in rows[0] if k!='ledger']); writer.writeheader(); writer.writerows({k:v for k,v in row.items() if k!='ledger'} for row in rows)
    summary={p:{k:sum(r[k] for r in rows if r['policy']==p) for k in ('task_success','safe_termination','unsafe_outcome')} for p in POLICIES}
    (path/'summary.json').write_text(json.dumps({'cases':len(rows),'faults':FAULTS,'summary':summary,'evidence_class':rows[0]['evidence_class']},indent=2)+'\n')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='results/inventory_services'); args=parser.parse_args()
    print(json.dumps(run_study(Path(args.output)),indent=2))
