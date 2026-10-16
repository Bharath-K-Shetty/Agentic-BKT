# Delayed-outcome Solana warning experiment

Selected 8,000 tokens at hash ranks 28,000–35,999 before evaluation; 4,295 have usable five-minute prefixes before migration. No overlap with earlier token cohorts. Test windows reuse the same historical calendar periods; this is not a new market period.

**Question:** does outcome-dependent label maturity bias online warning calibration, and does a simple observation-delay correction improve the warning tradeoff?

A fixed RF with 120 prefix features is trained on the previous cohort, with its previous validation-selected parameters and three-seed average. No model or replay setting is tuned on the new test outcomes. Labels enter the prospective replay only at migration + one hour. This is a conservative assumed operational schedule, not a verified publication timestamp. The target is released 20-minute price-collapse min_ratio < 0.3, not verified fraud.

## Primary result

Recall change versus the identical unweighted recent pool: **+0.77 percentage points (95% paired day-block interval +0.26 to +1.32)**.

False-positive-rate change: **+0.26 percentage points (95% paired day-block interval +0.00 to +0.67)**.

**Prespecified success gate: not passed.** The correction is not established as a useful new method. Do not rename this result as algorithmic novelty.

The success gate requires the recall interval above zero, no FPR increase by its interval, and observed candidate FPR at or below 5% in each period. Secondary controls are exploratory. Intervals condition on fitted models and do not account for shared wallet operators.

## Operating results

| Period | Method | Recall | FPR | Alerts | Static fallback |
|---|---|---:|---:|---:|---:|
| January_late (n=1363) | frozen_empirical | 9.58% | 4.12% | 7.92% | 0.0% |
| January_late (n=1363) | static_negative_tail | 7.79% | 3.15% | 6.38% | 0.0% |
| January_late (n=1363) | recent_negative_tail | 8.95% | 3.63% | 7.34% | 0.0% |
| January_late (n=1363) | arrival_negative_tail | 10.63% | 4.60% | 8.80% | 0.0% |
| January_late (n=1363) | buffered_negative_tail | 10.32% | 4.84% | 8.66% | 0.0% |
| January_late (n=1363) | delay_weighted_tail | 9.89% | 4.12% | 8.14% | 0.0% |
| January_late (n=1363) | oracle_immediate_tail | 9.79% | 3.63% | 7.92% | 0.0% |
| February_early (n=711) | frozen_empirical | 8.26% | 6.77% | 7.74% | 0.0% |
| February_early (n=711) | static_negative_tail | 8.26% | 6.77% | 7.74% | 0.0% |
| February_early (n=711) | recent_negative_tail | 3.26% | 5.18% | 3.94% | 3.7% |
| February_early (n=711) | arrival_negative_tail | 6.96% | 5.98% | 6.61% | 0.0% |
| February_early (n=711) | buffered_negative_tail | 5.43% | 4.38% | 5.06% | 0.3% |
| February_early (n=711) | delay_weighted_tail | 4.13% | 5.18% | 4.50% | 3.7% |
| February_early (n=711) | oracle_immediate_tail | 5.00% | 5.58% | 5.20% | 0.6% |
| February_late (n=422) | frozen_empirical | 5.85% | 3.23% | 4.50% | 0.0% |
| February_late (n=422) | static_negative_tail | 5.85% | 2.76% | 4.27% | 0.0% |
| February_late (n=422) | recent_negative_tail | 8.78% | 2.76% | 5.69% | 1.2% |
| February_late (n=422) | arrival_negative_tail | 6.34% | 3.69% | 4.98% | 0.0% |
| February_late (n=422) | buffered_negative_tail | 7.32% | 1.84% | 4.50% | 0.0% |
| February_late (n=422) | delay_weighted_tail | 8.78% | 2.76% | 5.69% | 1.2% |
| February_late (n=422) | oracle_immediate_tail | 8.78% | 2.76% | 5.69% | 0.7% |

All methods use identical model scores, so calibration does not improve their AUROC or AP. Recent and weighted pools use 48 hours of decision history; fewer than 20 available negatives trigger the static negative-tail fallback. The arrival-order control uses the last 128 revealed negatives. The buffer control uses a 48-hour cohort ending 36 hours earlier. The oracle uses past-decision labels before maturity and is **invalid for deployment**; it does not use the current token or labels from simultaneous decisions.

The weighted correction estimates delay CDFs in three model-score bins from older validation negatives, uses smoothed inverse observation probabilities clipped at 10, and adds unit pseudo-observation mass to the upper tail. This is an experimental weighting heuristic, not a proved conformal procedure. Weighting also changes the relative pseudo-observation mass; any benefit cannot be attributed solely to correcting selection without a mass-matched control. That control was not part of this locally fixed experiment. Static negative-tail validity requires exchangeability, which calendar drift can violate. The 36-hour buffer is audited on this data, not a universal upper bound on future label delay.

## Outcome-dependent maturity

| Outcome | n | Median assumed delay | Available by 6h | Available by 24h | Delay >36h |
|---|---:|---:|---:|---:|---:|
| Non-collapse | 1680 | 1.64h | 84.0% | 99.6% | 0 |
| Collapse | 2615 | 1.21h | 92.4% | 99.7% | 0 |

These diagnostics include all eligible new tokens, including decisions outside the evaluated calendar test windows. They describe this selected eventual-migrant archive. Tokens that never migrate are absent, so this cannot establish all-launch deployment performance or a general delay distribution.

## Relationship to prior work

[Delayed ACI (September 2026)](https://arxiv.org/abs/2609.07251) analyzes adaptive conformal updates with fixed forecast delay and dependence. [HAPS (May 2026)](https://arxiv.org/abs/2605.06581) already uses inverse censoring weights and time-varying histories for event-time prediction. [Delayed-feedback label correction (2023)](https://arxiv.org/abs/2307.12756) already addresses delayed conversion observations. Our implementation is not an exact reproduction of these algorithms. [Causal Label Recovery in Payment Networks (May 2026)](https://arxiv.org/abs/2605.29272) also studies biased financial labels and the tradeoff between label maturity and model freshness (abstract reviewed here; theory not independently verified). Applying established weighting ideas to irregular token outcomes alone is not a novel algorithm.

A possible empirical contribution is a reproducible evaluation of label maturity and warning tradeoffs in blockchain ML, if the effect is substantial, stable and not already reported. This experiment does not establish global novelty or publication readiness. Exact independent-period validation remains unresolved in the external-source audit.

## Reproduce

```sh
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/delayed_replay.py
.venv/bin/python research/solana/ml/report_delayed_replay.py
```

[Fixed local protocol](../research/solana/ml/delayed_protocol.json) · [Metrics and provenance hashes](results/solana_delayed_replay.json) · [External-source audit](SOLANA_STRONG_BASELINE_RESULTS.md)

Attribution: MELT, Hu et al., CC BY-NC 4.0. Raw data and derived per-token files remain local.
