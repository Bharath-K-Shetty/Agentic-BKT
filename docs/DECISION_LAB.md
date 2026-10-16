# HOMIE Decision Lab — behavioral knowledge tracing

Updated 8 October 2026. The decision lab extends the quiz-based
prototype with an instrumented transaction simulator and a behavioral DKT
evaluation. It is a local research prototype, not a completed learner study.

**Updated 8 October 2026:** v2 repairs the identical-order defect in the v1
simulator. Five uncoached diagnostics now precede ten practice scenarios, two per
skill. Diagnostic history changes the adaptive practice order; later practice
answers update that priority. Expert review and a frozen study protocol remain
required before recruitment. See [the completion plan](COMPLETION_PLAN.md).

## Research question

Does the sequence of a learner's earlier inspection, hint, revision, and
decision actions improve prediction of performance in subsequent unfamiliar
DeFi scenarios beyond correctness history alone?

This is a testable hypothesis, not a claim that adding features guarantees
an improvement. DKT is established prior work. The proposed contribution is
the decision environment, reviewed scenario rubrics, and a controlled
evaluation of behavioral signals in this setting.

## Environment

Open http://127.0.0.1:8420/simulator.html after starting the normal app:

```bash
.venv/bin/python -m uvicorn webapp.backend.main:app --host 127.0.0.1 --port 8420
```

The learner inspects evidence cards, chooses approve/reject/modify, selects
evidence-supported reasoning, and adjusts an execution parameter when the
scenario supports one. Saving a draft records a provisional decision; saving
a changed draft records a revision. Committing ends the scenario. No wallet
is connected and no transaction is signed, constructed, or submitted.

Five diagnostic scenarios cover permissions, token identity, liquidity,
slippage, and transaction safety without hints or scoring feedback. Ten distinct
practice scenarios cover those five skills twice. Five transfer scenarios change
the task details. Immediate practice coaching identifies whether the action, reason,
or execution setting fails the task constraints and provides a concept lesson.
Transfer withholds hints and scoring feedback until final review.

The bank includes reviewed-within-the-fiction requests that should be approved,
requests that should be rejected, and requests that should be modified.
Rejecting every request therefore fails to complete several tasks. These are
**authored hypothetical tasks**, not transactions from the collected wallets.
Names such as DEMO-MINT-A are fictional identifiers. Simplified pool-depth
and minimum-output rules are teaching models, not live quotes.

## Draft rubric and behavior observations

Success requires all three applicable checks: correct task action,
evidence-supported reason, and an execution value satisfying the task's bound.
The rubric is deterministic and inspectable in `src/learning/scenarios.py`.
It is not an independently validated competence measurement. Expert review
is still needed for alternative reasonable choices and equally plausible reasons.

Behavior fields are:

| Field | Operational definition | Limitation |
|---|---|---|
| inspection_count | Distinct evidence cards opened before commit | Opening does not establish reading or understanding |
| hint_count | Successful thinking-prompt requests in practice | Requesting help is not necessarily poor knowledge |
| revision_count | Changed saved drafts after the first draft | Unsaved local edits are not observed |
| duration_ms | Server wall-clock interval from scenario offer to commit | Includes idle time and reading previous feedback; not active engagement |

Companion event logs retain inspection order, draft contents, and timestamps.
The current DKT feature set aggregates those events per completed scenario;
it does **not** model the within-scenario event sequence. Raw logs support
that as future work. The time feature is included for exploration, not used
to label someone confused. No free-text personal information is collected.

Practice order uses configured, uncalibrated BKT predictions from diagnostic and
practice answers only. Diagnostic and transfer phases follow fixed skill order.
Adaptive practice selects the lowest predicted skill among remaining items,
breaking ties by skill and scenario ID. Fixed practice sorts by skill and scenario
ID throughout. All learners receive the same 20 items, ten coached opportunities,
and hint availability; duration is observed, not controlled. This tests ordering,
not a different amount of practice. Assessment phases hide skill probabilities;
transfer outcomes do not update the live policy. It is an experimental policy.
Behavior-augmented DKT currently runs **offline in the
evaluation pipeline**, rather than driving live instruction. Consequently,
using this app alone does not establish the benefit of DKT-guided coaching.

## Persistence and research collection

