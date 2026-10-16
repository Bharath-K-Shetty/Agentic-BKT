# EdNet real-data pilot

This is the first external real-learner benchmark for HOMIE's knowledge-tracing
pipeline. It evaluates next-answer prediction on English/TOEIC activity. It does
not establish DeFi learning benefit, validate our simulator rubrics, or establish
a novel research contribution. This baseline was followed by an implemented
[telemetry/recommendation stability audit](EDNET_AUDIT_RESULTS.md); the audit's
limited findings are documented separately.

## Source and attribution

[EdNet official repository](https://github.com/riiid/ednet) and
[dataset paper](https://arxiv.org/abs/1912.03072).
The publisher releases the data under CC BY-NC 4.0 for research purposes.
Use the official KT2 and Contents downloads, cite EdNet, and preserve attribution.
The downloader follows the repository's short links to public Google Drive files;
it handles Drive's large-file confirmation and rejects HTML masquerading as ZIP.

Downloaded archives remain local and gitignored. All members passed ZIP CRC
checks; SHA256 digests and source URLs are saved in
`data/raw/ednet/download_manifest.json`. Digests identify the files we received;
the publisher does not supply a cryptographic checksum for comparison.

## Reproduce

Run from the repository root:

```bash
.venv/bin/python -m src.data_collection.fetch_ednet
.venv/bin/python -m src.features.prepare_ednet --learners 1000 --min-responses 20 --max-responses 100 --seed 42
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m src.eval.run_learning --input data/processed/ednet/pilot/interactions.csv --dataset-manifest data/processed/ednet/pilot/manifest.json --n-skills 7 --epochs 10 --seed 42 --output data/processed/ednet/benchmark
```

The preprocessing manifest records parameters, input/output hashes, filtering
counts and mappings. The evaluator rejects a changed CSV or incorrect category
count when a manifest is supplied. This is a separate external benchmark;
its checkpoint is not compatible with the five-skill HOMIE question bank.

## Pilot protocol

- Rank all 297,444 learner files by SHA256 of `seed:learner_id`. Select the first
  1,000 eligible learners with at least 20 valid submitted bundles. This scanned
  4,067 files; 3,067 learners did not meet the minimum. Results are conditional
  on that eligibility rule, not representative of all EdNet users.
- Parse explicit bundle entry, answer selection and matching submission events.
  Use the last valid answer choice before submission. Exclude incomplete bundles,
  unmatched submissions and responses without matching metadata/active bundle.
- Retain exactly one question per bundle, chosen by question-ID hash independently
  of correctness. This avoids treating co-submitted answers as sequentially known
  outcomes. Keep at most the first 100 retained responses per learner.
- The pilot has 65,158 responses, with 62.85% correct. Each learner has 20–100
  retained responses. Original metadata tags are retained, but models use the
  seven TOEIC parts as coarse task categories. They are not seven atomic skills.
- Use submission order as the numeric `timestamp` expected by the existing model.
  Preserve original shifted time in `source_timestamp_ms`. Never interpret the
  ordinal as elapsed time. Raw file order resolves tied submission timestamps.
- Record choice changes as `revision_count`; identical repeated selections do
  not count as changes. `duration_ms` is bundle entry-to-submit wall time, including
  inactivity, and is not an active time measurement for the selected question.
  Do not invent hint or evidence-inspection features. This initial benchmark
  uses correctness history only; behavioral fields are retained for later work.
- Split learners, never individual answers: 600 train, 200 validation, 200 test.
  Every model predicts the same targets, excluding each learner's first response.
  Parameters are fitted only on training learners. Holdout learners' earlier
  observed answers update their history when predicting their subsequent answers.
- Compare smoothed category prior, category history, grid-fitted BKT, historical
  logistic regression and standard correctness-history DKT. DKT uses hidden size
  32, batch size 32, Adam at 0.001, seed 42 and a fixed 10-epoch budget. No test-set
  tuning or validation checkpoint selection is performed in this pilot.
- Report AUC, accuracy, log loss and Brier score, with 200 learner bootstrap
  resamples and a paired interval for DKT minus BKT AUC. Intervals describe this
  selected test sample; they do not account for training-seed variability.

## Outputs and next research gate

First run, 2026-10-08: 12,776 test predictions from 200 held-out learners.

| Predictor | Test AUC | Test log loss |
|---|---:|---:|
| Category prior | 0.5772 | 0.6426 |
| Category history | 0.5851 | 0.6591 |
| Fitted BKT | 0.5882 | 0.6602 |
| Historical logistic regression | 0.6070 | 0.6362 |
| Correctness-history DKT | 0.6070 | 0.6362 |

DKT minus BKT AUC is +0.0188, with a paired 95% learner bootstrap interval
of [+0.0120, +0.0260]. DKT and logistic regression are effectively tied in
this run. These results do not support claiming that the neural model is
necessary or that our method advances the state of the art. The result snapshot
also includes a paired DKT/logistic interval and category-level diagnostics.

`data/processed/ednet/pilot/` contains the CSV and preprocessing manifest.
`data/processed/ednet/benchmark/` contains `report.json`, target-level
`predictions.csv` and `dkt.pt`. `data/processed/ednet/environment.json` records
the environment used for the first run. A compact result snapshot is kept in
`docs/results/ednet_pilot.json` so the finding survives a clean checkout without
committing third-party learner logs or model binaries.

The category distribution is uneven: part 5 accounts for 36,506 responses,
while part 7 has only 584. A pooled score can obscure weak performance on rare
categories. This pilot is a baseline, not a publication-ready full evaluation.
The [follow-up audit](EDNET_AUDIT_RESULTS.md) specifies telemetry transformations,
a proxy recommendation policy, predictive/stability measures and controls.
Its results are limited; a stronger evaluation and a demonstrated distinction
from prior KT audit work are still required for a publication claim.
