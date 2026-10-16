# Evaluating transaction failure risk for Solana signers without available history

Manuscript for author and supervisor review. Authors: Bharath Kumar Shetty, Deepthi P. Salian, Shreya Shetty and Swaroop Nellitheertha, Department of Artificial Intelligence and Machine Learning, MITE. A target venue and immutable public artifact release remain to be supplied. Historical ranking results and later implementation diagnostics are distinguished below.

## Abstract

Historical signer outcomes can provide strong aggregate predictions of blockchain transaction failure while offering little information when signer history is unavailable. We study this problem on Solana using declared account roles and delayed historical outcomes. Four chronological evaluation windows contain approximately 1.59 million sampled transaction records across twelve dates. A role-separated history representation summarizes failures involving non-signer writable accounts and augments a gradient-boosted baseline containing transaction structure, signer history and read-only account and template context. Cold-history average precision improves in all four windows, although the confidence interval includes zero in one window. Account-identity controls yield mixed results, motivating a narrower first-appearance evaluation. On a reserved test containing 17,904 first signer appearances, writable history increases average precision from 0.1688 to 0.2004 after both models receive the same delayed account-identity score. The paired hourly bootstrap interval for the difference is [0.0168, 0.0501]. Ranking improvement does not imply better operational risk estimates: inherited validation thresholds produce high false-positive rates, and calibration deteriorates in this comparison. The contribution is an empirical evaluation of missing-history reliability prediction and a reproducible account-context benchmark, rather than a new learning algorithm or demonstrated transaction-failure prevention system.

## Introduction

Transaction reliability is an operational concern for applications interacting with a blockchain. A submitted operation may fail during execution even after it reaches a block. On Solana, a large empirical study has characterized failure initiators, programs, error categories and temporal patterns [1]. These descriptive findings motivate predictive evaluation, but a model's aggregate performance does not establish its usefulness for a signer with no available outcome history.

A transaction can involve accounts already observed in other transactions even when its signer is unfamiliar to an observer. We ask whether failures involving these accounts supply transferable execution-risk signal. The hypothesis concerns observed participation, not ownership: two signers touching the same account need not belong to the same operator. Nor does a shared account's historical failure rate identify the cause of a new failure.

The task is retrospective execution-risk screening conditional on eventual block inclusion. The archive supplies inclusion checkpoints and outcomes but not actual submission times or unlanded attempts. We restrict predictive inputs to declared account information and earlier outcomes whose assumed availability time has elapsed. This prevents current execution receipts from supplying the answer, while preserving the limitation that the checkpoint is reconstructed after inclusion.

The study contributes a concrete benchmark for transactions with unavailable signer history, an ablation of writable-account history against structure and read-only context, and a reserved first-appearance comparison with learned account-identity scores. It also documents the distinction between improved failure ranking and poor calibration. History aggregation and gradient boosting are established techniques; algorithmic novelty is not claimed.

## Related work

Zheng et al. characterize Solana failures at scale through initiator, program, error and temporal analyses [1]. Our evaluated question differs: we predict individual observed execution outcomes using declared account roles and delayed feedback, explicitly separating signers without available history. The distinction is an empirical task and evaluation boundary, rather than the discovery that Solana transactions can fail.

Relational information transfer is established in transaction learning. BRIGHT uses historical entity context and a graph architecture for real-time e-commerce fraud detection [2]. Our task is execution reliability rather than fraud, and our models use tabular summaries rather than a graph neural network. BRIGHT also demonstrates why information availability must constrain historical prediction. Neither relational transfer nor temporal information restrictions are new in themselves.

The broader review includes Ethereum outcome classification, a Solana transfer-network study, Ethereum multisignature anomaly triage and a TRON transaction simulation. Their task distinctions are recorded in the accompanying evidence report [4]. Before submission, the literature section needs complete bibliographic entries and comparison of these studies' full evaluation protocols. The reviewed sources do not establish worldwide absence of an equivalent cold-signer benchmark.

## Data and task definitions

We use public transaction records from SolArchive [3], under CC BY 4.0, pinned to Hugging Face revision `6588cad2832e62be03972ac80d69c6af11d631c8`. Each selected date contributes the first row group of one Parquet shard. The first two windows use the lexicographically first shard; later windows use alternate shards selected by a fixed date and seed hash based on file counts. Selection does not depend on transaction outcomes. This is neither complete chain coverage nor a verified uniform random sample.

