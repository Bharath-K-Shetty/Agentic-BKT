# Solana AI/ML feasibility and novelty review

## Implementation update 16 October 2026

The selected project is now cold-signer execution-risk research, with a working
integrated prototype at `/live`: fresh mature-block histories, actual HGB
inference, current balance/fee/unsigned-simulation checks, and a local study
recorder linking exact checked messages to later confirmed receipts. The same
historical feature extractor is reused. Live scores are experimental because
sampling and deployment conditions differ from training; stale or insufficient
history causes abstention. No ML score automatically blocks a transfer.

A five-period audit covers 102,443 cold-history transactions and finds unstable
warning utility. A local validator verifies fees on execution failure and the
prospective recording workflow. Neither demonstrates incremental ML benefit over
normal preflight, live calibrated accuracy, or fee/time savings. These require
prospective observations and a policy comparison, not more historical dashboard
examples. The updated paper and viva guide preserve these limitations. See
`webapp/README.md` and `docs/results/solana_ml_fee_policy_summary.json`.

The project-selection review below is retained as historical context.

Reviewed: 9 October 2026. User requirement: an AI/ML research project using real
blockchain data, rather than a security-review tool or an education model with
blockchain-themed questions. This review supersedes the earlier audit-tool
recommendation for project selection; existing experiments are retained.

## Decision

**Real blockchain ML is feasible, but the proposed generic temporal-GNN rug-pull
detector has substantial overlap and is not yet a defensible novelty claim.**
Proceed only to a bounded data/baseline feasibility experiment. Do not announce
a new architecture or promise publication before that experiment identifies a
specific limitation and a measurable improvement. A different chain, a dashboard,
or an added attention layer would not establish novelty.

## Closest work actually located

