"""Rug-pull exposure, from the wallet's own buy/sell swap pairs. Values only
swaps traded directly against SOL (the only mint every wallet unavoidably
has price context for) -- multi-hop routes through an intermediate token
without a direct SOL leg are not valued, a documented scope limit rather
than an oracle-based valuation (no price API available in this project).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.labels.swaps import SwapEvent
from src.labels.tx_utils import SOL


@dataclass(frozen=True)
class RugPullEvent:
    wallet: str
    mint: str
    buy_sig: str
    buy_slot: int
    buy_value_sol: float
    sell_sig: str | None
    sell_slot: int | None
    sell_value_sol: float | None
    kind: Literal["realized_dump", "abandoned_bag"]
    realized_loss_pct: float | None


def _sol_buys_and_sells(swaps: list[SwapEvent]) -> tuple[dict[str, list[SwapEvent]], dict[str, list[SwapEvent]]]:
    buys: dict[str, list[SwapEvent]] = {}
    sells: dict[str, list[SwapEvent]] = {}
    for s in sorted(swaps, key=lambda s: (s.slot, s.tx_index)):
        if s.mint_in == SOL and s.mint_out != SOL:
            buys.setdefault(s.mint_out, []).append(s)
        elif s.mint_out == SOL and s.mint_in != SOL:
            sells.setdefault(s.mint_in, []).append(s)
    return buys, sells


def rug_pull_events(
    swaps: list[SwapEvent],
    dump_loss_threshold: float = 0.8,
    abandon_days: int = 30,
    now_ts: int | None = None,
) -> list[RugPullEvent]:
    """FIFO-pairs each mint's SOL-denominated buys against its SOL-
    denominated sells. `now_ts` (unix seconds) anchors the abandoned-bag
    check; defaults to the latest block_time seen across `swaps`."""
    buys, sells = _sol_buys_and_sells(swaps)
    if now_ts is None:
        now_ts = max((s.block_time for s in swaps), default=0)

    events: list[RugPullEvent] = []
    for mint, mint_buys in buys.items():
        mint_sells = list(sells.get(mint, []))
        sell_i = 0
        for buy in mint_buys:
            if sell_i < len(mint_sells):
                sell = mint_sells[sell_i]
                sell_i += 1
                loss_pct = None
                if buy.amount_in > 0:
                    loss_pct = (buy.amount_in - sell.amount_out) / buy.amount_in
                if loss_pct is not None and loss_pct >= dump_loss_threshold:
                    events.append(
                        RugPullEvent(
                            wallet=buy.wallet,
                            mint=mint,
                            buy_sig=buy.signature,
                            buy_slot=buy.slot,
                            buy_value_sol=buy.amount_in,
                            sell_sig=sell.signature,
                            sell_slot=sell.slot,
                            sell_value_sol=sell.amount_out,
                            kind="realized_dump",
                            realized_loss_pct=loss_pct,
                        )
                    )
            else:
                days_since_buy = (now_ts - buy.block_time) / 86400
                if days_since_buy >= abandon_days:
                    events.append(
                        RugPullEvent(
                            wallet=buy.wallet,
                            mint=mint,
                            buy_sig=buy.signature,
                            buy_slot=buy.slot,
                            buy_value_sol=buy.amount_in,
                            sell_sig=None,
                            sell_slot=None,
                            sell_value_sol=None,
                            kind="abandoned_bag",
                            realized_loss_pct=None,
                        )
                    )
    return sorted(events, key=lambda e: e.buy_slot)