Selected fields are transaction signature, declared accounts with signer and writable flags, block timestamp, block slot and status. Block slot and signature order tied checkpoints; neither is a model feature. Status maps `Success` to zero and `Fail` to one. Identical signatures with identical selected payloads count once; conflicting duplicates or date mismatches abort processing. Fifteen identical repeated rows occur in the second date of the initial window. The twelve extracted groups contain 1,588,408 raw rows before deduplication and model partition exclusions.

We call the first declared signer the primary signer. A **cold-history transaction** has no matured outcome for that address as primary signer in the sampled replay. It may be a repeat transaction while earlier outcomes remain pending. A **first appearance** is the address's first occurrence as primary signer in that replay, regardless of label maturity. Neither definition establishes that an address is new to Solana or that its operator is new.

The archive does not contain complete instruction payloads in the selected table. Read-only account templates are sets of declared read-only accounts, not verified lists of invoked programs. Historical account resolution before execution is assumed. The later prototype constructs declared roles directly for plain SOL transfers and reads parsed account roles from public RPC blocks; this does not reconstruct historical submission conditions.

## Models and information availability

At checkpoint time t, an earlier transaction contributes its label only if its block checkpoint plus 3,600 seconds is no later than t. Features are computed before scheduling the current outcome. Histories update during validation and testing using earlier matured outcomes, making the evaluation an online-feedback replay with a fixed fitted boosting model.

Account participation is separated into primary signer, non-signer writable accounts, non-signer read-only accounts and exact read-only templates. Ten common infrastructure addresses are excluded from contextual histories and retained as structural presence indicators. For each role and account key, a smoothed historical rate is `(failures + 20 × global_rate) / (count + 20)`, where `global_rate = (available_failures + 1) / (available_count + 2)`. Multi-account roles are summarized through observed fractions, log-count means and maxima, and rate means, maxima, minima and standard deviations.

Structural features contain account and role counts, duplicate-account counts and infrastructure indicators. Current labels, logs, errors, actual consumed compute, balances, paid fees and block position are excluded. Time controls history availability and partitions, but is not a numeric model input.

Seven original models comprise signer-rate, read-only-rate and template-rate scorers; structure-only boosting; structure plus signer history; structure plus signer and read-only/template history; and all preceding features plus writable history. Histogram gradient boosting uses 150 iterations, at most 15 leaves, minimum leaf size 40, L2 regularization 5 and no early stopping. Three seed predictions are averaged; deterministic fitting means these seeds are not independent replications.

The identity control is an SGD logistic learner with role-tagged account identities and read-only templates hashed into 1,048,576 nonnegative dimensions. Binary tokens are L2 normalized. It uses regularization 0.0001, seed 42 and one chronological pass. Predictions precede each batch's learning update. Labels become eligible after one hour, with ten-minute update batches adding up to ten minutes of further delay. The resulting prequential score is supplied to both history-based boosting models. Thus the stronger baseline receives information from all declared account identities, including writable identities; the tested addition is the explicit writable-history summaries. The identity architecture and regularization are fixed rather than exhaustively tuned.

## Evaluation protocol

Each window uses one training date, one validation date and one test date. The first six training hours build history. Training and validation rows are excluded when their labels would not be available before the next date boundary. Test labels evaluate predictions and update later histories only after the stipulated delay. Models are fitted separately in each window using unchanged parameters.

| Window | Training date | Validation date | Test date | Fitted training rows | Validation rows | Test rows |
|---|---|---|---|---:|---:|---:|
| Initial | 2025-11-01 | 2025-11-02 | 2025-11-03 | 92,782 | 125,864 | 131,759 |
| Confirmation | 2025-11-08 | 2025-11-09 | 2025-11-10 | 92,135 | 126,214 | 133,071 |
| Extension | 2025-11-22 | 2025-11-23 | 2025-11-24 | 93,812 | 127,050 | 131,638 |
| Reserved refined test | 2025-11-29 | 2025-11-30 | 2025-12-01 | 100,517 | 126,840 | 131,907 |

The original primary endpoint is the cold-history difference in positive-class average precision between the read-only-context baseline and writable-context model. The first confirmation retains the initial settings. The extension follows after the first two results. Identity controls and first-appearance analyses are exploratory on these three windows.

