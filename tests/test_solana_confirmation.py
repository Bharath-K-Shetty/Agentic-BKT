"""Controls for disjoint confirmation and prospective calendar evaluation."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

DIRECTORY = Path(__file__).resolve().parents[1] / "research/solana/ml"
sys.path.insert(0, str(DIRECTORY))
try:
    spec = importlib.util.spec_from_file_location("solana_robustness", DIRECTORY / "robustness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
finally:
    sys.path.pop(0)


def test_confirmation_hash_sample_disjoint_and_input_order_independent():
    addresses = [f"mint{i}" for i in range(100)]
    pilot = module.confirmation_sample(addresses, 42, 0, 20)
    confirmation = module.confirmation_sample(addresses, 42, 20, 50)
    assert not set(pilot) & set(confirmation)
    assert confirmation == module.confirmation_sample(addresses[::-1], 42, 20, 50)


def test_calendar_boundaries_and_label_availability():
    a, b, c = map(module.epoch, ["2025-01-01", "2025-01-15", "2025-02-01"])
    f = pd.DataFrame({"decision_ts": [a-2, a-1, a, b-1, b, c],
                      "label_ready_ts": [a-1, a+1, a+2, b+1, c+1, c+2]})
    tr, va, te = module.calendar_split(f, {"train_end": "2025-01-01", "validation_end": "2025-01-15", "test_end": "2025-02-01"})
    assert tr.index.tolist() == [0]
    assert va.index.tolist() == [2]
    assert te.index.tolist() == [4]


def test_wallet_novelty_is_set_difference_not_operator_identity():
    assert module.novel_fraction(["a", "a", "b"], {"a"}) == .5
    assert module.novel_fraction([], {"a"}) is None


def test_paired_resampling_identical_predictions_has_zero_delta():
    p = {"y": np.array([0, 1, 0, 1]), "base": np.array([.1, .7, .2, .8]),
         "coord": np.array([.1, .7, .2, .8]), "days": np.array([1, 1, 2, 2])}
    result = module.paired_period_bootstrap([p, p], average_precision_score, repetitions=20)
    assert result["weighted_delta"] == 0
    assert result["ci95"] == [0, 0]
