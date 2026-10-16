# Research-first Solana auditing proposal

Updated 8 October 2026. Status: literature-grounded hypothesis; no new method,
baseline result or vulnerability has yet been validated. Research value takes
precedence over the earlier deadline-based ranking.

Follow-up code inspection found direct prior implementation of fee updates and
epoch activation tests in Orca, plus existing authority-relation probes in
Crucible. See [the gap review](SOLANA_GAP_REVIEW.md) for the revised assessment.
The method below remains an experimental hypothesis; the simple fee-change
example cannot serve as its novelty claim. The strongest next comparison is
now reachability-aware validation of audit findings.

## Decision

Pursue a feasibility study of **auditing Solana token integrations under mutable
external state**. Start with Token-2022 transfer fees and their authority/epoch
transitions. Extend to transfer hooks only after the underlying approach has
evidence. This is a specific candidate contribution inside the broader contract
auditing direction, not a claim that all Solana auditing is an open problem.

Working research question:

> Does search guided by an integration's external dependencies and permitted
> configuration changes find more independently validated accounting violations
> than coverage-guided sequence fuzzing with the same available actions,
> invariants and execution budget?

A secondary question asks whether explicit authority and policy modelling
reduces reports caused by impossible state mutations or intentionally accepted
token behavior. Those problems must first be measured, rather than presumed to
occur in every existing tool.

## What the search rules out

