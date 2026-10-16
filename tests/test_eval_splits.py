import warnings

from src.eval.metrics import evaluate_binary, naive_baseline_rate
from src.eval.splits import as_of_ts_at_fraction, time_based_wallet_split, wallet_train_test_split


def test_time_based_split_no_overlap():
    txs = [{"blockTime": t} for t in [100, 200, 300, 400, 500]]
    history, forward = time_based_wallet_split(txs, as_of_ts=300)
    assert history == [{"blockTime": t} for t in [100, 200, 300]]
    assert forward == [{"blockTime": t} for t in [400, 500]]
    assert len(history) + len(forward) == len(txs)


def test_as_of_ts_at_fraction_within_range():
    txs = [{"blockTime": t} for t in [100, 200, 300, 400, 500]]
    ts = as_of_ts_at_fraction(txs, 0.5)
    assert 100 <= ts <= 500


def test_wallet_train_test_split_partitions_all():
    addrs = [f"w{i}" for i in range(10)]
    train, test = wallet_train_test_split(addrs, test_frac=0.3, seed=1)
    assert set(train) | set(test) == set(addrs)
    assert set(train) & set(test) == set()
    assert len(test) == 3


def test_evaluate_binary_single_class_returns_nan_not_raise():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = evaluate_binary([0, 0, 0], [0.1, 0.4, 0.2])
    assert result["auc"] != result["auc"]  # NaN


def test_naive_baseline_rate():
    assert naive_baseline_rate([0, 1, 1, 0]) == 0.5
