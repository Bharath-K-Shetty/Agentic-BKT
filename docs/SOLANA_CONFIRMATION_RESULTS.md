# Solana ML confirmation results

Executed confirmation of the first pilot, using a protocol specified locally before this run. The protocol followed pilot exploration; it is not a public preregistration.

Primary comparison: adding six same-transaction co-participation summaries to random forest at the 300-second horizon changes period-weighted average precision by **-0.0023**, with paired day-block 95% interval **[-0.0077, +0.0023]**.

This does not support a consistent improvement in the primary comparison.

Selected 12,000 new sample tokens, excluding the 6,000 pilot ranks. Verified pilot/confirmation token overlap: **0**. Both cohorts come from the same historical MELT release, not independent market cycles.

Target: price below 30% of migration price within 20 minutes after migration. Only eventual migrants are represented. This is collapse prediction, not proof of fraud.

## Calendar-period results

Predictions average three tree seeds (one deterministic logistic fit). Base has 21 prefix activity/holding features; coord adds six observed co-participation summaries. Each threshold is selected using validation labels only under a 5% FPR budget.

| Prefix | Test period | Model | Features | Test n | AP | AUROC | Recall | FPR | Brier |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 60s | January_late | random_forest | base | 4086 | 0.824 | 0.646 | 13.8% | 4.4% | 0.207 |
| 60s | January_late | random_forest | coord | 4086 | 0.826 | 0.649 | 13.7% | 4.2% | 0.208 |
| 60s | January_late | hist_gradient_boosting | base | 4086 | 0.819 | 0.640 | 13.5% | 4.6% | 0.212 |
| 60s | January_late | hist_gradient_boosting | coord | 4086 | 0.822 | 0.643 | 15.0% | 5.8% | 0.214 |
| 60s | January_late | logistic | base | 4086 | 0.817 | 0.637 | 13.8% | 6.3% | 0.206 |
| 60s | January_late | logistic | coord | 4086 | 0.826 | 0.651 | 16.8% | 5.7% | 0.203 |
| 60s | February_early | random_forest | base | 2120 | 0.783 | 0.628 | 10.0% | 3.3% | 0.219 |
| 60s | February_early | random_forest | coord | 2120 | 0.786 | 0.629 | 10.3% | 3.5% | 0.219 |
| 60s | February_early | hist_gradient_boosting | base | 2120 | 0.781 | 0.624 | 9.2% | 2.9% | 0.225 |
| 60s | February_early | hist_gradient_boosting | coord | 2120 | 0.784 | 0.626 | 10.4% | 2.7% | 0.224 |
| 60s | February_early | logistic | base | 2120 | 0.772 | 0.602 | 6.4% | 2.4% | 0.218 |
| 60s | February_early | logistic | coord | 2120 | 0.787 | 0.630 | 5.1% | 2.1% | 0.217 |
| 60s | February_late | random_forest | base | 1039 | 0.672 | 0.600 | 6.8% | 1.6% | 0.238 |
| 60s | February_late | random_forest | coord | 1039 | 0.666 | 0.595 | 6.0% | 2.1% | 0.239 |
| 60s | February_late | hist_gradient_boosting | base | 1039 | 0.686 | 0.604 | 9.3% | 3.0% | 0.239 |
| 60s | February_late | hist_gradient_boosting | coord | 1039 | 0.684 | 0.596 | 7.8% | 3.2% | 0.242 |
| 60s | February_late | logistic | base | 1039 | 0.624 | 0.535 | 5.1% | 4.1% | 0.251 |
| 60s | February_late | logistic | coord | 1039 | 0.635 | 0.557 | 7.8% | 3.9% | 0.249 |
| 300s | January_late | random_forest | base | 2128 | 0.750 | 0.598 | 10.3% | 4.8% | 0.238 |
| 300s | January_late | random_forest | coord | 2128 | 0.745 | 0.596 | 10.1% | 5.9% | 0.239 |
| 300s | January_late | hist_gradient_boosting | base | 2128 | 0.740 | 0.583 | 10.6% | 5.5% | 0.254 |
| 300s | January_late | hist_gradient_boosting | coord | 2128 | 0.734 | 0.577 | 13.6% | 8.5% | 0.257 |
| 300s | January_late | logistic | base | 2128 | 0.729 | 0.583 | 10.2% | 6.1% | 0.239 |
| 300s | January_late | logistic | coord | 2128 | 0.741 | 0.590 | 11.0% | 5.9% | 0.238 |
| 300s | February_early | random_forest | base | 1116 | 0.706 | 0.595 | 10.1% | 4.0% | 0.238 |
| 300s | February_early | random_forest | coord | 1116 | 0.705 | 0.595 | 8.9% | 4.0% | 0.238 |
| 300s | February_early | hist_gradient_boosting | base | 1116 | 0.692 | 0.573 | 12.1% | 6.4% | 0.249 |
| 300s | February_early | hist_gradient_boosting | coord | 1116 | 0.693 | 0.574 | 10.7% | 4.7% | 0.251 |
| 300s | February_early | logistic | base | 1116 | 0.694 | 0.579 | 9.2% | 4.3% | 0.239 |
| 300s | February_early | logistic | coord | 1116 | 0.693 | 0.574 | 8.4% | 3.6% | 0.241 |
| 300s | February_late | random_forest | base | 655 | 0.636 | 0.634 | 12.4% | 7.1% | 0.239 |
| 300s | February_late | random_forest | coord | 655 | 0.639 | 0.635 | 13.0% | 7.1% | 0.240 |
| 300s | February_late | hist_gradient_boosting | base | 655 | 0.635 | 0.616 | 13.9% | 6.1% | 0.249 |
| 300s | February_late | hist_gradient_boosting | coord | 655 | 0.637 | 0.613 | 13.9% | 6.1% | 0.249 |
| 300s | February_late | logistic | base | 655 | 0.600 | 0.565 | 14.7% | 7.1% | 0.252 |
| 300s | February_late | logistic | coord | 655 | 0.600 | 0.561 | 16.2% | 7.1% | 0.254 |

