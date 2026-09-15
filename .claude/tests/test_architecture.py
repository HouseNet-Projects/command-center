import json, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'architecture'))
import brain_router, work_orchestrator
class ArchitectureTests(unittest.TestCase):
 def test_registry_has_one_deputy_and_nine_profiles(self):
  r=brain_router.load_registry(); self.assertEqual(r['identity'],'DEPUTY'); self.assertEqual(len(r['brains']),9)
  self.assertFalse(r['authority_boundary']['direct_external_write']); self.assertFalse(r['authority_boundary']['approval_authority']); self.assertFalse(r['authority_boundary']['independent_memory'])
 def test_single_brain_route(self):
  r=brain_router.route('prepare a billing collections report'); self.assertIn('BRAIN-BILLING',[x['brain_id'] for x in r['selected_brains']])
 def test_cross_functional_route_is_multi_brain(self):
  r=brain_router.route('Why has churn increased?'); self.assertTrue(r['synthesis_required']); self.assertGreaterEqual(len(r['selected_brains']),3)
 def test_empty_request_rejected(self):
  with self.assertRaises(ValueError): brain_router.route('')
 def test_work_graph_requires_evidence_for_completion(self):
  n=work_orchestrator.create_node('TASK','Close reconciliation',owner='BRAIN-BILLING',status='COMPLETED')
  self.assertTrue(any('evidence' in e for e in work_orchestrator.validate_graph([n])))
 def test_work_graph_verified_with_evidence(self):
  n=work_orchestrator.create_node('TASK','Close reconciliation',owner='BRAIN-BILLING',status='VERIFIED',evidence={'source':'INT-MB','record_id':'fixture-1'})
  self.assertEqual(work_orchestrator.validate_graph([n]),[])
 def test_unknown_owner_rejected(self):
  n=work_orchestrator.create_node('GOAL','Sales plan')
  self.assertTrue(work_orchestrator.validate_graph([n]))
if __name__=='__main__': unittest.main()
