import json

from tests.conftest import FakeSolanaRPCClient, make_block, make_transfer_tx
from src.data_collection import fetch_many_wallets

SAMPLE_WALLET = "SampleWallet1"
ACTIVE_WALLET = "ActiveWallet1"
INACTIVE_WALLET = "InactiveWallet1"
POOL_PDA = "PoolPda1"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SLOT = 500


def _make_sample_raw(tmp_path):
    tx = make_transfer_tx(SLOT, 1000, SAMPLE_WALLET, "SomePda1", 1000)
    path = tmp_path / f"{SAMPLE_WALLET}.json"
    path.write_text(json.dumps([tx]))
    return path


def _block_with_fee_payers(*fee_payers):
    txs = [make_transfer_tx(SLOT, 1000, payer, "receiver", 100) for payer in fee_payers]
    return make_block(SLOT, txs)


def test_discover_candidate_wallets_confirms_system_owned_and_active(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    block = _block_with_fee_payers(ACTIVE_WALLET)
    client = FakeSolanaRPCClient(
        blocks={SLOT: block}, signatures={ACTIVE_WALLET: [{"signature": "sig1"}]}
    )
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=5)
    assert candidates == [ACTIVE_WALLET]


def test_discover_candidate_wallets_excludes_inactive_wallet(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    block = _block_with_fee_payers(INACTIVE_WALLET)
    client = FakeSolanaRPCClient(blocks={SLOT: block}, signatures={INACTIVE_WALLET: []})
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=5)
    assert candidates == []


def test_discover_candidate_wallets_excludes_program_owned_pda(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    block = _block_with_fee_payers(POOL_PDA)
    client = FakeSolanaRPCClient(
        blocks={SLOT: block},
        signatures={POOL_PDA: [{"signature": "sig1"}]},
        account_owners={POOL_PDA: TOKEN_PROGRAM},
    )
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=5)
    assert candidates == []


def test_discover_candidate_wallets_excludes_nonexistent_account(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    block = _block_with_fee_payers("NonexistentAccount1")

    class NullOwnerClient(FakeSolanaRPCClient):
        def get_account_info(self, address):
            return {"value": None}

    client = NullOwnerClient(blocks={SLOT: block})
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=5)
    assert candidates == []


def test_discover_candidate_wallets_excludes_vote_transaction_fee_payers(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    vote_tx = make_transfer_tx(SLOT, 1000, "ValidatorIdentity1", "receiver", 100)
    vote_tx["transaction"]["message"]["instructions"] = [
        {"programId": "Vote111111111111111111111111111111111111111", "accounts": [], "data": ""}
    ]
    block = make_block(SLOT, [vote_tx])
    client = FakeSolanaRPCClient(
        blocks={SLOT: block}, signatures={"ValidatorIdentity1": [{"signature": "sig1"}]}
    )
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=5)
    assert candidates == []


def test_discover_candidate_wallets_excludes_sample_wallet_itself(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    block = _block_with_fee_payers(SAMPLE_WALLET, ACTIVE_WALLET)
    client = FakeSolanaRPCClient(
        blocks={SLOT: block}, signatures={ACTIVE_WALLET: [{"signature": "sig1"}]}
    )
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=5)
    assert candidates == [ACTIVE_WALLET]


def test_discover_candidate_wallets_stops_at_max_candidates(tmp_path):
    sample_path = _make_sample_raw(tmp_path)
    payers = [f"Wallet{i}" for i in range(5)]
    block = _block_with_fee_payers(*payers)
    client = FakeSolanaRPCClient(
        blocks={SLOT: block}, signatures={p: [{"signature": "sig"}] for p in payers}
    )
    candidates = fetch_many_wallets.discover_candidate_wallets(sample_path, client, max_candidates=2)
    assert len(candidates) == 2


def test_discover_candidate_wallets_accepts_multiple_seed_paths(tmp_path):
    sample1 = tmp_path / "Sample1.json"
    sample1.write_text(json.dumps([make_transfer_tx(SLOT, 1000, "Sample1", "x", 100)]))
    sample2 = tmp_path / "Sample2.json"
    other_slot = SLOT + 1
    sample2.write_text(json.dumps([make_transfer_tx(other_slot, 1000, "Sample2", "y", 100)]))

    block1 = _block_with_fee_payers("WalletFromBlock1")
    txs2 = [make_transfer_tx(other_slot, 1000, "WalletFromBlock2", "receiver", 100)]
    block2 = make_block(other_slot, txs2)

    client = FakeSolanaRPCClient(
        blocks={SLOT: block1, other_slot: block2},
        signatures={
            "WalletFromBlock1": [{"signature": "sig1"}],
            "WalletFromBlock2": [{"signature": "sig2"}],
        },
    )
    candidates = fetch_many_wallets.discover_candidate_wallets(
        [sample1, sample2], client, max_candidates=10
    )
    assert set(candidates) == {"WalletFromBlock1", "WalletFromBlock2"}


def test_main_skips_wallets_with_existing_raw_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_many_wallets, "RAW_DIR", tmp_path)
    existing = tmp_path / "AlreadyFetched.json"
    existing.write_text("[]")

    calls = []

    def fake_fetch_wallet(client, address, max_txs):
        calls.append(address)
        return 0

    monkeypatch.setattr(fetch_many_wallets, "fetch_wallet", fake_fetch_wallet)

    wallet_list = tmp_path / "wallets.txt"
    wallet_list.write_text("AlreadyFetched\nNewWallet\n")

    monkeypatch.setattr(
        "sys.argv", ["fetch_many_wallets", "--wallet-list", str(wallet_list)]
    )
    fetch_many_wallets.main()

    assert calls == ["NewWallet"]
