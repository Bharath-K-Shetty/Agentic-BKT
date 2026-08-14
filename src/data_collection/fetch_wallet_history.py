"""Pull a wallet's full transaction history from public Solana RPC and
save it to data/raw/<address>.json.

Usage:
    python -m src.data_collection.fetch_wallet_history <wallet_address> [--max-txs 2000]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from src.data_collection.solana_client import SolanaRPCClient

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def fetch_signatures(client: SolanaRPCClient, address: str, max_txs: int) -> list[str]:
    signatures: list[str] = []
    before = None
    with tqdm(total=max_txs, desc="signatures") as pbar:
        while len(signatures) < max_txs:
            page = client.get_signatures_for_address(address, limit=min(1000, max_txs - len(signatures)), before=before)
            if not page:
                break
            for entry in page:
                signatures.append(entry["signature"])
            pbar.update(len(page))
            before = page[-1]["signature"]
            if len(page) < 1000:
                break
    return signatures


def fetch_transactions(client: SolanaRPCClient, signatures: list[str]) -> list[dict]:
    txs = []
    for sig in tqdm(signatures, desc="transactions"):
        tx = client.get_transaction(sig)
        if tx is not None:
            txs.append(tx)
    return txs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("address", help="Solana wallet (base58 pubkey)")
    parser.add_argument("--max-txs", type=int, default=2000)
    args = parser.parse_args()

    client = SolanaRPCClient()
    signatures = fetch_signatures(client, args.address, args.max_txs)
    transactions = fetch_transactions(client, signatures)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{args.address}.json"
    out_path.write_text(json.dumps(transactions, indent=2))
    print(f"Saved {len(transactions)} transactions to {out_path}")


if __name__ == "__main__":
    main()
