# HOMIE: A Scenario-Based DeFi Learning Prototype with Deep Knowledge Tracing

## Real-data update — 2026-10-08

An external EdNet KT2 pilot now evaluates 1,000 real learners and 65,158
responses. On 200 held-out learners, DKT and historical logistic regression
both achieve about 0.607 AUC; BKT achieves 0.588. This establishes a working
real-data prediction benchmark, with no meaningful neural-model advantage over
logistic regression in this run. It does not establish DeFi learning benefit,
novelty or publication readiness. See [protocol and results](EDNET_PILOT.md).
The earlier synthetic results below remain engineering checks.

A subsequent [telemetry audit](EDNET_AUDIT_RESULTS.md) uses three neural training
seeds, feature ablations, a capacity control, logistic controls and unseen
recording stress scenarios. It finds no combined-telemetry DKT improvement and
little benefit from a consistency gate. This candidate contribution remains
unsupported by the current pilot.

An [original-tag replication](EDNET_SKILL_RESULTS.md) on a second, disjoint
1,000-learner EdNet cohort confirms that richer tags help the logistic baseline
(about 0.627 AUC), while the tested tag DKT models achieve about 0.609 with no
reliable telemetry gain. This is a controlled replication result, not evidence
for a novel behavioral-DKT method.

The subsequent [question-difficulty control and research decision](RESEARCH_DECISION.md)
raise the simple baseline to about 0.681 AUC. Learner history adds value beyond
static question information, but timing/revisions still show no reliable gain.
The literature check identifies established overlap and does not establish a
novel research gap. External-platform validation remains pending.

The active implementation has since been extended with the **Decision Lab**:
instrumented transaction scenarios, execution controls, draft revisions,
targeted coaching, transfer assessment, and an offline behavioral DKT
comparison with feature and model-capacity controls. See
[DECISION_LAB.md](DECISION_LAB.md) for the extension and its smoke results.
The quiz-only implementation report below remains a record of the first version.

Implementation report — 5 October 2026. Not a completed empirical research paper.

## Abstract

HOMIE is a local educational prototype for five DeFi concepts. It collects
ordered question responses, provides concept-specific explanations, and
supports adaptive or fixed practice sequences. An LSTM-based Deep Knowledge
Tracing model predicts next-answer correctness from prior responses. The
evaluation pipeline compares it with four simpler predictors under disjoint
learner holdouts. The implemented system includes a versioned question bank,
session persistence, optional research participation, pseudonymous export,
and reproducible benchmark artifacts. Verification establishes that the
software works end to end. A synthetic smoke evaluation is included solely
to exercise the pipeline; no real-learner effectiveness claim is made.

## Problem and bounded contribution

DeFi interfaces can require users to reason about unfamiliar permissions,
token settings, liquidity, and transaction execution. HOMIE turns these
concepts into educational scenarios and asks whether response history helps
predict subsequent answers. It provides an experimental learning environment
and evaluation workflow. It does not introduce a new knowledge-tracing
algorithm, infer knowledge from financial losses, or claim a first-ever
application to DeFi.

## System and method

The browser communicates with a FastAPI learning API. A local SQLite database
stores pseudonymous sessions, ordered responses, and recorded lesson views.
The learner completes five diagnostic items, ten practice items, and five
distinct final-assessment items. Server-side scoring prevents client-supplied
correctness labels. Adaptive order prioritizes the available skill with the
lowest predicted next-answer correctness; fixed order cycles through skills.
Both orders cover the same questions and lessons.

DKT consumes one-hot encodings of skill and observed correctness. Its LSTM
produces per-skill correctness logits after each historical interaction. The
training loss selects the output for the next question's skill; padded steps
are masked out. Evaluation holds out complete learners and excludes their
first response for all predictors. The benchmark additionally reports
train-prior, history, fitted BKT, and logistic-regression performance.

Demo sessions can use a synthetic-trained DKT checkpoint. Opt-in study
sessions exclude that checkpoint and use a configured BKT baseline unless
a compatible learner-trained model is explicitly installed. Accordingly, the
default study flow is not a test of DKT-guided instructional benefit.

## Verified software results

The expanded offline suite passed 47 tests in the final verification. Tests
cover the complete 20-question flow, question coverage, resume, guarded
submissions, deletion, consent filtering, synthetic checkpoint restrictions,
learner split isolation, chronological feature construction, and benchmark
serialization. Browser checks verified the landing page and live submission.
The full HTTP check exercises answers, lessons, final review, resume, and
deletion. These are engineering checks rather than research results.

The initial synthetic benchmark used 100 generated learners, 30 interactions
each, five skills, seed 42, and five DKT epochs. The split contained 60 training,
20 validation, and 20 test learners, giving 580 test predictions.

| Predictor | Test ROC-AUC | Test accuracy | Test Brier score |
|---|---:|---:|---:|
| Skill prior | 0.484 | 0.707 | 0.210 |
| Correctness history | 0.684 | 0.716 | 0.192 |
| BKT | 0.712 | 0.731 | 0.185 |
| Logistic regression | 0.728 | 0.709 | 0.181 |
| DKT | 0.434 | 0.579 | 0.247 |

The short DKT smoke run underperformed the simpler models. This is preserved
without selecting a favorable test result. These generated sequences are not
responses to the authored bank and do not establish the comparative behavior
of real learners. Artifacts are regenerated by the documented CLI and stored
locally under `data/processed/learning/benchmark/`, which is gitignored.

## Limitations and required evaluation

The authored bank is a draft, with only one diagnostic and one assessment
item per skill. Difficulty equivalence, construct validity, and learner
comprehension have not been established. The synthetic learning generator
is not an educational validation dataset. Short traces may be inadequate for
DKT, and simpler models may remain preferable even after real data collection.

A session currently represents an assumed learner rather than a verified
unique person. Study administration must prevent duplicate participation.
Opt-in randomization is supported, but a credible intervention study still
needs reviewed materials, a fixed predictor, a prospective analysis plan,
adequate participants, and dropout reporting. Higher next-answer accuracy
does not establish improved learning or financial outcomes.

## Conclusion

HOMIE now has a runnable learning prototype and an evaluation pipeline that
can test a bounded DKT research question. The remaining research work is
content review, real learner data collection, and an independent evaluation.
Publication readiness depends on those results, not on the presence of a
working interface or synthetic benchmark.

See [the protocol](DKT_PROJECT.md) for commands, data handling, sources,
study constraints, and model configuration.
