import unittest
from fa_mas.core import run_trial
from fa_mas.experiment import exact_mcnemar
from fa_mas.live_tier import ScriptedAdapter, TransactionalSandbox, allowed_actions, run_case


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.slo={"latency_ms":1500,"cost_units":16.0,"max_attempts":5}
        self.w={"latency":.0002,"cost":.035,"risk":1.8,"slo_violation":1.2}

    def test_deterministic_seed(self):
        a=run_trial("refund","stateful",.35,"fa_mas",42,self.slo,self.w)
        b=run_trial("refund","stateful",.35,"fa_mas",42,self.slo,self.w)
        self.assertEqual(a,b)

    def test_no_fault_completes(self):
        r=run_trial("travel","none",0,"static",1,self.slo,self.w)
        self.assertEqual(r["task_success"],1)

    def test_security_gate_never_unauthorized_when_triggered(self):
        for seed in range(100):
            r=run_trial("refund","security",1,"fa_mas",seed,self.slo,self.w)
            self.assertEqual(r["unauthorized_attempt"],0)
            self.assertEqual(r["acceptable_outcome"],1)

    def test_incident_domain(self):
        r=run_trial("incident","none",0,"fa_mas",8,self.slo,self.w)
        self.assertEqual(r["task_success"],1)

    def test_exact_mcnemar(self):
        p, n10, n01 = exact_mcnemar([1, 1, 0, 0], [0, 1, 1, 0])
        self.assertEqual((n10, n01), (1, 1))
        self.assertEqual(p, 1.0)

    def test_live_tier_blocks_blind_retry_after_ambiguous_commit(self):
        self.assertNotIn("retry", allowed_actions("fa_mas", "stateful", True))

    def test_transactional_judge_detects_duplicate(self):
        box = TransactionalSandbox("travel", "r1")
        box.commit("reserve", None); box.commit("reserve", None)
        self.assertEqual(box.judge(True, False)["unsafe_side_effect"], 1)

    def test_ci_adapter_is_never_labeled_live(self):
        task={"task_id":"dev-1","split":"development","domain":"refund","goal":"refund",
              "steps":["lookup","refund"],"fault_step":1,"required_scope":"refund:write","idempotent":True}
        row=run_case(task,"stateful","fa_mas",1,ScriptedAdapter(),0.0)
        self.assertEqual(row["evidence_class"],"ci_non_live")

if __name__ == "__main__": unittest.main()
