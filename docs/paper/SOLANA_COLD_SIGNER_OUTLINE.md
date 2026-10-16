# Working paper outline: Solana cold-signer reliability

Working title: **When Wallet History Fails: Evaluating Cold-Start Transaction
Reliability on Solana**.

This is a research outline, not a submission-ready manuscript. Numerical evidence
and every failed or uncertain comparison are in
[the results report](../SOLANA_TRANSACTION_RISK_RESULTS.md).

## Claim boundary

An empirical benchmark of execution-risk screening with declared account roles,
chronological label availability, missing signer history and strong context
controls. The proposed contribution is the specific problem/evaluation and
measured findings. Do not claim a novel boosting algorithm, first blockchain
failure predictor, identified malicious wallets, live failure prevention, or
independent operator identities. First appearance is within sampled windows.

## Research questions

1. How informative is historical first-signer failure rate overall and when
   that signer's outcomes are unavailable? Report prevalence, AUROC, both-class
   AP, calibration and operating metrics for each group.
2. Does non-signer writable-account history improve ranking beyond structure,
   signer history and read-only/template context? Keep the fixed original
   primary comparison separate from later diagnostics.
3. Does the answer change when limiting evaluation to the first signer
   appearance rather than all transactions before the first outcome matures?
   Include paired hourly and signer-cluster uncertainty, with address-level
   independence limits stated.
4. Does the refined first-appearance result survive learned account identity
   scores on dates reserved before inspecting their outcomes? Retain the fixed
   success gate, including a failure if it occurs.

## Sections and evidence

- Introduction: conditional execution reliability for transactions lacking
  signer history; potential relevance to wallet/dApp infrastructure, without
  asserting realized savings or mitigation.
- Related work: Solana descriptive failure/transfer studies, Ethereum/Tron
  outcome prediction, post-execution anomaly triage and relational fraud
  learning. Explicitly distinguish tasks and acknowledge established methods.
- Dataset: pinned SolArchive revision and attribution; column-range extraction,
  discontinuous archive inventory, per-date row-group selection, duplicate
  checks, source hashes and coverage limits.
- Information boundary: declared roles and past available outcomes; exclude
  current receipts, errors, used compute, balances and inclusion-position
  features. Submission times and unlanded attempts are unavailable.
- Methods: delayed participation summaries, seven primary baselines, matched
  history feedback, fixed HGB settings and prequential hashed identity control.
- Evaluation: purged calendar splits, validation-only global FPR threshold,
  fixed primary and refined endpoints, paired bootstrap and calibration drift.
- Results: all periods and controls, with uncertainty and negative results.
- Discussion: aggregate metrics can conceal missing-history weaknesses; account
  context is a partial recovery mechanism. Sampling, changing distributions,
  identity-control limits and cold-specific thresholds constrain deployment.
- Reproducibility: exact dependency versions, protocols, reports, raw and code
  hashes, and commands. Do not imply original whole-shard hashes were verified.

## Evidence still required for a stronger submission

Broader and denser source samples; more distinct weeks and regimes; independently
tested, validation-tuned identity architectures; matched batching and feedback
delay sensitivity; independent collection/source checks; and actual submission
and simulation observations for any live reliability claim. The present results
can support a focused student research study, but acceptance and global novelty
cannot be promised.
