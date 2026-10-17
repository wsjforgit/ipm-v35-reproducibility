#!/usr/bin/env python3
"""Synthetic unit tests for author-created controlled evidence retrieval code.

These tests contain no third-party benchmark text, qrels or patient data.
No model training, no inference. Run: python3 -B -m unittest discover -s tests -v
"""
import importlib.util, pathlib, sys, unittest
BASE=pathlib.Path(__file__).resolve().parents[1]
def load(name,rel):
 path=BASE/rel
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec)
 sys.modules[name]=module
 spec.loader.exec_module(module)
 return module
m=load("cmpb_beir_exp","src/beir_lexical_four_arm.py")
s=load("cmpb_four_source","src/four_source_qrel_sensitivity.py")
class TestBM25DataContract(unittest.TestCase):
 def test_query_tokenizer(self):
  self.assertEqual(m.tokens("A trial and melanoma BRAF V600E"),["trial","melanoma","braf","v600e"])
  self.assertEqual(m.query_expr(["braf","trial"]),'"braf" OR "trial"')
 def test_max_original_query_tokens(self):
  long=" ".join("gene"+str(i) for i in range(80))
  self.assertEqual(len(m.tokens(long)),48)
 def test_query_marker_order(self):
  text="melanoma title evidence"
  orig=m.tokens(text)
  ext=list(dict.fromkeys(orig+["title","abstract"]))
  self.assertEqual(orig,["melanoma","title","evidence"])
  self.assertEqual(ext,["melanoma","title","evidence","abstract"])
 def test_ndcg_exact_ranking(self):
  q={"A":2,"B":1}
  self.assertAlmostEqual(m.dcg(q,["A","B"]),1.0)
  self.assertLess(m.dcg(q,["B","A"]),1.0)
 def test_empty_candidate_is_a_valid_zero_outcome(self):
  self.assertEqual(m.eval_rank({"A":2},[])["ndcg10_linear"],0.0)
  self.assertEqual(m.eval_rank({"A":2},[])["p10"],0.0)
  self.assertEqual(m.eval_rank({"A":2},[])["recall100"],0.0)
 def test_factorial_difference(self):
  x={"G00":{"ndcg10_linear":.1},"G01":{"ndcg10_linear":.2},
     "G10":{"ndcg10_linear":.3},"G11":{"ndcg10_linear":.5}}
  self.assertAlmostEqual(m.effect(x,"ndcg10_linear"),.1)
class TestSourceFamilies(unittest.TestCase):
 def test_four_source_id_prefixes(self):
  self.assertEqual(s.family("NCT01234567@2019:field"),"clinical_trial")
  self.assertEqual(s.family("drug_label::something"),"drug_label")
  self.assertEqual(s.family("PMC11145753::guidance"),"guidance")
  self.assertEqual(s.family("case_report::PMID:123"),"case_report")
 def test_no_guess_unknown_type(self):
  with self.assertRaises(ValueError):s.family("random-unmapped-source")
 def test_score_with_no_positives_not_a_score(self):
  self.assertIsNone(s.metric(["A"],set()))
 def test_source_specific_ndcg(self):
  self.assertAlmostEqual(s.metric(["A","B"],{"A","B"}),1.0)
if __name__=="__main__":unittest.main()
