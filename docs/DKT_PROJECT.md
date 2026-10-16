# HOMIE: Deep Knowledge Tracing for DeFi Education

Active project scope, 5 October 2026. This supersedes the wallet-prediction
critical path in `PROPOSAL.md` for the current implementation. The old
proposal and broader agent manuscript remain historical drafts.

## Objective

Build an educational prototype that models ordered quiz responses, predicts
the next response, and recommends concept-specific practice. The proposed
research contribution is an evaluation of knowledge tracing in a carefully
defined DeFi education setting. DKT itself is an established method, and
its use here is not claimed as a new algorithm or the first such application.

Primary research question: does DKT improve next-answer prediction over
skill priors, correctness history, BKT, and historical-feature logistic
regression on held-out learners?

Secondary research question: does personalized practice order improve a
separate final assessment relative to a fixed order? This requires a
prospective, adequately sized learner study. Prediction performance alone
cannot answer it.

## Implemented learning flow

- Five concepts: wallet permissions, token risk, liquidity, slippage, and
  transaction safety.
- Five diagnostic questions, two practice questions per concept, and five
  distinct assessment questions: 20 responses per complete session.
- Practice shows a short authored lesson and immediate explanatory feedback.
  Diagnostic and final-assessment feedback is withheld until final review.
- Adaptive practice selects the available concept with the lowest predicted
  next-answer correctness. Each concept still receives two practice items.
- Fixed practice cycles through concepts in a fixed order. Both conditions
  have the same questions and access to the same lessons; only order differs.
- Completion shows phase scores, suggested concepts to revisit, and answer
  explanations. Score differences are descriptive, not proof of learning.
- A random session token supports local resume. No name, email, or wallet is
  collected. Losing that token loses access to that session.
- Opt-in sessions are randomly assigned adaptive or fixed order. Demo
  sessions use adaptive order and are excluded from research exports.
- The delete endpoint removes the session, its answers, and lesson records.
  It cannot retract records from CSV files already exported by the researcher.

The bank in `src/learning/content.py` is authored hypothetical content.
It has **not** been reviewed by an educator or calibrated for difficulty.
It is not a set of verified real-world incident labels. The wallet analysis
remains separate and must not be treated as evidence of learner knowledge.

## Run and demonstrate

From the repository root with the existing virtual environment:

```bash
.venv/bin/python -m src.eval.run_learning --synthetic --epochs 5
.venv/bin/python -m uvicorn webapp.backend.main:app --host 127.0.0.1 --port 8420
```

Open http://127.0.0.1:8420. The first command creates the synthetic
benchmark report, predictions, and a DKT checkpoint. The server automatically
uses that checkpoint for demo sessions if it exists when first initializing
the learning service. The concept map explicitly identifies it as synthetic.

Without a checkpoint, the app uses BKT with uncalibrated demonstration
parameters: initial mastery 0.3, learning 0.15, guessing 0.2, and slipping 0.1.
Displayed probabilities estimate next-answer correctness; they are not
validated mastery scores, certifications, or individual ability judgments.

Opt-in sessions never use a synthetic-trained DKT model. They default to
configured BKT until a compatible learner-trained checkpoint is supplied.
Consequently, a study using the default server evaluates **BKT-guided order**,
not DKT-guided instruction. This distinction must be retained in every report.

To use a real-data checkpoint trained on this version of the question bank:

```bash
HOMIE_DKT_MODEL=data/processed/learning/real-eval/dkt.pt .venv/bin/python -m uvicorn webapp.backend.main:app --host 127.0.0.1 --port 8420
```

Restart the server when changing checkpoints. Keep the checkpoint fixed
throughout a prospective study and recruit a separate group for testing its
instructional benefit. Do not deploy a model trained on the same participants
whose learning benefit will be reported.

The earlier wallet interface remains at `/wallet.html`. It has known weak
label limitations and is not part of the DKT validation.

## Data collection and export

Local SQLite storage: `data/processed/learning/sessions.sqlite3`.
Set `HOMIE_LEARNING_DB` before startup to use another path.

```bash
.venv/bin/python -m src.learning.service --completed-only
```

