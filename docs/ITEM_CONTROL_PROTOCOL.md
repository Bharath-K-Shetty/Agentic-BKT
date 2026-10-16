# Question-difficulty control protocol v1

Specified before running this control on the EdNet replication cohort,
2026-10-08. The cohort's previous model results have already been inspected;
this is exploratory, not a fresh confirmatory test set.

Keep the original-tag replication cohort, eligibility rules and 600/200/200
learner split. Add a smoothed question-correctness-rate predictor fitted only
on training learners: `(question_successes + 5 * global_rate)/(question_count + 5)`.
For logistic training rows, exclude **all responses from that row's learner**
from both question statistics and the global rate. Thus even the target's own
label or later responses from its learner cannot leak through the estimated
question difficulty. For validation/test rows use the complete training cohort
only. Report question-rate-only and global-rate-only baselines.

Compare the existing tag-history logistic model, the same model with past
telemetry, a static tag/question model without learner history, tag/history with
question-rate logit and log-count, and the latter with past telemetry. The
static and history models receive the same question-rate/count information;
history adds only past learner state. Use fixed smoothing strength 5,
StandardScaler + LogisticRegression(max_iter=1000, random_state=42). No test
tuning, feature search, neural retraining or model selection is performed.
These are controls inspired by established item-difficulty learner models,
not a new IRT or state-of-the-art LKT implementation.

Use one target per response, original tag sets, the same past-only history
features, and the same normalized historical telemetry. Report AUC, log loss
and Brier score on identical validation/test targets, seen/unseen question
subgroups, and training-support strata. Compute 200 paired learner-bootstrap
draws for incremental question information, history and telemetry. Learner
bootstrap does not quantify uncertainty over newly sampled questions. Seen
versus unseen question subgroups are observational and may differ in difficulty.

This control answers whether omitted question-level information changes the
interpretation of our earlier model comparison. It cannot establish cognition,
causal learning gains, intervention usefulness or novelty. The primary next
research question will be selected using this control and the literature review;
no post-result claim that this protocol was preregistered is permitted.
