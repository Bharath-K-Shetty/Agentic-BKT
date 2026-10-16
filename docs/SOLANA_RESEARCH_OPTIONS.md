# Solana research options after the EdNet review

Research checked: 8 October 2026. This initial comparison used a 2–4-week
planning horizon. The user subsequently removed that constraint as a selection
criterion. For the current novelty assessment and research-first protocol, see
[SOLANA_NOVELTY_PROTOCOL.md](SOLANA_NOVELTY_PROTOCOL.md). The schedule and
deadline-dependent rankings below are retained as the original planning context.

## Recommendation

**Investigate Token-2022 integration correctness first, starting with transfer-fee accounting.** The proposed deliverable is a tool that executes bounded tests against an integration and reports an accounting violation with a replayable transaction sequence. This is a stronger practical direction for this project than another broad wallet-risk classifier or an unrestricted LLM auditor.

This is a provisional recommendation based on documented need, accessible tooling and scope. It is **not an established novelty claim**, a reproduced finding, or a promise of publication. A known vulnerability reproduced in a new interface is insufficient for a research paper. The first two days must establish whether we can evaluate a distinct method across independent integrations.

If retaining an AI contribution is compulsory, the strongest alternative to investigate is **transaction recovery that preserves explicit user constraints**. Do not attach DKT to either direction without a defensible reason. EdNet cannot provide evidence about blockchain transaction or program security.

## Ranked shortlist

| Direction | Practical user | Potential contribution to investigate | Main obstacle | Decision |
|---|---|---|---|---|
| Token-2022 integration correctness | DeFi/payment developers and auditors | Execution-backed accounting tests across token configurations and state changes | Existing audit guidance already identifies these risks; independent evaluation corpus needed | First feasibility probe |
| Authority relationship auditing | Anchor developers and auditors | Validate which signer is bound to trusted state, with executable counterexamples | Mature static/symbolic analysis and existing Anchor constraints | Best auditing fallback |
| Safe transaction recovery | Wallet and agent developers | Complete a failed task while preserving recipient, mint, budget and minimum output | Existing retry tools and semantic transaction guards; intent must be specified | Best alternative if AI is required |
| Compute/fee right-sizing | Transaction builders | Reliable cost reduction under workload changes | Simulation-based sizing already standard; landing counterfactuals expensive | Useful engineering, weaker immediate paper case |
| Early rug/phishing detection | Users and monitoring services | Pre-incident evaluation on independently labelled cohorts | Label quality, historical access, temporal leakage and substantial prior work | Deprioritize for this deadline |

The ordering is our judgement for this project's constraints, not a measured ranking of ecosystem demand.

## 1. Token-2022 integration correctness

### Evidence of need

