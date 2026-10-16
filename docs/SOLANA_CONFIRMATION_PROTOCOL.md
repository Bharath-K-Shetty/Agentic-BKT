# Calendar-period confirmation protocol

Specified locally on 9 October 2026 after the exploratory pilot, before executing
the confirmation evaluation. This is not a public preregistration.

Question: do the six observed wallet co-participation summaries improve collapse
prediction consistently, and do alert thresholds maintain their validation
false-positive budget in subsequent calendar periods?

Select 12,000 tokens from the same MELT source, excluding all 6,000 pilot sample
ranks. Selection is by SHA256(seed:mint), independent of outcomes. This is
confirmation on disjoint tokens, not an independent external dataset or a new
market cycle. Only eventual migrants are available.

Keep the pilot endpoint: `min_ratio < 0.3` during the 20 minutes after migration.
It measures collapse, not fraud intent. Features contain only transactions
through launch + 60 or + 300 seconds; already migrated tokens are ineligible.
Creation comes from an explicit mint event, not metadata's platform-account field.

Three expanding calendar folds, all boundaries UTC:

| Training before | Validation | Test |
|---|---|---|
| 1 January 2025 | 1–14 January | 15–31 January |
| 15 January 2025 | 15–31 January | 1–14 February |
| 1 February 2025 | 1–14 February | 15–28 February |

Training labels must mature before validation starts; validation labels must
mature before test starts. Maturation is migration + one hour, conservative for
the statistical endpoint. Test windows do not overlap within a horizon.
Earlier test outcomes may enter later training/validation once mature, matching
rolling deployment. Horizon eligibility differs, so this is not a matched
comparison of whether waiting longer helps.

Compare the same fixed logistic, random-forest and histogram-gradient-boosting
settings with versus without co-participation. Use three seeds for the tree
models and one deterministic logistic fit. Ensemble probabilities over seeds;
report seed variability. Neural architecture claims are outside this experiment;
the pilot MLP did not converge at its iteration limit.

Primary comparison: 300-second random forest, co-participation minus base average
precision, weighted by test count across the three periods. Use 500 paired
calendar-day bootstrap repetitions within each period. Estimates are conditional
on fitted models. Secondary model/horizon comparisons are exploratory.

Choose each fitted ensemble's threshold using validation only, under an empirical
5% FPR budget. Report test FPR and recall, AUROC, AP for both classes, and Brier
score. A test FPR above 5% is retained, rather than repaired using test outcomes.

Diagnostic: calculate the share of observed prefix wallets absent from labeled
training prefixes. Use median validation share to define the high/low novelty
subgroups, without test-label selection. This is wallet overlap, not new creators
or independent operators. Do not reconstruct ownership from mere co-participation.

Interpretation is fixed before results: an interval including zero does not
support a consistent gain. A positive interval is evidence on this historical
dataset, not automatically publication novelty. These 27 inputs do not exhaust
the richer coordination, motif or graph methods in prior work.

Sources: [MELT](https://arxiv.org/html/2602.13480v2),
[closest public prefix comparison](https://github.com/Gauravpoudel7/AI_RugPull_Prediction).
Neither author's performance is claimed to have been independently reproduced.
Exact settings and their hash are recorded in
[the machine-readable protocol](../research/solana/ml/robustness_protocol.json).

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/robustness.py
.venv/bin/python -m pytest tests/test_solana_prefix_baseline.py tests/test_solana_confirmation.py -q
```
