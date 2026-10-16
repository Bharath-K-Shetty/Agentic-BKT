"""Leakage-boundary and holdout logic for wallet-level evaluation (proposal
§7: features come from earlier history, the target label from a later,
forward-looking window)."""
from __future__ import annotations

import random


def time_based_wallet_split(raw_txs: list[dict], as_of_ts: int) -> tuple[list[dict], list[dict]]:
    """Partition one wallet's raw_txs into (history, forward) by blockTime.
    No tx appears in both halves."""
    history = [tx for tx in raw_txs if (tx.get("blockTime") or 0) <= as_of_ts]
    forward = [tx for tx in raw_txs if (tx.get("blockTime") or 0) > as_of_ts]
    return history, forward


def as_of_ts_at_fraction(raw_txs: list[dict], frac: float) -> int | None:
    """The blockTime that splits a wallet's own history at `frac` through
    its span (0=earliest tx, 1=latest tx)."""
    times = sorted(t.get("blockTime") or 0 for t in raw_txs)
    if not times:
        return None
    idx = min(len(times) - 1, int(len(times) * frac))
    return times[idx]


def wallet_train_test_split(
    wallet_addresses: list[str], test_frac: float = 0.2, seed: int = 42
) -> tuple[list[str], list[str]]:
    """Wallet-level holdout. With single-digit-to-dozens wallets in Month 1
    this is a coarse split, documented as such."""
    addrs = list(wallet_addresses)
    random.Random(seed).shuffle(addrs)
    n_test = max(1, int(len(addrs) * test_frac)) if addrs else 0
    return addrs[n_test:], addrs[:n_test]
