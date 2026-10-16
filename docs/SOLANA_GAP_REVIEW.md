# Solana auditing: gap check against papers and code

Checked 8 October 2026. This updates the candidate decision in
[the novelty protocol](SOLANA_NOVELTY_PROTOCOL.md).

## Verdict

Further cross-platform review below adds ExGen, SmarTest, TracExp and SmartShot
code inspection. These narrow the claim further: generating setup transactions
or validating a model-produced PoC is established in other settings. The
unvalidated candidate is a Solana-specific method for modelling and enforcing
account capabilities, with an empirical evaluation of when audit results depend
on unavailable capabilities.

**The simple fee-change testing idea is already implemented in public integration
tests. It is not sufficient novelty.** A stronger research candidate is validating
whether an audit warning can be realized through legal Solana transactions under
explicit attacker capabilities. This is a documented limitation in current work,
but a novel general solution has not been established by this review.

Do not interpret a documented limitation as proof that no other tool addresses
it. No new vulnerability or comparative performance result was obtained here.

## Evidence added beyond the earlier literature search

### Fee changes and activation epochs: existing implementation

I retrieved and inspected selected sections of [Orca's transfer-fee integration
tests](https://github.com/orca-so/whirlpools/blob/main/legacy-sdk/whirlpool/tests/integration/token-extensions/transfer-fee.test.ts).
They submit fee changes, advance to the effective epoch, and check subsequent
fee/reward collection behavior. This directly overlaps with our earlier example.
It does not prove that every integration handles every change safely, but rules
out presenting that example as a new testing concept.

The [Token-2022 reference tests](https://github.com/solana-program/token-2022/blob/main/clients/rust-legacy/tests/transfer_fee.rs)
also cover fee updates, epoch advancement and authority changes. Testing the
reference token program is distinct from auditing applications that integrate it.

### Authority relationship probes: existing implementation

[Crucible's constraint-check documentation](https://github.com/asymmetric-research/crucible/blob/main/docs/constraint-check-engine.md)
already describes wrong-signer, cross-authority, field-reference and account-alias
probes. Its source sequence mutator inserts, swaps, repeats, deletes and shuffles
typed actions. Therefore, neither relationship checking nor sequence mutation is
an adequate stand-alone novelty claim.

The same documentation describes known reports caused by changing an account
owner that an attacker cannot actually change. Some SPL-specific probes also
skip Token-2022 extension accounts because of an exact-length parser. These are
specific implementation limits, not proof that Crucible's general fuzzing engine
cannot execute Token-2022 actions. Adding TLV parsing alone would mainly be an
engineering improvement.

### Dependency-guided search: established outside Solana

[ConFuzzius](https://arxiv.org/abs/2005.12156) already uses dynamic data dependencies
to construct useful transaction sequences. [SMARTIAN](https://softsec.kaist.ac.kr/~sangkilc/papers/choi-ase2021.pdf)
uses static and dynamic data-flow analyses for seed generation and guidance.
Consequently, transplanting a dependency graph into Solana is not automatically
a new research method. The adaptation must solve a demonstrated problem and be
evaluated against an applicable version of the prior technique.

### Reachable preconditions: explicit research limitation

[SseRex, section 4](https://arxiv.org/html/2603.16349v1) states that its generated
exploit transactions depend on a compatible initial blockchain state and identifies
generating complete precondition-establishing chains as future work. This is
stronger motivation than our earlier broad claim about stateful auditing.

However, [SmartShot](https://doi.org/10.1145/3715714) already investigates validated
state mutation in another smart-contract setting, and [SEMA](https://www.mdpi.com/2079-9292/15/10/2187)
already separates model proposals from replay-validated findings. Neither state
validation nor deterministic checking of an AI-generated exploit is itself new.
The full SmartShot paper and a reproduction of its validation method are still
needed for a definitive feature-level comparison.

## Candidate gaps, with honest status

| Candidate | Evidence | Status |
|---|---|---|
| Automatically test transfer-fee changes over time | Orca already does this in integration tests | Reject as stand-alone novelty |
| Learn/derive instruction dependencies to guide search | Established in ConFuzzius and SMARTIAN | Requires a materially distinct Solana-specific contribution |
| Parse Token-2022 extension accounts in existing account probes | Specific documented probe limitation | Useful contribution to a tool; weak paper alone |
| Turn assumed malicious account states into legal transaction chains | Explicit SseRex limitation; related Crucible false-positive cases | Strongest method hypothesis to investigate next |
| Measure how often audit warnings depend on unavailable capabilities | Concrete motivation, no completed representative measurement | Empirical study candidate; corpus and labels unresolved |
| Generalize configuration search across independent integrations | Existing tests are program-specific | Possible reusable tool/study; absence of a matching method not established |

## Strongest refined project

Working title: **Reachability-Aware Validation of Solana Audit Findings**.

Plain-language objective: when an auditor says an attacker can steal money,
determine whether that attacker can actually create the required accounts and
state, then execute the alleged attack. Do not give the attacker imaginary
private keys or edit protected accounts to make the demonstration work.

Inputs are an audit candidate, a pinned initial state, attacker-controlled keys
and accounts, an allowed funding budget, program binaries and an independently
specified security property. Deployment/setup assumptions must be explicit.

The proposed research delta is a Solana-specific account/capability model that
helps construct the missing setup transactions. It would track account creation,
owner restrictions, expected addresses/PDAs, actual signer control, token
authorities and permissions passed through CPI. Use it to constrain planning
rather than letting a model invent arbitrary state changes. This component is
proposed, not implemented or known to be novel.

Every accepted witness must run from the declared initial snapshot through
ordinary legal transactions. Creating attacker-owned accounts with chosen data
can be legitimate; overwriting a victim-owned account in the test harness is not
an attacker action. Assigning a token-admin role is a different threat model from
an ordinary outsider and must be labelled accordingly.

Output three outcomes:

- **Validated witness:** a legal chain reaches the stated violation under the
  specified initial state and capabilities.
- **Refuted under the model:** a check or explicit bounded argument rules out the
  particular candidate within the declared scope.
- **Unresolved:** timeout, unsupported operation or incomplete model. Failure to
  find a chain does not establish safety or prove a false positive.

The tool validates exploitability of a particular finding, not whether the whole
program is safe. A replay from a convenient synthetic snapshot does not prove
that the same attack works against a current mainnet deployment.

## How to establish novelty and publication potential

1. **Literature distinction:** fully compare the proposed capability model and
   chain construction with SseRex, FuzzDelSol, Crucible, Riverguard, SmartShot,
   ConFuzzius/SMARTIAN and prior exploit-generation methods. A future-work sentence
   is motivation, not an exclusive claim to the gap.
2. **Corpus:** assemble known reachable findings, deliberately impossible
   assumption cases, legitimate authority-controlled behavior and unresolved
   real-world findings. Record provenance and independently review labels.
   Artificial cases must remain separate from real findings.
3. **Matched experiment:** compare manual/simple transaction templates,
   unconstrained model planning, ordinary sequence fuzzing, and the proposed
   capability-guided planner. Supply identical initial states, action interfaces,
   target properties and budgets. Report human specification effort.
4. **Ablations:** remove capability tracking, account-dependency guidance and
   model assistance separately. A benefit caused only by a larger action set or
   more manual knowledge is not evidence of better planning.
5. **Outcomes:** validated chains per independent finding/family, unsupported and
   unresolved rates, time/cost, false acceptance of impossible demonstrations,
   and independent replay success. Do not score unresolved findings as refuted.

A strong methods paper would need a distinct algorithm and reproducible gains.
A strong empirical paper could instead establish the extent and causes of
unrealistic exploit assumptions across a defensibly sampled corpus. A handful
of planted examples plus a dashboard supports an engineering project, not the
claimed research contribution. There is no evidence yet to guarantee either
paper outcome.

## Next experiment that can change the decision

Use one known reachable finding and one explicitly impossible-owner-mutation
control. Require construction of all attacker setup actions, and run a baseline
with the same legal action interface. Then test independent program families.
If capability modelling adds no useful discrimination or construction benefit,
do not retain the method claim simply because the prototype works.

Record this as a **feasibility experiment**, not a novel vulnerability discovery.
Actual experiments remain the next phase; this review executed no upstream code.

## Audit trail and limitations

[Code inventory](results/solana_gap_code_inventory.json) records five repository
tree probes and four retrieved files with SHA-256 content hashes. Only selected
relevant sections were inspected; entire repositories were not audited. The
repository trees were not truncated. Branch-based raw downloads are separately
hashed and are not claimed to match a pinned commit checkout. Copies are cached
under `/tmp/homie_gap_review`; they are not packaged as project source.

Searches included Token-2022 configuration/stateful fuzzing, Solana environment
mutation and dependency-guided fuzzing, and exploit reachability/precondition
chains. Search engine coverage is incomplete. Publication counts, commercial
marketing claims and repository popularity were not used as evidence that a
method works.

## Further review: exploit generation outside Solana

### Additional closest work

| Work | What it already covers | Implication for this project |
|---|---|---|
| [ExGen, TDSC](https://yinzhicao.org/ExGen/EXGEN.pdf) | Backward analysis constructs partially ordered setup/attack transactions; symbolic execution and private-chain validation on Ethereum/EOS | Constructing preconditions or multi-transaction witnesses is not itself new |
| [SmarTest, USENIX Security 2021](https://www.usenix.org/conference/usenixsecurity21/presentation/so) | Language-model-guided symbolic search for vulnerable transaction sequences | Model-guided sequence search is established; its language model is not the same as today's general-purpose chat models |
| [EF/CF](https://arxiv.org/abs/2304.06341) | Structure-aware fuzzing and exploit generation including cross-contract interactions | Neither compositional execution nor executable financial-impact demonstrations is enough |
| [TracExp, 2026 preprint](https://arxiv.org/html/2601.16681v1) | Reconstructs PoCs from observed attack traces using reverse engineering and model code generation | Known-attack reproduction is a different task from establishing whether an unexecuted warning is realizable; do not claim first automated PoC generation |
| [SmartShot, PACMSE/FSE 2025](https://doi.org/10.1145/3715714) | Mutates state/environment snapshots with symbolic guidance and validation | Must distinguish legal Solana account construction from generic state mutation/validation |
| [PoPoC dataset/thesis](https://zenodo.org/records/17865427) | Curated executable audit PoCs and their oracle quality | Collecting runnable PoCs is already a research direction; a new corpus needs distinct scope and validation |

ExGen is particularly close conceptually: its backward analysis constructs
transactions that prepare state for later exploitation. Its reported evaluation
is Ethereum/EOS. A Solana implementation might be valuable, but a chain-name
substitution would not substantiate a new algorithm.

TracExp begins with observed attacks. Our candidate begins with a warning and
declared capabilities, without the successful attack trace. This is a legitimate
task distinction, not proof that our proposed solution is novel. Its reported
performance was not independently reproduced.

PoPoC's public record describes 58 executable exploits and incomplete assertion
coverage in some original PoCs. The archive is 5.5 GB and was not downloaded;
its contents have not been verified as usable Solana cases. Do not represent it
as a ready Solana dataset.

### What the SmartShot code check establishes

Four candidate files were fetched read-only. In
[`execution_trace_analysis.py`](https://github.com/SCFuzzing/SmartShot/blob/main/fuzzer/engine/analysis/execution_trace_analysis.py),
the inspected snapshot path writes selected storage values into an instrumented
EVM; another path solves constraints involving storage and transaction input.
This confirms that state mutation and symbolic constraints are implementation
elements, not just abstract claims.

It does **not** establish that SmartShot reports unreachable attacks: a partial
read cannot assess its complete validation pipeline. One fetched mutation file
was empty. The [probe manifest](results/smartshot_code_probe.json) records exact
content hashes and inspection leads. The publisher identifies the paper as
PACMSE/FSE 2025; the earlier protocol's ICSE label has been corrected.

### A distinction worth measuring: execution versus attacker realizability

A simulator can execute a transaction successfully after the harness changes
account data. That success establishes behavior under those supplied inputs.
It does not necessarily establish that an outsider can obtain those inputs.

The candidate method must separately check:

1. Who controls the transaction signers, and whether their signatures are valid.
2. Who may create or modify each required account under its actual owner program.
3. Whether an expected address or PDA can be supplied or created by that actor.
4. Which CPI can legitimately supply a PDA signature and which privileges it may
   pass onward.
5. Whether a required token-admin action is within the stated threat model.

[Solana account](https://solana.com/docs/core/accounts),
[PDA](https://solana.com/docs/core/pda), and
[CPI documentation](https://solana.com/docs/core/cpi) define relevant runtime
mechanics. These mechanics are established facts; the research contribution
would be their effective integration into validation/planning, not their discovery.

[LiteSVM exposes signature-verification controls](https://litesvm.github.io/litesvm/api/classes/LiteSVM.html).
Disabling signature checks can be appropriate for ordinary tests, but a final
outsider-exploit witness must not rely on pretending to own a victim's signing
key. Record signature verification and all fixture privileges explicitly. This
review has not established misuse of this option by any particular tool.

### Concrete public evaluation leads

| Lead | What was verified in this review | What remains |
|---|---|---|
| Anchor CPI return-data validation | [PR #4411](https://github.com/otter-sec/anchor/pull/4411) merged on 16 April 2026; code/test changes address return-data producer identity | Pin pre/post revisions, reproduce relevant tests, establish attacker-controlled CPI preconditions |
| Crucible address-pinned owner-mutation reports | The documentation explicitly describes a class of non-exploitable mutations | Obtain actual recorded findings; do not invent a prevalence estimate from documentation |
| Scanner benchmark's corrected account-reinitialization case | [Changelog](https://github.com/AIOilShield/solana-scanner-benchmark) says caller-dependent PDA seeds prevented the described takeover | Recover original/corrected source revisions and independently validate the explanation |
| Sealevel examples | Public insecure/corrected account-validation examples | Resolve licensing and treat as educational rather than production incidents |

The Anchor fix is someone else's finding, not a new vulnerability we discovered.
The initial PR #4231 was closed and superseded; #4411 is the merged fix. A merged
fix does not establish which deployed programs still use older generated code.

One community audit repository inspected during discovery had inconsistent
finding counts and different scope descriptions across its README and metadata.
Its headline numbers were not adopted as ground truth. Use primary patches,
specific reproductions and independent adjudication instead of aggregating
unverified claims.

## Revised research strategy

Start with **measurement**, then decide whether a new planner is justified.
Collect a provenance-checked set of Solana findings and record what each existing
reproducer assumes. Determine whether strict execution under declared attacker
capabilities changes its outcome. Include unresolved cases and disclose how the
sample was selected; convenience sampling cannot establish ecosystem-wide rates.

Use paired tasks in which code is held fixed but relevant account state or actor
capabilities differ. For example, a mint authority may be controlled in one task
and unavailable in another. Judge the exact declared property: a permitted admin
operation is not an outsider exploit. The pairing reduces reliance on superficial
code clues, but paired/counterfactual evaluation itself is not claimed as new.

If the study reveals a material recurring gap, implement capability-guided
precondition construction and compare it with ordinary fuzzing and model-only
planning using the same actions and information. A methods contribution requires
more than an allowlist of known false-positive patterns. An empirical contribution
requires representative enough cases, reliable labels and a result that matters.

**Current recommendation remains Solana auditing, but the next research target
is validation of attacker capabilities—not a general autonomous auditor and not
transfer-fee testing alone.** The documented limitation is credible. Exact method
novelty, prevalence of the problem and publication strength remain unestablished.
Further search can reject overlaps; experiments are now necessary to resolve
the remaining uncertainty.
