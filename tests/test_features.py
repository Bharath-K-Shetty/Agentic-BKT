from tests.conftest import SOL_MINT, make_token_swap_tx
from src.features.wallet_features import extract_wallet_features

WALLET = "Wallet1"
MINT = "TokenA"


def test_basic_feature_extraction():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, MINT, 500.0, tx_index=0)
    sell = make_token_swap_tx(101, 1000 + 86400, WALLET, MINT, 500.0, SOL_MINT, 3.0, tx_index=0)
    feats = extract_wallet_features(WALLET, [buy, sell])
    assert feats["tx_count"] == 2
    assert feats["swap_count"] == 2
    assert feats["failed_tx_rate"] == 0.0
    assert feats["unique_tokens_touched"] == 2  # SOL + TokenA
    assert feats["rugpull_realized_dump_count"] == 0.0  # profitable sell


def test_swap_size_sol_ignores_non_sol_denominated_swaps():
    # token-to-token swap: amount_in is in TokenB units (huge), not SOL --
    # must not corrupt avg/median_swap_size_sol
    token_swap = make_token_swap_tx(100, 1000, WALLET, "TokenB", 81111.0, MINT, 500.0, tx_index=0)
    sol_swap = make_token_swap_tx(101, 1000 + 60, WALLET, SOL_MINT, 2.0, MINT, 500.0, tx_index=0)
    feats = extract_wallet_features(WALLET, [token_swap, sol_swap])
    assert feats["avg_swap_size_sol"] == 2.0
    assert feats["median_swap_size_sol"] == 2.0


def test_as_of_ts_excludes_later_txs():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 2.0, MINT, 500.0, tx_index=0)
    sell = make_token_swap_tx(101, 1000 + 86400, WALLET, MINT, 500.0, SOL_MINT, 0.1, tx_index=0)
    feats_before = extract_wallet_features(WALLET, [buy, sell], as_of_ts=1000 + 100)
    feats_after = extract_wallet_features(WALLET, [buy, sell], as_of_ts=1000 + 2 * 86400)
    assert feats_before["tx_count"] == 1
    assert feats_before["rugpull_realized_dump_count"] == 0.0
    assert feats_after["tx_count"] == 2
    assert feats_after["rugpull_realized_dump_count"] == 1.0