| Work | Existing contribution | Consequence |
|---|---|---|
| [TokenScout, CCS 2024 author paper](https://cactilab.github.io/assets/pdf/3658644.3690234.pdf) | Temporal graph learning and contrastive refinement for early Ethereum scam-token detection, including creator/investor representations | Temporal graphs, early detection and creator behavior are established |
| [RugScreener, IEEE TIFS 2025](https://ieeexplore.ieee.org/document/11201921/) | Temporal GNN with memory/attention for Ethereum rug-pull risk | Memory and temporal attention are insufficient distinctions |
| [Catching the Rug, August 2026 preprint](https://arxiv.org/html/2608.20271v1) | Early Solana prediction from five-minute trading features; PumpFun/Raydium generalization | Solana, short observation windows and cross-platform testing already overlap |
| [MELT, May 2026 v2](https://arxiv.org/html/2602.13480v2) | Parsed Solana launch traces, coordination/bundle information, engineered features, risk annotations and ML benchmarks | Wallet coordination and public behavioral-trace learning are established |
| [Early Rug-Pull Warning on Solana, public research repository](https://github.com/Gauravpoudel7/AI_RugPull_Prediction) | Chronological prefix evaluation comparing trees, GCN/TGN and cross-token wallet memory; reports trees outperforming tested graph models | Our original comparison is already substantially explored; its results have not been independently rerun here |
| [SolRugDetector, March 2026 preprint](https://arxiv.org/html/2603.24625v1) | Solana incident characterization and post-hoc detection; explicitly identifies early warning as future work | Useful motivation, not proof that early prediction remains unstudied |
| [LROO, March 2026 preprint](https://arxiv.org/html/2603.11324v1) | Temporally constrained on-chain/OSINT prediction with TabPFN and calibration | Leakage controls, multimodality and calibration alone are insufficient novelty |
| [TM-RugPull, February 2026 preprint](https://arxiv.org/html/2602.21529v1) | Multimodal dataset with lifespan-midpoint feature boundaries | A midpoint before an event is not necessarily a decision time selectable prospectively |

TokenScout's CCS paper and its later TDSC article belong to the same research
family; do not count them as independent discoveries merely because venues differ.
MELT was called MemeTrans in v1; the current v2 title and repository are MELT.
Venue labels above distinguish published articles, preprints and repository work.

The closest public repository's results are author-reported, not reproduced
evidence that GNNs can never help. Selected source reads confirm chronological
splits, prefix budgets, a migration-based warning anchor and two evaluation
regimes. Full implementation correctness and fair hyperparameter tuning have
not been independently established. Its warning anchor also should not silently
become the actual first harmful transaction in our experiments.

## Public-data feasibility

### MELT: strongest initial source, with important scope limits

The [official repository](https://github.com/git-disl/MELT) releases metadata,
labels and code directly and links parsed transaction/bundle archives on Drive.
The paper describes a cohort selected through successful migration to a DEX.
That supports a conditional post-migration-risk task; it is not an all-launch
population or a representative set of confirmed fraud incidents. Risk annotations
combine price behavior and manual trajectory judgments.

**Verified locally:** the pinned `memecoin_list.jsonl` contains 46,139 records,
and every record has the same `creator` value. The paper's collection description
identifies this as the platform account initiating migration. It is not a usable
token-deployer identity for creator-disjoint evaluation. The record timestamps
likewise must not be assumed to be launch times. Actual creation events and
deployer roles need reconstruction and validation from parsed transactions.

The metadata file has 46,139 records; the subsequently downloaded archive has
45,609 token histories and the released CSV has 41,470 labeled tokens. All 41,470
labeled tokens join the archive and migration metadata. The archive is now
available locally and the [first prefix-only pilot](SOLANA_PREFIX_BASELINE_RESULTS.md)
has been executed. These counts describe different released assets, rather than
interchangeable cohort sizes. The source states CC BY-NC 4.0. Full-lifecycle
feature files cannot substitute for recomputed early prefixes.

### SolRPDS: useful reference, unsuitable as the only early graph dataset

[SolRPDS](https://huggingface.co/datasets/DeFiLab/SolRPDS) releases pool summaries.
The locally inspected 2021 JSON has 1,703 records and 12 fields: pool/mint IDs,
liquidity totals/counts, activity timestamps, a last-swap ID and inactivity status.
It does not supply a transaction-edge sequence in that file. Inactivity is not
independent proof of developer fraud. Lifetime totals and last-activity fields
cannot be treated as known at launch. Neither an early temporal graph nor honest
prefix features can be reconstructed from these summaries alone.

### PumpFun Launch Corpus: rich raw-data lead, not ready ground truth

[The uploader's card](https://huggingface.co/datasets/Slinky21/Pumpfun_Memecoin_Corpus)
lists linked token/trade/snapshot tables. Its
[known-issues document](https://huggingface.co/datasets/Slinky21/Pumpfun_Memecoin_Corpus/blob/13bec2bf3089d56d50c35e602616d1b993bb37f5/KNOWN_ISSUES.md)
reports missing/inconsistent prices, stale wallet summaries, collection gaps,
concentration corrections and synthetic migration sentinels. The card also
mentions ongoing survival/clustering research. These are uploader claims, not
independently verified facts about every row.

The metadata license says MIT while the prose says CC BY 4.0; resolve this before
redistribution. No parquet contents were inspected. Do not adopt cleaning rules
blindly: one account-role claim in the issues document conflicts with the
[canonical System Program ID](https://solana.com/docs/core/programs/builtin-programs),
which is `11111111111111111111111111111111`.

### Forward PumpFun capture: a different target

[The trenches release](https://huggingface.co/datasets/Tr4m0ryp/trenches-pumpfun-forward-2026-08)
documents a vendor-curated capture, completion/hazard labels, timing limitations
and trade files from a different population. It is a possible methodology lead,
not a ready confirmed-rug corpus. We read its documentation/manifest, not parquet
contents. Its restrictions and joins need separate review before use.

### Existing HOMIE data cannot validate this proposal

EdNet contains education interactions. The earlier wallet pipeline measures
heuristic wallet losses/abandoned holdings rather than independently established
token fraud. Neither is the ground truth for the proposed token-level prediction
task. Keep their results separate.

## A narrower AI/ML hypothesis worth testing

Working question: **Can learning from early transaction relationships improve
future adverse-outcome prediction when coordination links are uncertain and
operators or market regimes change?**

The model input would be an event-ordered wallet/token graph. Observed transfers,
co-purchases, same-funder relations and bundled submissions are different edge
types with different evidential strength. A shared exchange funder does not
establish common control; a bundle does not by itself establish malicious intent.
Relationship confidence must use information available by the decision time.

A candidate method could learn how much to trust each relation type and combine
graph representations with a calibrated future-risk head. This is proposed work,
not an implemented or proven novel algorithm. Confidence weighting, graph learning
and calibration all have prior art. The contribution would need a precise
mechanism and reproducible benefit beyond their straightforward combination.

First test whether the graph adds information beyond engineered coordination
features. If it does not, accept that result rather than attaching a GNN solely
to make the project look advanced. Classical ML on blockchain data is still an
AI/ML project, although a routine classifier alone is a weak methods-paper claim.

## Freeze the task before training

Start with a task the verified data actually supports: prediction of a stated
post-migration adverse market outcome among migrated tokens. Call it risk or
drawdown prediction unless independently reviewed incident evidence supports
the stronger fraud label. Separate liquidity withdrawal, insider selling and
ordinary market decline wherever evidence permits.

Use fixed launch-relative decision times, such as 60 and 300 seconds, only after
launch semantics are validated. An alternative is a migration-time decision with
an explicitly conditional target. These are different tasks and must not be
silently mixed. Do not select the observation window using the token's future
lifetime midpoint. Outcomes already realized before the decision are detection
cases, not future warnings.

For true time-to-event modeling, reconstruct event time from the outcome path.
A label or minimum-price summary alone cannot locate the first harmful event.
Observation end is censoring, not a negative label; migration is not itself a rug.
Handle adequate outcome follow-up, recording gaps and data-end cases explicitly.

Use chronological train/validation/test splits, embargo overlapping outcome
windows, and require training labels to be observable before the training cutoff.
Then evaluate a separate unseen-creator subset using validated deployer identities.
Define any operator grouping with evidence, avoid joining ordinary exchange users
into one operator, and disclose how held-out grouping was constructed. Future
links must never enter training features or graph memory.

Compare logistic regression, tuned trees, an MLP, a temporal sequence model and a
standard temporal GNN. Give every model identical samples, eligible information,
labels and tuning budgets; include trees with the graph-derived features. Add
the proposed confidence mechanism only after a baseline limitation is measured.

Report average precision and lift over prevalence, warning recall at a fixed
false-alert budget, calibration, and warning time to the defined outcome.
Choose thresholds on validation data. Use paired uncertainty estimates that
respect repeated tokens/operators, and report results across dates/regimes.
Inspect dropout, missing-price and relation-type ablations; synthetic edge
corruption can supplement, not replace, observed data-quality evaluation.

## Go/no-go gate

Proceed to a methods claim only if:

1. Parsed transactions are accessible with usable event order, creation roles,
   early prefixes and sufficient outcome follow-up.
2. The chosen labels have a documented meaning and no target-derived features.
3. A distinct mechanism addresses a measured baseline failure rather than simply
   repeating graph-versus-tree comparisons already available.
4. Gains persist with matched information, creator/date separation, ablations
   and a held-out cohort; model complexity and computation are justified.

If (1) or (2) fails, change the task or source before training. If (3) or (4)
fails, retain an honest replication/empirical result and reassess publication
scope. An empirical paper can be valuable, but ordinary replication is not
automatically a publishable new contribution.

## Audit trail and limitations

[The read-only probe](../research/solana/probe_ml_sources.py) collected 18 pinned
documents/code/data files. The [inventory](results/blockchain_ml_source_probe.json)
records URLs, revisions, byte counts, content hashes and the two JSON schema/count
checks. Cached content is under ignored `data/raw/solana_ml_probe/` and is not
redistributed. That initial probe did not execute upstream programs or train
models. The later local pilot trained our own prefix baselines; it did not
reproduce another author's exact experiment or audit a complete repository.

Searches covered early Solana rug prediction, temporal/heterogeneous graph
methods, coordination, creator generalization, warning time, survival, calibration
and public datasets. Coverage is incomplete. Absence from these searches does
not establish global novelty. The recommendation is a conditional feasibility
study, not another unconditional project switch or publication guarantee.