The [official Kora advisory](https://github.com/solana-foundation/kora/security/advisories/GHSA-725g-w329-g7qr), published March 2026, describes payment verification counting a requested transfer amount without subtracting the Token-2022 transfer fee. Its stated precondition includes accepting a fee-bearing mint. This is evidence of an integration failure class; it does not establish that the current Kora deployment remains vulnerable. We have not reproduced the advisory or verified current fixes.

For illustration, an application might credit a deposit of 100 units even though only 98 spendable units arrived after a fee. The error is the application's accounting assumption. A transfer-fee token is not inherently malicious.

The [official extension guide](https://www.solana-program.com/docs/token-2022/extensions) documents the token features; the [on-chain integration guide](https://www.solana-program.com/docs/token-2022/onchain) already recommends testing both token programs. [QEDIT's primary audit report](https://qed-it.com/services/audits/solana-token-2022/) discusses extension interactions as a maintainability and correctness concern. That audit concerns particular reviewed versions and includes confidential-transfer internals, which are outside our proposed scope.

### Bounded research question

Can a reusable, execution-backed test generator expose incorrect deposit/payment credit and withdrawal assumptions under transfer-fee configurations while accepting integrations that correctly account for fees or explicitly reject unsupported mints?

Start with transfer fees only. Include zero fees, rounding boundaries, fee caps, epoch-dependent configuration and deposit/withdrawal sequences. Add a second extension only after the core evaluation works. Do not attempt cryptographic auditing of confidential transfers.

The invariant must reflect each integration's declared accounting model. A share-based vault cannot be checked by naively equating shares to token units. Protocol-subsidized fees also require a different rule. Withheld fees must be distinguished from spendable balance; do not sum arbitrary account fields and call it conservation.

### What would make it research

- A clearly specified method for choosing configurations and transaction sequences, compared with ordinary hand-written tests, generic fuzzing or a simpler configuration sampler.
- Independent program families, known vulnerable versions where obtainable, corrected counterparts and legitimate controls. Mutations are useful supplementary cases, not independent real vulnerabilities.
- Measured false alarms, detection by program family, reproducibility and test-generation cost. Measure the benefit of stateful sequences over single transfers and of extension-aware generation over ordinary inputs.
- Replay artifacts containing pinned program/runtime versions, initial accounts, configuration, instruction sequence and violated invariant.

The proposed novelty is **not** recognizing that fees reduce received amounts. That is already documented. It must be a demonstrated improvement in detecting integration errors or producing useful reproducible evidence.

### Closest overlap and tooling

[Trident](https://github.com/Ackee-Blockchain/trident) already provides stateful Solana fuzzing. [Mutanchor](https://docs.rs/crate/mutanchor/latest) already provides Anchor mutation testing. Neither stateful testing nor mutation testing can be presented as our invention. The [scanner benchmark](https://github.com/AIOilShield/solana-scanner-benchmark) includes Token-2022-related cases. A [public toolkit requirements document](https://github.com/LiamCarPer/solana-audit-toolkit/blob/main/PRD.md) also proposes extension analysis; the repository root returned 404 during this check, so implementation availability was not established.

[LiteSVM](https://github.com/LiteSVM/litesvm) and [Mollusk](https://solana.com/docs/programs/testing/mollusk) are candidates for actual runtime execution. A Python arithmetic demonstration alone would not validate integration behavior. Baseline compatibility and build cost remain untested.

## 2. Authority relationship auditing

The narrow problem is whether the required signer is the authority bound to the relevant trusted account, rather than whether any signer check exists. Correct handling also distinguishes the Solana account's owner program from the token account's authority field.

[SseRex](https://arxiv.org/html/2603.16349v1), a 2026 symbolic-execution study, already covers missing signer, owner and key checks and arbitrary CPI. Its limitations describe heuristics that treat a signer check on any account as sufficient and the difficulty of recovering business context from bytecode. This motivates investigation of relationship checking, but does not prove that source-level authority analysis is new. [VRust](https://github.com/parasol-aser/vrust-open-source) and [Soleker](https://www4.comp.polyu.edu.hk/~csxluo/Soleker.pdf) are additional close work.

A feasible prototype would extract explicit account relationships from a bounded subset of Anchor source and constraints, then generate account-substitution tests. [Anchor already supplies `has_one`, signer, owner, seeds and other constraints](https://www.anchor-lang.com/docs/references/account-constraints). [Sealevel examples](https://github.com/coral-xyz/sealevel-attacks) already demonstrate account-data matching. The contribution cannot be a warning whenever `has_one` is absent.

Evaluation must include permissionless instructions, custom correct checks, multisignature patterns and properly constrained programs. Keep each program's vulnerable, corrected and mutated variants in the same split. Do not treat a stateful test that violates an invariant as a formal proof of general safety.

This route fits the earlier contract-auditing preference, but broad security-tool competition and old baseline build requirements make it less attractive than a focused accounting study.

## 3. Transaction recovery with explicit constraints

The [ISSTA study of failed Solana transactions](https://arxiv.org/html/2504.18055v1) establishes a substantial failure-analysis problem. Its [replication repository](https://github.com/ZXXYy/Solana_Failed_Tx) supplies a 10,000-transaction sample and categorization artifacts; its README describes the complete data as approximately 5 TB requiring collection. The sample does not reveal a user's original intent or supply a validated repair for each failure.

Candidate question: can a constrained repair system increase successful task completion without changing the intended recipient, mint, maximum spend, minimum output or fee budget?

For example, increasing swap slippage can make execution succeed while violating the user's minimum-output condition. Count that as an unsafe repair, not a success. Retrying must also account for whether the original transaction already landed; duplicate execution is a distinct failure.

Construct sandbox tasks with explicit intent and injected failures. Compare rule-based retry, unconstrained model repair and repair checked against the same constraints. Report safe completion, unsafe completion, duplicate intents, refusal and cost. Historical transaction logs can inform failure categories, but cannot substitute for labelled intent.

Overlap is substantial: [SolFix-AI](https://github.com/LHAJsolana/SolFix-AI) offers failure diagnosis, [Replico Copilot](https://github.com/replicolabs/copilot) describes retry automation, and [Graphite](https://github.com/Stan-lee13/graphite) already implements semantic transaction verification for agents. Graphite's published benchmark is small, but this does not make the core idea new.

The [Foundation's Solana Bench announcement](https://solana.com/news/solana-bench) explicitly supports evaluating agents on real transaction tasks. Its [environment documentation](https://solana-foundation.github.io/solana-gym-env/) describes instruction-based reward and reward-gaming limitations. A stronger semantic-completion evaluation is worth investigating, but simply building another agent benchmark is insufficient differentiation. Historical funding statements are not evidence of an available grant today.

## 4. Other ecosystem needs and why they rank lower here

**Fees and compute limits:** [official fee documentation](https://solana.com/docs/core/fees/fee-structure) and [simulation RPC documentation](https://solana.com/docs/rpc/http/simulatetransaction) already support compute estimation. A worthwhile study would need uncertainty, workload drift or a different measurable advantage. Scope transaction formats explicitly: fee semantics differ. Successful historical transactions alone cannot tell us how a different fee would have changed landing probability.

**Rug detection:** [From Hype to Collapse](https://arxiv.org/html/2603.24625v2) already studies Solana rug pulls. Its manually verified benchmark and much larger heuristic candidate set must not be conflated. A direct dataset download was not located during this review. Early detection requires evidence available before the incident and deployment-family/time separation.

**Phishing:** [SolPhishHunter](https://github.com/liziwei1/SolPhishHunter) releases incident annotations and covers multiple phishing patterns. Its CSV header contains signatures, times, victim/phisher fields and loss. This is not a ready pre-signing feature dataset with representative benign transactions. Repository licensing was not detected in the metadata/tree check.

**Infrastructure:** The [Solana RFP forum](https://forum.solana.com/c/rfp/10) lists topics including testing infrastructure, historical state verification, indexing and monitoring. These provide need signals, not proof that a request remains unfilled. A validator, archival verifier or new indexer is too large for this deadline; a narrowly scoped testing extension may be feasible.

## Public sources: what is actually usable

| Source | Observed availability | Important limit |
|---|---|---|
| Sealevel attacks | Public educational Rust examples and corrected variants | Not independent production incidents; no license detected in this check |
| AIOilShield scanner benchmark | MIT; 19 planted vulnerable and 7 clean examples per README | Creator withdrew earlier accuracy claims because of leakage; audit labels and remove clues |
| LLM non-EVM audit benchmark | MIT; 15 Solana vulnerable/corrected pairs in the repository | Generic LLM auditing and prompting comparisons already explored |
| W3SA Solana | [Dataset page](https://huggingface.co/datasets/almanax/w3sa-bm-solana) describes real-project audit cases | Gated access; not downloaded or immediately usable |
| Failed-transaction study | Public sample and analysis code | Full dataset not bundled; user intent and repair ground truth absent |
| SolPhishHunter | Public incident CSV and detector | Negatives, historical inputs and license need work |
| Kora advisory and Token-2022 sources | Public documented failure and reference implementation | Exact affected commit/build and independent reproduction still needed |

The [machine-readable source inventory](results/solana_source_inventory.json) records nine repository metadata/tree probes, including tree SHAs and license observations. A tree SHA identifies a source tree, not necessarily a commit. Missing license metadata is not a definitive legal conclusion; resolve redistribution permissions before packaging upstream examples. File counts are not counts of independent programs.

## Concrete next 48 hours

1. Pin a Token-2022 runtime and execute an actual transfer with zero and nonzero fees. Read spendable and withheld balances separately.
2. Build three local integration controls: incorrect gross credit, correct net credit and intentional rejection. Obtain a replayable violation only for the incorrect control.
3. Locate and build the version implicated by the Kora advisory where feasible. Treat the advisory as the original report, and verify current source separately. Do not test live systems.
4. Find at least three independently developed, legally usable integration families for evaluation. This is a feasibility threshold, not an adequate final sample-size claim. Keep all derivatives of a family together.
5. Run the simplest applicable existing test approach on identical inputs. Establish what our proposed method adds beyond a hand-written invariant and parameter sweep.

**Continue this direction only if** the runtime works, legitimate controls pass, independent cases are available and a distinct comparison can be specified. If we only reproduce one arithmetic error in our own examples, it is a useful demonstration, not publication evidence. Switch to the bounded authority study or safe-recovery study only after their own baseline/data feasibility checks.

## Two-to-four-week deliverable

- Week 1: runnable reference, threat/accounting model, source provenance, baseline and written evaluation protocol.
- Week 2: bounded generator and replay reports; freeze the corpus and independent evaluation cases before tuning.
- Week 3 if available: held-out comparison, ablations, false-alarm review and uncertainty reported by independent program family rather than transaction count.
- Week 4 if available: release preparation, reproducibility check, limitations and paper writing around observed results. At two weeks, prioritize a reproducible prototype and honest evaluation over a broad feature set.

The current wallet dataset and EdNet experiments do not validate this new direction. Preserve them as prior work. Existing dashboard/report infrastructure may be reusable, but the method, experimental evidence and manuscript claims need to change. This review added research documentation and source metadata only; no proposed audit method or upstream baseline has been executed.

Suggested pitch, contingent on feasibility: **“We build and evaluate an execution-backed auditor that checks whether Solana applications account correctly for Token-2022 transfers and produces reproducible evidence when they do not.”**
