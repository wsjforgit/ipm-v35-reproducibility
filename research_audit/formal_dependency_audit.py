#!/usr/bin/env python3
"""Read-only dependency and ranking-sensitivity audit of an author's frozen Formal-40 capsule.

This code recomputes parent-unit nDCG@10 from the *already saved* ranking identifiers.
It does NOT rerun retrieval, generate labels, establish independent gold judgments, or
certify topic-bootstrap exchangeability. All perturbations are explicitly post-outcome,
descriptive and do not produce or overwrite inferential confidence intervals or p-values.
Only Python standard library is required.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib
import statistics
from typing import Any

METHODS = ("G00", "G01", "G10", "G11")
SCHEMA = "biomedical-retrieval-formal-audit-v1"


def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def file_sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ndcg10(parent_ranks: list[str], positives: set[str]) -> float | None:
    """Binary parent-level nDCG@10 with exact rank discount. No repeated hits."""
    if not positives:
        return None
    unique = list(dict.fromkeys(parent_ranks))
    dcg = sum(1.0 / math.log2(i + 2) for i, pid in enumerate(unique[:10]) if pid in positives)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(10, len(positives))))
    return dcg / ideal


def delta(scores: dict[str, float | None]) -> float | None:
    if any(scores.get(name) is None for name in METHODS):
        return None
    return (scores["G11"] - scores["G10"]) - (scores["G01"] - scores["G00"])


def load_cases(qrels: list[dict], runs: list[dict]) -> list[dict]:
    ids = [str(q["topic_id"]) for q in qrels]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Duplicate or absent topic IDs in qrels")
    looked: dict[str, dict[str, list[str]]] = collections.defaultdict(dict)
    for row in runs:
        tid = str(row["topic_id"])
        method = str(row["method"])
        parents = row["parent_ids"]
        if method in looked[tid]:
            raise ValueError("Duplicate topic/method ranking")
        if not isinstance(parents, list) or not all(isinstance(x, str) for x in parents):
            raise ValueError("Invalid ranked parent list")
        if len(parents) != len(set(parents)):
            raise ValueError("Ranked parent list contains duplicate parents")
        looked[tid][method] = parents
    cases = []
    for q in qrels:
        tid = str(q["topic_id"])
        if not isinstance(q.get("primary_parent_ids"), list):
            raise ValueError("Missing primary parent reference list")
        positives = set(q["primary_parent_ids"])
        if not positives:
            raise ValueError("Empty primary parent qrels")
        if not all(x in looked.get(tid, {}) for x in METHODS):
            raise ValueError(f"Incomplete four-condition rankings for topic {tid}")
        cases.append({"topic_id": tid, "category": str(q["category"]),
                      "positives": positives,
                      "ranks": {name: looked[tid][name] for name in METHODS}})
    return cases


def connected_components(sets: list[set[str]]) -> list[int]:
    parent = list(range(len(sets)))
    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(sets):
        for j in range(i + 1, len(sets)):
            if a & sets[j]:
                parent[find(i)] = find(j)
    sizes = collections.Counter(find(i) for i in range(len(sets)))
    return sorted(sizes.values(), reverse=True)


def mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def score_cases(cases: list[dict], remove: set[str] = frozenset()) -> list[dict]:
    result = []
    for x in cases:
        refs = x["positives"] - remove
        scores = {m: ndcg10(x["ranks"][m], refs) for m in METHODS}
        result.append({"topic_id": x["topic_id"], "category": x["category"],
                       "positive_count": len(refs), "scores": scores,
                       "interaction": delta(scores)})
    return result


def summarize(cases: list[dict], scored: list[dict]) -> dict:
    effect = [x["interaction"] for x in scored if x["interaction"] is not None]
    means = {m: mean([x["scores"][m] for x in scored if x["scores"][m] is not None]) for m in METHODS}
    cats = sorted(set(x["category"] for x in scored))
    leave_one_cat = {}
    for cat in cats:
        sample = [x["interaction"] for x in scored if x["category"] != cat and x["interaction"] is not None]
        leave_one_cat[cat] = {"topics": len(sample), "interaction": mean(sample)}
    loo = []
    for row in scored:
        xs = [x["interaction"] for x in scored if x["topic_id"] != row["topic_id"] and x["interaction"] is not None]
        loo.append({"topic_id": row["topic_id"], "interaction": mean(xs)})
    return {
        "topics_evaluated": len(effect), "non_scoreable_topics": len(cases) - len(effect),
        "condition_means": means, "interaction": mean(effect),
        "topic_interaction_positive_count": sum(x > 0 for x in effect),
        "topic_interaction_negative_count": sum(x < 0 for x in effect),
        "topic_interaction_zero_count": sum(x == 0 for x in effect),
        "topic_interaction_min_max": [min(effect), max(effect)] if effect else [],
        "leave_one_category_out": leave_one_cat, "leave_one_topic_out": loo,
    }


def audit(qrels: list[dict], runs: list[dict]) -> dict:
    cases = load_cases(qrels, runs)
    pos_sets = [x["positives"] for x in cases]
    positive_frequency = collections.Counter(pid for s in pos_sets for pid in s)
    n_pair = len(cases) * (len(cases) - 1) // 2
    shared = 0
    jaccard = []
    for a, b in itertools.combinations(pos_sets, 2):
        overlap = len(a & b)
        shared += bool(overlap)
        jaccard.append(overlap / len(a | b))
    baseline = score_cases(cases)
    base_stats = summarize(cases, baseline)
    ordered = [pid for pid, count in sorted(positive_frequency.items(), key=lambda p: (-p[1], p[0]))]
    # Post-hoc stress: REMOVE MOST-REUSED PARENT LABELS FROM THE REFERENCE SETS ONLY.
    # This changes relevance judgments and is NOT an independent or causal experiment.
    removal_sensitivity = {}
    for k in (1, 5, 10):
        removed = set(ordered[:k])
        stats = summarize(cases, score_cases(cases, removed))
        removal_sensitivity[str(k)] = {
            "reference_parent_ids_removed": k, "topics_remaining": stats["topics_evaluated"],
            "interaction": stats["interaction"],
            "definition": "post-outcome top-K frequency qrel-label deletion; candidate rankings held frozen",
        }
    return {
        "schema": SCHEMA,
        "topic_count": len(cases),
        "runs_count": len(runs),
        "methods": list(METHODS),
        "evaluation_unit": "selected documentary topic; original silver primary parent references",
        "positive_reference_dependence": {
            "topic_pairs": n_pair, "shared_positive_parent_pairs": shared,
            "shared_pair_fraction": shared / n_pair,
            "unique_positive_parent_ids": len(positive_frequency),
            "reused_parent_ids": sum(c > 1 for c in positive_frequency.values()),
            "max_topic_frequency_of_one_parent": max(positive_frequency.values()),
            "graph_component_sizes": connected_components(pos_sets),
            "positive_set_min_max": [min(map(len, pos_sets)), max(map(len, pos_sets))],
            "pairwise_jaccard_mean": statistics.mean(jaccard),
            "pairwise_jaccard_median": statistics.median(jaccard),
        },
        "original_saved_rank_evaluation": base_stats,
        "posthoc_reference_removal_sensitivity": removal_sensitivity,
        "per_topic_frozen_scores": baseline,
        "inferential_limits": [
            "The shared-positive-parent graph is connected but this alone does not establish a formal correlation model.",
            "No confidence interval or significance test is recomputed or independently validated here.",
            "LOCO, LOTO and top-frequency qrel deletion are post-outcome descriptive diagnostics only.",
            "References are author-created silver qrels and are not independent physician relevance gold.",
            "No new neural retrieval, data annotation or clinical validation occurs in this audit.",
        ],
    }


def main() -> None:
    pa = argparse.ArgumentParser()
    pa.add_argument("--qrels", type=pathlib.Path, required=True)
    pa.add_argument("--runs", type=pathlib.Path, required=True)
    pa.add_argument("--out", type=pathlib.Path, required=True)
    a = pa.parse_args()
    if a.out.exists():
        raise SystemExit("Refusing to overwrite prior frozen result: " + str(a.out))
    qs, runs = read_json(a.qrels), read_json(a.runs)
    result = audit(qs, runs)
    result["inputs"] = {
        "qrels_filename": a.qrels.name, "qrels_sha256": file_sha(a.qrels),
        "runs_filename": a.runs.name, "runs_sha256": file_sha(a.runs),
    }
    if result["topic_count"] == 40:
        # This is a provenance and shape gate, not a way to edit a score to match expectations.
        if abs(result["original_saved_rank_evaluation"]["interaction"] - .14438650633397873) > 1e-9:
            raise ValueError("Formal40 baseline drift; do not publish without investigation")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(a.out), "topics": result["topic_count"],
        "overlap_pairs": result["positive_reference_dependence"]["shared_positive_parent_pairs"],
        "baseline_interaction": result["original_saved_rank_evaluation"]["interaction"],
        "LOCO": {k: round(v["interaction"], 6) for k, v in result["original_saved_rank_evaluation"]["leave_one_category_out"].items()},
        "stress_top_frequency": {k: round(v["interaction"], 6) if v["interaction"] is not None else None for k, v in result["posthoc_reference_removal_sensitivity"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
