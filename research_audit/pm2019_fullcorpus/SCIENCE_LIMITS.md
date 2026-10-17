# Scope and interpretation before CMPB paper integration

1. This is a real new full-corpus lexical run over the official May-2019 trial snapshot (306,238 trials; 40 queries; 38 judged topics). It is NOT new neural training and NOT the original BCKB four-source representation/query task.
2. The observed external within-task interaction is NEGATIVE, roughly -0.0075511 on linear-gain nDCG@10. The 2019 official qrels have appeared in older frozen analyses; do not call this an independent untouched blind prospective test.
3. A major non-degeneracy problem is documented: the two labelled-document arms G10/G11 produce IDENTICAL top-10 and top-100 NCT-ID ranks on all 40 official topics. Nearly ubiquitous literal labels condition and eligibility explain why this simplistic role prefix can fail to discriminate.
4. R0 vs R1 also alters FTS5 document length normalization and extra field-label terms, not only abstract medical roles. No causal inference about clinically appropriate source-state reasoning is warranted.
5. No newly valid confidence interval/p-value is calculated from these already exposed qrels. Original Formal40 confidence interval / sign-flip dependence remains unresolved (669/780 shared positive-parent topic pairs).
6. New external task judgments were made by the official TREC 2019 process on clinical trials, not by independent clinicians reviewing our BCKB four-source references.
7. The public code is a new runnable lexical baseline. Third-party raw trial XML and NIST qrels must be obtained separately and are not redistributed; unblinded published NCT run IDs are author-derived public evaluation output only.
8. If the target CMPB editorial standard requires broad transferable method gains or clinical validation, further independently sampled gold/matched multi-source evaluation must be designed. Do not simply adjust labels or models to get a positive sign.