Simulator records use separate SQLite tables in the same local database as
the quiz lab. Existing quiz sessions and exports remain separate. Session
tokens enable resume and deletion. Deleting a simulator session cascades to
its offered scenarios, decisions, and events. It cannot retract exported CSVs.

Opt-in sessions are randomly assigned adaptive or fixed practice order. Both
conditions see the same scenarios and prompt availability. Demo records stay
out of exports. One session represents one assumed learner; a study must
control repeat participation externally.

```bash
.venv/bin/python -m src.learning.simulator --completed-only
```

Outputs: `data/processed/simulator/interactions.csv`,
`interactions_events.csv`, and `interactions_sessions.csv`. All use the same
export pseudonyms and exclude session bearer tokens. The sessions file retains
all opt-in assignments, answered counts, bank-specific expected totals and
completion status, including zero-answer sessions even with `--completed-only`.
Existing v1 sessions resume with their original ten-item bank and exports preserve
their version; never pool v1 and v2 as the same intervention. The current benchmark
accepts v2 only. Freeze a single snapshot for analysis; pseudonyms are
not guaranteed stable across exports. Completion-only snapshots are useful
for pilot model evaluation but may bias a randomized intervention analysis.

## Behavioral benchmark

```bash
.venv/bin/python -m src.eval.run_simulator --synthetic --epochs 2
.venv/bin/python -m src.eval.run_simulator --input data/processed/simulator/interactions.csv --epochs 10 --output data/processed/simulator/real-eval
```

All predictors use disjoint learner train/validation/test partitions,
chronological responses, train-only parameter fitting, and identical target
rows. A learner's first decision is excluded for every model.

Models include skill prior, correctness history, BKT, logistic regression,
correctness-only DKT, and behavior-augmented DKT. Feature ablations remove
inspection or hint features. A zero-behavior control keeps the augmented
architecture and parameter count, with behavior inputs zeroed, to help
distinguish feature value from a change in model capacity.

The augmented LSTM receives the skill, correctness, and observed behavior
of **completed earlier scenarios**. Behavior and correctness for the target
scenario never enter its own prediction. Fixed log transforms and clipping
normalize counts and elapsed time without using labels or test statistics.
All DKT variants use hidden size 32, the same declared epochs, and fixed seed.
No variant is selected based on test performance.

Reports include held-out predictions, overall and transfer-only ROC-AUC,
accuracy, log loss, Brier score, parameter counts, and a learner-bootstrap
interval for the augmented-minus-correctness-only AUC difference. The original
benchmark also reports baseline intervals. Ten real decisions per learner is
a short trace: DKT may be inappropriate at this scale, and pilot results
should determine whether longer traces or simpler methods are preferable.

The synthetic generator uses artificial ability/behavior correlations. Its
sequences are not human actions in the authored scenario bank. The two-epoch
smoke run scored overall AUC 0.514 for correctness-only DKT, 0.550 for augmented
DKT, and 0.553 for the zero-behavior control. Transfer AUC was 0.516 for
correctness-only DKT and 0.485 for augmented DKT. This **does not demonstrate
behavioral benefit**; the results remain engineering verification. The simpler
logistic baseline scored overall AUC 0.700. These results are retained rather
than tuning on the test set to obtain a favorable comparison.

## Verification and remaining research

The full suite passes **74 tests** (8 October 2026).
Run it with `.venv/bin/python -m pytest -q`.
The new tests cover evidence gating,
draft scoring, transfer restrictions, export consent, cascading deletion,
settings, matched-capacity controls, and feature leakage boundaries.

With the server running, the local integration check is:

```bash
.venv/bin/python -m tests.smoke_simulator_http
```

It creates and deletes its own demo session and exercises all twenty decisions.
Regression coverage checks all 32 diagnostic correctness patterns, fixed-order
consistency, equal practice exposure, practice-dependent reprioritization, and
v1 resume/export compatibility.

Before publication, reviewers must check scenario validity, reason options,
reading burden, and assessment difficulty. Expand the bank, freeze the
protocol, plan sample size, and collect real learner sequences. Evaluate
prediction and instructional benefit separately. A later intervention study
needs a fixed learner-trained policy and independent participants; the
default BKT order must not be described as a DKT-guided intervention.

Use the existing [DKT protocol](DKT_PROJECT.md) for foundational sources and
broader study constraints. No claim about preventing financial losses or
improving learning is currently supported.
