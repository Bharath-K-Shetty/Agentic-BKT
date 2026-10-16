# EdNet telemetry audit: first results

Completed 2026-10-08. [Protocol](EDNET_AUDIT_PROTOCOL.md),
[aggregate results](results/ednet_telemetry_audit.json),
[source/data preparation](EDNET_PILOT.md).

## Finding

The tested historical timing and answer-revision features do not establish
an improvement over correctness-history DKT. The recommendation-instability
problem is small under the tested scenarios, and the consistency gate offers
little advantage over a simple margin control. These findings do not support
promoting this pilot as a novel robust-tutoring method.

This is a useful completed experiment with negative/limited findings. It does
not show that behavioral information is universally useless: we tested two
features, one selected subset, coarse task categories and a small fixed model.

## Prediction

All models use the same 600/200/200 learner split and the same target responses.
The test set contains 12,776 responses from 200 learners. Neural models use
three initialization/training seeds, with ten epochs each. The logistic models
are fitted once and reused; their repeated scores are not independent runs.

| Model | Mean test AUC | Range over three neural seeds |
|---|---:|---:|
| Historical logistic regression | 0.6070 | Single fit |
| Logistic + historical telemetry | 0.6088 | Single fit |
| Correctness-history DKT | 0.6069 | 0.6064–0.6074 |
| Duration-only DKT | 0.6072 | 0.6068–0.6078 |
| Revisions-only DKT | 0.6073 | 0.6070–0.6077 |
| Duration + revisions DKT | 0.6062 | 0.6058–0.6066 |
| Same-width zero-telemetry DKT | 0.6063 | 0.6056–0.6067 |

Combined-telemetry DKT minus correctness DKT AUC:

| Model seed | Difference | Paired 95% learner-bootstrap interval |
|---|---:|---:|
| 42 | -0.00124 | [-0.00333, +0.00060] |
| 43 | -0.00016 | [-0.00186, +0.00169] |
| 44 | -0.00087 | [-0.00449, +0.00220] |

All three intervals include zero. The matched-width zero-input control performs
similarly. Logistic regression's telemetry gain is +0.00182 AUC, with a paired
interval of [+0.00061, +0.00325]. That is a small sample-specific predictive
improvement, not evidence of an important educational benefit. Means and ranges
over seeds describe training variability on the same learners; they do not
increase the effective learner sample size.

## Recommendation sensitivity

The proxy recommends the lowest-scoring *previously observed* TOEIC category.
There are 11,299 eligible test decision points; 1,477 prefixes have only one
observed category and are excluded. Recommendations are hypothetical: EdNet
does not provide outcomes for our alternative recommended lessons.

Combined-telemetry DKT's fraction of changed recommendations across seeds:

| Alternative recording | Flip-rate range |
|---|---:|
| Duration rounded to one second | 0% |
| Duration +5 seconds | 0–0.027% |
| Revision count reduced to a binary flag | 0–0.009% |
| Duration +30 seconds, unseen by gate | 0.035–0.159% |
| One lost revision, unseen by gate | 0–0.044% |
| Both telemetry channels missing and zero-imputed | 0.221–1.354% |

The cautious rule keeps recommendations only when the clean recording and
three development scenarios agree. It retains 99.973–99.991% of eligible test
points. On unseen missing-telemetry stress, its flip rates are 0.221–1.354%,
essentially unchanged from recommending at every eligible point. The validation
coverage-matched margin control is also similar. There is no convincing added
value for this gate in this pilot. Agreement on its included scenarios is true
by construction and is not independent evidence of generalization.

The additive behavioral logistic model has no recommendation flips: its
telemetry terms shift all category logits equally. That is a consequence of
the chosen feature structure, not a learned robustness result. Its probabilities
can still change, which the full report measures. Correctness-only and
zero-telemetry models are invariant because they ignore the altered channels.

## What this changes about the research plan

The proposed original-tag/disjoint-cohort gate below has since been completed;
see [the replication results](EDNET_SKILL_RESULTS.md). It did not establish a
reliable telemetry gain for DKT.

Do not use “behavior-enhanced DKT is superior” or “our robust gate fixes a major
recommendation failure” as the current paper claim. The evidence supports
neither. Keep the prototype and reproducible benchmark as final-year project
deliverables, and keep these null results in the research record.

Before investing in another model or intervention, the next research gate is
to evaluate the original expert skill tags rather than the seven broad TOEIC
parts, and to check an independently defined evaluation sample. The current
category simplification may obscure both useful telemetry and meaningful
recommendation differences. This is an open explanation, not an established
cause of the limited findings. Any multi-tag encoding must avoid duplicating
one response into multiple sequential known outcomes.

Existing work already studies
[behavioral testing of KT models](https://files.eric.ed.gov/fulltext/ED615512.pdf)
and [student gaming effects on learner modeling](https://arxiv.org/abs/2512.18659).
Our restricted recording-sensitivity experiment does not establish novelty
against that literature. A publication pitch needs a demonstrable difference,
stronger validation and a clear result before claiming a contribution.

## Reproduce and inspect

```bash
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m src.eval.run_ednet_audit
.venv/bin/python -m pytest -q
```

Local artifacts in `data/processed/ednet/telemetry_audit/` include the complete
report, fifteen model checkpoints, and compressed clean target-level predictions.
Aggregate results are saved under `docs/results/`; learner logs and checkpoints
remain gitignored. The default runner verifies the pilot CSV against its hash
manifest and uses the exact protocol settings above.

Verification: 61 tests pass, including past-only features, unchanged answers
under recording scenarios, future-telemetry exclusion, capacity matching,
single-category exclusion and an example where the gate fails on unseen stress.
Three controls have zero measured probability changes under every scenario.
