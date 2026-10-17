# TREC Precision Medicine 2019 — new full-corpus four-arm lexical experiment

**Author-derived negative-control evidence, frozen 18 Oct 2026.** In contrast to earlier saved-score audits, this extension creates a NEW SQLite FTS5 index over all **306,238** trial records in the original May 2019 TREC Precision Medicine XML snapshot, scores all **40** official topics under four predeclared configurations, and evaluates the **38 judged** topics using official NIST relevance judgments.

**Critical scope:** This is a trial-only benchmark, not a matched external replication of the four-source BCKB source-role mechanism, nor an untouched blinded study. The authors previously accessed the 2019 qrels in historical analyses. No new trained neural ranker or clinical safety assessment was created.

## Official upstream input data (NOT bundled here)

- Original 2019 four tar.gz snapshots: https://www.trec-cds.org/2019.html
- Official 2019 topics and trial qrels: https://trec.nist.gov/data/precmed2019.html
- Exact source file SHA-256 hashes: protocol/00_FROZEN_FULL2019_EXPERIMENT_PROTOCOL.json

Do not substitute the 2021 TREC Clinical Trials collection or current ClinicalTrials.gov records. The original XML texts and official judged labels stay OUTSIDE this public repository, under their respective upstream terms.

## Execution protocol (Python 3.9+, SQLite FTS5, CPU)

From a cloned repository root, with source archives, topics and qrels in a separately authorized local directory:

    EXTERNAL=/authorized/pm2019
    OUT=/local/tmp/pm2019
    python3 -B research_audit/pm2019_fullcorpus/protocol/01_ingest_2019_snapshot.py --corpus-dir "$EXTERNAL/archives" --output-dir "$OUT/index"
    python3 -B research_audit/pm2019_fullcorpus/protocol/02_retrieve_sqlite_fts5.py --sqlite "$OUT/index/official_2019_snapshot_full_fts.sqlite" --topics "$EXTERNAL/topics2019.xml" --topic-limit 40 --output "$OUT/all40_runs.json"
    python3 -B research_audit/pm2019_fullcorpus/protocol/03_evaluate_new_retrieval.py --retrieval-json "$OUT/all40_runs.json" --qrels "$EXTERNAL/qrels-treceval-trials.38.txt" --output "$OUT/judged38.json"
    python3 -B -m unittest discover -s research_audit/pm2019_fullcorpus/tests -v

Outputs intentionally refuse silent overwrite. This repository includes four gzip-compressed, author-generated ranked NCT-ID files in runs/, the per-topic derived numeric results, source hashes, and synthetic tests. It does not include official qrels or raw trial descriptions. Decompress run files and use NIST trec_eval -q -m ndcg_cut.10 -m P.10 -m recall.100 for independent checking. A separate local build of usnistgov/trec_eval commit 35cf096ba6d5ae08ca4803c056b31ed61a56a6d4 agreed with our scorer in all **456 topic-by-arm metric comparisons** to four-decimal rounding tolerance.

## Pre-specified 2×2 trial-only retrieval

All four arms use exactly the same 306,238 source trials, same SQLite FTS5 porter/unicode61 tokenizer and default BM25 parameters, top-1000 output per topic, deterministic NCT tie-breaking.

- G00 = concatenated unlabelled trial text + flat disease/gene/demographic query
- G01 = concatenated unlabelled trial text + fixed condition/eligibility-labelled query
- G10 = the same text fields plus literal labels + flat query
- G11 = labelled text + labelled query

These literal lexical prefixes are NOT proof of semantic role-aware clinical reasoning. The source snapshot/official topics/stopword list/field construction/metrics were recorded before the new rank run; scientific qrels have been accessible to this project previously.

## Results (no positive general-effect claim)

Mean linear-gain nDCG@10 on 38 TREC-judged topics:

- G00 = 0.5494761815
- G01 = 0.5570272526
- G10 = 0.5492887332
- G11 = 0.5492887332

The interaction (G11-G10)-(G01-G00) is **−0.0075510711**. This is a newly executed negative external lexical comparison, NOT evidence that BCKB source-role effects transfer positively. Secondary graded gain metrics are in derived/new_FTS5_evaluation_38_judged.json. No new independent significance or clinical performance claim is made.

The labels condition and eligibility appear in 305,427 and 305,362 labelled-index documents, respectively (out of 306,238), making them nearly ubiquitous. Therefore, **G10 and G11 yield identical top-10 and top-100 rankings for all 40 topics**. This is a diagnosed limitation of naive field-label serialization; it is NOT successful role-aware reranking. Index source words are otherwise the same; field labels and BM25 document-length normalization introduce additional effects that prevent simplistic causal attribution.

## Scientific limitations and publication scope

Official 2019 trial relevance qrels are independent of the original BCKB study-created SILVER labels but they address a DIFFERENT trial-only task. This experiment cannot independently validate four-source documentary evidence correctness or patient-level clinical safety. Positive overlaps in the BCKB 40 topics remain and original topic-bootstrap inference is not dependence-recalibrated. Query serialization/parameter choices in this study are newly executed but the historical official judgments are not a pristine untouched test set.

The release includes only author-written source, synthetic tests, input fingerprints, author-derived NCT rankings and aggregate/per-topic scores. Publicly available trial IDs are not the corresponding source texts. All third-party content, NIST labels, full corpus and neuro-model data remain with their upstream owners and licenses. Public repository attribution versus future journal blind-review policies must be checked before citation in a manuscript.

## Independent clean-checkout replay of the new full-corpus retrieval

The original full-corpus FTS5 index and frozen Python script were rerun in a separate clean Git checkout. All 160,000 newly computed rank/float-score rows matched exactly (fingerprint 13e33b1a9befd9eb39a299ae70252d090b58d7ff2c358f7628a86d274a90ad77). The JSON files differ only in runtime timing fields, which are not part of the scientific scores. All 38 per-topic metric records also agreed. See derived/CLEAN_CHECKOUT_REPRODUCIBILITY.json. This is independent software re-execution on the same corpus snapshot, not a blind independent clinical study.
