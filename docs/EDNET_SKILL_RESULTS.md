# Original-skill replication results

Completed 2026-10-08. [Protocol](EDNET_SKILL_PROTOCOL.md),
[aggregate results](results/ednet_skill_replication.json),
[preceding telemetry experiment](EDNET_AUDIT_RESULTS.md).

## Outcome

The original expert tags improve the historical logistic baseline over the
seven broad TOEIC parts. They do not establish a consistent telemetry benefit
for the tested DKT extension. The strongest tested predictor is the simpler
tag-based logistic model. This is useful evidence for model/representation
selection, but it does not establish a novel algorithm or learning benefit.

## Independent learner cohort

The new cohort has 1,000 learners and 65,474 retained responses. Every learner
from the first 1,000-learner pilot was excluded; measured overlap is zero.
Both representations use the same new 600/200/200 learner split, with 12,653
test predictions. This is replication on disjoint learners from the **same
EdNet platform**, not validation on an independent dataset.

All original question tags are preserved. The downloaded question metadata
contains 188 known tags, plus a separate unknown-metadata category for -1.
Only three retained cohort responses have unknown tags; none occur among test
targets, so no unknown-tag test performance can be estimated. All test-target
tags were observed in the new training cohort. The report includes training
counts and per-part diagnostics.

## Paired comparison

Neural scores below are averages across training seeds 42,43,44 on the same
test learners. Logistic models are fitted once per representation.

| Model | Broad parts: test AUC | Original tags: test AUC |
|---|---:|---:|
| Historical logistic regression | 0.6022 | 0.6260 |
| Logistic with timing/revisions | 0.6033 | **0.6269** |
| Correctness DKT | 0.6030 | 0.6091 |
| DKT with timing/revisions | 0.6048 | 0.6092 |
| Same-width zero-telemetry DKT | 0.6044 | 0.6092 |

Original tags minus broad parts for the historical logistic baseline is +0.02386
AUC, with a paired 95% learner-bootstrap interval of [+0.01466, +0.03034].
The behavioral logistic difference is similar. DKT's tag-versus-part point
estimates are positive, but their bootstrap intervals include zero.

Within the original-tag DKT, timing/revisions minus correctness-only:

| Training seed | AUC difference | Paired 95% learner-bootstrap interval |
|---|---:|---:|
| 42 | -0.00067 | [-0.00289, +0.00160] |
| 43 | +0.00040 | [-0.00161, +0.00193] |
| 44 | +0.00062 | [-0.00097, +0.00232] |

Every interval includes zero. The telemetry and zero-input control means are
nearly identical. In the broad-part model, timing/revisions have small positive
point differences, but the same-width zero control accounts for most of that
gain; telemetry-minus-zero intervals include zero for all seeds.

The tag-based behavioral logistic model beats tag-based behavioral DKT by
roughly 0.016–0.019 AUC across seeds; the paired intervals exclude zero in favor
of logistic regression. Adding telemetry to the tag-based logistic model itself
gains only +0.00088 AUC, with interval [-0.00062, +0.00281]. A useful independent
telemetry gain is not established there either.

## What the implementation guarantees

A multi-tag response stays one event. Unit input mass is shared across its
tags. The next response uses the mean of target-tag logits and exactly one
binary loss. There are no exploded rows that let one response's correctness
leak into another tag of the same response. Logistic training also uses one
target row per response. Tag vocabulary uses public content metadata; priors
and fitted parameters use training learner responses only. Current-target
timing/revisions never enter the predictors.

The tag neural model has 58,973 parameters without telemetry, versus 6,375
for the part model; the respective telemetry models have 59,229 and 6,631.
Comparing representations therefore changes both information and model size.
The within-representation zero-telemetry controls match parameter counts, but
the cross-representation comparison does not isolate semantic granularity
causally. Results apply to this fixed ten-epoch, hidden-size-32 training budget;
they do not show that all neural KT models are inferior.

## Research decision

The earlier null result was not simply fixed by replacing seven broad categories
with original skill tags. Retain both experiments and their controls. Do not
pitch a behavior-enhanced DKT breakthrough or a demonstrated need for the
recommendation stability gate from this evidence.

For the final-year project, the simulator, data pipeline, multi-tag implementation
and controlled replication are concrete deliverables. For a paper, the next
decision should concern a clearly differentiated research question and external
validation, rather than further model changes intended only to raise AUC.
Neither experiment validates DeFi educational effectiveness.

## Reproduce

```bash
.venv/bin/python -m src.features.prepare_ednet --seed 2026 --exclude-input data/processed/ednet/pilot/interactions.csv --output data/processed/ednet/replication
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m src.eval.run_ednet_skills
.venv/bin/python -m pytest -q
```

The preparation manifest records source/output hashes, cohort exclusion hash,
tag mapping and selection rules. The runner verifies both dataset and exclusion
hashes and rejects any cohort overlap. Local detailed results, 18 neural
checkpoints and compressed target-level predictions are in
`data/processed/ednet/skill_replication/`. The aggregate snapshot omits learner
IDs and includes package versions, training configuration and the protocol hash.

Verification: 67 tests pass. New checks cover canonical/unknown tags, unit input
and target mass, one target per response, single-tag backward compatibility,
past-only features, prior-cohort exclusion and a complete small replication run.
