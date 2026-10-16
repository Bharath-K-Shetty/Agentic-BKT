"""Sandwich-attack victim detection: for each of a wallet's own swaps, fetch
the full block at that slot and look for another wallet's swap on the same
mint pair immediately before (frontrun, same direction, pushes price against
the victim) and immediately after (backrun, opposite direction, unwinds the
position) it, in program-order.

This is the one label in `src.labels` that needs network access beyond the
wallet's own transaction history, since the front/backrun transactions
belong to a different signer and won't appear in `getSignaturesForAddress`
for the victim wallet. `client=None` makes this a safe no-op, so it can be
skipped entirely when running offline / in tests that don't want network
calls.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.data_collection.solana_client import SolanaRPCClient
from src.labels.swaps import SwapEvent, extract_block_swaps, extract_wallet_swaps


@dataclass(frozen=True)
class SandwichEvent:
    victim_wallet: str
    victim_sig: str
    attacker_wallet: str
    slot: int
    mint_pair: tuple[str, str]
    front_sig: str
    back_sig: str
    est_loss_ui: float | None


def _is_frontrun(candidate: SwapEvent, victim: SwapEvent) -> bool:
    return (
        candidate.wallet != victim.wallet
        and candidate.mint_in == victim.mint_in
        and candidate.mint_out == victim.mint_out
    )


def _is_backrun(candidate: SwapEvent, victim: SwapEvent, attacker: str) -> bool:
    return (
        candidate.wallet == attacker
        and candidate.mint_in == victim.mint_out
        and candidate.mint_out == victim.mint_in
    )


def _estimate_loss_ui(victim: SwapEvent, front: SwapEvent) -> float | None:
    if victim.amount_out == 0 or front.amount_out == 0:
        return None
    victim_price = victim.amount_in / victim.amount_out
    front_price = front.amount_in / front.amount_out
    if victim_price <= front_price:
        return None
    return (victim_price - front_price) * victim.amount_out


def _find_sandwich(block_swaps: list[SwapEvent], victim: SwapEvent) -> SandwichEvent | None:
    same_pair = [s for s in block_swaps if s.pair == victim.pair]
    same_pair.sort(key=lambda s: s.tx_index)
    try:
        idx = next(
            i
            for i, s in enumerate(same_pair)
            if s.signature == victim.signature and s.wallet == victim.wallet
        )
    except StopIteration:
        return None
    if idx == 0 or idx == len(same_pair) - 1:
        return None
    front, back = same_pair[idx - 1], same_pair[idx + 1]
    if not _is_frontrun(front, victim):
        return None
    if not _is_backrun(back, victim, front.wallet):
        return None
    return SandwichEvent(
        victim_wallet=victim.wallet,
        victim_sig=victim.signature,
        attacker_wallet=front.wallet,
        slot=victim.slot,
        mint_pair=victim.pair,
        front_sig=front.signature,
        back_sig=back.signature,
        est_loss_ui=_estimate_loss_ui(victim, front),
    )


def detect_sandwich_for_wallet(
    wallet: str,
    raw_txs: list[dict],
    client: SolanaRPCClient | None,
    block_cache: dict[int, dict] | None = None,
) -> list[SandwichEvent]:
    if client is None:
        return []
    block_cache = {} if block_cache is None else block_cache
    victim_swaps = extract_wallet_swaps(raw_txs, wallet)

    events = []
    for victim in victim_swaps:
        block = block_cache.get(victim.slot)
        if block is None:
            block = client.get_block(victim.slot)
            block_cache[victim.slot] = block
        if not block:
            continue
        block_txs = block.get("transactions", [])
        block_swaps = extract_block_swaps(block_txs)
        event = _find_sandwich(block_swaps, victim)
        if event is not None:
            events.append(event)
    return events
