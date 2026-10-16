"""End-to-end Part 1 smoke test: for every wallet with raw data, split its
own history at `--as-of-frac`, extract features from the history half,
label = whether it fell victim to a realized rug-pull dump or sandwich
attack in the forward half, fit WalletRiskBaseline, report AUC vs. the naive
baseline.

    python -m src.eval.run_wallet_baseline [--raw-dir data/raw] [--as-of-frac 0.7]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.data_collection.solana_client import SolanaRPCClient
from src.eval.metrics import evaluate_binary, naive_baseline_rate
from src.eval.splits import as_of_ts_at_fraction, time_based_wallet_split, wallet_train_test_split
from src.features.wallet_features import extract_wallet_features
from src.labels.build_labels import compute_all_labels
from src.models.wallet_risk_baseline import WalletRiskBaseline

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def _target_from_forward(wallet: str, forward_txs: list[dict]) -> int:
    if not forward_txs:
        return 0
    labels = compute_all_labels(wallet, forward_txs, client=None)
    summary = labels["summary"]
    return int(summary["n_rugpull_realized_dump"] > 0 or summary["n_sandwich_victim"] > 0)


def build_dataset(raw_dir: Path, as_of_frac: float) -> tuple[pd.DataFrame, pd.Series]:
    rows = {}
    targets = {}
    for path in sorted(raw_dir.glob("*.json")):
        wallet = path.stem
        raw_txs = json.loads(path.read_text())
        as_of_ts = as_of_ts_at_fraction(raw_txs, as_of_frac)
        if as_of_ts is None:
            continue
        history, forward = time_based_wallet_split(raw_txs, as_of_ts)
        if not history:
            continue
        rows[wallet] = extract_wallet_features(wallet, history, as_of_ts=as_of_ts)
        targets[wallet] = _target_from_forward(wallet, forward)
    X = pd.DataFrame.from_dict(rows, orient="index")
    y = pd.Series(targets).reindex(X.index)
    return X, y


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--as-of-frac", type=float, default=0.7)
    parser.add_argument("--estimator", default="gbdt", choices=["gbdt", "logreg"])
    args = parser.parse_args()

    X, y = build_dataset(args.raw_dir, args.as_of_frac)
    n = len(X)
    print(f"N={n} wallets — AUC is a plumbing smoke test only, not statistically meaningful below ~50 wallets")
    if n < 4:
        print("Too few wallets to split train/test. Run src.data_collection.fetch_many_wallets first.")
        return

    train_addrs, test_addrs = wallet_train_test_split(list(X.index), test_frac=0.3)
    X_train, y_train = X.loc[train_addrs], y.loc[train_addrs]
    X_test, y_test = X.loc[test_addrs], y.loc[test_addrs]

    naive = naive_baseline_rate(y_train)
    if y_train.nunique() < 2:
        print(
            f"train split has a single class (naive rate {naive:.3f}) -- "
            "not enough positive/negative examples yet to fit a classifier. "
            "Expected at this N; collect more wallets and/or widen the forward window."
        )
        return

    model = WalletRiskBaseline(estimator=args.estimator).fit(X_train, y_train)
    proba = model.predict_proba(X_test)

    metrics = evaluate_binary(y_test, proba)
    print(f"naive baseline rate (train prior): {naive:.3f}")
    print(f"test metrics: {metrics}")
    print("top features:")
    print(model.feature_importances().head(10))


if __name__ == "__main__":
    main()
