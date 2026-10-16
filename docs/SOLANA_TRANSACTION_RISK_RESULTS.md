# Beyond the wallet: cold-signer execution-risk screening on Solana

## Research claim and status

**Candidate empirical contribution:** a declared-account, delayed-feedback ML
benchmark that separates transactions with available signer history from those
without it, and tests how much non-signer account context recovers the missing
signal. We have executed this question on real public blockchain records. This
is a specific, evidence-backed research direction; global originality and paper
acceptance are not established. Ordinary aggregation and boosting are not a new
algorithm.

**Pitch:** We study how ML can assess Solana transaction failure risk when the
signer's history is unavailable, using the accounts the transaction touches and
testing whether strong aggregate accuracy hides a cold-signer blind spot.

The narrower practical use is reliability screening for wallets, dApps and
transaction infrastructure. We have not demonstrated safer trades, prevented
failures, fee savings, or improvement over live transaction simulation. A failure
can be an intentional protective rejection, not a bug or an attack.

## Primary results

Average precision (AP) measures failure ranking across thresholds; it is not
accuracy. The cold subgroup has approximately 6–7% failures in the first two
test periods. Compare models on the same subgroup, not cold AP against aggregate
AP as if prevalence were identical.

| Test date | Cold transactions | Signer history AP: all / cold | Strong read-only baseline AP | Writable-context AP | Paired cold AP gain, 95% hour interval |
|---|---:|---:|---:|---:|---|
| 2025-11-03 (pilot) | 19,621 | 0.820 / 0.069 | 0.319 | 0.379 | +0.059 [+0.039, +0.086] |
| 2025-11-10 (confirmation) | 20,636 | 0.801 / 0.073 | 0.225 | 0.251 | +0.027 [+0.005, +0.050] |
| 2025-11-24 (extension) | 21,028 | 0.807 / 0.072 | 0.205 | 0.223 | +0.018 [-0.014, +0.066] |
| 2025-12-01 (prospective) | 19,577 | 0.834 / 0.062 | 0.173 | 0.219 | +0.045 [+0.025, +0.064] |

The baseline includes structure, signer history, read-only participation and
exact read-only-template history. The candidate adds non-signer writable-account
participation. Both receive the same available past outcomes. Pilot parameters
were specified before model results; the November 8–10 confirmation retained
them. The November 22–24 extension was specified after those results and uses
different source shards selected by a fixed date/seed hash, without outcomes.
It is additional evidence, not retrospective preregistration.

- pilot: train 92,782, validation 125,864, test 131,759; test cold prevalence 6.67%; candidate global test FPR 5.61%.
- confirmation: train 92,135, validation 126,214, test 133,071; test cold prevalence 6.72%; candidate global test FPR 3.30%.
- extension: train 93,812, validation 127,050, test 131,638; test cold prevalence 6.36%; candidate global test FPR 6.19%.
- prospective: train 100,517, validation 126,840, test 131,907; test cold prevalence 6.04%; candidate global test FPR 15.33%.

## Stronger account-identity diagnostic

A hashed logistic learner receives role-tagged account identities and read-only
templates. It updates chronologically using outcomes at least one hour old,
in ten-minute batches. Its prequential score is added to both nonlinear models.
The comparison then tests writable history after both models also receive that
identity score. Fixed diagnostic settings were specified after the first two
primary results; these are post-result diagnostics, not untouched confirmations.

| Cohort | Identity-only AP | Read-only history + identity AP | Writable context + identity AP | Additional writable gain, 95% hour interval |
|---|---:|---:|---:|---|
| pilot | 0.185 | 0.300 | 0.372 | +0.072 [+0.034, +0.109] |
| confirmation | 0.191 | 0.223 | 0.227 | +0.004 [-0.021, +0.017] |
| extension | 0.153 | 0.234 | 0.269 | +0.035 [+0.008, +0.088] |
| prospective | 0.130 | 0.190 | 0.229 | +0.039 [+0.017, +0.064] |

An interval crossing zero means the gain is not established in that period.
The uncertain second-period identity-control result prevents claiming that
writable history universally adds value beyond account memorization. The linear
identity baseline is not an exhaustive search over identity architectures.
Its batching introduces up to ten minutes extra feedback delay; this mismatch
must accompany any comparison. The primary ranking result remains separate.

## Dependence and strict first-appearance checks

Primary cold means no *matured outcome* for the first signer in sampled history.
It can include repeated transactions during the first hour. The diagnostic below
also restricts to the signer's first appearance in the sample and bootstraps the
primary cold comparison by declared signer address. Addresses are not independent
operators; neither check establishes operator independence.

| Cohort | Cold signer addresses | Largest cold signer count | Cold gain signer-bootstrap interval | First appearances | First-appearance AP gain, hour interval |
|---|---:|---:|---|---:|---|
| pilot | 17,920 | 39 | [+0.036, +0.084] | 17,912 | +0.047 [+0.031, +0.060] |
| confirmation | 19,086 | 39 | [+0.009, +0.042] | 19,076 | +0.027 [+0.012, +0.042] |
| extension | 18,862 | 96 | [-0.006, +0.060] | 18,851 | +0.024 [+0.015, +0.035] |
| prospective | 17,912 | 36 | [+0.031, +0.057] | 17,904 | +0.042 [+0.024, +0.060] |

## Reserved confirmation of the refined first-appearance question

