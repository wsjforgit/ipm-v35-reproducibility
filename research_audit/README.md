# Evidence-retrieval saved-output audit and evaluation contract

This research-audit extension is **a bounded, author-derived, computational reproducibility supplement** to the existing frozen biomedical retrieval capsule. It provides three CPU-only programs in the Python standard library and **does not** claim a new neural retrieval model, full licensed corpus availability, independently judged clinical relevance or validated patient-safety decisions.

## What was evaluated

| Module | Inputs | Outputs | What this demonstrates | What it does not |
|---|---|---|---|---|
| E1: `formal_dependency_audit.py` | `formal_40/DOCUMENTARY_QRELS.json`, `FORMAL_RUNS.json` | Dependency topology, original +0.1443865 interaction, leave-category/topic-out and high-frequency-positive label-removal diagnostics | Saved-score parent-ranking arithmetic and sensitivity to overlapping study-created silver references | New independent gold, re-estimated p-values, or corrected bootstrap confidence intervals |
| E2: `external_saved_run_audit.py` | Legally obtained TREC trial qrels and the four **historical** x00/x01/x10/x11 run files | Official-qrel saved-score 2×2 interaction with alternative gains and candidate intersection sensitivity | A second evaluation context yields a negative interaction and no change in the reported aggregate when filtering the saved common candidates | Identical protocol across BCKB and TREC, new inference, prospective matched retrieval, or an independent four-source trial |
| E3: `contract_checker.py` | Author-derived Formal40 qrels and runs, `external_ip/PER_TOPIC_METRICS.json` | Schema, input fingerprints, complete-condition consistency, separate Formal/TREC/CLEF outcome matrix | Executable evaluation **contract** with explicit units, reference source and noncomparable metric boundaries | Full-text corpus release, neural inference, patient safety, or clinical validation |

## Run the public part on a cloned repository

Python 3.9+ and standard library only:

```bash
python3 -B research_audit/formal_dependency_audit.py \
  --qrels formal_40/DOCUMENTARY_QRELS.json \
  --runs formal_40/FORMAL_RUNS.json \
  --out /tmp/formal_dependency_sensitivity.json

python3 -B research_audit/contract_checker.py \
  --formal-qrels formal_40/DOCUMENTARY_QRELS.json \
  --formal-runs formal_40/FORMAL_RUNS.json \
  --external-metrics external_ip/PER_TOPIC_METRICS.json \
  --out /tmp/evaluation_contract_report.json

python3 -B -m unittest discover -s research_audit/tests -v
```

Use a **new output path** each time; scripts intentionally refuse to overwrite prior results. Test calls that run on a standalone copy without the capsule still work, but the integration test skips if `formal_40/` is absent.

### E2: official external qrels are intentionally not included

The external saved-run checker needs a properly authorized copy of the TREC clinical-trial task judgments and four historical saved runs:

```bash
python3 -B research_audit/external_saved_run_audit.py \
  --qrels /authorized_inputs/qrels_treceval_trials.txt \
  --g00 /authorized_inputs/trec_x00raw.run \
  --g01 /authorized_inputs/trec_x01rawq.run \
  --g10 /authorized_inputs/trec_x10field.run \
  --g11 /authorized_inputs/trec_x11fieldq.run \
  --out /tmp/trec_saved_four_factor_sensitivity.json
```

For 38 judged topics, the original **linear graded-gain nDCG@10** interaction is **−0.001808469058654727**. Replacing the gain convention with `2^rel - 1` changes the interaction magnitude to **−0.0008746345129868605** (same negative sign). Four saved top-1000 lists have a common intersection of **250–838** candidates per topic. Filtering that intersection changes the displayed top-ten ranked IDs on **one G01 and one G11 topic**, but leaves the **aggregate nDCG interaction unchanged** for both gain conventions. This is a **post-outcome saved-score sensitivity**, **not** proof the original models had identical candidate eligibility at inference time.

## E1 label dependence results (post-outcome, descriptive)

The 40 purposefully selected queries share source-derived positive parents:

- 669 of 780 unordered topic pairs share one or more positive parents;
- 486 unique registered positive parents; 357 reused across topics, max reused by 21 topics;
- overlap connectivity: one 40-topic connected component;
- original 2×2 parent nDCG@10 interaction: **+0.14438650633397873**;
- omit any one of the four study-defined categories: interaction remains positive, **+0.1063 to +0.1795**;
- after removing top 1, 5 and 10 most frequently reused **positive labels** from qrels (leaving ranked outputs frozen), interactions: **+0.1151, +0.1064, +0.1057**, respectively.

**Critical interpretation:** All these are retrospective descriptive robustness probes. Label removal changes the relevance reference itself. Connectivity indicates shared positive labels but does **not** prove a particular correlation value or that *all* prior p-values are mathematically false. Neither bootstrap exchangeability nor independent clinical generalizability is certified.

## E3 separate saved-metric scores

The TREC saved neural/fusion comparison (38 topics, nDCG@10) has mean `RRF_RAW_IP - MEDCPT_RAW_IP = +0.1273863`. The CLEF screening comparison (31 topics, NCG) has a mean difference of `−0.0440737`. These metrics and tasks are **not pooled** and the differences cannot be interpreted as a single broadly superior ranking algorithm.

## Provenance, ethical and software boundaries

- Outputs are computed from preserved, pre-existing ranked IDs and author-created derived references. Input filenames and SHA256 values are recorded in each generated JSON.
- Source code only relies on stdlib and synthetic tests. The new code does not launch neural training, query rewriting, model scoring, or a data-labeling exercise.
- No private clinical reports, full copyrighted guidance, proprietary label text, official external benchmark qrels, model checkpoints, private personal information, or third-party confidential reviews are uploaded in this extension.
- Original code is subject to the root `LICENSE`; eligible original derived summary data follow the root `DATA_LICENSE.md`. No license to upstream third-party documents is claimed.
- Publishing the extension in a non-default branch preserves the historical capsule `main`. Author/publisher anonymity, journal upload requirements, and public release linking must be checked before manuscript submission.

See `AUDIT_SCOPE.md` and `derived/` for frozen result JSON with exact SHA fingerprints.
