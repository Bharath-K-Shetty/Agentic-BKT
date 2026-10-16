# Research decision after the EdNet experiments

Current direction, 2026-10-08: the user selected Solana research over DKT and
asked to prioritize novelty and publication potential over a fixed deadline.
See [the Solana novelty protocol](SOLANA_NOVELTY_PROTOCOL.md). The EdNet findings
below remain valid as prior experiment results; the proposed KT next study is
historical and is not the current project direction.

Updated 2026-10-08. This replaces the proposed behavioral-DKT superiority and
recommendation-instability claims. Those claims are not supported by our results.

## What the closest work already covers

| Primary source | Established overlap | Implication for HOMIE |
|---|---|---|
| [Gervet et al., JEDM 2020](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/451) | Nine-dataset comparison of logistic, Markov and deep learner models; conditions where simple models lead | “Logistic beats DKT” alone is not a new contribution |
| [Pavlik and Eglington, JEDM 2023](https://jedm.educationaldatamining.org/index.php/JEDM/article/download/722/178) | Logistic feature search using student, skill and item information, including difficulty and temporal features | Our earlier baselines omitted an important established source of predictive information |
| [Kim et al., EDM 2021](https://files.eric.ed.gov/fulltext/ED615512.pdf) | Behavioral testing of KT models beyond predictive metrics | We cannot claim to introduce KT model auditing |
| [Badran and Preisach, SN Computer Science 2026](https://link.springer.com/article/10.1007/s42979-026-05344-3) | Multi-concept label leakage and leakage-free embeddings | Preserving one response per event is necessary evaluation hygiene, not established novelty |
| [Agentic Knowledge Tracing, 2026 preprint](https://arxiv.org/abs/2606.25358) | Financial-literacy serious-game assessment evaluated with real participants | Combining financial education, games and tracing is already explored; DeFi-specific usefulness needs direct evidence |

This targeted search establishes overlap, not exhaustive coverage. It has **not
established a novel gap** for the existing method. No “first” claims are justified.

## The missing control, now implemented

We added question-level correctness-rate information to the original-tag
replication. For training targets, the rate excludes all responses from the
target learner. Validation/test statistics use only training learners. The
protocol was written before running the added control, but the cohort was
already inspected in earlier experiments, so this remains exploratory.

| Predictor | Test AUC | Test log loss |
|---|---:|---:|
| Question-rate prior only | 0.6532 | 0.6279 |
| Previous best tag-history + telemetry baseline | 0.6269 | 0.6395 |
| Static tags + question rate, without learner history | 0.6596 | 0.6249 |
| Tags + question rate + learner history | 0.6811 | 0.6139 |
| The same model + historical timing/revisions | 0.6815 | 0.6137 |

On the same 12,653 test responses:

- Adding question information to tag/history yields +0.0551 AUC, with paired
  learner-bootstrap interval [+0.0478, +0.0631].
- Adding learner history to the static tag/question model yields +0.0215 AUC,
  with interval [+0.0145, +0.0284]. History retains useful predictive information.
- Adding timing/revisions after those controls yields only +0.000405 AUC,
  with interval [-0.000446, +0.001520]. A telemetry benefit remains unestablished.

These contrasts are predictive feature ablations, not causal effects of
learning or explanations of cognition. We have not retrained an item-aware
neural model, so this is not a fair information-matched architecture ranking.
The finding is that our earlier comparison lacked a strong question-level
control. It does not justify claiming that logistic regression universally wins.

There are 543 unseen-question test responses and 12,110 seen-question responses.
On the unseen subset, the history model scores 0.6551 AUC and telemetry scores
0.6505; this is descriptive and too limited for a general cold-start claim.
Learner bootstrap does not estimate uncertainty over new question populations.

[Full aggregate control results](results/ednet_item_control.json) and
[specified protocol](ITEM_CONTROL_PROTOCOL.md).

## Bounded next study

Working research question:

**Does historical behavioral telemetry add practically useful predictive value
after accounting for question difficulty and learner history, and does that
value persist on unseen questions and another tutoring platform?**

This is an empirical evaluation question, not a claim that the question or
model is new. Its contribution would require a clearly differentiated protocol,
independent replication and a result that matters beyond another pooled AUC.

1. Keep the current item/skill/history logistic control, with and without native
   telemetry. Add a documented established KT comparator receiving comparable
   question/skill information; do not compare an item-aware model to a skill-only
   model as an architecture superiority test.
2. Replicate on the corrected ASSISTments 2009–2010 skill-builder release. The
   [official page](https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010)
   identifies a corrected download that collapses multiple skill tags into one
   response. Use that source and cite the requested ASSISTments system paper.
   Source and schema are verified; download, preprocessing and evaluation are
   **not yet completed**.
3. Preserve native field semantics. ASSISTments supplies first-response time,
   hints and attempts; EdNet supplies bundle wall time and changed answer choices.
   Attempts are not revisions, hints are not evidence inspections, and the two
   duration fields are not equivalent. Fit datasets separately; describe a
   duration-only comparison as platform-specific timing, and report native
   features separately. Never fill unavailable concepts with fabricated zeros.
4. Use learner-disjoint train/validation/test splits, unique response events,
   train-only outcome-derived item statistics and past-only features. Define an
   item-disjoint evaluation separately; existing seen/unseen subgroups alone
   are not a controlled item-novelty experiment.
5. Freeze preprocessing, feature/model budgets and outcomes before inspecting
   the new platform's test labels. Use validation data for any tuning. Report
   log loss, calibration and learner/item support alongside AUC. Use uncertainty
   estimates appropriate to the learner and question populations being claimed.

Practical continuation criterion, chosen as a project decision rather than a
universal standard: telemetry should improve AUC by at least 0.005 with a paired
interval excluding zero, improve log loss, and show a consistent benefit on
both platforms before funding a more elaborate behavioral method. Failure means
retain a null/replication result and stop architecture hunting. Passing still
does not establish novelty or educational usefulness.

## Final-year project and publication boundary

The software contribution remains a scenario-based DeFi learning simulator
with measurable decisions, transfer scenarios, tracing baselines and a
reproducible evaluation pipeline. Public education data tests the prediction
pipeline; it does not validate DeFi learning or financial safety.

For a domain-specific educational claim, a separate educator-reviewed study
must compare instructional conditions on unseen transfer scenarios. The
existing scenario bank and rubrics need review before such a study; present
app participants are insufficient. An observational public-data benchmark
cannot replace that evidence. Participant recruitment and outreach have not
been performed as part of this work.

The defensible current position is: useful implemented project and controlled
exploratory findings; publication readiness and a novel contribution remain
unestablished. A limited search and one improved score cannot guarantee either.

## Reproduce the new control

```bash
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m src.eval.run_item_control
.venv/bin/python -m pytest -q
```

Local reports and target-level predictions are in
`data/processed/ednet/item_control/`; aggregate results are retained in `docs/results/`.
