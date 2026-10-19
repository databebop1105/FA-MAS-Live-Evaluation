"""Read-only replay and end-state audit; never overwrites evidence."""
from pathlib import Path
import hashlib, io, json, platform
import pandas as pd
from fa_mas.core import run_trial, POLICIES
from fa_mas.inventory_services import judge
from audit_workflow import audit

root = Path(__file__).resolve().parents[1]
original = root / 'results/runs.csv'
cfg = json.loads((root / 'results/manifest.json').read_text())['config']
saved = pd.read_csv(original)
rows = [run_trial(r.domain, r.fault, r.intensity, r.baseline, r.seed,
                  cfg['slo'], cfg['utility_weights'], r.ablation)
        for r in saved.itertuples(index=False)]
replayed = pd.DataFrame(rows)
assert replayed.to_csv(index=False).encode() == original.read_bytes()
assert len(saved) == 52500 and not saved.isna().any().any()
inventory = [json.loads(s) for s in (root/'results/inventory_services/inventory_traces.jsonl').read_text().splitlines()]
assert len(inventory) == 35
for r in inventory:
    assert judge(r['ledger']) == {k:r[k] for k in ('task_success','safe_termination','unsafe_outcome')}
c = json.loads((root/'configs/matched_controls_v1.json').read_text())
matched = pd.read_csv(root/'results/matched_controls/runs.csv')
assert len(matched) == 18000 and not matched.isna().any().any()
matched_rows = []
for r in matched.itertuples(index=False):
    policy = dict(POLICIES['fa_mas'], detect=c['detect'], localize=c['localize'])
    if r.variant == 'no_gates': policy.update(contracts=False, security=False)
    if r.variant == 'no_compensation': policy['compensate'] = False
    row = run_trial(r.domain,r.fault,r.intensity,'fa_mas',r.seed,c['slo'],c['weights'],
                    policy_override=policy,detection_bonus=False,
                    selection='first' if r.variant=='first_feasible' else 'frontier',strict_terminal=True)
    row['variant'] = r.variant
    matched_rows.append(row)
assert pd.DataFrame(matched_rows).to_csv(index=False).encode() == (root/'results/matched_controls/runs.csv').read_bytes()
assert not ((matched.safe_termination == 1) & (matched.unsafe_side_effect == 1)).any()
v2_cfg = json.loads((root/'configs/matched_controls_v2.json').read_text())
v2 = pd.read_csv(root/'results/matched_controls_v2/runs.csv')
v2_rows = []
for r in v2.itertuples(index=False):
    policy = dict(POLICIES['fa_mas'], detect=v2_cfg['detect'], localize=v2_cfg['localize'])
    if r.variant == 'no_gates': policy.update(contracts=False, security=False)
    if r.variant == 'no_compensation': policy['compensate'] = False
    row = run_trial(r.domain,r.fault,r.intensity,'fa_mas',r.seed,v2_cfg['slo'],v2_cfg['weights'],
                    policy_override=policy,detection_bonus=False,
                    selection='first' if r.variant=='first_feasible' else 'frontier',strict_terminal=True,
                    recovery_semantics='effect_aware')
    row['variant'] = r.variant
    v2_rows.append(row)
assert len(v2) == 18000
assert pd.DataFrame(v2_rows).to_csv(index=False).encode() == (root/'results/matched_controls_v2/runs.csv').read_bytes()
report = {'status':'passed','python':platform.python_version(),
          'original_rows_byte_identical':len(saved),'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
          'matched_rows_byte_identical':len(matched),'effect_aware_rows_byte_identical':len(v2),'inventory_verdicts_recomputed':len(inventory),
          'workflow':audit(root/'results/workflow_services'),
          'limits':'Replay verifies reproducibility, not construct validity, live efficacy or independent replication.'}
(root/'results/evidence_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
