# First Solana transaction-prefix ML experiment

This is an executed feasibility baseline, not a publication-ready contribution.

Target: min_ratio < 0.3 within 20 minutes after migration; price-collapse proxy, not confirmed fraud.

Data: Hu et al., [MELT](https://arxiv.org/html/2602.13480v2), [author release](https://github.com/git-disl/MELT), CC BY-NC 4.0. Source and derived-file hashes are in the machine-readable report.

Sampled 6,000 tokens by address hash without using labels from 41,470 joinable released tokens. Only eventual migrants are represented.

Models use prefix transactions only. Chronological decisions define train, validation and test; migration + one hour defines outcome maturity. All training/validation outcomes must mature before the next partition starts. Calendar/migration times and label-source fields are not inputs.

## 60-second prefix

- train: 3,574 tokens; positive prevalence 67.3%.
- validation: 1,180 tokens; positive prevalence 71.9%.
- test: 1,194 tokens; positive prevalence 66.3%.
- Boundary label-maturity exclusions: 20.

| Model | Features | Test AUROC | AP positive | AP negative | Recall | Test FPR |
|---|---|---:|---:|---:|---:|---:|
| logistic | activity_holdings | 0.588 | 0.746 | 0.378 | 13.0% | 3.7% |
| random_forest | activity_holdings | 0.635 | 0.774 | 0.471 | 6.9% | 2.7% |
| hist_gradient_boosting | activity_holdings | 0.620 | 0.758 | 0.444 | 9.0% | 4.2% |
| mlp | activity_holdings | 0.600 | 0.749 | 0.419 | 12.0% | 4.7% |
| logistic | plus_coparticipation | 0.605 | 0.755 | 0.411 | 18.7% | 6.2% |
| random_forest | plus_coparticipation | 0.634 | 0.766 | 0.475 | 7.1% | 3.2% |
| hist_gradient_boosting | plus_coparticipation | 0.620 | 0.761 | 0.446 | 9.6% | 4.7% |
| mlp | plus_coparticipation | 0.620 | 0.756 | 0.429 | 12.2% | 4.5% |

Highest validation AUROC: random_forest with activity_holdings. Its test AUROC is 0.635; selection used validation, not test.

Thresholds were chosen separately using a 5% validation FPR budget; test FPR is reported without adjusting thresholds to test labels. Constant-score AUROC is 0.5; its AP equals test class prevalence.

Co-participation ablation, added minus base test AUROC:

- logistic: +0.0165; paired day-block 95% interval [+0.0045, +0.0327].
- random_forest: -0.0011; paired day-block 95% interval [-0.0117, +0.0099].
- hist_gradient_boosting: +0.0002; paired day-block 95% interval [-0.0149, +0.0162].
- mlp: +0.0202; paired day-block 95% interval [+0.0007, +0.0382].

Fit limitations:

- mlp, activity_holdings: Stochastic Optimizer: Maximum iterations (150) reached and the optimization hasn't converged yet.
- mlp, plus_coparticipation: Stochastic Optimizer: Maximum iterations (150) reached and the optimization hasn't converged yet.

## 300-second prefix

- train: 1,982 tokens; positive prevalence 58.8%.
- validation: 655 tokens; positive prevalence 65.2%.
- test: 663 tokens; positive prevalence 59.9%.
- Boundary label-maturity exclusions: 15.

| Model | Features | Test AUROC | AP positive | AP negative | Recall | Test FPR |
|---|---|---:|---:|---:|---:|---:|
| logistic | activity_holdings | 0.560 | 0.640 | 0.448 | 11.3% | 9.4% |
| random_forest | activity_holdings | 0.658 | 0.745 | 0.509 | 10.3% | 2.3% |
| hist_gradient_boosting | activity_holdings | 0.616 | 0.697 | 0.480 | 8.1% | 3.4% |
| mlp | activity_holdings | 0.602 | 0.685 | 0.491 | 10.3% | 4.5% |
| logistic | plus_coparticipation | 0.569 | 0.656 | 0.433 | 11.3% | 6.8% |
| random_forest | plus_coparticipation | 0.663 | 0.749 | 0.517 | 8.8% | 1.5% |
| hist_gradient_boosting | plus_coparticipation | 0.636 | 0.720 | 0.489 | 7.1% | 2.6% |
| mlp | plus_coparticipation | 0.606 | 0.689 | 0.488 | 14.4% | 8.3% |

Highest validation AUROC: mlp with plus_coparticipation. Its test AUROC is 0.606; selection used validation, not test.

Thresholds were chosen separately using a 5% validation FPR budget; test FPR is reported without adjusting thresholds to test labels. Constant-score AUROC is 0.5; its AP equals test class prevalence.

Co-participation ablation, added minus base test AUROC:

- logistic: +0.0088; paired day-block 95% interval [-0.0086, +0.0282].
- random_forest: +0.0051; paired day-block 95% interval [-0.0134, +0.0168].
- hist_gradient_boosting: +0.0196; paired day-block 95% interval [-0.0086, +0.0426].
- mlp: +0.0046; paired day-block 95% interval [-0.0286, +0.0387].

Fit limitations:

- mlp, activity_holdings: Stochastic Optimizer: Maximum iterations (150) reached and the optimization hasn't converged yet.
- mlp, plus_coparticipation: Stochastic Optimizer: Maximum iterations (150) reached and the optimization hasn't converged yet.

## Limits and next decision

- Single training seed and exploratory sample; not publication evidence.
- Only eventual migrants; no all-launch deployment claim.
- No true operator identities or operator-disjoint evaluation.
- Co-participation is not evidence of common wallet ownership.
- No graph neural model, external replication, or first-harm-time evaluation.
- Labels and parsed transaction correctness inherited from MELT, not independently verified.

Price-collapse prediction has potential practical use as one risk signal, but these results do not establish profitability, fraud detection or general deployment reliability. Fixed-prefix models and wallet coordination already overlap prior work; this pilot adds evidence of feasibility, not evidence of novelty.

The next research gate is a prespecified experiment on additional periods and stronger coordination baselines, followed by a distinct method only if it addresses a demonstrated failure. True operator holdouts require defensible identities. A graph architecture alone does not satisfy that requirement.

Reproduction and exact controls: [experiment README](../research/solana/ml/README.md). Detailed metrics: [JSON report](results/solana_prefix_baseline.json).
