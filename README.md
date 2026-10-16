# homie-research

## Active investigation — AI/ML on real blockchain data

The [integrated live prototype](http://127.0.0.1:8430/live) now combines current
network checks, actual model inference on freshly collected mature history, and
prospective decision/receipt recording. Live scores remain experimental; no
ML-driven fee or time saving has been established. See [setup and demo steps](webapp/README.md).

Working additions: [actual trained-model inference](http://127.0.0.1:8430/predict)
on held-out historical inputs and a [live SOL transfer checker](http://127.0.0.1:8430/check)
for balance, fee quotes and unsigned simulation. See [the setup and demonstration](webapp/README.md).
The live utility is based on RPC checks; it does not claim a validated live ML
score or measured retry-time savings. The [local fee experiment](http://127.0.0.1:8430/fee-proof)
verifies a paid execution failure and a matching stopped attempt using test SOL.
It also shows that normal preflight rejects this example for free; no added
saving over preflight or ML-driven saving has been demonstrated.

The [final-presentation replay](webapp/README.md) runs locally at
http://127.0.0.1:8430 after starting
`.venv/bin/python -m uvicorn webapp.backend.replay:app --host 127.0.0.1 --port 8430`.
It compares saved ML predictions, exposes the historical information boundary,
reveals actual outcomes, includes model mistakes and reports the full calibration
follow-up. Build the local bundle with
`OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/build_replay_demo.py`.
This is a historical research demo; scores are not live transaction guarantees.
The [demo guide](webapp/README.md) also records a fifth, previously unused test
window: identity-controlled first-appearance AP gain +0.0186, with a positive
hour-bootstrap interval, plus the calibration follow-up's mixed tradeoffs.

The project requirement is an AI/ML contribution using real blockchain data.
The active candidate is now [cold-signer execution-risk screening on Solana](docs/SOLANA_TRANSACTION_RISK_RESULTS.md):
test whether declared account context helps when signer outcome history is
unavailable. Two time windows show a positive primary ranking gain; a later
alternate-shard extension and stronger identity controls are reported alongside
them. A reserved fourth period passes the refined first-appearance test after
identity control: AP gain +0.0316 on 17,904 first appearances, with a positive
hour-bootstrap interval. This supports a specific empirical benchmark candidate;
generalization, calibration and global originality remain unresolved. It is not
publication-ready. See [the working paper outline](docs/paper/SOLANA_COLD_SIGNER_OUTLINE.md).

Earlier token-collapse experiments are preserved below.
The [Solana ML feasibility review](docs/SOLANA_ML_FEASIBILITY_REVIEW.md) investigates
early token-risk prediction, existing graph methods, public datasets and a
bounded next experiment. The generic temporal-GNN detector substantially overlaps
with existing work; a distinct method and publication potential remain unproven.
The [first executed Solana ML pilot](docs/SOLANA_PREFIX_BASELINE_RESULTS.md)
uses 6,000 sampled real tokens and fixed transaction prefixes to predict later
price collapse. It provides an initial baseline, not a novel detector.
See the [reproduction commands](research/solana/ml/README.md).
The [confirmation study](docs/SOLANA_CONFIRMATION_RESULTS.md) now evaluates
12,000 additional, disjoint sample tokens across three calendar test periods.
It does not confirm a consistent coordination-feature gain in the primary
comparison. The [next publication gate](docs/SOLANA_PUBLICATION_NEXT_GATE.md)
sets out the controls and independent evidence still needed.
The [stronger-baseline follow-up](docs/SOLANA_STRONG_BASELINE_RESULTS.md) compares
27 versus 120 prefix features on 10,000 further sample tokens. Richer RF features
improve the primary AP comparison. A separate 2026 source has been downloaded
and audited, but exact external validation remains incomplete because its
inspected post-migration observations do not match the transaction-minimum target.
The [delayed-outcome experiment](docs/SOLANA_DELAYED_REPLAY_RESULTS.md) now tests
seven warning-calibration controls on 8,000 further sampled tokens. Delay weighting
increases recall slightly but also increases false alarms and fails its fixed
success criterion. A useful new algorithm and publication readiness remain unproven.
The audit-tool direction below is retained as earlier work.

## Earlier investigation — Solana audit-finding validation

The earlier security-study direction investigated whether a reported Solana exploit can be
executed under the attacker's actual account and signing permissions. The
[feasibility workspace](research/solana/README.md) contains pinned public-source
leads, a case registry and runnable local runtime controls. See the
[literature and gap review](docs/SOLANA_GAP_REVIEW.md) for overlapping work and
unresolved novelty questions. This is an initial study, not a completed auditor
or a publication-ready result. Earlier DKT and wallet experiments remain below
as historical work.

The [first feasibility results](docs/SOLANA_FEASIBILITY_RESULTS.md) record ten
passing local runtime controls and three targeted regression tests. These are
authored controls, not detection-accuracy results or upstream bug reproductions.

## Real public learner data — EdNet pilot

EdNet KT2 and question metadata are now downloaded locally. A reproducible pilot
contains 1,000 real learners and 65,158 responses, with learner-disjoint model
evaluation. See [the source, protocol, commands and limitations](docs/EDNET_PILOT.md).
This evaluates English-learning prediction; DeFi learning benefit remains
unestablished. The follow-up audit is described below.

The [telemetry audit](docs/EDNET_AUDIT_RESULTS.md) is now implemented and evaluated
over three neural training seeds. Combined timing/revision DKT does not improve
over correctness DKT; tested recommendation sensitivity is small, and the
consistency gate offers little benefit. These exploratory findings do not
establish a publishable novel method. Protocol, controls and results are retained.

A [replication with original skill tags](docs/EDNET_SKILL_RESULTS.md) now uses a
second cohort of 1,000 learners with zero overlap. Tags improve the logistic
baseline to 0.627 AUC; tag-based DKT is about 0.609, with no reliable timing/revision
gain. Both encodings are compared on identical targets without splitting a
multi-tag response into multiple events.

The [research decision and literature check](docs/RESEARCH_DECISION.md) now
include a missing question-difficulty control: skill/question information plus
learner history reaches 0.681 AUC on the same replication test targets. Telemetry
adds only 0.0004 AUC, with an interval including zero. This is a stronger control,
not a new algorithm or an information-matched neural/logistic comparison.

## Decision lab — behavioral DKT extension

The current prototype now includes an instrumented transaction simulator.
Learners inspect evidence, approve/reject/modify hypothetical requests,
adjust order sizes and slippage, and receive concept-specific coaching.
Five uncoached diagnostics precede ten practice scenarios (two per skill).
Adaptive practice prioritizes weaker skills using diagnostic and practice history;
the fixed arm sees the same items in a fixed order. Five later transfer scenarios
hold scoring feedback until final review. Existing v1 sessions retain their old bank.

Open http://127.0.0.1:8420/simulator.html with the normal server running.
The [decision-lab protocol](docs/DECISION_LAB.md) describes the draft rubrics,
telemetry, exports, behavior-augmented DKT, feature ablations, and limitations.
Live ordering currently uses configured BKT; behavioral DKT is evaluated offline.

```bash
.venv/bin/python -m src.eval.run_simulator --synthetic --epochs 2
.venv/bin/python -m src.learning.simulator --completed-only
.venv/bin/python -m src.eval.run_simulator --input data/processed/simulator/interactions.csv --epochs 10 --output data/processed/simulator/real-eval
```

The simulator has a complete runnable implementation. Its rubrics and
educational effectiveness still require independent review and real learner data.

## Earlier direction — HOMIE DeFi learning lab

The earlier final-year prototype explored **Deep Knowledge Tracing for scenario-based
DeFi education**. The complete local prototype includes a diagnostic quiz,
short lessons, adaptive practice, a separate final check, session resume and
deletion, opt-in research collection, and a learner-level model benchmark.
The earlier wallet research below is exploratory background, not evidence
that wallet losses measure knowledge.

Start the app:

```bash
.venv/bin/python -m src.eval.run_learning --synthetic --epochs 5
.venv/bin/python -m uvicorn webapp.backend.main:app --host 127.0.0.1 --port 8420
```

Open http://127.0.0.1:8420. The generated synthetic DKT checkpoint powers
the explicitly labeled demo; without it, the app uses a configured BKT
baseline. Opt-in sessions never use a synthetic-trained DKT model. They
use the configured BKT baseline until a compatible learner-trained
checkpoint is selected with `HOMIE_DKT_MODEL` before starting the server.

The implementation is demo-ready; **DeFi learning effectiveness and prediction
accuracy on HOMIE learners have not been established**. The authored question bank
needs educator review before recruiting participants. See
[the research protocol and commands](docs/DKT_PROJECT.md) and
[the current project report](docs/DKT_PROJECT_REPORT.md).

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.learning.service --completed-only
.venv/bin/python -m src.eval.run_learning --input data/processed/learning/interactions.csv --epochs 10 --output data/processed/learning/real-eval
```

Only opt-in records are exported. At least six learners with ordered
response sequences are needed to execute the benchmark; that is a software
minimum, not a statistically sufficient study size. Never report synthetic
metrics as evidence about real learners.

## Earlier wallet prediction work

Final year AI research project — Phase 2 of HeyHomie. See
[`docs/PROPOSAL.md`](docs/PROPOSAL.md) for the full writeup and
[`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md) for the running log of
methodology decisions and preliminary findings as they happen.

Core question: can real, public, on-chain wallet behavior predict a DeFi
learner's future costly mistakes better than quiz data alone?

## Structure

```
src/
  data_collection/   Solana RPC clients, wallet tx history fetchers
  labels/            weak-label construction (rug-pull, sandwich, slippage)
  features/          feature engineering over raw tx history
  models/            wallet behavior encoder, KT head
  eval/              baselines, metrics, ablations
data/
  raw/               untouched pulled data (gitignored)
  processed/         feature tables, label tables (gitignored)
notebooks/           exploration
docs/                proposal, notes, writeup drafts
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Status

Month 1 plumbing is in place:

- `src/data_collection/` — Solana RPC client, single- and batch-wallet
  history fetchers. `fetch_many_wallets.py` discovers candidate wallets by
  scanning full blocks at slots already-fetched wallets transacted in (no
  paid indexer access needed), filtering out validator vote accounts and
  program-owned PDAs, or accepts a manual `--wallet-list`.
- `src/labels/` — offline weak-label heuristics computed directly from raw
  transaction balance deltas (no external dataset downloads): swap
  detection, rug-pull exposure (realized dumps + abandoned bags), slippage
  vs. own trading history. Sandwich-attack victim detection additionally
  needs `getBlock` calls (network-dependent, opt-in).
- `src/features/` — per-wallet feature table built from the labels.
- `src/models/` — `WalletRiskBaseline` (sklearn GBDT/logreg, Part 1) and a
  standard LSTM-based `DKT` baseline trained on a synthetic
  quiz-interaction generator (Part 2 case study; real HeyHomie data isn't
  available in this repo yet, but the schema is a drop-in swap).
- `src/eval/` — leakage-safe time-based train/test splits and an end-to-end
  smoke-test CLI (`run_wallet_baseline.py`).
- `tests/` — offline unit tests for every label/feature/eval/model module
  (`pytest`).

127 real wallets are collected in `data/raw/` as of this writing (1,434
swaps, 31 realized rug-pull-dump events — see
[`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md) for exact current
counts). The Part 1 baseline trains end-to-end on this data, but **no
trustworthy result yet**: AUC hovers around 0.47–0.49 (indistinguishable
from random) at N=127 under both a 70/30 and 50/50 history/forward split.
An earlier N=83 run had scored AUC 0.667, but that did not replicate as N
grew — a concrete illustration of why small-N single-split AUC shouldn't be
trusted, documented in RESEARCH_NOTES. Two real data-quality bugs were
found and fixed by running against live mainnet data (validator-vote false
candidates, wrapped-SOL swap false positives). Getting a trustworthy eval
needs substantially more wallets (rate-limited on the free public RPC),
cross-validation instead of a single random split, and probably biasing
collection toward wallets more likely to have hit a rug-pull/sandwich (the
current block-scan discovery samples generic active wallets, not
risk-selected ones).

Not yet done: Part 1 hasn't been evaluated at a statistically meaningful N;
rug-pull heuristic isn't validated against a labeled dataset (none was
available offline); real HeyHomie quiz data hasn't been wired into the DKT
baseline (that data lives in HeyHomie's own app/database, not this repo).

Run the tests: `pytest`
Collect more wallets: `python -m src.data_collection.fetch_many_wallets --discover-from-all-raw --discover-count 60 --max-txs 60`
Run the Part 1 smoke eval: `python -m src.eval.run_wallet_baseline`
