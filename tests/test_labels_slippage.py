from tests.conftest import SOL_MINT, USDC_MINT, make_token_swap_tx
from src.labels.slippage import realized_price, wallet_slippage_series
from src.labels.swaps import extract_wallet_swaps

WALLET = "Wallet1"


def test_realized_price_sol_to_usdc():
    tx = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, USDC_MINT, 400.0, tx_index=0)
    swap = extract_wallet_swaps([tx], WALLET)[0]
    # price of SOL in USDC terms
    assert abs(realized_price(swap) - 200.0) < 1e-6


def test_realized_price_none_for_non_quote_pair():
    tx = make_token_swap_tx(100, 1000, WALLET, "TokenA", 10.0, "TokenB", 20.0, tx_index=0)
    swap = extract_wallet_swaps([tx], WALLET)[0]
    assert realized_price(swap) is None


def test_slippage_series_flags_worse_price():
    tx1 = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 1.0, USDC_MINT, 200.0, tx_index=0)
    tx2 = make_token_swap_tx(101, 2000, WALLET, SOL_MINT, 1.0, USDC_MINT, 150.0, tx_index=0)
    swaps = extract_wallet_swaps([tx1, tx2], WALLET)
    series = wallet_slippage_series(swaps)
    assert len(series) == 1
    assert series[0] < 0
