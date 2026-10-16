"""Swap detection: a wallet's transactions where its own net balance moved
negative in exactly one mint and positive in exactly one other. This is the
single source of truth for "was this a swap", reused by sandwich, rug-pull,
and slippage detection, and by feature extraction.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.labels.tx_utils import is_failed, signature, signer_keys, program_ids, wallet_net_deltas


@dataclass(frozen=True)
class SwapEvent:
    wallet: str
    signature: str
    slot: int
    block_time: int
    tx_index: int
    mint_in: str
    amount_in: float
    mint_out: str
    amount_out: float
    program_ids: frozenset[str] = field(default_factory=frozenset)

    @property
    def pair(self) -> tuple[str, str]:
        return tuple(sorted((self.mint_in, self.mint_out)))


def _swap_from_deltas(
    wallet: str, deltas: dict[str, float], tx: dict, tx_index: int
) -> SwapEvent | None:
    negative = {m: d for m, d in deltas.items() if d < 0}
    positive = {m: d for m, d in deltas.items() if d > 0}
    if len(negative) != 1 or len(positive) != 1:
        return None
    mint_in, amount_in = next(iter(negative.items()))
    mint_out, amount_out = next(iter(positive.items()))
    return SwapEvent(
        wallet=wallet,
        signature=signature(tx),
        slot=tx.get("slot", -1),
        block_time=tx.get("blockTime") or 0,
        tx_index=tx_index,
        mint_in=mint_in,
        amount_in=-amount_in,
        mint_out=mint_out,
        amount_out=amount_out,
        program_ids=frozenset(program_ids(tx)),
    )


def extract_wallet_swaps(raw_txs: list[dict], wallet: str) -> list[SwapEvent]:
    swaps = []
    for i, tx in enumerate(raw_txs):
        if is_failed(tx):
            continue
        deltas = wallet_net_deltas(tx, wallet)
        swap = _swap_from_deltas(wallet, deltas, tx, i)
        if swap is not None:
            swaps.append(swap)
    return sorted(swaps, key=lambda s: (s.slot, s.tx_index))


def extract_block_swaps(block_txs: list[dict]) -> list[SwapEvent]:
    """Same logic applied to every signer of every tx in a full block
    (as returned by SolanaRPCClient.get_block). Used for sandwich detection,
    where the counterparties aren't known in advance."""
    swaps = []
    for i, tx in enumerate(block_txs):
        if is_failed(tx):
            continue
        for signer in signer_keys(tx):
            deltas = wallet_net_deltas(tx, signer)
            swap = _swap_from_deltas(signer, deltas, tx, i)
            if swap is not None:
                swaps.append(swap)
    return sorted(swaps, key=lambda s: (s.slot, s.tx_index))
