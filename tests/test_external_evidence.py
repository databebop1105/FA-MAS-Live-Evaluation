"""Saved-state integrity checks; these do not execute an LLM benchmark."""
import hashlib,json,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PublicEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rows=[json.loads(s) for s in (ROOT/'results/external_services/traces.jsonl').read_text().splitlines()]

    def test_complete_matrix_and_saved_state_verdicts(self):
        self.assertEqual(len(self.rows),150)
        keys={(r['domain'],r['task_id'],r['fault'],r['policy']) for r in self.rows}
        self.assertEqual(len(keys),150)
        for r in self.rows:
            equal=r['terminal_state']==r['expected_state']
            self.assertEqual(r['task_success'],int(equal))
            self.assertEqual(r['unsafe_outcome'],int(not equal))
            digest=hashlib.sha256(json.dumps(r['terminal_state'],sort_keys=True).encode()).hexdigest()
            self.assertEqual(r['terminal_sha256'],digest)
            self.assertEqual(equal,r['whole_database_sha256']==r['expected_whole_database_sha256'])
            self.assertEqual(r['evidence_class'],'public_upstream_tools_reference_actions_no_llm')

    def test_upstream_bytes_and_commit_are_pinned(self):
        manifest=json.loads((ROOT/'results/external_services/manifest.json').read_text())
        self.assertEqual(len(manifest['source']['commit']),40)
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/'third_party/tau2'/name).read_bytes()).hexdigest(),digest)

    def test_lost_reply_difference_is_service_specific(self):
        for r in self.rows:
            expected_unsafe=(r['domain']=='airline' and r['fault']=='lost_reply' and r['policy']=='feature_matched')
            self.assertEqual(r['unsafe_outcome'],int(expected_unsafe))
