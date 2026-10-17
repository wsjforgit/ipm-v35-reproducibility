#!/usr/bin/env python3
"""Unittests for the public, standard-library-only saved-output evaluation contract."""
from __future__ import annotations
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import contract_checker as cc
import external_saved_run_audit as ea
import formal_dependency_audit as fa


class FormalTests(unittest.TestCase):
    def test_ndcg_identity(self):
        self.assertAlmostEqual(fa.ndcg10(["a", "b", "c"], {"a", "b"}), 1.0)
        self.assertAlmostEqual(fa.ndcg10(["c", "d"], {"a", "b"}), 0.0)
        self.assertIsNone(fa.ndcg10(["a"], set()))

    def test_correct_difference_in_differences(self):
        self.assertAlmostEqual(fa.delta({"G00": .1, "G01": .2, "G10": .3, "G11": .5}), .1)

    def test_qrel_topic_duplicates_rejected(self):
        row = {"topic_id": "1", "category": "X", "primary_parent_ids": ["P"]}
        with self.assertRaises(ValueError):
            fa.load_cases([row, row], [])

    def test_duplicate_rank_parent_rejected(self):
        q = [{"topic_id": "1", "category": "X", "primary_parent_ids": ["P"]}]
        runs = [{"topic_id": "1", "method": m, "parent_ids": ["P", "P"]} for m in fa.METHODS]
        with self.assertRaises(ValueError):
            fa.load_cases(q, runs)

    def test_connected_component_not_number_of_topics(self):
        s = [{"a", "b"}, {"b", "c"}, {"d"}]
        self.assertEqual(fa.connected_components(s), [2, 1])


class ExternalTests(unittest.TestCase):
    def test_linear_and_exponential_gain_differ(self):
        q = {"a": 2, "b": 1}
        n_linear = ea.dcg10(q, ["b", "a"], "linear")
        n_exp = ea.dcg10(q, ["b", "a"], "exp2")
        self.assertNotAlmostEqual(n_linear, n_exp)
        self.assertAlmostEqual(ea.dcg10(q, ["a", "b"], "linear"), 1.0)

    def test_common_pool_rank_order_stable(self):
        q = {"a": 1, "b": 0}
        runs = {
            "G00": {"1": ["a", "b"]}, "G01": {"1": ["b", "a"]},
            "G10": {"1": ["a", "b"]}, "G11": {"1": ["b", "a"]},
        }
        report = ea.analyze({"1": q}, runs, {})
        self.assertEqual(report["judged_topics"], 1)
        self.assertEqual(report["common_candidate_count_min_max_mean"][0], 2)
        self.assertEqual(report["original_top10_changed_by_posthoc_filter"], {m: 0 for m in ea.METHOD_TO_RUN})

    def test_run_duplicate_docs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "bad.run"
            f.write_text("1 Q0 A 1 1.0 label\n1 Q0 A 2 0.8 label\n")
            with self.assertRaises(ValueError):
                ea.run_load(f)


class ContractTests(unittest.TestCase):
    def test_external_dataset_missing_pair_rejected(self):
        with self.assertRaises(ValueError):
            cc.external_validate([{"dataset": "TREC", "topic_id": "1", "method": "RRF_RAW_IP", "ndcg10": .5}])

    def test_dataset_metric_not_mixed(self):
        with self.assertRaises(ValueError):
            cc.external_validate([{"dataset": "CLEF", "topic_id": "1", "method": "RRF_RAW_IP", "ndcg10": .5}])

    def test_known_input_capsule_if_repository_available(self):
        # Standard public cloned repository layout: research_audit/ next to formal_40/.
        repo = pathlib.Path(__file__).resolve().parents[2]
        q = repo / "formal_40" / "DOCUMENTARY_QRELS.json"
        runs = repo / "formal_40" / "FORMAL_RUNS.json"
        external = repo / "external_ip" / "PER_TOPIC_METRICS.json"
        if not all(x.is_file() for x in (q, runs, external)):
            self.skipTest("Full public capsule inputs not adjacent; standalone unit tests still work")
        report = cc.contract(cc.json_from_file(q), cc.json_from_file(runs),
                             cc.json_from_file(external), {})
        self.assertAlmostEqual(report["formal_40_saved_metrics"]["factorial_interaction"],
                               .14438650633397873)
        self.assertEqual(report["formal_40_saved_metrics"]["shared_positive_parent_topic_pairs"], 669)
        self.assertEqual(report["external_saved_metrics"]["TREC"]["topic_count"], 38)
        self.assertEqual(report["external_saved_metrics"]["CLEF"]["topic_count"], 31)
        self.assertFalse(report["gates"]["clinically_validated"])


if __name__ == "__main__":
    unittest.main()