Before inspecting the fourth window's transaction outcomes, a refined endpoint is fixed: first-appearance average precision for writable versus read-only history when both models receive the identity score. The local success condition requires a positive difference and a paired-hour interval entirely above zero. This is a reserved historical evaluation, not public preregistration or a live prospective trial. The change in hypothesis follows earlier diagnostics and is explicitly disclosed.

We report average precision, AUROC, Brier loss and operating metrics. Thresholds are chosen on global validation data under a 5% false-positive budget and then held fixed. Differences in average precision use 500 paired bootstrap draws of hourly blocks within the test day. Signer-address resampling supplies an additional dependence diagnostic. These intervals condition on fitted predictions and sampled days; they exclude retraining uncertainty and independent operator identification.

## Results

Signer history alone gives overall average precision between approximately 0.80 and 0.83, but cold-history scores of 0.062–0.073 are close to subgroup failure prevalence. This is partly structural: absent signer outcomes, the scorer mostly returns the changing global prior. Aggregate performance therefore cannot substitute for an evaluation of missing-history transactions.

| Test date | Cold-history rows | Read-only baseline AP | Writable-context AP | AP difference and hourly 95% interval |
|---|---:|---:|---:|---|
| 2025-11-03 | 19,621 | 0.3193 | 0.3787 | +0.0594 [0.0390, 0.0865] |
| 2025-11-10 | 20,636 | 0.2249 | 0.2514 | +0.0265 [0.0049, 0.0498] |
| 2025-11-24 | 21,028 | 0.2052 | 0.2231 | +0.0179 [−0.0138, 0.0656] |
| 2025-12-01 | 19,577 | 0.1734 | 0.2185 | +0.0451 [0.0253, 0.0637] |

All point differences are positive, but the extension interval crosses zero. Adding identity scores produces cold-history gains of approximately 0.0718, 0.0041, 0.0353 and 0.0391 across the four windows. The second interval crosses zero. These results prevent a claim of universal advantage beyond learned account identities.

On the reserved first-appearance endpoint, 17,904 transactions have failure prevalence 5.88%. The identity-controlled read-only baseline reaches average precision 0.1688; writable context reaches 0.2004. Their difference is 0.0316 with hourly 95% interval [0.0168, 0.0501], satisfying the locally specified ranking criterion. AUROC rises from 0.7288 to 0.7545.

Operational and calibration results are less favorable. At inherited global-validation thresholds, first-appearance false-positive rates are 22.66% for the baseline and 28.65% for writable context. Recall rises from 50.90% to 64.48%, but this is not a matched-false-positive comparison. Brier loss worsens from 0.0967 to 0.1218. The stronger ranking model therefore cannot be described as an overall better probabilistic predictor or alert system. These results also show why validation-only threshold selection does not guarantee a test-period budget.

## Discussion and threats to validity

The findings support a bounded interpretation: explicit account-participation histories can improve ranking for sampled signers without outcomes, including a reserved first-appearance comparison after an identity-score control. They do not establish that writable accounts cause failure or that the gain extends to all applications and market regimes. Some failed operations may be protective rejections, so reducing failures is not automatically a beneficial intervention.

Sampling is a central limitation. One group per date may reflect partitioning biases, and a sample-cold address may have extensive unsampled history. The archive's dated inventory is discontinuous. All windows come from the same provider and a limited period, leaving independent-source generalization unresolved. Range and derived-file hashes support extraction reproducibility, but original complete-shard hashes have not been verified.

The information boundary is also limited. Inclusion time is not submission time and unlanded attempts are absent. The later live implementation covers plain SOL transfer roles, not arbitrary historical account resolution. The identity control uses batching while exact participation histories do not, introducing a feedback mismatch. Additional validation-tuned identity models and matched update schedules could alter the comparison.

Hourly resampling captures some within-day temporal dependence but not uncertainty across independently sampled regimes. Address clustering does not identify operators. The refined endpoint follows earlier exploratory findings; its reserved confirmation supplies additional evidence without making the earlier analyses confirmatory. No multiplicity-adjusted claim is made across all diagnostics.

For practical use, cold-specific calibration and independently tested operating thresholds are required. Comparison against live transaction simulation additionally requires actual submission, simulation and execution observations. The current archive cannot demonstrate superiority to simulation, fee savings or prevented failures.

## Implementation and operational follow-up

A fifth chronological window uses December 3 for training, December 4 for validation and December 5, 2025 for testing. Its settings were fixed before those outcomes were inspected. On 19,515 first appearances, the identity-controlled baseline and writable-context models achieve average precision 0.2207 and 0.2393, respectively; the difference is 0.0186 with paired-hour interval [0.0095, 0.0288]. This supports the ranking result without establishing operational utility.

