# Interpretation and reproducibility matrix

| Question | Evidence | Status | Do not conclude |
|---|---|---|---|
| Is Formal40 original representation×query contrast mechanically reproducible? | 360 saved ranking rows and author silver parent IDs; +0.1443865063 | PASS saved-output recomputation | Not new retrieval nor independent gold |
| Could shared positive references influence the magnitude? | 669/780 overlapping topic pairs, 357 repeatedly used positive parents; top-frequency label removal | PASS descriptive sensitivity | Not formally independent statistical resampling |
| Is the reported topic-bootstrap p-value robust to cross-topic dependence? | Original paired bootstrap/sign-flip provenance and post-freeze overlap analysis | **OPEN** | No revalidated inferential CI or p supplied |
| Is the 2×2 contrast reproducible on a second, differently configured task? | 38 TREC judged topics, four original ranking runs, linear graded gain −0.001808469 | PASS different-protocol saved-output contrast | Not matched BCKB→TREC transfer |
| Does common saved-candidate filtering affect the reported overall interaction? | 250–838 common candidates per TREC topic, 1 G01 and 1 G11 top-ten list changed | PASS unchanged aggregate nDCG on archived ranks | Not prospective candidate-access fairness |
| Does a different graded-gain definition change interaction? | Exponential gain yields −0.000874635 | PASS magnitude sensitivity; sign preserved | Not same estimand as original nDCG |
| Can a single tool validate three saved-result source contracts? | Formal40 + TREC(38) + CLEF(31) JSONs, explicit reference/metric types and SHAs | PASS CPU-only validation tool | Not an implemented new clinical recommendation algorithm |
| Are independent medical relevance judgments or new question sets available? | No eligible, blinded gold relevance trial currently | **OPEN, requiring new independent evidence** | Do not call archived silver or trial-only labels clinician gold |
| Is the complete source corpus and full neural inference publicly reproducible? | Only derived numerical public capsule; upstream full texts/models restricted | **OPEN/rights-limited** | No full-system open reproduction |
| Is publication-ready, anonymous clinical safety validated? | Author decisions and targeted journal policies pending | **OPEN** | No patient-level claims or physician review |

The saved-score external analysis uses historical runs with official judgments accessible only in authorized research environments. Source file hashes in derived JSON are reproducibility references, not a grant of permission to republish third-party judged data.

**No inference from this release establishes clinical correctness, a universal improvement, an independent external validation of all four documentary roles, or a valid dependence-adjusted p-value.**
