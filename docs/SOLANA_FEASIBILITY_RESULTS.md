# First Solana feasibility milestone

Date: 8 October 2026. Scope: local authored runtime controls and pinned source
collection. This milestone does not execute upstream Anchor/Sealevel programs,
discover a vulnerability, estimate detection accuracy, or establish novelty.

## What now runs

The [workspace and reproduction commands](../research/solana/README.md) build a
native Solana fixture and execute ten controls in fresh local LiteSVM instances.
The [machine-readable results](results/solana/runtime_controls.json) include
serialized transactions, signer identities, runtime logs, failure codes, observed
properties, signature-check settings and binary/source hashes.

| Control | Observed behavior | Interpretation |
|---|---|---|
| Outsider submits a transfer with an unavailable signature | Rejected; recipient not credited | This transfer attempt fails with signature verification enabled |
| Same transfer with signature verification disabled | Executes | Invalid outsider witness; explicit harness shortcut |
| Same transfer with actual signer control | Executes | Legal local transfer under a different capability assumption |
| Attacker creates and writes a record; consumer omits owner check | Fabricated balance accepted | Legal construction path in an authored vulnerable fixture |
| Same attacker record; consumer checks trusted owner | Rejected | This attempted substitution fails |
| Legitimate record initialized by trusted writer's admin | Checked consumer accepts | Positive control against an always-rejecting consumer |
| Protected record changed by an outsider writer attempt | Write and subsequent fabricated-balance assertion fail | Tested attempt rejected, not a universal unreachability proof |
| Protected record changed directly by the test harness | Fabricated balance accepted | Invalid witness relying on a harness-only mutation |
| Intervening CPI changes return data; producer unchecked | Substituted value accepted | Native model of the documented return-data mechanism |
| Same intervening CPI; producer checked | Rejected | Native producer check blocks this attempt |

All **10/10 expected control observations passed**. Three targeted regression
tests also pass: capability-gate rejection before execution, all runtime-control
outcomes, and outsider rejection by the trusted writer. These counts measure
regression checks on authored fixtures, not research performance.

The controls show that execution success can differ from a valid outsider
witness. They do not show how frequently public audit demonstrations have that
problem or whether a new planner outperforms existing tools.

## Public case collection

The [case registry](../research/solana/cases/registry.json) contains three distinct
leads. The [source manifest](../research/solana/cases/source_manifest.json) records
eight files at exact revisions, with hashes and local-only cached contents.

- **Anchor return-data fix:** the merged fix and its parent are pinned. Both
  standard and `declare_program!` code-generation paths were collected, along
  with the added test source. Upstream build/replay remains pending.
- **Crucible owner-mutation limitation:** a documented limitation is pinned.
  An actual recorded finding and independent replay are still needed.
- **Sealevel owner checks:** insecure/secure educational examples are pinned.
  They remain separate from production findings and authored controls.

The Anchor test source includes an explicit intervening malicious-program CPI.
That is a supplied reproducer condition, not evidence that every application
using the older helper exposes such a CPI to an outsider. Its post-fix
`get_unchecked()` demonstration models the old behavior; it must not be reported
as execution of the pre-fix revision. A proper before/after study must run both
revisions or disclose any compatibility adaptation precisely.

## Decision and outstanding evidence

Continue with the measurement-first study. The harness is technically feasible;
the publication hypothesis remains untested. Next, reproduce an upstream case,
record all attacker/fixture assumptions, obtain a real address-pinned mutation
report, and expand to independently reviewed production cases. A failing replay
must remain unresolved unless a separate bounded argument refutes the finding.

No capability-guided planner, fuzzing/model baseline comparison, independent
ground-truth review or held-out evaluation has been completed. Do not claim
publication readiness from this milestone. The detailed inclusion rules and next
steps are in the [workspace protocol](../research/solana/README.md).
