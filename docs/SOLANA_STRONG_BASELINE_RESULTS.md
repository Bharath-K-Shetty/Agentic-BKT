# Stronger Solana baselines and independent-period audit

Selected 10,000 additional tokens, excluding all 18,000 earlier sample ranks. 5,481 have usable 300-second prefixes and have not migrated by the decision. Observed overlap with earlier cohorts: **0**.

Compare **27 versus 120 features**, with the same model-family tuning budget, validation-only configuration selection and three-seed ensembles. Richer features are ordinary summaries of early buyers, holdings, observed co-participation, trade sizes, fees, price changes and six fixed activity bins. They do not introduce a new algorithm.

Primary RF comparison: period-weighted AP change **+0.0129**, paired day-block 95% interval **[+0.0039, +0.0205]**.

The richer RF features improve the primary comparison within this historical cohort.

This is evidence about a stronger baseline, not a novelty or publication-readiness result. The model and feature definitions were specified after earlier exploration, before this run. No public preregistration or independent market-cycle validation is claimed.

## Results

| Test period | Model | Inputs | Test n | Prevalence | AP | AUROC | Recall | FPR |
|---|---|---|---:|---:|---:|---:|---:|---:|
| January_late | random_forest | pilot_27 | 1693 | 67.5% | 0.749 | 0.602 | 7.4% | 4.2% |
| January_late | random_forest | enriched | 1693 | 67.5% | 0.760 | 0.611 | 11.6% | 4.5% |
| January_late | hist_gradient_boosting | pilot_27 | 1693 | 67.5% | 0.746 | 0.597 | 10.1% | 4.9% |
| January_late | hist_gradient_boosting | enriched | 1693 | 67.5% | 0.739 | 0.590 | 10.8% | 6.0% |
| February_early | random_forest | pilot_27 | 911 | 65.0% | 0.702 | 0.574 | 9.8% | 7.2% |
| February_early | random_forest | enriched | 911 | 65.0% | 0.711 | 0.569 | 10.3% | 5.6% |
| February_early | hist_gradient_boosting | pilot_27 | 911 | 65.0% | 0.681 | 0.533 | 7.9% | 5.0% |
| February_early | hist_gradient_boosting | enriched | 911 | 65.0% | 0.679 | 0.532 | 7.1% | 5.3% |
| February_late | random_forest | pilot_27 | 560 | 49.5% | 0.559 | 0.589 | 5.8% | 5.7% |
| February_late | random_forest | enriched | 560 | 49.5% | 0.584 | 0.610 | 5.1% | 3.2% |
| February_late | hist_gradient_boosting | pilot_27 | 560 | 49.5% | 0.567 | 0.578 | 7.6% | 3.2% |
| February_late | hist_gradient_boosting | enriched | 560 | 49.5% | 0.580 | 0.587 | 10.1% | 5.7% |

The threshold is selected on validation at an empirical 5% FPR budget. Test FPR is reported without adjustment. AUROC chance level is 0.5; constant-score AP equals test prevalence. Outcomes must mature before the next training/validation boundary.

Exclusions from the selected tokens:

- already_migrated: 4,335.
- no positive holdings: 184.

## Separate period: what was actually checked

[PumpFun Launch-to-Graduation Corpus](https://huggingface.co/datasets/Slinky21/Pumpfun_Memecoin_Corpus), revision `13bec2bf3089d56d50c35e602616d1b993bb37f5`. Downloaded and inspected three linked Parquet tables plus one trade shard. Data remains local and is not redistributed.

| Check | Observed |
|---|---:|
| Migration records | 5,701 |
| Post-migration snapshot rows | 1,392,133 |
| First post-migration native-price median delay (seconds) | 21.34 |
| Tokens with first native-price snapshot within 5 seconds | 525 |
| Tokens with observed early start and late end in 20-minute window | 1,786 |
| Synthetic/backfilled pool records | 1,449 |
| Inspected trade-shard rows | 1,966,080 |
| Missing prices in inspected shard | 451,451 |
| Shard mints joining migration records | 3 |
| Post-migration first-20-minute trades in inspected shard | 0 |

**Exact external validation remains incomplete.** The current label is a minimum over transaction prices, while these post-migration tables provide periodic prices. A short collapse can happen between observations. The outcome table supplies a USD migration-price anchor, not the native-unit anchor needed to match our existing price ratio. Missing or incomplete follow-up is not evidence of a safe token.

The inspected trade shard covers an early collection interval and has no usable post-migration 20-minute trades in the three mints that join the migration table. That does not establish absence across the 17 uninspected shards. It also does not resolve the documented missing-price and unit-consistency issues. No external model accuracy has been measured.

Using a snapshot endpoint would require an explicit new target and reconstructing that same target in both sources. That is a separate study, not silent validation of this endpoint.

## Research decision

A more complex graph or uncertainty method must now be compared against the stronger baseline. The richer-feature result cannot itself be presented as an invented method: early features and coordination already overlap [MELT](https://arxiv.org/html/2602.13480v2) and [the closest public comparison](https://github.com/Gauravpoudel7/AI_RugPull_Prediction). No global novelty or publication acceptance is established.

- Same historical MELT data; not independent-period validation.
- Price-collapse proxy on eventual migrants, not verified fraud.
- New ordinary features, not a novel algorithm or exact upstream replication.
- No retrospective funder/Jito links or verified creator identity.
- Validation used for configuration selection and threshold selection; test untouched.
- Bootstrap conditional on fitted models; secondary comparisons exploratory.

[Exact baseline settings](../research/solana/ml/strong_baseline_protocol.json) · [Baseline metrics and hashes](results/solana_strong_baselines.json) · [External audit](results/solana_external_period_audit.json)

Attribution: MELT, Hu et al., CC BY-NC 4.0. The external corpus card names Slink Dev and has conflicting MIT metadata / CC BY 4.0 prose; no redistribution is performed.
