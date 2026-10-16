# Solana ML research experiments

## Active candidate: cold-signer execution risk

See [the evidence report](../../../docs/SOLANA_TRANSACTION_RISK_RESULTS.md) for
the measured contribution, identity controls and limits. These are reliability
predictions on actual blockchain records, not DKT or contract security review.

Source: data from [SolArchive.org](https://huggingface.co/datasets/solarchive/solarchive),
CC BY 4.0, revision `6588cad2832e62be03972ac80d69c6af11d631c8`.
The probe downloads selected Parquet columns by HTTP range, about 65–80 MB per
sample rather than each complete shard. It verifies response bounds and hashes
ranges/derived files; it does not verify the original whole-file hash. The raw
folder must exist. Data and predictions remain local and ignored by git.
The exact tested dependency versions are recorded in
`transaction_requirements.txt` and `docs/results/solana_transaction_environment.json`.

```sh
mkdir -p data/raw/novelty_search data/processed/solana_ml docs/results
for date in 2025-11-01 2025-11-02 2025-11-03 2025-11-08 2025-11-09 2025-11-10; do
  .venv/bin/python research/solana/ml/archive_probe.py --date "$date"
done
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/transaction_risk.py
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/transaction_risk.py --protocol research/solana/ml/transaction_confirmation_protocol.json --output-name confirmation
.venv/bin/python research/solana/ml/archive_probe.py --date 2025-11-22 --shard-index 203
.venv/bin/python research/solana/ml/archive_probe.py --date 2025-11-23 --shard-index 60
.venv/bin/python research/solana/ml/archive_probe.py --date 2025-11-24 --shard-index 39
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/transaction_risk.py --protocol research/solana/ml/transaction_extension_protocol.json --output-name extension
.venv/bin/python research/solana/ml/archive_probe.py --date 2025-11-29 --shard-index 91
.venv/bin/python research/solana/ml/archive_probe.py --date 2025-11-30 --shard-index 132
.venv/bin/python research/solana/ml/archive_probe.py --date 2025-12-01 --shard-index 24
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/transaction_risk.py --protocol research/solana/ml/transaction_prospective_protocol.json --output-name prospective
for cohort in pilot confirmation extension prospective; do
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/transaction_identity.py --cohort "$cohort"
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/transaction_audit.py --cohort "$cohort"
done
.venv/bin/python research/solana/ml/report_transaction_risk.py
.venv/bin/python -m pytest tests/test_solana_transaction_risk.py -q
```

Settings, primary/diagnostic distinctions and all source hashes are recorded in
the JSON reports in `docs/results/`. No current logs/errors/actual compute use
enter the models. A one-hour label delay applies to online history; submission
time and unlanded attempts are absent. This is conditional-inclusion screening,
not a proven live failure-prevention tool or a new boosting algorithm.

## Earlier candidate: token price-collapse pilot

This experiment tests whether a real transaction prefix predicts a later price
collapse. It is a baseline and data-quality check, not a novel algorithm.

The data belongs to Hu et al., [MELT](https://arxiv.org/html/2602.13480v2),
[author repository](https://github.com/git-disl/MELT), CC BY-NC 4.0.
Use with attribution for noncommercial research. The author's Drive ZIP is
unversioned; the experiment hashes the downloaded bytes. Repository metadata and
labels use commit `0732bcfab54f508c27becd6d9b2b10b1b6ac2517`.

```bash
.venv/bin/python research/solana/ml/fetch_melt.py
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/prefix_baseline.py
.venv/bin/python -m pytest tests/test_solana_prefix_baseline.py -q
```

The default sample selects 6,000 mints by the hash of seed and address, without
using outcomes. Features come from events through launch + 60 or + 300 seconds,
including the boundary. Explicit mint events define launch time. Migration
metadata defines eligibility: tokens already migrated by the decision are
excluded. The source only contains eventual migrants, so this selection cannot
represent all launches. No future lifetime or eventual holder count is a feature
or quality filter.

The default positive label is released `min_ratio < 0.3`: price falls below 30%
of migration price within the subsequent 20 minutes. The model sees none of
`min_ratio`, `return_ratio`, `manipulated`, the label, mint address, migration time,
calendar date or full-launch feature files. This endpoint is price collapse;
fraud intent, victim losses and time of first harm are not established.

An optional `--target high_risk` uses the author's combined risk label. Its manual
judgments have unverified availability times; that alternative is a retrospective
sensitivity analysis, not a verified prospective training protocol.

Splits follow decision time, approximately 60/20/20. A training token's outcome
must have matured before the first validation decision; validation labels must
mature before the first test decision. The default uses migration + one hour,
conservative for the 20-minute statistical endpoint. Tied decision times stay
together. The actual purged counts are reported.

Four fixed models (logistic regression, random forest, histogram gradient
boosting, MLP) use identical splits, with and without six co-participation
features. These features describe observed same-transaction wallet relationships;
they do not assert common ownership. This is a statistical relational ablation,
not a graph neural network or an operator identity detector. No retrospective
funder/Jito bundle archive is used.

The validation set determines each alert threshold under a 5% false-positive
budget. Test false-positive rates can differ. Report AUROC, average precision for
both classes, Brier score and operating metrics, plus a training-prevalence
constant baseline. Day-block bootstrap intervals use fixed predictions; they
exclude retraining uncertainty and do not establish operator independence.

Outputs:

- `docs/results/solana_prefix_baseline.json`: counts, exclusions, metrics, hashes,
  source attribution, environment and limitations.
- `data/processed/solana_ml/prefix_price_drop_6000_42.jsonl`: local prefix features.
- `data/processed/solana_ml/predictions.jsonl`: local validation/test predictions.

Neither derived data nor the multi-GB archive is committed. A single sample/seed
is exploratory. Publication requires a distinct contribution, strong existing
baselines, robustness across periods and independently defensible evaluation.

## Delayed-outcome replay

```sh
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/delayed_replay.py
.venv/bin/python research/solana/ml/report_delayed_replay.py
.venv/bin/python -m pytest tests/test_solana_delayed_replay.py -q
```

The [locally fixed settings](delayed_protocol.json) select hash ranks 28,000–35,999
without outcomes. RF120 parameters come from the earlier stronger-baseline study;
only that earlier cohort supplies training and initial validation labels. Seven
threshold/calibration controls share identical scores. Online updates use only
past decisions whose labels have matured, except the explicitly invalid oracle.
The correction fails the fixed success gate; see the
[full result and limitations](../../../docs/SOLANA_DELAYED_REPLAY_RESULTS.md).

## Disjoint-token confirmation

The [confirmation protocol](../../../docs/SOLANA_CONFIRMATION_PROTOCOL.md)
selects 12,000 additional tokens, excluding the pilot ranks, and evaluates three
calendar folds using three tree-model seeds. Settings are fixed in
`robustness_protocol.json`; the results record its hash. This is a confirmation
within the same source period, not an independent market-cycle validation.

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/robustness.py
.venv/bin/python research/solana/ml/report_confirmation.py
.venv/bin/python -m pytest tests/test_solana_prefix_baseline.py tests/test_solana_confirmation.py -q
```

[Results and limitations](../../../docs/SOLANA_CONFIRMATION_RESULTS.md) include
the primary paired comparison, separate calendar outcomes, wallet-overlap
diagnostics and validation-threshold transfer. Raw predictions stay under ignored
`data/processed/solana_ml/confirmation_predictions.jsonl`.

## Stronger baselines and external-source audit

The third sample excludes all 18,000 previous ranks. Compare the original 27
features with 120 ordinary prefix summaries, using matched configuration grids
and three-seed tree ensembles. This is stronger feature engineering, not a new
method or an exact reproduction of the author's 119-feature benchmark.

```bash
.venv/bin/python -m pip install -r research/solana/ml/requirements.txt
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/strong_baselines.py
.venv/bin/python research/solana/ml/audit_external_period.py
.venv/bin/python research/solana/ml/report_strong_baselines.py
```

The external auditor fetches the three pinned migration/outcome/snapshot tables
if absent. One trade shard was additionally inspected during the study; the
auditor records it when `data/raw/external_ml/trades-00000.parquet` is present.
That optional probe does not constitute a full external trade-corpus audit.
The [results](../../../docs/SOLANA_STRONG_BASELINE_RESULTS.md) describe the
remaining endpoint mismatch. No external model accuracy is reported.