The output defaults to `data/processed/learning/interactions.csv`.
Only consenting complete sessions are included with `--completed-only`.
Without that switch, partial consenting sessions are also exported. Session
bearer tokens are replaced by export pseudonyms. Use a single frozen export
for an analysis: export pseudonyms can change when the set of sessions changes.

Fields: student_id, skill_id, correct, timestamp, question_id, phase,
prediction, predictor, lesson_seen, condition, consent, and bank_version.
Timestamps preserve order within each learner. Correctness is computed on
the server against the versioned bank; the browser cannot submit its own score.
`lesson_seen` records a click on “Mark lesson as read”, not verified reading.

One session is one assumed learner in the current prototype. Repeated sessions
by the same person are not automatically linked. During collection, assign
one session per participant and track repeat participation separately; otherwise
learner holdouts and randomization can be compromised. The local opt-in notice
does not replace the supervisor's study procedures or institution's requirements.

## Prediction benchmark

```bash
.venv/bin/python -m src.eval.run_learning --input data/processed/learning/interactions.csv --epochs 10 --seed 42 --output data/processed/learning/real-eval
```

The split is approximately 60% training, 20% validation, and 20% test by
learner. A learner never appears in multiple partitions. Response ordering is
preserved; each predictor sees only earlier responses when predicting a target.
Every model excludes the first response of each learner from evaluation.

Models:

1. Training-set smoothed per-skill correctness prior.
2. Smoothed same-skill correctness history with a training-set prior.
3. BKT: per-skill parameters selected by training likelihood over a fixed grid.
4. Logistic regression: target skill and historical practice/correctness
   statistics; the scaler and classifier are fitted only on training data.
5. DKT: LSTM with one-hot skill/correctness inputs and per-skill next-answer
   outputs. Fixed hidden size 32, Adam optimizer, fixed seed, and declared
   epoch count. No checkpoint is selected using test performance.

Reports include ROC-AUC, accuracy, log loss, Brier score, learner membership,
training losses, held-out per-response predictions, learner-bootstrap AUC
intervals (200 resamples), and a paired DKT-minus-BKT AUC interval. AUC is
reported as null for a single-class sample. Validation is reported separately
and is available for future tuning; the current CLI does not tune on it.

The benchmark needs at least six learners with at least two responses each
and both outcome classes in training. **These are execution checks, not a
sample-size justification.** Short traces and small cohorts can strongly
favor simpler models. Report all baselines, seed sensitivity, dropout, class
balance, and interval uncertainty. More epochs or complexity do not guarantee
that DKT will help.

Generic four-column CSV files can be benchmarked, but their checkpoint is
marked with an unspecified bank and cannot be deployed into this learning
app. Only a compatible versioned HOMIE export establishes the app's skill
mapping. Generated data remains explicitly synthetic throughout the demo.

## Before a real study or publication

Have a DeFi subject reviewer and an educator check the skill mapping, answer
keys, ambiguity, reading burden, and assessment difficulty. Expand the bank
and pilot it: one pre/post item per skill is insufficient for a reliable
mastery measure. Avoid claiming the draft pre/post forms are equally difficult.

Freeze a study protocol, content version, predictor, epoch policy, outcome
definitions, and analysis plan before collection. Plan sample size using the
effect and precision of interest rather than a convenient wallet count.
Use separate data for model development and the intervention study. Report
intention-to-treat and attrition for a randomized study; completion-only export
is useful for a pilot but can create selection bias in a learning-effect study.

No learner study has yet been run. No claim about improved understanding,
reduced losses, or safer transactions is currently supported. A null result
can still be informative if labels, sample size, and evaluation are credible.

## Reference foundations

- [Piech et al., Deep Knowledge Tracing (2015)](https://arxiv.org/abs/1506.05908):
  established recurrent approach used as the model foundation.
- [How deep is knowledge tracing?](https://arxiv.org/abs/1604.02416):
  motivation to scrutinize model comparisons and use simpler baselines.
- [Solana SPL Token basics](https://solana.com/docs/tokens/basics):
  mint identification, delegation/revocation, and token authorities.
- [Jupiter custom swap guide](https://developers.jup.ag/docs/guides/how-to-build-a-custom-swap-with-metis):
  output thresholds, slippage tolerance, and price impact.

These sources inform the implementation and teaching content; they do not
constitute an independent validation of this question bank.
