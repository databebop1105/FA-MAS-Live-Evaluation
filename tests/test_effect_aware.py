import unittest
from fa_mas.core import run_trial, POLICIES

SLO = {'latency_ms':1800,'cost_units':18,'max_attempts':6}
WEIGHTS = {'latency':.0002,'cost':.035,'risk':1.8}

class EffectAwareTests(unittest.TestCase):
    def run_case(self, fault, seed, **kw):
        return run_trial('travel',fault,1,'fa_mas',seed,SLO,WEIGHTS,
                         strict_terminal=True,selection='frontier',**kw)

    def test_compensation_does_not_replace_an_uncommitted_step(self):
        repaired = False
        for seed in range(100):
            old = self.run_case('infrastructure',seed)
            new = self.run_case('infrastructure',seed,recovery_semantics='effect_aware')
            if new['task_success'] and not old['task_success']:
                repaired = True
                self.assertEqual(new['compensated'],0)
        self.assertTrue(repaired)

    def test_detected_security_fault_stays_unsafe_without_gate(self):
        policy = dict(POLICIES['fa_mas'],contracts=False,security=False,detect=1)
        for seed in range(20):
            result = self.run_case('security',seed,policy_override=policy,
                                   recovery_semantics='effect_aware')
            self.assertEqual(result['unsafe_side_effect'],1)
            self.assertEqual(result['task_success'],0)
            self.assertEqual(result['unauthorized_attempt'],1)

    def test_invalid_semantics_rejected(self):
        with self.assertRaises(ValueError):
            self.run_case('none',0,recovery_semantics='invented')