After the first three periods, the November 29–December 1 dates and alternate
shards were reserved before inspecting their transaction outcomes. The refined
primary comparison is writable history versus read-only history **with the same
delayed account-identity score supplied to both**, restricted to first signer
appearances in the sampled replay. Its locally fixed success condition requires
a positive AP gain and a paired-hour interval entirely above zero. Model and
history parameters are unchanged. It is a reserved historical evaluation, not
a live prospective trial or public preregistration.

| Cohort | First-appearance gain after identity control, 95% hour interval | Refined gate |
|---|---|---|
| prospective | +0.032 [+0.017, +0.050] | PASS |

The reserved refined comparison **passed** on 17,904 first appearances: AP gain +0.0316, 95% hour-bootstrap interval [+0.0168, +0.0501]. This evaluates ranking, not deployment calibration.

First-appearance AP is 0.1688 versus 0.2004. At the inherited global-validation thresholds, subgroup FPR is 22.66% versus 28.65%, and Brier loss is 0.0967 versus 0.1218. These poor calibration/operating results prevent describing the candidate as an overall better or deployment-ready risk model.

Earlier first-appearance comparisons remain exploratory. A failed refined gate
must remain visible; it cannot be replaced with a favorable secondary result.

## Difference from reviewed prior work

| Reviewed primary source | Existing contribution | Our narrower question |
|---|---|---|
| [Zheng et al., ISSTA 2025](https://zhiyuan-wan.github.io/assets/publications/zheng_issta_25_solana.pdf) | Large-scale descriptive study of Solana failure initiators, programs, errors and temporal patterns | Cold-signer execution-outcome ranking from declared account roles and delayed historical outcomes |
| [Oliveira et al., 2021](https://www.researchgate.net/publication/351723407_Analyzing_Transaction_Confirmation_in_Ethereum_Using_Machine_Learning_Techniques) | Ethereum execution-outcome classification with gas and inclusion-related attributes | Exclude current execution receipts and explicitly evaluate missing signer-history transfer |
| [Solana's transaction network, EPJ Data Science 2025](https://link.springer.com/article/10.1140/epjds/s13688-025-00561-x) | Transfer-graph structure and descriptive failed-transfer analysis | Chronological predictive benchmark with matched structure/read-only controls |
| [Chaudhary et al., CMC 2026](https://www.techscience.com/cmc/v89n2/68773/html) | Temporally evaluated Ethereum multisig anomaly triage after execution | Observed Solana success/failure labels, exclude current logs/compute use, cold-signer breakdown |
| [Blockchain platforms and computational evaluation, AIA](https://ojs.bonviewpress.com/index.php/AIA/article/view/6923) | Platform review and TRON transaction success/failure simulation | Public Solana records, available-label replay and account-role ablation |
| [BRIGHT, 2022](https://arxiv.org/abs/2205.13084) | Real-time fraud learning using graph entity context | Execution reliability rather than fraud; relational transfer itself is established |

The literature search did not locate this exact benchmark question in the
reviewed sources. Absence from a search is not proof of worldwide novelty.
We cannot claim the first blockchain failure classifier, the first contextual
risk learner, or a new temporal-validation technique. Commercial reliability
tools, including [Belay](https://devpost.com/software/belay-1i4kjo), also advertise
failure prediction; their existence rules out a broad first-product claim.
The detailed search and rejected directions are retained in
[the search log](SOLANA_NOVELTY_SEARCH_LOG.md).

## Data and information boundary

Data from [SolArchive.org](https://huggingface.co/datasets/solarchive/solarchive),
CC BY 4.0, pinned HF revision
`6588cad2832e62be03972ac80d69c6af11d631c8`. One Parquet row group per date is
sampled, not the entire chain. Byte ranges and derived files have recorded hashes;
the original full-file SHA256 has not been independently verified. The archived
inventory is discontinuous, so continuous-history coverage is not assumed.

Inputs are declared account roles/counts and history of outcomes at least one
hour earlier. Current status, logs, errors, consumed compute, balances, paid fees,
block position and inclusion timestamp are excluded from model inputs. Actual
submission times are absent. Block time supplies the retrospective checkpoint,
so this is **conditional on eventual block inclusion**, not validated live
pre-submission prediction. Unlanded transactions are absent. Account resolution
is assumed possible before execution; actual runtime availability is not tested.

All seven primary models use identical date partitions. Initial six hours build
history; fitting and threshold calibration purge labels unavailable before the
next split. Test-time histories update from earlier matured test outcomes. No
current or pending labels update features. Identical selected-payload duplicate
signatures count once; conflicting duplicates and partition mismatches abort.
Three HGB seeds are averaged, but deterministic fitting does not make them three
independent empirical replications. The independent time windows matter more.

Alert thresholds use a global validation FPR budget of 5%. Test FPR drifts, and
the same threshold may be unsuitable for cold signers. A positive AP gain does
not prove better recall at a common test false-positive rate or a guaranteed
budget. The hour bootstrap uses fixed predictions within one test day per
cohort, excluding retraining and longer-regime uncertainty.

## Publication assessment and next evidence

This is an implemented blockchain ML research candidate with a narrower gap
and measured results, rather than a novelty promise. A paper should center its
benchmark and cold-history evaluation, retain the identity-control uncertainty,
and avoid selling an invented algorithm. Submission readiness still requires
broader periods/source samples, a tuned but independently tested identity
baseline, feedback-delay sensitivity and an independent data collection or
live-arrival validation. Comparisons with simulation require collecting actual
submission and simulation results; this archive cannot supply that evidence.

All numeric tables come from saved JSON reports. Run
`research/solana/ml/report_transaction_risk.py` to regenerate this document.
Reproduction commands and source-download details are in
[the ML workspace README](../research/solana/ml/README.md).
