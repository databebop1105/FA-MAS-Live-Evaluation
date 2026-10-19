"""Construct an authored held-out task bank; not an independently sampled dataset."""
import json
from pathlib import Path
rows=[]
for service in ('workflow','inventory'):
    for v in range(2):
        rows.append({'task_id':f'dev-{service}-{v}','split':'development','service':service,
                     'fault':'clean' if v==0 else ('lost_reply_after_commit' if service=='workflow' else 'lost_after_hold'),
                     'length':2,'requested_sku':'sku-A','capacity':1,'variant':v})
    faults=(('clean','lost_reply_after_commit','lost_reply_before_commit','stale_status_after_commit','partial_commit','primary_unavailable','incompatible_alternate','compensation_unavailable') if service=='workflow' else
            ('clean','lost_after_hold','lost_before_hold','stale_read','primary_outage','wrong_sku_alternate','capture_denied_release_unavailable','capacity_exhausted'))
    for fault in faults:
        for v in range(2):
            rows.append({'task_id':f'held-{service}-{fault}-{v}','split':'confirmatory','service':service,'fault':fault,
                         'length':3+v,'requested_sku':('sku-B' if v==0 else 'sku-C'),'capacity':2+v,'variant':v})
p=Path('configs/bounded_tasks_v1.jsonl');p.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
print('development',sum(r['split']=='development' for r in rows),'confirmatory',sum(r['split']=='confirmatory' for r in rows))
