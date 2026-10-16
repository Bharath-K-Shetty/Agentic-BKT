# Research notes — running log

## 8 October 2026: public learner experiments and question-difficulty control

EdNet KT2 and content metadata are downloaded and verified. The original pilot
uses 1,000 learners; an original-tag replication uses a second 1,000 learners
with zero overlap. Neither establishes a behavioral-DKT advantage. A subsequent
question-rate control on the replication test set reaches 0.681 AUC with learner
history, versus 0.660 without history. Adding past timing/revisions gives only
+0.0004 AUC with an interval including zero. Question statistics for logistic
training exclude the entire target learner; test statistics use training
learners only. Existing literature already covers simple-model comparisons,
item difficulty, multi-skill leakage and KT behavioral testing. See
[the research decision](RESEARCH_DECISION.md) for sources, exact contrasts and
the external-validation gate. No novel-method or DeFi learning-effect claim
has been established.

## 5 October 2026: learning prototype becomes the active project

The accepted direction is scenario-based DeFi education with DKT, rather
than contract auditing or treating wallet losses as knowledge ground truth.
The implementation now includes a local quiz/lesson flow, session storage,
opt-in exports, and disjoint-learner evaluation against four simpler models.
See `DKT_PROJECT.md` and `DKT_PROJECT_REPORT.md` for the active scope.

The initial five-epoch synthetic DKT smoke test scored test AUC 0.434;
BKT scored 0.712 and logistic regression 0.728. This is an engineering run
on generated sequences, not a real learner result, and no model superiority
is claimed. The earlier wallet findings below remain exploratory background.

Working notes on methodology decisions and preliminary findings, kept as
they happen so nothing has to be reconstructed from memory when writing the
paper. See [`PROPOSAL.md`](PROPOSAL.md) for the frozen research plan; this
file is the log of what actually happened building Part 1.

## Methodology decisions made during implementation

**Weak labels are computed from balance deltas, not decoded instructions.**
`jsonParsed` transaction data only decodes instructions for RPC-recognized
programs (System, SPL Token). DEX/AMM instruction data (Raydium, Orca,
Jupiter, Pump.fun) comes back as opaque base58 bytes without each program's
IDL. So "was this a swap" is inferred from `preTokenBalances`/
`postTokenBalances` and `preBalances`/`postBalances` deltas: exactly one
mint net-negative and one net-positive in a wallet's own balances, within
one transaction. This is a clean, dataset-independent signal, but it has a
real failure mode documented below (multi-hop routing).

**No labeled rug-pull/sandwich dataset was available offline**, so both
labels are heuristics built directly from on-chain balance deltas rather
than adapted from the TON rug-pull dataset or the IMC 2025 Jito paper's
tooling (per proposal §3, "adapt, don't invent" — the adaptation here is
necessarily from first principles, not from the cited prior art, and that
gap should be named explicitly in the paper's related-work / limitations
section):
- *Rug-pull exposure*: FIFO-paired SOL-denominated buy/sell swaps per
  mint. `realized_dump` = sold back for ≤20% of the SOL originally spent.
  `abandoned_bag` = bought, never sold, 30+ days of wallet inactivity on
  that mint since. Only values swaps traded directly against SOL — a
  documented scope limit, not an oracle-based valuation.
- *Sandwich-attack victimhood*: for each of a wallet's own swaps, fetch
  the full block at that slot and check whether the immediately preceding
  and following same-pool-pair swap are from one other wallet, trading in
  the frontrun/backrun pattern. This is the one label needing network
  access beyond the wallet's own history (`getBlock` per candidate swap).

**Leakage boundary**: features are computed only from transactions at or
before a per-wallet cutoff (`as_of_ts`); the label is computed only from
transactions strictly after it. No transaction contributes to both.

## Two real bugs found by running against live mainnet data (not caught by
unit tests, since the fakes didn't reproduce the real failure mode)

1. **Wallet-discovery false candidates**: block-scanning for candidate
   wallets initially treated every transaction's fee payer as a candidate.
   Solana blocks are 70%+ validator vote transactions — the first 5 wallets
   fetched this way were validator identity accounts with a single
   `Vote111...` instruction and (correctly, in hindsight) zero swaps ever.
   Fix: skip any transaction that invokes the vote program before taking
   its fee payer as a candidate.

