# Original-tag replication protocol v1

Specified before preparing or evaluating the new cohort, 2026-10-08.
This is an exploratory follow-up to the negative telemetry pilot. It is not
a new independent dataset or a preregistered publication study.

Select 1,000 learners by hash ranking with sample seed 2026, excluding **all**
1,000 learners in the original pilot. Keep the same eligibility rule (20 valid
submissions minimum) and earliest-100-response cap. Retain one question per
bundle independently of correctness. Make new train/validation/test splits
of 600/200/200 learners with split seed 42. Check cohort disjointness explicitly.

On these exact same responses and splits, compare two encodings:

- Seven TOEIC parts, as before.
- Every original expert tag. Build the vocabulary from public question metadata,
  without learner answers or held-out outcomes. Preserve all tags for each
  question. Treat -1 as a separate **unknown-metadata** category, not a known
  skill, and report unknown-target results separately.

For multi-tag DKT, each completed question is exactly one time step. Distribute
unit input weight equally among its tags in the correct/incorrect input block.
For the next question, average its tag-specific logits and apply sigmoid once;
compute **one** binary loss against its single response. Never explode a response
into sequential skill rows or independently count its shared correctness label.
This is an explicit mean-logit multi-tag extension, not unchanged original DKT.

Fit correctness-only, duration+revision, and matched-input-width zero-telemetry
DKT for both encodings. Use model seeds 42,43,44; hidden size 32; ten epochs;
batch size 32; Adam 0.001. Fit historical logistic regression with and without
historical telemetry as strong simple controls. For multi-tag logistic features,
use a unit-weight bag of target tags plus the average per-tag past attempt count
and smoothed correct rate, and global history length/rate/last correctness.
Each previous response updates its observed tag counters simultaneously; it
still contributes only one row to the logistic training objective. Priors and
all fitted parameters use training learners only. Telemetry consists of the
last completed response and running mean of fixed normalized duration/revisions.
No target-response telemetry is allowed.

Report held-out AUC, log loss, Brier score, model parameter counts, per-part
diagnostics, unknown/known-target diagnostics and paired learner bootstrap
intervals (200 draws). Directly pair coarse vs fine predictions on the same
test learners, and behavior vs correctness/zero controls within each encoding.
Do not tune or stop based on test results. Compare three training seeds without
treating them as new learners. The tag model has more parameters than the part
model at equal hidden size; any encoding advantage is not proof that semantic
granularity alone caused the gain.

Decision gate: does behavior improve prediction within the original-tag model
consistently across seeds and against the capacity and logistic controls?
Changing categories or improving baseline accuracy alone is not a novel method
or evidence of learning effectiveness. Retain negative findings. Revisit the
stability intervention only if the features first show useful signal.
