#!/usr/bin/env python3
"""Executable data-contract validation for biomedical retrieval *saved outputs*.

This public subset offers:
  * deterministic Formal-40 schema checking and ranking/relevance replay;
  * separate external TREC (nDCG@10) and CLEF (NCG) metric validation;
  * explicit input SHA-256s, scope limits and metric comparability gates;
  * machine-readable JSON report without exposing any licensed full-text corpus.

Does NOT build or run a medical model, create clinical gold or prove patient safety.
No third-party official qrels are read in this public-evidence CLI; the separate
optional external_saved_run_audit.py can be run with properly obtained official qrels.
Python 3.9+ stdlib.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import math
import pathlib
import statistics
from formal_dependency_audit import audit as formal_audit

SCHEMA_VERSION = "biomedical-retrieval-evaluation-contract-v1"
FORMAL_METHODS = {"G00", "G01", "G10", "G11", "BM25", "BGE", "MedCPT", "MedCPT_IP", "RRF"}
EXTERNAL_METHODS = {"MEDCPT_RAW_IP", "RRF_RAW_IP"}
EXTERNAL_METRIC = {"TREC": "ndcg10", "CLEF": "ncg"}
EXPECTED_EXTERNAL_TOPIC_COUNT = {"TREC": 38, "CLEF": 31}


def json_from_file(f: pathlib.Path):
    with f.open(encoding="utf-8") as fh:
        return json.load(fh)


def sha256(f: pathlib.Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def external_validate(records: list[dict]) -> dict:
    if not isinstance(records, list) or not records:
        raise ValueError("External evaluation must be a list of saved score rows")
    rows: dict[str, dict[str, dict[str, dict]]] = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in records:
        ds, topic, method = str(r.get("dataset")), str(r.get("topic_id")), str(r.get("method"))
        if ds not in EXTERNAL_METRIC or method not in EXTERNAL_METHODS:
            raise ValueError("Unexpected dataset or ranking method in saved external scores")
        if method in rows[ds][topic]:
            raise ValueError("Duplicated external dataset/topic/method")
        key = EXTERNAL_METRIC[ds]
        value = r.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("External score missing or nonfinite")
        if value < 0 or value > 1:
            raise ValueError("Invalid external metric range")
        rows[ds][topic][method] = dict(r)
    output = {}
    for ds, expected_topics in EXPECTED_EXTERNAL_TOPIC_COUNT.items():
        data = rows.get(ds, {})
        if len(data) != expected_topics:
            raise ValueError(f"Unexpected {ds} topic count")
        if any(set(pair) != EXTERNAL_METHODS for pair in data.values()):
            raise ValueError("Incomplete paired ranker comparison on external topic")
        metric = EXTERNAL_METRIC[ds]
        means = {m: statistics.mean(pair[m][metric] for pair in data.values())
                 for m in sorted(EXTERNAL_METHODS)}
        diffs = [pair["RRF_RAW_IP"][metric] - pair["MEDCPT_RAW_IP"][metric]
                 for pair in data.values()]
        output[ds] = {
            "topic_count": len(data),
            "metric": metric,
            "comparison_unit": "archived topic-local official benchmark scores",
            "methods": means,
            "RRF_minus_MedCPT": statistics.mean(diffs),
            "positive_diff_count": sum(d > 0 for d in diffs),
            "negative_diff_count": sum(d < 0 for d in diffs),
            "zero_diff_count": sum(d == 0 for d in diffs),
            "interpretation": "within-dataset saved rank outputs only; not comparable across TREC and CLEF reference designs",
        }
    return output


def contract(formal_qrels: list[dict], formal_runs: list[dict],
             external_records: list[dict], input_hashes: dict) -> dict:
    # Every Formal topic has exactly one ranking from the nine declared methods.
    by_topic = collections.defaultdict(set)
    for item in formal_runs:
        topic, method = str(item["topic_id"]), str(item["method"])
        if method not in FORMAL_METHODS or method in by_topic[topic]:
            raise ValueError("Invalid or duplicate Formal topic/method")
        by_topic[topic].add(method)
    ids = {str(q["topic_id"]) for q in formal_qrels}
    if len(ids) != 40 or set(by_topic) != ids or any(v != FORMAL_METHODS for v in by_topic.values()):
        raise ValueError("Formal contract does not have 40x9 complete unique rankings")
    dependency = formal_audit(formal_qrels, formal_runs)
    effect = dependency["original_saved_rank_evaluation"]["interaction"]
    if abs(effect - .14438650633397873) > 1e-9:
        raise ValueError("Frozen Formal interaction drift")
    external = external_validate(external_records)
    return {
        "schema": SCHEMA_VERSION,
        "inputs_sha256": input_hashes,
        "data_contract": {
            "Formal40": {"topics": 40, "saved_rankings": 360,
                         "judgment_source": "study-created field/alias silver reference",
                         "record_unit": "parent documentary evidence unit",
                         "metric": "binary parent nDCG@10",
                         "clinical_gold": False,
                         "independent_topic_sampling_assured": False},
            "TREC": {"topics": 38,
                     "judgment_source": "official TREC trial relevance labels (NOT distributed by this tool)",
                     "metric": "nDCG@10 saved external scores, two neural/fusion methods",
                     "matched_BCKB_replication": False},
            "CLEF": {"topics": 31,
                     "judgment_source": "official systematic review screening evaluation",
                     "metric": "topic NCG saved output, two methods",
                     "matched_BCKB_replication": False},
            "NLI4CT": {"included": False,
                       "reason": "Trial statement correctness is not a comparable relevance ranking metric"},
        },
        "formal_40_saved_metrics": {
            "condition_means": dependency["original_saved_rank_evaluation"]["condition_means"],
            "factorial_interaction": effect,
            "positive_topic_count": dependency["original_saved_rank_evaluation"]["topic_interaction_positive_count"],
            "negative_topic_count": dependency["original_saved_rank_evaluation"]["topic_interaction_negative_count"],
            "shared_positive_parent_topic_pairs": dependency["positive_reference_dependence"]["shared_positive_parent_pairs"],
            "connected_component_sizes": dependency["positive_reference_dependence"]["graph_component_sizes"],
        },
        "external_saved_metrics": external,
        "gates": {
            "formal_schema_complete": True,
            "formal_parent_rank_replay": True,
            "external_separate_dataset_scoring_only": True,
            "clinically_validated": False,
            "independent_gold_for_F40": False,
            "new_neural_inference": False,
            "full_corpus_reproduced": False,
            "topic_independent_significance_calibrated": False,
            "executable_evaluation_contract_only": True,
        },
        "limitations": [
            "Formal40 relevance labels overlap in source parents and are not independent clinician relevance ground truth.",
            "No comparison across unrelated datasets may be pooled without a matched label, candidate and metric protocol.",
            "The same data-contract validator can execute on saved result files, not reconstruct licensed biomedical source text.",
            "Existing model and saved-ranking results are immutable: this release does not claim a new neural ranking algorithm.",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--formal-qrels", type=pathlib.Path, required=True)
    ap.add_argument("--formal-runs", type=pathlib.Path, required=True)
    ap.add_argument("--external-metrics", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit("Refusing to overwrite frozen output " + str(args.out))
    paths = [args.formal_qrels, args.formal_runs, args.external_metrics]
    qrels, runs, metrics = (json_from_file(x) for x in paths)
    report = contract(qrels, runs, metrics, {x.name: sha256(x) for x in paths})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(args.out), "schema": report["schema"],
        "formal_effect": report["formal_40_saved_metrics"]["factorial_interaction"],
        "TREC_RRF_minus_MedCPT": report["external_saved_metrics"]["TREC"]["RRF_minus_MedCPT"],
        "CLEF_RRF_minus_MedCPT": report["external_saved_metrics"]["CLEF"]["RRF_minus_MedCPT"],
        "contract_pass": all(report["gates"][k] for k in ("formal_schema_complete", "formal_parent_rank_replay", "external_separate_dataset_scoring_only"))
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
