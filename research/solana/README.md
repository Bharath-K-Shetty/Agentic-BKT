# Solana audit-finding validation: feasibility workspace

This workspace starts the measurement study proposed in
[the gap review](../../docs/SOLANA_GAP_REVIEW.md). It contains source provenance,
a case registry and executable local runtime controls. It is not a completed
auditor, exploit planner, representative benchmark or publication result.

## Reproduce the controls

From the repository root, with Solana's `cargo build-sbf` installed:

```bash
.venv/bin/pip install -r research/solana/requirements.txt
cargo build-sbf --manifest-path research/solana/runtime-controls/Cargo.toml --sbf-out-dir research/solana/target/deploy
.venv/bin/python research/solana/run_controls.py
.venv/bin/python -m pytest -q tests/test_solana_controls.py
```

Commit the Cargo.lock alongside the fixture source: newer dependency resolutions
can require an edition unsupported by the installed Solana platform compiler.
The initial build uses Solana CLI/build-sbf 2.3.0 and platform-tools 1.48.
Python dependency versions, source/lockfile hashes and the binary hash are
included in the result JSON.
No cluster connection, RPC URL, wallet file or real funds are used. Deterministic
keys are public lab identities and must never hold real funds.

`run_controls.py` records transaction bytes/hashes, signer identities, signature-check
settings, program logs, failures and observed properties in
[`runtime_controls.json`](../../docs/results/solana/runtime_controls.json).
Each control uses a fresh LiteSVM. Program loading and funding are declared
fixture operations. Account construction uses real local transactions except
the deliberately labelled invalid account-injection control.

The same authored binary is loaded under four fixture program identities. The
return-data control demonstrates runtime behavior; it does not reproduce Anchor
source revisions or establish that an application exposes an attacker-controlled
intervening CPI. The owner control uses a custom record, not an SPL Token account.
The trusted writer additionally requires the declared fixture administrator;
the outsider cannot initialize arbitrary records under that trusted owner.
The signer allowlist is a small harness guard, not an inferred capability model
or a security boundary against a caller with access to the Python VM object.

## Public sources

[`registry.json`](cases/registry.json) keeps three leads separate:

- A merged Anchor return-data validation fix, with exact before/after revisions.
- Crucible's documented address-pinned owner-mutation limitation, not a recorded
  population of false positives.
- A Sealevel educational owner-check example, not a production theft incident.

Fetch the pinned evidence with:

```bash
.venv/bin/python research/solana/collect_sources.py
```

The collector records exact commits and content hashes in
[`source_manifest.json`](cases/source_manifest.json). Crucible's branch is resolved
to a commit at collection time; rerunning collection can create a new snapshot.
Upstream files are cached locally in the ignored `cache/` directory. They are not
redistributed here. Licensing must be reviewed before adding upstream code to a
published dataset. Source collection alone is not independent bug adjudication.

## Study protocol and next work

Research question: **How often do public Solana exploit demonstrations rely on
capabilities unavailable to the stated attacker, and can those preconditions be
constructed through legal transactions?** This is a question, not an established
prevalence claim.

Before scoring a finding, record the source revision, deployed program/fixture
identities, original security claim, initial accounts, signer control, funding,
owner/write permissions, PDA/CPI assumptions, security oracle and setup sequence.
Separate fixture establishment from attacker actions. Keep admin and outsider
threat models separate. A present-day deployment claim needs a verified snapshot,
not merely vulnerable historical source code.

Eligible empirical cases need public source/patch provenance and enough detail
to specify an independent violation oracle. Record rejected leads and reasons.
Deduplicate reports of the same underlying bug; group related program families
when splitting future training/tuning and held-out evaluation. Educational and
authored cases are calibration controls, never independent production findings.
The present convenience sample supports feasibility only.

Use three outcomes: validated legal witness, refuted within an explicitly bounded
model, or unresolved. A failing transaction or timeout remains unresolved at the
finding level unless a separate bounded argument rules out the candidate.
Preserve raw original reproductions and the strict rerun result; do not silently
rewrite a failed PoC into a successful one. Obtain independent label review.

Next milestones, in order:

1. Execute the pinned Anchor upstream reproducer before and after the fix; record
   build dependencies and the intervening-CPI assumptions. Currently pending.
2. Obtain an actual recorded address-pinned owner-mutation report and replay it;
   documentation and our protected-record control are not substitutes.
3. Expand the provenance-checked production corpus and independently adjudicate
   cases. Freeze inclusion rules before estimating rates.
4. Compare legal-action templates, sequence fuzzing and model-only planning with
   identical initial states/actions/budgets. Only then test a capability-guided
   planner and its ablations.

Do not present the control pass count as detection accuracy, evidence of novelty
or proof that real programs are safe. No upstream reproduction or new
vulnerability discovery is claimed by this first milestone.