Chance AUROC is 0.5. Constant-score AP equals class prevalence. AUPRC/AP cannot be compared across periods without accounting for prevalence:

| Prefix | Test period | Train n | Validation n | Test n | Positive prevalence |
|---|---|---:|---:|---:|---:|
| 60s | January_late | 2530 | 2150 | 4086 | 73.1% |
| 60s | February_early | 4687 | 4065 | 2120 | 69.0% |
| 60s | February_late | 8764 | 2107 | 1039 | 58.0% |
| 300s | January_late | 1533 | 1171 | 2128 | 67.5% |
| 300s | February_early | 2710 | 2118 | 1116 | 62.2% |
| 300s | February_late | 4838 | 1108 | 655 | 52.8% |

## Threshold transfer and wallet overlap

Test FPR exceeds the nominal 5% budget in 15/36 model/period/horizon comparisons. In 1, the marginal 95% Wilson lower bound also exceeds 5%. These are exploratory diagnostics; intervals are not adjusted for multiple comparisons or correlated wallets. A point estimate above the budget alone is not proof of a systematic failure.

| Prefix | Test period | RF features | Higher novelty n | Higher novelty AUROC | Lower novelty n | Lower novelty AUROC |
|---|---|---|---:|---:|---:|---:|
| 60s | January_late | base | 3649 | 0.646 | 437 | 0.643 |
| 60s | January_late | coord | 3649 | 0.648 | 437 | 0.647 |
| 60s | February_early | base | 1740 | 0.632 | 380 | 0.611 |
| 60s | February_early | coord | 1740 | 0.632 | 380 | 0.614 |
| 60s | February_late | base | 862 | 0.609 | 177 | 0.548 |
| 60s | February_late | coord | 862 | 0.602 | 177 | 0.556 |
| 300s | January_late | base | 1976 | 0.599 | 152 | 0.584 |
| 300s | January_late | coord | 1976 | 0.593 | 152 | 0.622 |
| 300s | February_early | base | 942 | 0.612 | 174 | 0.507 |
| 300s | February_early | coord | 942 | 0.613 | 174 | 0.502 |
| 300s | February_late | base | 556 | 0.632 | 99 | 0.636 |
| 300s | February_late | coord | 556 | 0.632 | 99 | 0.646 |

Wallet novelty means absent from labeled training prefixes. The subgroup threshold is the median validation share, fixed without test outcomes. It does not prove previously unseen operators, and subgroup outcomes may differ in prevalence or token activity.

## What this adds, and what remains

This supplies a reproducible, token-disjoint confirmation across three expanding calendar folds with outcome-maturity purging, seed averaging, paired uncertainty and an explicit operating-point check. It does not introduce a new learning algorithm. Calendar evaluation, calibration and coordination are already present in prior research; a distinct publication contribution remains unestablished.

- Same historical MELT source period; token-disjoint confirmation is not an external dataset.
- Only eventual migrants; price collapse is not confirmed fraud.
- Wallet overlap diagnostic does not identify creators or operators.
- Different horizon cohorts; scores cannot quantify benefit of waiting.
- Bootstrap is conditional on fitted models; secondary comparisons are exploratory.
- Protocol specified after pilot exploration, not a public preregistration.
- These fixed models do not exhaust tuned 119-feature coordination or graph baselines.

The next decision is to test a narrowly scoped intervention against stronger coordination baselines and an independent data period. Increasing model complexity without demonstrating a specific benefit would not address these limitations.

[Protocol](SOLANA_CONFIRMATION_PROTOCOL.md) · [Detailed results](results/solana_confirmation.json) · [FPR diagnostics](results/solana_confirmation_diagnostics.json) · [Reproduction code](../research/solana/ml/robustness.py)

Data attribution: Hu et al., [MELT](https://arxiv.org/html/2602.13480v2), [author release](https://github.com/git-disl/MELT), CC BY-NC 4.0. Results are our own experiments; published benchmarks have not been independently reproduced.
