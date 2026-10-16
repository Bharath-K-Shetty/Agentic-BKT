"""Slippage / position-management-quality signal, derived directly from swap
transaction data. No price-oracle or quoted-price API is available in this
environment, so 'slippage' here is a self-referential baseline: how a swap's
realized price compares to the wallet's own prior realized prices for the
same mint pair, not vs. a ground-truth quote. Documented limitation.
"""
from __future__ import annotations

import statistics

from src.labels.swaps import SwapEvent

QUOTE_MINTS = {
    "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}


def realized_price(swap: SwapEvent) -> float | None:
    """Price of the non-quote leg in quote-mint terms. If both legs are
    quote mints (e.g. SOL/USDC), returns the price of mint_in expressed in
    mint_out units instead. None if neither leg is a recognized quote mint
    (can't be valued without an oracle)."""
    in_is_quote = swap.mint_in in QUOTE_MINTS
    out_is_quote = swap.mint_out in QUOTE_MINTS
    if in_is_quote and out_is_quote:
        if swap.amount_in == 0:
            return None
        return swap.amount_out / swap.amount_in
    if in_is_quote and not out_is_quote:
        if swap.amount_out == 0:
            return None
        return swap.amount_in / swap.amount_out
    if out_is_quote and not in_is_quote:
        if swap.amount_in == 0:
            return None
        return swap.amount_out / swap.amount_in
    return None


def slippage_vs_history(swap: SwapEvent, prior_same_pair_swaps: list[SwapEvent]) -> float | None:
    """(realized_price - median(prior realized prices for same pair)) / median.
    `prior_same_pair_swaps` must already be filtered to the same `.pair` and
    to swaps strictly earlier than `swap` (caller's responsibility, keeps
    this function leakage-agnostic)."""
    price = realized_price(swap)
    if price is None:
        return None
    prior_prices = [p for s in prior_same_pair_swaps if (p := realized_price(s)) is not None]
    if not prior_prices:
        return None
    median = statistics.median(prior_prices)
    if median == 0:
        return None
    return (price - median) / median


def wallet_slippage_series(swaps: list[SwapEvent]) -> list[float]:
    """Slippage-vs-history for every swap in a wallet's own chronological
    swap list, each compared only against that wallet's earlier swaps of the
    same pair (no cross-wallet or forward-looking data)."""
    by_pair: dict[tuple[str, str], list[SwapEvent]] = {}
    out = []
    for s in sorted(swaps, key=lambda s: (s.slot, s.tx_index)):
        prior = by_pair.setdefault(s.pair, [])
        val = slippage_vs_history(s, prior)
        if val is not None:
            out.append(val)
        prior.append(s)
    return out