| Primary source | Existing contribution | Claim we cannot make |
|---|---|---|
| [FuzzDelSol](https://arxiv.org/abs/2309.03006) | Binary-level, coverage-guided Solana fuzzing with runtime-specific bug oracles | First Solana fuzzer or first execution-backed detector |
| [SseRex](https://arxiv.org/html/2603.16349v1) | Symbolic execution for account-validation and CPI issues | First automated signer/owner/key-check auditor |
| [Crucible](https://github.com/asymmetric-research/crucible) | Typed instruction-sequence mutation, coverage feedback, stateful execution, invariant checks, minimization and replay | First multi-transaction auditor, stateful fuzzer or replayable failure report |
| [Trident](https://github.com/Ackee-Blockchain/trident) | Stateful, developer-guided Solana fuzzing and testing | First flow-based Solana testing system |
| [Riverguard](https://neodyme.io/en/blog/riverguard_1_intro/) | Mutation of real transaction contexts, simulation and triage | First transaction mutation or account-substitution detector |
| [cf-invariants](https://github.com/caliperforge/cf-invariants) | Heuristic/AI invariant suggestions and harness emission atop existing fuzzers | First LLM invariant author for Solana |
| [Solana invariant atlas](https://github.com/caliperforge/solana-invariant-atlas) | Libraries of invariant classes and paired clean/planted regression cases | First Solana invariant benchmark or clean/buggy pair corpus |
| [SEMA, Electronics 2026](https://www.mdpi.com/2079-9292/15/10/2187) | LLM/multi-agent search with replay-based property validation, evaluated on a Solidity benchmark | First model proposes / deterministic executor validates architecture |
| [SmartShot, PACMSE/FSE 2025](https://doi.org/10.1145/3715714) | Snapshot mutation with validation for smart-contract state exploration | First environment/state mutation or reachability validation approach |
| [Mutanchor](https://docs.rs/crate/mutanchor/latest) | Anchor mutation testing | First security-check mutation testing on Solana |

These are descriptions from papers and repository documentation, not reproduced
performance comparisons. SmartShot's publisher search abstract was accessible;
its full paper was not retrieved here. Repository capabilities and roadmap items
must be separated when implementing baselines. In particular, cf-invariants
documents a working Crucible target and a placeholder Trident target; its model
transport defaults to a mock unless the live option is enabled.

**Important correction to the earlier pitch:** stateful auditing plus executable
counterexamples is useful, but already exists. Merely adding an LLM or Token-2022
rules does not establish novelty.

## Why this narrower problem is worth testing

The [Kora advisory](https://github.com/solana-foundation/kora/security/advisories/GHSA-725g-w329-g7qr)
documents an integration that credited a transfer's gross amount rather than its
post-fee amount. It motivates the accounting problem; we did not discover it or
verify its current deployment status.

[Official transfer-fee documentation](https://solana.com/docs/tokens/extensions/transfer-fees)
describes updating fees with delayed epoch activation. A test that fixes the
mint configuration at setup can miss behavior after a permitted change. That is
a hypothesis about test coverage, not an assertion that existing fuzzers cannot
perform these actions.

Existing developers also test this domain: a [DMV fuzz-harness plan](https://github.com/Romulus-Sol/DMV/blob/devnet/docs/FUZZ-HARNESS-PLAN.md)
documents a transfer-fee account-close regression and its valid harvest-before-close
handling. Therefore, even Token-2022 lifecycle testing itself is established.

The contribution to investigate is a **reusable search method** for selecting
external changes and their ordering relative to an integration's operations,
with authority assumptions and accounting policies explicit. A targeted search
did not locate an exact match combining these elements, but absence from search
results does not establish novelty. Review full papers, code and citations before
writing any priority claim.

## Concrete example, with correct interpretation

Consider a hypothetical vault that advertises support for a fee-bearing mint:

1. Create the mint and deposit under an initial fee configuration.
2. Have the actual fee authority submit a permitted fee update.
3. Advance the local runtime to the activation epoch without changing balances
   or manufacturing signatures.
4. Deposit or withdraw again, observing spendable balances, withheld fees,
   credited claims and application-defined output limits.

A violation would be the vault crediting claims that its declared accounting
model cannot back. A changed output, legitimate fee, or rejected transaction is
not sufficient evidence of a bug. Expected minimum-output rejection is correct
behavior. Withdrawal liveness requires an explicit guarantee and bounded
environment assumptions; a single rejection does not prove permanent lockup.

Distinguish an ordinary user's capabilities from a mint authority's capabilities.
A mint authority abusing powers the application explicitly accepts is a trust
exposure, not automatically an authorization vulnerability. Record which
precondition the finding requires. If an update authority has been revoked, the
search must not silently restore it.

## Proposed method to implement and test

**Inputs:** pinned program binaries/source and IDLs where available; reproducible
initial state; integration adapters; reviewed accounting policies; actor keys
and authority relationships. Source/IDL names are hints, not authoritative
security specifications. An IDL alone does not encode the business model.

**Dependency representation:** for each tested operation, record the external
mint/configuration/accounts it uses, legal update operations, required
authorities and activation conditions. Start with a hand-validated schema for
one token extension. Automatic extraction is a separate component and must be
evaluated against manually reviewed mappings.

**Search:** jointly vary integration operations and legal external operations.
Candidate scheduling prioritizes dependencies the current sequence exercises
and activation boundaries it crosses. Compare this with simpler strategies to
find out whether the prioritization adds value. Do not assume code coverage is
useless or that semantic scheduling will win.

**Execution and checking:** execute actual Token-2022 instructions in a pinned
Solana runtime. Separate initialization fixtures from permitted post-setup
actions. Use independently specified policy checks, not a copy of the target's
possibly incorrect fee arithmetic. Record rollback/error behavior. A rejected
transaction does not leave ordinary instruction updates partially committed.

**Reporting:** minimize the legal sequence while preserving both its required
capabilities and the observed violation. Emit the initial-state artifact,
versions, actor roles, transactions and property. Re-run in a fresh process;
confirm important findings in another supported runtime where practical. A
counterexample validates a bounded violation, not general program insecurity or
the absence of other bugs.

**Optional model assistance:** use a model to propose dependency mappings,
candidate policies or promising sequences. Require review of policies and
execution of sequences. Evaluate this component separately against deterministic
extraction/templates. Do not use an LLM to both invent and certify ground truth.

## Evaluation designed to support a paper

### Corpus

Create a provenance manifest before tuning: source commit and license, exact
build, extension support policy, origin of each finding, actor capabilities,
known patch where available, and independent program-family identifier.

Candidate sources include [Kora](https://github.com/solana-foundation/kora),
[Orca Whirlpools](https://github.com/orca-so/whirlpools),
[Raydium CLMM](https://github.com/raydium-io/raydium-clmm),
[Raydium CPMM](https://github.com/raydium-io/raydium-cp-swap), and the documented
DMV regression. These are evaluation candidates, **not programs we claim are
vulnerable**. Current Raydium source already contains explicit transfer-fee
handling. Raydium variants are related, not independent families.

Separate known real findings, current implementations with no known finding,
and injected mutations. A program with no known bug is not proven clean. Use
reviewed correct controls and intentionally unsupported extensions to measure
specific false alarms. Group derivatives, versions and mutations together;
reserve independent families for final evaluation. Token mints and transaction
counts do not increase the number of independent integration families.

### Baselines and fairness

1. Ordinary deterministic integration tests and boundary sweeps.
2. Uniform random sequence search with the same legal actor/actions/schema.
3. Crucible's applicable coverage-guided mode with the same extension actions,
   fixtures and invariant checks.
4. Trident flows where a comparable adapter can be implemented; disclose manual
   effort and semantic differences.
5. Static/LLM auditing only as secondary, scope-matched comparisons. Do not force
   SseRex to detect an accounting property outside its stated scope and then
   present this as beating symbolic execution generally.

Compare both equal execution budgets and total wall-clock budgets, including
setup, model calls and analysis. Report adapter/harness effort. Giving our method
fee updates while withholding them from the baseline would test action access,
not a superior search algorithm.

### Research questions and measurements

- **RQ1: Search effectiveness.** Independently validated bug instances found,
  detection probability across seeds, time/transactions to first violation and
  replay success. Report censored runs and per-family results.
- **RQ2: Specific benefit of modelling external changes.** Remove external
  actions, remove dependency-guided prioritization, and remove boundary targeting
  separately. Separate the benefit of action availability from scheduling.
- **RQ3: Finding validity.** Manual adjudication of policy violations, accepted
  trust exposure, unsupported-token rejection, invalid-state artifacts and
  unresolved cases. Report disagreements instead of forcing labels.
- **RQ4: Generalization and engineering value.** Held-out integration families,
  new configuration ranges, adapter effort and actionable regression tests.
- **Optional RQ5: AI value.** Same downstream executor/budget with and without
  model proposals; model version, prompts, cost and rejected suggestions logged.

Use repeated seeds and paired comparisons. Estimate uncertainty at the
independent family or bug-instance level as appropriate. Replaying one bug
thousands of times does not establish a large benchmark. Publish negative
results and all exclusions with reasons.

## Evidence gates and publication potential

**Gate A — distinctness:** complete a feature-level comparison of Crucible,
Trident, Riverguard, cf-invariants, SmartShot and relevant citations. If the
proposed scheduling/model is already implemented, refine or abandon the novelty
claim rather than rename it.

**Gate B — feasibility:** reproduce one documented real failure locally, retain
correct controls, and run a comparable baseline. A self-authored buggy vault
alone does not clear this gate.

**Gate C — contribution:** show useful performance, lower authoring effort or a
new empirical result across independent cases under fair controls. The
statement of contribution must match the observed result.

**Gate D — external validity:** independent reproduction, reviewed properties,
source provenance, documented limits and, where possible, maintainer feedback.
No messages to maintainers have been sent. Any new findings should be handled
through the relevant disclosure process before a public release.

Possible outcomes:

| Outcome | Defensible research claim |
|---|---|
| Novel search method with repeatable gains on independent integrations | Methods paper candidate, subject to literature and reviewer assessment |
| Strong corpus revealing a previously unmeasured integration-testing problem | Empirical/benchmark paper candidate with validated labels and meaningful scope |
| Useful harness, but no distinction or gain over existing tools | Engineering project; novelty claim not supported |
| Several synthetic examples and model-generated warnings | Demonstration only; insufficient publication evidence |

Do not choose a journal by promised acceptance, and do not choose a venue before
the result determines the paper's scope. Software testing and blockchain
security are relevant communities; current calls and deadlines have not been
checked in this review.

## Immediate next work

First reproduce and characterize existing tooling, then implement the proposed
delta. Create a pinned corpus manifest, a runtime smoke test, one real regression
and a matched baseline before building a dashboard or a broad autonomous auditor.
Advance by evidence gates rather than a fixed two-week feature list.

This protocol updates the earlier recommendation without discarding the DKT or
wallet work. No new experiment, novel vulnerability or publication-ready result
is claimed by this document.
