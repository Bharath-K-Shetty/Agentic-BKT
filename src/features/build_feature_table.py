"""Builds a one-row-per-wallet feature table from data/raw/<address>.json
files, for use by src.models.wallet_risk_baseline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.features.wallet_features import extract_wallet_features

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def build_feature_table(
    wallet_addresses: list[str],
    raw_dir: Path = RAW_DIR,
    as_of_ts: int | None = None,
) -> pd.DataFrame:
    rows = {}
    for address in wallet_addresses:
        path = raw_dir / f"{address}.json"
        if not path.exists():
            print(f"warning: no raw data for {address}, skipping")
            continue
        raw_txs = json.loads(path.read_text())
        rows[address] = extract_wallet_features(address, raw_txs, as_of_ts=as_of_ts)
    return pd.DataFrame.from_dict(rows, orient="index")
