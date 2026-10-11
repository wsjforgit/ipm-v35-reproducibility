# Formal-40 documentary retrieval reproduction

This subset contains author-generated documentary silver references, frozen ranking identifiers, derived numeric metrics and one standard-library evaluator supporting the Formal-40 mechanism study. It does not redistribute copyrighted medical full text, official benchmark qrels or model weights.

Reproduce the 40-topic documentary evaluation:

    python3 formal_40/reproduce_metrics.py

The command checks stored per-topic nDCG@10 values against frozen ranked parent IDs and reference sets, and recalculates the exploratory inverse-positive-parent-reuse-weighted factorial interaction. It does not rerun BM25 or neural retrieval, and cannot independently establish the accuracy of documentary silver references.

The 40 topics were deliberately coverage-enriched, not random clinical cases; multiple topics share positive parent evidence items. Reported statistical tests condition on declared design and resampling assumptions. The weighted interaction and category analyses are post-freeze diagnostics, not new sealed experiments. No independent physician review or patient-level safety validation is claimed. Details of earlier P11/P12 and full-source verification remain subject to rights and version restrictions.
