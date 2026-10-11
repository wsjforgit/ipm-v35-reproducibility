# Anonymous research-derived data and deterministic replay (local pre-publication draft)

This data capsule accompanies a double-anonymized submission on structured multisource biomedical evidence retrieval.

Included materials: numeric run scores/rank inputs from frozen E19 (clinical-trial retrieval) and CLEF (systematic-review screening) runs, numeric evaluation summaries, NLI4CT aggregate/replay summaries, aggregate relation diagnostics, and standalone replay scripts.

It intentionally does NOT contain any third-party full-text articles, medical advice, patient records, independently licensed TREC/CLEF qrels, benchmark claims/premises, model weights, raw source snapshots, private chat logs, usernames, identities, or alleged expert reviews.

## Reproduce saved-output arithmetic

With Python 3.9+ installed:

    python3 replay_external_scores.py --dataset e19
    python3 replay_external_scores.py --dataset eclef
    python3 verify_capsule_baselines.py

All scripts operate on already-saved rank scores/metadata and do not download or re-run neural inference. The first two scripts rewrite derived NUMERICAL_REPLAY.json in the working directory. Run on a copy if preserving the published checksums.

For original benchmark qrels, corpora, and official evaluators, obtain separately from upstream organizers:
- TREC Precision Medicine 2019: https://trec.nist.gov/data/precmed2019.html
- CLEF TAR organizer: https://github.com/CLEF-TAR/tar
- NLI4CT official materials: obtain under the upstream data terms.

Reported scores and run identifiers are evaluation outputs, not patient-level eligibility/safety judgments. Development annotations may have been AI assisted; no independent clinician evaluation is claimed.

### Scope and limitations

This is a partial, saved-output numerical replay capsule. It demonstrates arithmetical consistency of released run scores, relative ranking/fusion, and reported summary measures. Full raw-corpus retrieval/neural training/inference and re-grading from official restricted qrels require lawful separate upstream inputs and checkpoints; those are not included.

Method-level differences in candidate pool and reranking configuration remain material. No new sealed-test claim is made. Publication license and permanent location must be recorded at release.

## Licensing and peer-review anonymity

- Original code: MIT License (see LICENSE).
- Original numeric/derived data: Creative Commons Attribution 4.0 International (see DATA_LICENSE.md).
- Anonymous contributor attribution applies until editorial review is complete.
- Reviewers should use only the anonymous repository mirror link in the submission. Do not cite the identifying GitHub owner URL in an anonymous manuscript.

The released outputs are deterministic saved-output replay artifacts, not a full rebuild of the underlying biomedical corpus. The upstream datasets/organizer judgments must be acquired under their original terms.

## Large numerical run file

The CLEF numerical output is stored as external_ip/eclef/RUNS.json.gz to stay within anonymous review mirror file-size limits. The replay script transparently decompresses it. COMPRESSED_INPUT_PROVENANCE.json records the exact SHA-256 of the original uncompressed byte sequence; no ranks or scores were changed.