2. **wSOL/native-SOL swap false positives**: native SOL and wrapped SOL
   (`So11111111111111111111111111111111111111112`) are tracked through
   different fields in the raw transaction (`preBalances`/`postBalances`
   vs. token balances). Before the fix, a plain wrap/unwrap — or a
   multi-hop route that happened to pass through wSOL — registered as a
   "SOL → wSOL" swap. One real wallet (a routing/arb bot) had all 60 of its
   sampled transactions misclassified as swaps this way; after aliasing
   wSOL into the same balance bucket as native SOL, that fell to 41 real
   swaps. This is worth a line in the paper's data-cleaning section: naive
   balance-delta swap detection overcounts unless wrapped-native-token
   aliasing is handled explicitly.

## Known remaining limitation: multi-hop attribution

Balance-delta swap detection is transaction-scoped: it sees the wallet's
net position change for the whole transaction, not each hop. A route like
A → B → C → A that mostly round-trips will show only the small net
remainder as a "swap," potentially mislabeling the traded pair and amount.
This wasn't fully solved (would require per-instruction decoding, which the
missing-IDL problem above already rules out) — flagged as a limitation
rather than fixed, consistent with Part 1's scope.

## Wallet discovery method

No paid indexer/labeled wallet list was available. Candidates are
discovered by scanning full blocks at the slots already-fetched wallets
transacted in, taking each non-vote transaction's fee payer, and confirming
via `getAccountInfo` (owner = System Program, ruling out PDAs/vaults) and
`getSignaturesForAddress` (has activity). This samples *generically active*
wallets, not wallets pre-selected for risky behavior — worth naming as a
sampling-bias limitation: the true rug-pull/sandwich base rate among
*all* active wallets is presumably low, which is exactly what was observed
(see results below).

## Preliminary results (informal, not the paper's final eval)

As of this log entry: N=127 wallets collected (public RPC, 60 tx/wallet
cap; collection is bottlenecked by public-RPC rate limits, not by
discovery — 60/60 candidates confirmed and fetched successfully each
round). At N=127:

- 1,434 total swaps detected across 49 wallets with ≥1 swap
- 31 realized rug-pull-dump events, 0 abandoned-bag events, 0 sandwich
  victims (sandwich detection is network-heavy and hasn't been run at
  batch scale — only unit- and spot-tested against live data)

**Result history, and why the first "good" number doesn't stand**: at
N=83 (50/50 split), the baseline scored AUC 0.667 / precision 1.0 / recall
0.33 — reported at the time as a first non-degenerate signal, with a
caveat that N was too small to trust. That caveat turned out to matter:
re-run at N=127 (more wallets, same code), the same 50/50 split now scores
**AUC 0.473** — indistinguishable from random — and the default 70/30
split scores **AUC 0.486**. Both are essentially noise. The N=83 result
was very likely a small-test-set fluke (that test split had only a
handful of positives; a single random split with that few positives has
enormous variance) rather than a real signal.

**This is itself a finding worth stating plainly in the paper**: an early
AUC of 0.667 evaporated to ~0.48 when N grew by ~50%, purely from
re-splitting the same collection pipeline's output. It's a concrete,
citable illustration of why the proposal's own risk table is right to
treat small-N results as non-indicative, and it argues for reporting
cross-validated (not single-split) metrics, and for treating any
single-digit-N-per-class AUC as provisional until N is much larger.

Feature importances are also unstable across the three runs (N=83:
`avg_slippage_vs_history` dominant; N=127 70/30: `total_realized_rug_loss_sol`
dominant; N=127 50/50: `rugpull_realized_dump_count` dominant) — further
evidence that nothing here is stable yet at this N.

**Caveat that must travel with any of these numbers in the paper**: N=127
is still below the ~50-*positive-example* floor that actually matters
(N=127 *wallets* but only 31 realized-dump events, spread thin across
train/test), and every number above comes from a single random split, not
cross-validation. Treat this entire section as a plumbing-validated
pipeline that has not yet produced a trustworthy result — that is the
honest status, and worth stating in the paper as exactly that.

## Open items before these numbers are paper-ready

- Scale N substantially (currently bottlenecked by public RPC rate limits;
  a dedicated RPC provider key would remove this bottleneck).
- Cross-validate rather than a single random split, once N supports it.
- Run sandwich-attack detection at batch scale (currently validated on
  live data only for a handful of spot-checked wallets).
- Address the sampling-bias limitation above — consider a discovery
  strategy that biases toward wallets active in memecoin/new-token pools,
  where rug-pull exposure is concentrated, rather than generic active
  wallets.
