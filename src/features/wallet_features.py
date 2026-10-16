"""Wallet-level feature extraction for the Part 1 wallet-behavior encoder.
Consumes src.labels outputs; every stat is computed only from the raw_txs
slice passed in, so leakage control (proposal §7) is entirely the caller's
responsibility via the `as_of_ts` cutoff.
"""
from __future__ import annotations

import statistics

from src.labels.build_labels import compute_all_labels
from src.labels.tx_utils import is_failed
from src.labels.swaps import extract_wallet_swaps


def _filter_by_time(raw_txs: list[dict], as_of_ts: int | None) -> list[dict]:
    if as_of_ts is None:
        return raw_txs
    return [tx for tx in raw_txs if (tx.get("blockTime") or 0) <= as_of_ts]


def extract_wallet_features(
    wallet: str,
    raw_txs: list[dict],
    labels: dict | None = None,
    as_of_ts: int | None = None,
) -> dict[str, float]:
    txs = _filter_by_time(raw_txs, as_of_ts)
    if labels is None:
        labels = compute_all_labels(wallet, txs, client=None)

    block_times = [t.get("blockTime") or 0 for t in txs if t.get("blockTime")]
    n_tx = len(txs)
    n_failed = sum(1 for t in txs if is_failed(t))
    span_days = (max(block_times) - min(block_times)) / 86400 if len(block_times) >= 2 else 0.0
    days_since_last = None
    if block_times:
        ref = as_of_ts if as_of_ts is not None else max(block_times)
        days_since_last = (ref - max(block_times)) / 86400

    swaps = extract_wallet_swaps(txs, wallet)
    # amount_in/amount_out are in whichever mint was traded, not always SOL --
    # only swaps with a SOL leg can be meaningfully sized in SOL terms.
    swap_sizes_sol = [
        s.amount_in if s.mint_in == "SOL" else s.amount_out
        for s in swaps
        if "SOL" in (s.mint_in, s.mint_out)
    ]
    unique_tokens = {m for s in swaps for m in (s.mint_in, s.mint_out)}
    unique_programs = {p for s in swaps for p in s.program_ids}

    slippage_series = labels.get("slippage_series", [])
    rugpull = labels.get("rugpull_events", [])
    n_dump = sum(1 for e in rugpull if e["kind"] == "realized_dump")
    n_abandoned = sum(1 for e in rugpull if e["kind"] == "abandoned_bag")
    total_rug_loss = sum(
        (e["buy_value_sol"] - (e["sell_value_sol"] or 0.0))
        for e in rugpull
        if e["kind"] == "realized_dump"
    )

    mints_bought = {s.mint_out for s in swaps if s.mint_in == "SOL"}
    mints_sold = {s.mint_in for s in swaps if s.mint_out == "SOL"}
    pct_bought_never_sold = (
        len(mints_bought - mints_sold) / len(mints_bought) if mints_bought else 0.0
    )

    total_fee_sol = sum(t.get("meta", {}).get("fee", 0) for t in txs) / 1e9

    return {
        "tx_count": float(n_tx),
        "failed_tx_rate": n_failed / n_tx if n_tx else 0.0,
        "active_span_days": span_days,
        "days_since_last_tx": days_since_last if days_since_last is not None else float("nan"),
        "txs_per_day": n_tx / span_days if span_days > 0 else float(n_tx),
        "swap_count": float(len(swaps)),
        "unique_tokens_touched": float(len(unique_tokens)),
        "unique_programs_touched": float(len(unique_programs)),
        "avg_swap_size_sol": statistics.mean(swap_sizes_sol) if swap_sizes_sol else 0.0,
        "median_swap_size_sol": statistics.median(swap_sizes_sol) if swap_sizes_sol else 0.0,
        "avg_slippage_vs_history": statistics.mean(slippage_series) if slippage_series else float("nan"),
        "median_slippage_vs_history": statistics.median(slippage_series) if slippage_series else float("nan"),
        "rugpull_realized_dump_count": float(n_dump),
        "rugpull_abandoned_bag_count": float(n_abandoned),
        "total_realized_rug_loss_sol": total_rug_loss,
        "sandwich_victim_count": float(labels.get("summary", {}).get("n_sandwich_victim", 0)),
        "pct_bought_never_sold": pct_bought_never_sold,
        "total_fee_sol": total_fee_sol,
    }
