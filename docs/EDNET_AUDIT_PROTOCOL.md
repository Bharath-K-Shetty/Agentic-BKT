# EdNet telemetry audit protocol v1

Protocol specified before running this experiment, 2026-10-08. The existing
pilot's test results have already been seen; this is an exploratory follow-up,
not a preregistered confirmatory study.

Question: do historical duration and choice revisions improve next-response
prediction, and how sensitive is a hypothetical category-practice policy to
alternative recordings of those same historical interactions?

Use the existing 1,000-learner EdNet pilot, unchanged: 600 training, 200
validation and 200 test learners; split seed 42. Train correctness DKT,
duration-only DKT, revisions-only DKT, duration+revisions DKT, and a two-input
zero-telemetry DKT control. Use model seeds 42, 43 and 44, hidden size 32,
10 epochs, batch size 32, Adam 0.001. No model selection from test outcomes.
Include historical logistic regression with and without the same normalized
historical telemetry (last observation and running mean). These deterministic
logistic fits are reused across model seeds, not treated as independent runs.

Use completed previous responses only. Fixed log transforms clip duration at
600,000 ms and revision count at 10, as in the existing behavioral model.
No current-target telemetry, correctness or future history may enter prediction.
Report held-out AUC, log loss, Brier score, parameter counts and per-seed paired
learner-bootstrap AUC differences (200 draws). Do not pool seed repeats as
additional learners. Compare augmented models to correctness DKT, logistic
regression and the matched-input-width zero control.

Alternative recording scenarios preserve learner IDs, answer correctness,
question/category identity and ordering. They change completed-response telemetry:

| Scenario | Change | Assumption / limitation |
|---|---|---|
| identity | no change | Negative control; all scores must match exactly |
| duration_round_1s | nearest 1,000 ms | Hypothetical coarse timestamp resolution |
| duration_plus_5s | add 5,000 ms | Hypothetical fixed recording overhead |
| revisions_binary | cap revisions at one | Logger records whether any revision occurred; loses count information |
| duration_plus_30s | add 30,000 ms | Larger, unseen overhead stress; plausibility not established |
| revisions_minus_one | subtract one, floor at zero | Unseen lost-revision stress; not a claim that EdNet loses events |
| telemetry_missing_zero | set both channels to zero | Unseen telemetry failure with zero imputation; zero conflates missing and observed zero |

These are synthetic measurement scenarios applied to real logs, not observed
EdNet faults or evidence of unchanged cognition. Invariance is an explicit
conditional assumption. Duration can contain genuine task/learner information;
binary/lost revisions remove information. Record sensitivity, not a causal
effect or proof that every changed recommendation is wrong.

Define a hypothetical practice recommendation after each completed response:
choose the lowest predicted-correctness category among categories already
observed in that learner's prefix. Require at least two observed categories.
This is a transparent proxy policy, not the Santa policy or a validated tutoring
intervention. The output vectors refer to the seven coarse TOEIC parts, not
validated mastery probabilities. Exclude single-category prefixes from policy
flip denominators and report their number.

Report response-weighted probability changes, recommendation flip rates,
and learner-bootstrap intervals for recommendation flips. Test a cautious gate
that recommends only when clean, rounded-duration, +5s-duration and binary-revision
recordings all agree. Its agreement on those included scenarios is true by
construction and must not be presented as independent robustness evidence.
Evaluate its retained recommendations on the three *unseen* stress scenarios.
As an abstention control, set a clean top-two category margin threshold using
validation data to match the gate's validation coverage. Freeze that threshold
before examining test retention/flip rates; report test coverage for both rules.
No guarantee of robustness beyond the tested scenarios is claimed. Stable
recommendations do not establish that the recommendation is educationally useful.

The main decision is whether there is enough predictive benefit and a meaningful
stability/coverage tradeoff to justify a larger, finer-skill, independently
validated study. Null or negative findings are retained. This experiment does
not establish novelty, DeFi learning benefit or publication readiness.
