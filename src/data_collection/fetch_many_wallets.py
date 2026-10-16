"""Batch wallet collection for Part 1's training set.

No labeled/curated wallet-address list is available in this project (no
paid indexer access), so the primary path discovers candidate wallets by
scanning full blocks at the slots one existing sample wallet transacted in,
taking each non-vote transaction's fee payer as a candidate, and confirming
it's a plain (System-Program-owned) active wallet, not a PDA/vault or a
validator identity.

    python -m src.data_collection.fetch_many_wallets --discover-from <address> --discover-count 15
    python -m src.data_collection.fetch_many_wallets --wallet-list data/seed_wallets.txt

Resumable: skips any address that already has data/raw/<address>.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data_collection.fetch_wallet_history import RAW_DIR, fetch_signatures, fetch_transactions
from src.data_collection.solana_client import SolanaRPCClient
from src.labels.tx_utils import KNOWN_PROGRAM_IDS, program_ids

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_SEED_LIST = DATA_DIR / "seed_wallets.txt"
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
VOTE_PROGRAM_ID = "Vote111111111111111111111111111111111111111"


def _is_confirmed_wallet(client: SolanaRPCClient, pubkey: str) -> bool:
    info = client.get_account_info(pubkey)
    value = (info or {}).get("value") or {}
    if value.get("owner") != SYSTEM_PROGRAM_ID:
        return False
    return bool(client.get_signatures_for_address(pubkey, limit=1))


def discover_candidate_wallets(
    sample_raw_path: Path | list[Path],
    client: SolanaRPCClient,
    exclude: set[str] | None = None,
    max_candidates: int = 20,
) -> list[str]:
    """Discover candidate wallets by scanning full blocks at the slots the
    sample wallet(s) themselves transacted in, and taking each transaction's
    fee payer (accountKeys[0], always a signer under the Solana tx format)
    as a candidate. This works far better than looking at the sample
    wallet's own transaction counterparties: in a typical swap/transfer, the
    counterparty is a program-owned pool/vault/PDA, not another person's
    wallet, so that account list rarely contains real wallets at all. A
    single block, by contrast, contains hundreds of distinct real fee
    payers. Passing multiple sample paths (e.g. every wallet already
    fetched) widens coverage by drawing candidates from more, different
    blocks instead of repeatedly re-scanning the same one. Each candidate is
    confirmed via `getAccountInfo` (owner must be the System Program, ruling
    out PDAs) and `getSignaturesForAddress` (has on-chain activity). No
    external dataset needed -- both are standard RPC calls."""
    sample_paths = [sample_raw_path] if isinstance(sample_raw_path, Path) else list(sample_raw_path)
    exclude = set(exclude or set())
    slots: set[int] = set()
    for path in sample_paths:
        exclude.add(path.stem)
        raw_txs = json.loads(path.read_text())
        slots |= {tx["slot"] for tx in raw_txs if "slot" in tx}
    slots = sorted(slots, reverse=True)

    seen: set[str] = set()
    confirmed: list[str] = []
    for slot in slots:
        if len(confirmed) >= max_candidates:
            break
        block = client.get_block(slot)
        if not block:
            continue
        for tx in block.get("transactions", []):
            if len(confirmed) >= max_candidates:
                break
            if VOTE_PROGRAM_ID in program_ids(tx):
                # ~70%+ of transactions in any block are validator votes;
                # their fee payer is a validator identity, not a DeFi user
                continue
            keys = tx.get("transaction", {}).get("message", {}).get("accountKeys", [])
            if not keys:
                continue
            fee_payer = keys[0]["pubkey"]
            if fee_payer in seen or fee_payer in exclude or fee_payer in KNOWN_PROGRAM_IDS:
                continue
            seen.add(fee_payer)
            if _is_confirmed_wallet(client, fee_payer):
                confirmed.append(fee_payer)
    return confirmed


def load_wallet_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def fetch_wallet(client: SolanaRPCClient, address: str, max_txs: int) -> int:
    signatures = fetch_signatures(client, address, max_txs)
    transactions = fetch_transactions(client, signatures)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{address}.json"
    out_path.write_text(json.dumps(transactions, indent=2))
    return len(transactions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wallet-list", type=Path, default=None)
    parser.add_argument("--discover-from", default=None, help="sample wallet address to discover counterparties from")
    parser.add_argument(
        "--discover-from-all-raw",
        action="store_true",
        help="use every wallet already in data/raw/ as a discovery seed, for broader block coverage",
    )
    parser.add_argument("--discover-count", type=int, default=15)
    parser.add_argument("--max-txs", type=int, default=500)
    parser.add_argument("--rpc-url", default=None)
    args = parser.parse_args()

    client = SolanaRPCClient(rpc_url=args.rpc_url)

    if args.wallet_list and args.wallet_list.exists():
        addresses = load_wallet_list(args.wallet_list)
    elif args.discover_from_all_raw:
        sample_paths = sorted(RAW_DIR.glob("*.json"))
        already_fetched = {p.stem for p in sample_paths}
        addresses = discover_candidate_wallets(
            sample_paths, client, exclude=already_fetched, max_candidates=args.discover_count
        )
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_SEED_LIST.write_text("\n".join(addresses) + "\n")
        print(f"Discovered {len(addresses)} candidate wallets from {len(sample_paths)} seeds, wrote {DEFAULT_SEED_LIST}")
    elif args.discover_from:
        sample_path = RAW_DIR / f"{args.discover_from}.json"
        addresses = discover_candidate_wallets(sample_path, client, max_candidates=args.discover_count)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_SEED_LIST.write_text("\n".join(addresses) + "\n")
        print(f"Discovered {len(addresses)} candidate wallets, wrote {DEFAULT_SEED_LIST}")
    else:
        parser.error("must pass --wallet-list, --discover-from, or --discover-from-all-raw")
        return

    fetched, skipped, failed = 0, 0, 0
    for address in addresses:
        out_path = RAW_DIR / f"{address}.json"
        if out_path.exists():
            skipped += 1
            continue
        try:
            n_txs = fetch_wallet(client, address, args.max_txs)
            print(f"{address}: {n_txs} transactions")
            fetched += 1
        except Exception as exc:  # noqa: BLE001 - keep the batch going on a bad wallet
            print(f"{address}: FAILED ({exc})")
            failed += 1

    print(f"fetched={fetched} skipped_existing={skipped} failed={failed}")


if __name__ == "__main__":
    main()
