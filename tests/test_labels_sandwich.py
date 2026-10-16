from tests.conftest import FakeSolanaRPCClient, SOL_MINT, make_block, make_token_swap_tx
from src.labels.sandwich import detect_sandwich_for_wallet

VICTIM = "Victim1"
ATTACKER = "Attacker1"
OTHER_A = "Other1"
OTHER_B = "Other2"
MINT = "TokenX"


def test_detects_classic_sandwich():
    slot = 500
    block_time = 1000
    front = make_token_swap_tx(slot, block_time, ATTACKER, SOL_MINT, 5.0, MINT, 1000.0, tx_index=0)
    victim_tx = make_token_swap_tx(slot, block_time, VICTIM, SOL_MINT, 5.0, MINT, 800.0, tx_index=1)
    back = make_token_swap_tx(slot, block_time, ATTACKER, MINT, 1000.0, SOL_MINT, 6.0, tx_index=2)
    block = make_block(slot, [front, victim_tx, back])
    client = FakeSolanaRPCClient(blocks={slot: block})

    events = detect_sandwich_for_wallet(VICTIM, [victim_tx], client)
    assert len(events) == 1
    e = events[0]
    assert e.attacker_wallet == ATTACKER
    assert e.victim_wallet == VICTIM
    assert e.est_loss_ui is not None
    assert e.est_loss_ui > 0


def test_no_false_positive_on_unrelated_swaps():
    slot = 501
    block_time = 1000
    tx_a = make_token_swap_tx(slot, block_time, OTHER_A, SOL_MINT, 1.0, MINT, 100.0, tx_index=0)
    victim_tx = make_token_swap_tx(slot, block_time, VICTIM, SOL_MINT, 1.0, MINT, 100.0, tx_index=1)
    tx_b = make_token_swap_tx(slot, block_time, OTHER_B, SOL_MINT, 1.0, MINT, 100.0, tx_index=2)
    block = make_block(slot, [tx_a, victim_tx, tx_b])
    client = FakeSolanaRPCClient(blocks={slot: block})

    events = detect_sandwich_for_wallet(VICTIM, [victim_tx], client)
    assert events == []


def test_client_none_is_noop():
    slot = 500
    victim_tx = make_token_swap_tx(slot, 1000, VICTIM, SOL_MINT, 5.0, MINT, 800.0, tx_index=1)
    assert detect_sandwich_for_wallet(VICTIM, [victim_tx], None) == []
