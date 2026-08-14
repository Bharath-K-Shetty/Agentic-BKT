# homie-research

Final year AI research project — Phase 2 of HeyHomie. See
[`docs/PROPOSAL.md`](docs/PROPOSAL.md) for the full writeup.

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

Month 1: building the wallet transaction data collection pipeline
(`src/data_collection/`). No model training yet.
