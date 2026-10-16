# Next publication gate: useful warnings under delayed outcomes

Candidate research question, not an established novelty claim:

**When collapse outcomes arrive at different times, can a Solana launch-risk
model maintain a useful false-alarm/recall tradeoff on later tokens?**

**Executed follow-up:** the [delayed-label replay](SOLANA_DELAYED_REPLAY_RESULTS.md)
evaluates seven controls on 8,000 newly sampled tokens (4,295 eligible;
2,496 evaluated across three test periods). The primary weighted correction
increases recall by 0.765 percentage points, but also increases FPR by 0.264
percentage points and misses the prespecified gate. Do not promote it as a
successful new algorithm. The outcome-dependent migration-delay finding is a
candidate empirical observation, not an established original contribution.
The remaining priority is independent evidence and prior-art differentiation,
not tuning more variants on these now-used test tokens.

The confirmation experiment tests fixed thresholds across calendar periods.
Its outcomes determine whether this question merits an intervention experiment.
Ranking metrics alone do not establish reliable alerts. A changed FPR alone also
does not prove a research gap: sampling noise, class composition and ordinary
calibration must be checked first.

**Current evidence:** the primary coordination AP delta is -0.0023 with a
day-block interval including zero. Fifteen of 36 diagnostic comparisons have
test FPR above 5%, but only one has a marginal Wilson lower bound above 5%, without
multiple-comparison correction or wallet-cluster adjustment. This does not
establish a systematic alarm-budget failure. Do not build a novelty claim on it.
First strengthen the feature baselines and obtain an independently defensible
period before selecting a proposed intervention. See the
[completed confirmation](SOLANA_CONFIRMATION_RESULTS.md).

The [stronger-baseline stage](SOLANA_STRONG_BASELINE_RESULTS.md) is now executed
on a third sample, excluding the earlier 18,000 ranks. Increasing ordinary prefix
features from 27 to 120 improves RF AP by +0.0129, with a paired day-block interval
above zero. The corresponding AUROC interval includes zero; operating-point
benefits vary across periods. This raises the baseline a proposed method must
beat. It does not establish a new learning mechanism.

The newer Slinky21 corpus has now been inspected at the Parquet level: three
tables and one trade shard. Its periodic post-migration observations do not
reproduce our transaction-minimum endpoint. Exact independent-period validation
is still incomplete. Do not claim it from the downloaded files alone. Aligning a
new snapshot endpoint would require raw post-migration data from both sources,
an explicit protocol change and new evaluation, rather than reusing `min_ratio`
as if it were a snapshot label.

A focused follow-up would compare, on identical saved predictions and decisions:

1. A frozen validation threshold.
2. A recent-window threshold using only outcomes already available at each decision.
3. A standard class-conditional conformal/risk-control baseline under its actual assumptions.
4. An oracle using outcomes before they mature, clearly marked as an invalid prospective control.

Do not introduce a new method unless these controls demonstrate a specific
failure. The population remains eventual migrants until an all-launch endpoint
and appropriate data source are defined. Keep price collapse distinct from fraud.
Report how variable migration/label delays select the available calibration
cohort, and do not silently treat unavailable outcomes as safe tokens.

Metrics must include recall at the alert budget, observed FPR with uncertainty,
calibration, day-by-day coverage and the fraction of decisions receiving no
confident warning. Report computation and outcome-availability assumptions.
Use a new confirmation cohort or independent period for a chosen intervention;
current test outcomes cannot repeatedly become tuning targets.

## Prior art that the contribution must exceed

[Conformal Risk Control, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf)
already provides model-agnostic risk control and extensions. Applying it to Solana
alone would be an application, not a new algorithm.

[Online conformal prediction under arbitrary distribution shifts, JMLR 2024](https://www.jmlr.org/papers/v25/22-1218.html)
and [CAP, JMLR 2025](https://jmlr.org/papers/v26/24-0452.html)
already address adaptive prediction and online selection. Coverage/FCR guarantees
are not automatically a bound on token-alert false positives.

[Anytime-Valid Conformal Risk Control, 2026 preprint](https://arxiv.org/abs/2602.04364)
also addresses growing calibration data. We have read its abstract; its exact
assumptions and applicability to delayed blockchain outcomes still need review.

The [existing Solana prefix repository](https://github.com/Gauravpoudel7/AI_RugPull_Prediction)
already studies rich coordination features, temporal motifs and graph baselines.
The [earlier literature review](SOLANA_ML_FEASIBILITY_REVIEW.md) also locates
calibrated blockchain-risk work. A separate domain or combination of these ideas
does not by itself establish novelty.

## Independent-data lead found during this run

[ian05012/solana-memecoin-dataset](https://github.com/ian05012/solana-memecoin-dataset)
documents June 2026 detection snapshots, wallet trades and forward-return labels.
Its detection-time snapshots and return endpoints differ from our pre-migration
20-minute collapse endpoint. The documentation and file inventory were read;
Parquet contents, timing integrity and joins were not validated here. It is a
lead for a separate study, not external validation already completed. Snapshot
wallet tags and profiles must be checked for retrospective information.

## Defensible deliverable

A publishable empirical contribution would need a clear finding that existing
evaluations miss, strong established controls and independent confirmation.
A new-method paper additionally needs a distinct mechanism and demonstrated
benefit. We have neither established acceptance prospects nor proven global
novelty. Retain unsuccessful experiments instead of renaming them as innovations.
