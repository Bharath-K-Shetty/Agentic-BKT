from tests.conftest import SOL_MINT, make_token_swap_tx
from src.labels.build_labels import compute_all_labels

WALLET = "Wallet1"
MINT = "RugToken"


def test_compute_all_labels_offline_without_client():
    buy = make_token_swap_tx(100, 1000, WALLET, SOL_MINT, 10.0, MINT, 1000.0, tx_index=0)
    sell = make_token_swap_tx(101, 2000, WALLET, MINT, 1000.0, SOL_MINT, 0.5, tx_index=0)
    labels = compute_all_labels(WALLET, [buy, sell])
    assert labels["wallet"] == WALLET
    assert labels["summary"]["n_swaps"] == 2
    assert labels["summary"]["n_rugpull_realized_dump"] == 1
    assert labels["summary"]["n_sandwich_victim"] == 0
