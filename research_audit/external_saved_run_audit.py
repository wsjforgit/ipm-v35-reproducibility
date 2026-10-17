#!/usr/bin/env python3
"""Read-only official-qrel TREC 2x2 saved-output sensitivity.

TREC evaluation here is an external, DIFFERENT protocol from Formal-40 and must NOT
be described as a matched cross-corpus replication. The common-set filter is a
post-outcome *diagnostic on saved ranked lists*, not a prospective equal-access
retrieval or a new model inference. No official qrels or run files are redistributed.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import math
import pathlib
import statistics

METHOD_TO_RUN = {"G00": "x00", "G01": "x01", "G10": "x10", "G11": "x11"}
SCHEMA = "biomedical-retrieval-external-saved-run-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qrel_load(path: pathlib.Path) -> dict[str, dict[str, int]]:
    judgements = collections.defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise ValueError("Expected official qrel four-field format")
        topic, _, doc, rel = fields
        if doc in judgements[topic] and judgements[topic][doc] != int(rel):
            raise ValueError("Inconsistent duplicated qrel")
        judgements[topic][doc] = int(rel)
    return dict(judgements)


def run_load(path: pathlib.Path) -> dict[str, list[str]]:
    rankings: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 6:
            raise ValueError("Expected TREC run format six fields")
        topic, _, doc, rank_s, score, _ = fields
        rank = int(rank_s)
        if not math.isfinite(float(score)):
            raise ValueError("Nonfinite TREC score")
        rankings[topic].append((rank, doc))
    result: dict[str, list[str]] = {}
    for topic, rows in rankings.items():
        rows.sort()
        docs = [doc for _, doc in rows][:1000]
        if len(docs) != len(set(docs)):
            raise ValueError("Duplicate document in TREC run")
        result[topic] = docs
    return result


def dcg10(qrels: dict[str, int], docs: list[str], gains: str = "linear") -> float:
    if gains not in ("linear", "exp2"):
        raise ValueError("Invalid gain family")
    fn = (lambda r: float(r)) if gains == "linear" else (lambda r: float(2**r - 1))
    dcg = sum(fn(max(0, qrels.get(doc, 0))) / math.log2(idx + 2)
              for idx, doc in enumerate(docs[:10]))
    top = sorted((fn(max(0, v)) for v in qrels.values()), reverse=True)[:10]
    ideal = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(top))
    return dcg / ideal if ideal > 0 else 0.0


def interaction(four: dict[str, float]) -> float:
    return (four["G11"] - four["G10"]) - (four["G01"] - four["G00"])


def mean(xs: list[float]) -> float:
    return statistics.mean(xs)


def analyze(qrels: dict, runs: dict[str, dict], source_hashes: dict) -> dict:
    topics = sorted(qrels, key=lambda x: int(x) if x.isdigit() else x)
    if not topics:
        raise ValueError("No judged topics")
    for name in METHOD_TO_RUN:
        if name not in runs or not set(topics).issubset(runs[name]):
            raise ValueError("Missing judged topic in method run " + name)
    samples = []
    candidate_size = []
    top10_change = {m: 0 for m in METHOD_TO_RUN}
    for topic in topics:
        ranked = {m: runs[m][topic] for m in METHOD_TO_RUN}
        eligible = set.intersection(*(set(v) for v in ranked.values()))
        candidate_size.append(len(eligible))
        if not eligible:
            raise ValueError("Empty saved common-eligibility candidate set")
        filtered = {m: [doc for doc in ids if doc in eligible] for m, ids in ranked.items()}
        for m in METHOD_TO_RUN:
            if ranked[m][:10] != filtered[m][:10]:
                top10_change[m] += 1
        metrics = {}
        for gain in ("linear", "exp2"):
            base = {m: dcg10(qrels[topic], ids, gain) for m, ids in ranked.items()}
            common = {m: dcg10(qrels[topic], ids, gain) for m, ids in filtered.items()}
            metrics[gain] = {
                "original": base,
                "saved_common_candidate_intersection": common,
                "factorial_original": interaction(base),
                "factorial_common_candidate": interaction(common),
            }
        samples.append({"topic_id": topic, "common_saved_candidate_count": len(eligible),
                        "metrics": metrics})
    means = {}
    for gain in ("linear", "exp2"):
        means[gain] = {}
        for variant in ("original", "saved_common_candidate_intersection"):
            mean4 = {m: mean([s["metrics"][gain][variant][m] for s in samples])
                     for m in METHOD_TO_RUN}
            means[gain][variant] = {
                "condition_means": mean4,
                "factorial_interaction": interaction(mean4),
                "positive_topic_delta_count": sum(
                    s["metrics"][gain]["factorial_" + ("original" if variant == "original" else "common_candidate")] > 0
                    for s in samples),
            }
    judged_pos = {topic: {doc for doc, rel in q.items() if rel > 0} for topic, q in qrels.items()}
    pairs_shared_pos = 0
    for i, t in enumerate(topics):
        for other in topics[i + 1:]:
            pairs_shared_pos += bool(judged_pos[t] & judged_pos[other])
    return {
        "schema": SCHEMA,
        "judged_topics": len(topics),
        "archived_run_extra_unjudged_topics": {
            m: len(set(run).difference(qrels)) for m, run in runs.items()
        },
        "common_candidate_count_min_max_mean": [
            min(candidate_size), max(candidate_size), mean(candidate_size)
        ],
        "original_top10_changed_by_posthoc_filter": top10_change,
        "qrel_positive_overlap_topic_pairs": pairs_shared_pos,
        "qrel_total_topic_pairs": len(topics) * (len(topics) - 1) // 2,
        "input_file_sha256": source_hashes,
        "means": means,
        "per_topic_derived_metrics": samples,
        "external_validity_status": "SAVED-TREC-COMMON-POOL-DIAGNOSTIC_NOT_MATCHED_BCKB_REPLICATION",
        "limits": [
            "Topic qrels are from the official TREC trial collection, a different task and reference design than Formal-40.",
            "Four ranked lists were saved before this experiment; no retrieval, query regeneration or model scoring is performed here.",
            "Posthoc candidate-set intersection retaining top10 does not establish a prospective equal-eligibility model comparison.",
            "Gain-function choice affects the interaction magnitude, so the evaluation convention must be declared explicitly.",
            "Original clinical-trial corpus and model inference cannot be inferred from derived saved scores.",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qrels", type=pathlib.Path, required=True)
    for method in METHOD_TO_RUN:
        ap.add_argument("--" + method.lower(), type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("Refusing overwrite: " + str(a.out))
    files = {m: getattr(a, m.lower()) for m in METHOD_TO_RUN}
    qrels = qrel_load(a.qrels)
    runs = {m: run_load(f) for m, f in files.items()}
    hashes = {a.qrels.name: sha(a.qrels)}
    hashes.update({f.name: sha(f) for f in files.values()})
    d = analyze(qrels, runs, hashes)
    if d["judged_topics"] == 38:
        observed = d["means"]["linear"]["original"]["factorial_interaction"]
        if abs(observed - (-.001808469058654727)) > 1e-10:
            raise ValueError("TREC archived linear-gain baseline drift")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(a.out), "judged_topics": d["judged_topics"],
                      "intersection": d["common_candidate_count_min_max_mean"],
                      "top10_changes": d["original_top10_changed_by_posthoc_filter"],
                      "linear_interaction": d["means"]["linear"]["original"]["factorial_interaction"],
                      "exp2_interaction": d["means"]["exp2"]["original"]["factorial_interaction"],
                      "shared_positive_topic_pairs": d["qrel_positive_overlap_topic_pairs"]}))


if __name__ == "__main__":
    main()
