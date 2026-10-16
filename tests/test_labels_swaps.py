from tests.conftest import SOL_MINT, USDC_MINT, make_token_swap_tx
from src.labels.swaps import extract_wallet_swaps

WALLET = "Wallet1"


def test_extracts_sol_to_token_swap():
    tx = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, "TokenA", 500.0)
    swaps = extract_wallet_swaps([tx], WALLET)
    assert len(swaps) == 1
    s = swaps[0]
    assert s.mint_in == SOL_MINT
    assert s.amount_in == 2.0
    assert s.mint_out == "TokenA"
    assert s.amount_out == 500.0


def test_excludes_failed_tx():
    tx = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, "TokenA", 500.0, err={"InstructionError": [0, {}]})
    assert extract_wallet_swaps([tx], WALLET) == []


def test_ignores_txs_not_touching_wallet():
    tx = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, "TokenA", 500.0)
    assert extract_wallet_swaps([tx], "SomeoneElse") == []


def test_sol_wrap_unwrap_not_counted_as_swap():
    wsol_mint = "So11111111111111111111111111111111111111112"
    tx = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 0.5, wsol_mint, 0.5, tx_index=0)
    assert extract_wallet_swaps([tx], WALLET) == []


def test_pair_is_order_independent():
    tx = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, "TokenA", 500.0)
    s = extract_wallet_swaps([tx], WALLET)[0]
    assert s.pair == tuple(sorted((SOL_MINT, "TokenA")))
