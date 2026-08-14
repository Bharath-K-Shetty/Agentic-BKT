# HeyHomie Phase 2 — Research Proposal (v2, restructured)

Final Year Project — AI Research Track

This supersedes the original two-part proposal. Core idea is unchanged;
priority and risk allocation are restructured based on a literature/feasibility
pass (2026-08-14).

## 1. Research question

Can a knowledge-tracing-style model trained on **real, public, on-chain wallet
behavior** predict a user's future costly DeFi mistakes better than models
that only see quiz/lesson data or in-platform behavioral signals?

## 2. Why this is a real gap (verified)

- Deep Knowledge Tracing and its behavior-augmented variants (e.g. HAKT,
  auxiliary-task DKT) use in-platform signals only: correctness, hint use,
  response time.
- The closest existing work, *Agentic Knowledge Tracing* (2026), validates a
  financial-literacy KT model against **post-test scores in a simulated
  serious game** — not real financial outcomes.
- Web3 transaction-risk tools (DeepTx, wallet forensics/AML models, Phantom
  Shield-style previews) either flag malicious transactions or classify
  wallets as bad actors. None ask whether an honest user understands what
  they're doing, and none feed that signal into a learner model.

No published work uses real, monetary-stakes on-chain behavior as ground
truth for a knowledge-tracing model. That is the confirmed, defensible gap.

## 3. Restructured priority (the actual change from v1)

**v1 problem:** the two parts were treated as equally load-bearing. Part 2
(HeyHomie's own quiz+wallet users) has an N that is realistically single
digits to low dozens for a young app — not enough to support a headline
result, and it made the whole project's success depend on the smallest,
least controllable dataset.

**v2 structure:**

### Part 1 — Wallet Behavior Encoder (REQUIRED, headline contribution)
- Trained entirely on public Solana on-chain data. Does not depend on
  HeyHomie's user base at all.
- Input: any wallet's transaction history.
- Output: a behavioral/financial-sophistication representation.
- Ground-truth labels, built on existing prior art rather than invented from
  scratch:
  - **Rug-pull exposure** — adapt methodology from labeled DEX rug-pull
    detection work (e.g. the TON rug-pull dataset approach, 27K+ tokens) to
    Solana DEXs.
  - **Sandwich-attack victimhood** — adapt the swap-triplet /
    frontrun-victim-backrun detection method from the IMC 2025 Jito
    measurement paper; reuse open-source detection tooling where possible
    instead of rebuilding from zero.
  - **Slippage / position management quality** — derived directly from swap
    transaction data (realized vs. quoted price).
- This is large-N, low-risk, and reusable by anyone — not locked to
  HeyHomie's product.

### Part 2 — Knowledge-Tracing Head (OPTIONAL, case study only)
- Combines the Part 1 wallet representation with HeyHomie's own quiz/lesson
  data, for HeyHomie users who have linked a wallet (Privy) and consented.
- Framed explicitly as a secondary, exploratory case study. If the N is too
  small when Month 3 arrives, this section is cut or reduced to a
  qualitative discussion — it must not be a dependency for the paper's
  central claim.

### Downstream demo (stretch, optional)
- Just-in-time transaction explainer: parses raw instructions/Anchor IDL
  into plain language at signing time, personalized to the model's estimate
  of what the user understands. Real, currently-open gap (no Solana-native
  equivalent to DeepTx exists) but scoped as a demo surface, not required
  for the paper.

## 4. Venue strategy (dual-track, not single-bet)

- **Primary:** EDM 2027 / AIED 2027 (deadlines ~Feb 2027 based on historical
  pattern — confirm when calls open). AIED/EDM 2026 cycles are already
  closed (conference held June 27–July 3, 2026).
- **Secondary / faster path:** Web3-security or DeFi-ML workshops (e.g.
  IMC-adjacent, blockchain security workshops). These have more frequent,
  non-annual deadlines, which matters for a solo 4-month build with no
  do-over if a single yearly deadline is missed. Part 1 alone is a
  legitimate submission to this track independent of the education framing.

## 5. Known risks & mitigations (updated)

| Risk | Mitigation |
|---|---|
| Part 2 sample size too small | Explicitly optional; Part 1 stands alone as the paper's contribution. |
| Weak-label engineering (sandwich/rug-pull detection) underscoped | De-risked by existing published methodology + open-source tooling (IMC 2025 paper, open MEV dashboards, rug-pull datasets) — adapt, don't invent. |
| No real transaction execution in mobile app (Play Store policy) | Irrelevant to Part 1 (public data only). Deferred to Part 2/stretch. |
| Confounding — engaged users may just be more careful | Flagged as a limitation; framed as correlational. |
| Null result | Still publishable, informative either way. |
| Ethics / consent for real user financial data | Part 1 uses already-public on-chain data, no consent dependency. Part 2 requires an explicit consent flow via the existing Privy wallet link — flag with supervisor before touching real user data. |
| Missed once-a-year ed-tech deadline | Dual-venue strategy — Web3-security workshop as a non-annual fallback. |

## 6. 4-month timeline (Part 1 as critical path)

| Month | Deliverable |
|---|---|
| 1 | Solana wallet data collection pipeline (public RPC). Adapt rug-pull and sandwich-attack weak-label methods to Solana. Baseline DKT running on existing HeyHomie quiz data (for later comparison). |
| 2 | Train Part 1 wallet-behavior encoder on public data. First eval vs. naive baselines (AUC on predicting future rug-pull/sandwich exposure from early wallet behavior). |
| 3 | If Part 2 N is sufficient: train KT head combining quiz + wallet data for HeyHomie users. If not: deepen Part 1 (ablations, robustness, cross-time validation) and write it up as the sole contribution. |
| 4 | Finalize evaluation, write paper, submit to chosen venue(s). |

## 7. Concrete prediction target (was vague in v1, fixed here)

Binary/continuous target per wallet: probability of falling victim to a
rug-pull or sandwich attack (or incurring high realized slippage) in a
forward-looking window, predicted from features derived only from **earlier**
transaction history — avoids label leakage, gives a clean AUC-style metric
against a quiz-only / no-behavior baseline.
