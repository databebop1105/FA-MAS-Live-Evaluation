import itertools,unittest
from fa_mas.frontier import Candidate,frontier,select_frontier
from fa_mas.core import run_trial,POLICIES
class FrontierTests(unittest.TestCase):
 def test_dominance_and_equal_candidates(self):
  good=Candidate('good',.8,10,1,.1);bad=Candidate('bad',.7,20,2,.2);trade=Candidate('trade',.9,30,3,.3)
  self.assertEqual(frontier([good,bad,trade]),[good,trade])
  self.assertEqual(len(frontier([good,good])),2)
 def test_monotone_utility_is_preserved(self):
  cs=[Candidate('a',.8,10,1,.1),Candidate('b',.7,20,2,.2),Candidate('c',.95,30,4,.3)]
  for l,c,r in itertools.product((0,.1,1),repeat=3):
   w={'latency':l,'cost':c,'risk':r};score=lambda x:x.success-l*x.latency-c*x.cost-r*x.risk
   self.assertEqual(score(select_frontier(cs,w)),max(map(score,cs)))
 def test_invalid_weights_and_empty_frontier(self):
  with self.assertRaises(ValueError):select_frontier([],{k:0 for k in ('latency','cost','risk')})
  with self.assertRaises(ValueError):select_frontier([Candidate('a',.8,1,1,.1)],{'latency':-1,'cost':0,'risk':0})
 def test_strict_judge_exposes_orphaned_abstention(self):
  slo={'latency_ms':1800,'cost_units':18,'max_attempts':6};w={'latency':.0002,'cost':.035,'risk':1.8}
  found=False
  for seed in range(100):
   old=run_trial('refund','security',1,'fa_mas',seed,slo,w)
   strict=run_trial('refund','security',1,'fa_mas',seed,slo,w,strict_terminal=True)
   if strict['orphaned_effect']:
    self.assertEqual(old['safe_termination'],1);self.assertEqual(strict['unsafe_side_effect'],1);found=True;break
  self.assertTrue(found)
