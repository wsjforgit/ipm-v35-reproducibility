# Independent biomedical retrieval controls and four-source silver-qrel sensitivity

This is an **author-owned, CPU-only evaluation extension**, frozen on 18 October 2026, based on a pre-registered protocol. It reports (i) two independently authored BEIR relevance benchmarks, and (ii) a retrospective source-family perturbation of the original Formal40 **silver** qrels. It does **not** establish matched external replication of breast-cancer four-source source-role inference, physician gold relevance, patient safety, or a universal improvement.

## Source and relevance labels

Official [BEIR dataset catalogue](https://github.com/beir-cellar/beir/wiki/Datasets-available): SciFact (5,183 scientific-document abstracts; 300 test queries) and NFCorpus (3,633 health/nutrition documents; 323 test queries). The two original BEIR test reference files were created by third-party benchmark authors, independent of the researcher's BCKB silver-reference rules.

Download official archives to a local folder **outside your cloned repository**:

- `https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip` — official MD5 `5f7d1de60b170fc8027bb7898e2efca1`
- `https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/nfcorpus.zip` — official MD5 `a89dba18a62ef92f7d323ec890a0d38d`

Original SciFact project distinguishes CC BY 4.0 claim/evidence annotations and ODC-By 1.0 abstracts, while downstream Hugging Face metadata lists a CC BY-NC variant; the *upstream source-specific terms should be checked by any reuser*. NFCorpus and its derivative obligations should likewise follow the actual original providers. **No corpus text, question texts, or test qrels are redistributed here.**

## Pre-registered lexical four-arm experiment

The SHA-pinned protocol was created **before downloading or opening the BEIR datasets**: `protocol/00_PREREGISTERED_BEIR_EXTERNAL_PROTOCOL.json`. Each test query is drawn from the official BEIR test split. No learning, hyperparameter selection or re-ranking with qrels occurs.

- **R0**: concatenate the original document title and body.
- **R1**: prefix the same title/body with literal `title` and `abstract` markers.
- **Q0**: fixed first 48 distinct lowercase ASCII [a-z0-9] non-stopword query tokens.
- **Q1**: same query tokens with fixed `title` and `abstract` tokens appended.
- **G00/G01/G10/G11**: cross-product of R0/R1 × Q0/Q1.

All four arms query the **same complete document set** with SQLite FTS5 BM25, `porter unicode61` tokenizer, fixed default weights, top-1000 ranking and `doc_id` tie-breaking.

Queries producing no matches are real zero-result retrieval outcomes and contribute **zero** to ranking metrics. The implementation initially rejected this legitimate case on NFCorpus; the error-handling correction was logged *without changing parameters or looking at NFCorpus effectiveness*, and the rankings were frozen. Its audit is `derived/zero_hit_edge_case_audit.json`.

## Results: do not confuse factorial interactions with absolute retrieval gains

| Corpus / test judgments | G00 nDCG@10 | G01 | G10 | G11 | 2×2 interaction | G11−G00 |
|---|---:|---:|---:|---:|---:|---:|
| SciFact, 300 claims | 0.686771 | 0.676415 | 0.686731 | 0.686731 | +0.010356 | −0.000040 |
| NFCorpus, 323 health queries | 0.322346 | 0.226078 | 0.322402 | 0.322901 | +0.096767 | +0.000555 |

**Critical interpretation:** Both interaction effects are positive, but absolute G11 gains over G00 are negligible. NFCorpus has **15 true no-hit queries** under each unmarked-query arm G00/G10, and zero no-hit queries under G01/G11. The generic added markers affect candidate matching, not clinical-role semantic understanding. These data are better understood as negative-control evidence for naive lexical marking and the need to separate interaction contrasts from end-point effectiveness. SciFact has 65/44,850 test-query pairs sharing positive documents; NFCorpus has 4,262/52,003. Source query and qrel dependence cannot be assumed absent.

Metrics are reported *separately* per task. No between-task averages, hypothesis-test p-values, causal explanations or medically safe recommendations are claimed.

## Independent software and numerical validation

- The entire SciFact and NFCorpus index, test retrieval, and scoring procedures were repeated on fresh local workdirs using the portable source. **Both saved rank files and both numerical evaluation files reproduced with identical SHA-256**.
- Locally built **NIST trec_eval** independently checked **7,386 scored topic × arm × metric cells** within four-decimal precision; another **90 legitimate empty ranking cells** were explicitly verified as zero, total **7,476**.
- NIST's program requires an actual run for a query; to handle empty-list queries *without fake documents*, its validation-only qrels were restricted to genuinely scored query IDs, and aggregate means restored by weighting the zero-result cases. **The original retrieval and official qrels were not modified.**
- There are **10 synthetic unit tests**, including four-source parent-prefix classification and correct handling of empty rankings.

The detailed numerical results and source hashes are under `derived/`. Source texts, test qrels, full rank files, temporary augmented validator qrels, and SQLite indices remain in a private local research directory.

## Reproduce on a legitimate local copy

Python 3.9+ standard library (no large neural model, no paid service). Store downloaded BEIR zip files under a separate **WORKDIR/private_data/**. Copy the SHA-pinned protocol into **WORKDIR/protocol/**:

```sh
WORKDIR=/your/private/beir_reproduction
mkdir -p "$WORKDIR/protocol" "$WORKDIR/private_data" "$WORKDIR/private_outputs"
cp research_audit/independent_biomedical/protocol/00_PREREGISTERED_BEIR_EXTERNAL_PROTOCOL.json "$WORKDIR/protocol/"
# Privately download scifact.zip and nfcorpus.zip into "$WORKDIR/private_data/".
export CMPB_BEIR_WORKDIR="$WORKDIR"
for DS in scifact nfcorpus; do
  python3 -B research_audit/independent_biomedical/src/beir_lexical_four_arm.py --dataset "$DS" --stage index
  python3 -B research_audit/independent_biomedical/src/beir_lexical_four_arm.py --dataset "$DS" --stage retrieve
  python3 -B research_audit/independent_biomedical/src/beir_lexical_four_arm.py --dataset "$DS" --stage score
done
python3 -B -m unittest discover -s research_audit/independent_biomedical/tests -v
```

All output and hash comparisons must use **new private paths**. The ranking stage refuses to overwrite its archived output. The test-query ID list comes from the official split; relevance *grades* are only used in the subsequent scoring stage.

## Original four-source silver reference family perturbations (separate analysis)

In the original BCKB selected 40 silver-reference topics, rank outputs were held frozen and the positive references associated with one documentary source role were removed or kept in turn. The original overall interaction was **+0.144387**. Removing **guidance** positives reduced it to **+0.050521**; removing trials to **+0.106965**; removing drug labels to **+0.150554**; removing case reports to **+0.150281**. This is *retrospective qrel-definition sensitivity*, not gold correctness, with changing numbers of scoreable topics in per-family-only results.

The script `src/four_source_qrel_sensitivity.py` runs against the already-public Formal40 **derived** qrel and rank files; it does not fetch or redistribute source medical texts.

## Where this leaves CMPB submission

**Useful:** an executable evaluation contract tested on TWO independently annotated biomedical/scientific retrieval tasks and a four-source source-reference construction stress test.

**Not established:** a matched external performance gain for the original BCKB four-source retrieval, reliable independent clinical grounding, validity of the Formal40 original topic-bootstrap CI/p-value under shared references, or patient safety.

The previously published real full-corpus 2019 TREC experiment remains a separate NEGATIVE comparison (−0.007551 nDCG interaction), not overridden by these BEIR results. Publisher SCIE/JCR Q1 and anonymization/code policy still need authoritative confirmation. Original V48 manuscript has **not** been silently updated or submitted.
