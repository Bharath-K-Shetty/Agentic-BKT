"""Orchestrates label construction for one wallet's raw transaction history.

    python -m src.labels.build_labels <address> [--with-sandwich-detection]

Reads data/raw/<address>.json, writes data/processed/labels/<address>.json.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from src.data_collection.solana_client import SolanaRPCClient
from src.labels.rugpull import rug_pull_events
from src.labels.sandwich import detect_sandwich_for_wallet
from src.labels.slippage import wallet_slippage_series
from src.labels.swaps import extract_wallet_swaps

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
LABELS_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "labels"


def compute_all_labels(
    wallet: str,
    raw_txs: list[dict],
    client: SolanaRPCClient | None = None,
) -> dict:
    """client=None skips sandwich detection (network-dependent); every other
    label is computed offline from raw_txs alone."""
    swaps = extract_wallet_swaps(raw_txs, wallet)
    rugpull = rug_pull_events(swaps)
    sandwich = detect_sandwich_for_wallet(wallet, raw_txs, client)
    slippage = wallet_slippage_series(swaps)

    return {
        "wallet": wallet,
        "swaps": [asdict(s) | {"program_ids": sorted(s.program_ids)} for s in swaps],
        "rugpull_events": [asdict(e) for e in rugpull],
        "sandwich_events": [asdict(e) | {"mint_pair": list(e.mint_pair)} for e in sandwich],
        "slippage_series": slippage,
        "summary": {
            "n_swaps": len(swaps),
            "n_rugpull_realized_dump": sum(1 for e in rugpull if e.kind == "realized_dump"),
            "n_rugpull_abandoned_bag": sum(1 for e in rugpull if e.kind == "abandoned_bag"),
            "n_sandwich_victim": len(sandwich),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("--with-sandwich-detection", action="store_true")
    parser.add_argument("--rpc-url", default=None)
    args = parser.parse_args()

    raw_path = RAW_DIR / f"{args.address}.json"
    raw_txs = json.loads(raw_path.read_text())

    client = SolanaRPCClient(rpc_url=args.rpc_url) if args.with_sandwich_detection else None
    labels = compute_all_labels(args.address, raw_txs, client=client)

    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LABELS_DIR / f"{args.address}.json"
    out_path.write_text(json.dumps(labels, indent=2))
    print(f"Wrote labels for {args.address}: {labels['summary']}")


if __name__ == "__main__":
    main()
