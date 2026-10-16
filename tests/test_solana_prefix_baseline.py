"""Controls for prospective cutoffs and label availability, not model scores."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path(__file__).resolve().parents[1] / "research/solana/ml/prefix_baseline.py"
spec = importlib.util.spec_from_file_location("prefix_baseline", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def event(ts, slot, signature, kind="swap", wallets=None, price=1):
    return {"type": kind, "timestamp": ts, "block_slot": slot, "block_index": 0,
            "signature": signature, "trader_map": wallets or {"a": 1},
            "sol_amount": -1, "fee_amount": .001, "price": price}


def test_future_rows_cannot_change_features_and_boundary_is_included():
    events = [event(100, 1, "mint", "mint&swap"), event(160, 2, "boundary")]
    before = module.prefix_features(events, 60)
    after = module.prefix_features(events + [event(161, 3, "future", wallets={"z": 999}, price=1000)], 60)
    assert before == after
    assert before[1]["swap_count"] == 2


def test_chain_order_and_duplicate_rejection():
    events = [event(100, 2, "b", price=2), event(100, 1, "a", "mint&swap")]
    assert module.prefix_features(events, 60)[1]["log_price_return"] == np.log(2)
    assert module.prefix_features(events[::-1], 60) == module.prefix_features(events, 60)
    with pytest.raises(ValueError, match="duplicate"):
        module.prefix_features(events + [events[0]], 60)
    with pytest.raises(ValueError, match="missing mint"):
        module.prefix_features([events[0]], 60)


def test_purge_labels_unavailable_at_next_partition():
    f = pd.DataFrame({"decision_ts": np.arange(100, 110),
                      "label_ready_ts": [101, 102, 103, 104, 105, 200, 107, 200, 109, 110],
                      "mint_address": list("abcdefghij")})
    train, val, test, info = module.temporal_split(f)
    assert (train.label_ready_ts < info["validation_start"]).all()
    assert (val.label_ready_ts < info["test_start"]).all()
    assert info["purged"] == 2
    assert len(test) == 2


def test_fpr_threshold_handles_ties_without_test_labels():
    y = np.array([0, 0, 0, 1])
    p = np.array([.9, .9, .1, .95])
    t = module.threshold_at_fpr(y, p, .05)
    assert (p[y == 0] >= t).mean() == 0
    assert t == .95