A subsequent exploratory policy audit evaluates 102,443 cold-history transactions, including 6,410 failures, across all five test dates. Exported non-identity HGB models use isotonic calibration fitted on early cold validation data and thresholds chosen on later cold validation data. On December 5 the deployed context threshold warns on 357 failures and 649 successes. Fixed cost-based thresholds are also evaluated: for assumed failed-attempt fee F and cost C of blocking a success, the theoretical probability threshold is C/(F+C). Calibration is imperfect, so the rule need not deliver its assumed utility. With C/F=5, pooled context warnings cover 107 failures and 60 successes and miss 6,303 failures; hypothetical net utility TP-5FP is -193 fee units. All three evaluated positive cost ratios (1, 5 and 10) yield negative pooled utility. These are assumed costs, not paid fees or measured savings. The audit is retrospective and must not be promoted to an independent confirmation.

The integrated FastAPI prototype constructs fresh features with the same participation-history extractor, using mature public RPC block samples. At verification it collected 302 devnet transactions in 16 sampled blocks and 8,871 mainnet transactions in eight sampled blocks, spanning roughly eight hours per network. Earlier outcomes must be at least one hour old, a snapshot must be no older than one hour, and minimum history requirements are enforced. Actual HGB inference runs on the resulting feature row. Because source, sampling and operating conditions differ from training, outputs are explicitly experimental model scores: no validated live probabilities or automatic ML blocking decisions are supplied. Central training-range diagnostics do not establish distributional equivalence.

Current balance and fee checks and an unsigned simulation accompany each candidate. Signature verification is disabled; this observation is distinguished from a signed submission's normal preflight. A local SQLite study store records the candidate message hash, feature/history/model hashes and prediction before an outcome can be attached. A confirmed receipt is accepted only for the exact checked message and a later slot and timestamp. Missing receipts remain unknown outcomes. Observed paid fees and elapsed observation intervals are recorded without relabelling them as savings.

A controlled local-validator experiment proves the fee mechanism: an execution failure deliberately submitted with preflight disabled pays 5,000 lamports, while a matched checked-and-stopped attempt pays zero. Normal preflight also rejects that error at zero cost. A separate local successful transfer verifies the decision-to-matching-receipt workflow. These functional checks establish neither superiority over standard preflight nor ML-driven fee or time savings. A prospective study of candidates passing standard preflight, followed by an authorised policy comparison, is still needed for those claims.

## Conclusion

A high aggregate score from signer history conceals weak information for transactions without available signer outcomes. On sampled Solana records, shared writable-account participation supplies additional ranking signal beyond structure and read-only context. A reserved first-appearance test retains a positive gain after a learned identity-score control. Calibration and false-alarm performance constrain the result's operational interpretation. The study offers a reproducible empirical benchmark and evidence for account-context transfer under missing signer history, with broader validation needed before deployment claims.

## Data and code availability

Source data: SolArchive [3], CC BY 4.0, with the pinned revision above. Extraction scripts, local protocols, model code and reproduction instructions are in `research/solana/ml/`. Machine-readable reports are in `docs/results/solana_transaction_*.json`; the environment snapshot and exact dependency versions accompany them. Raw data and derived predictions remain local. A public code repository URL and immutable release identifier must be added before submission.

## References

1. Xiaoye Zheng, Zhiyuan Wan, David Lo, Difan Xie and Xiaohu Yang. 2025. *Why Does My Transaction Fail? A First Look at Failed Transactions on the Solana Blockchain*. Proceedings of the ACM on Software Engineering 2, ISSTA, Article ISSTA066. [DOI 10.1145/3728943](https://doi.org/10.1145/3728943); [author preprint](https://arxiv.org/abs/2504.18055).
2. Mingxuan Lu et al. 2022. *BRIGHT—Graph Neural Networks in Real-Time Fraud Detection*. [Author preprint](https://arxiv.org/abs/2205.13084).
3. SolArchive. *Public Solana transaction archive*. [Dataset and license](https://huggingface.co/datasets/solarchive/solarchive). Revision `6588cad2832e62be03972ac80d69c6af11d631c8`.
4. Local research evidence and expanded source comparison. [Solana transaction risk results](../SOLANA_TRANSACTION_RISK_RESULTS.md). Supporting artifact, not an independently published reference.
