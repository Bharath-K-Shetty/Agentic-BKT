from tests.conftest import SOL_MINT, make_token_swap_tx
from src.labels.rugpull import rug_pull_events
from src.labels.swaps import extract_wallet_swaps

WALLET = "Wallet1"
MINT = "RugToken"


def test_realized_dump_detected():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 10.0, MINT, 1000.0, tx_index=0)
    sell = make_token_swap_tx(101, 2000, WALLET, MINT, 1000.0, SOL_MINT, 0.5, tx_index=0)
    swaps = extract_wallet_swaps([buy, sell], WALLET)
    events = rug_pull_events(swaps)
    assert len(events) == 1
    e = events[0]
    assert e.kind == "realized_dump"
    assert e.mint == MINT
    assert abs(e.realized_loss_pct - 0.95) < 1e-6


def test_profitable_sell_not_flagged():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 10.0, MINT, 1000.0, tx_index=0)
    sell = make_token_swap_tx(101, 2000, WALLET, MINT, 1000.0, SOL_MINT, 15.0, tx_index=0)
    swaps = extract_wallet_swaps([buy, sell], WALLET)
    assert rug_pull_events(swaps) == []


def test_abandoned_bag_detected_after_threshold():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 10.0, MINT, 1000.0, tx_index=0)
    swaps = extract_wallet_swaps([buy], WALLET)
    now_ts = 1000 + 40 * 86400
    events = rug_pull_events(swaps, abandon_days=30, now_ts=now_ts)
    assert len(events) == 1
    assert events[0].kind == "abandoned_bag"


def test_recent_unsold_bag_not_yet_flagged():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 10.0, MINT, 1000.0, tx_index=0)
    swaps = extract_wallet_swaps([buy], WALLET)
    now_ts = 1000 + 5 * 86400
    assert rug_pull_events(swaps, abandon_days=30, now_ts=now_ts) == []
