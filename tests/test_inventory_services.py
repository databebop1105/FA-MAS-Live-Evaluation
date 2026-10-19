import copy
import json
import tempfile
import unittest
from pathlib import Path
from fa_mas.inventory_services import run_study, judge, POLICIES, FAULTS

class InventoryStudyTests(unittest.TestCase):
    def test_distinct_service_terminal_verdicts_and_raw_trace_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary=run_study(Path(tmp))
            rows=[json.loads(s) for s in (Path(tmp)/'inventory_traces.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows),len(POLICIES)*len(FAULTS))
        self.assertEqual(len({(r['fault'],r['policy']) for r in rows}),len(rows))
        for row in rows:
            self.assertEqual(judge(row['ledger']),{k:row[k] for k in ('task_success','safe_termination','unsafe_outcome')})
            self.assertEqual(sum(row[k] for k in ('task_success','safe_termination','unsafe_outcome')),1)
            self.assertEqual(row['evidence_class'],'engineered_distinct_inventory_http_sqlite_no_llm')
        self.assertEqual(summary['fa_mas']['unsafe_outcome'],1)
        self.assertEqual(summary['feature_matched']['unsafe_outcome'],3)
        self.assertEqual(next(r for r in rows if r['policy']=='fa_mas' and r['fault']=='capture_denied_release_unavailable')['unsafe_outcome'],1)
        self.assertEqual(next(r for r in rows if r['policy']=='feature_matched' and r['fault']=='wrong_sku_alternate')['unsafe_outcome'],1)
        altered=copy.deepcopy(next(r['ledger'] for r in rows if r['policy']=='fa_mas' and r['fault']=='clean'))
        altered['stock'][0]['sold']=2
        self.assertEqual(judge(altered)['unsafe_outcome'],1)
