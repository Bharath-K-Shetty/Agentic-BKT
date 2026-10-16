"""Controls for richer inputs' cutoff and cohort membership semantics."""
import importlib.util
from pathlib import Path
import sys

import numpy as np

DIRECTORY = Path(__file__).resolve().parents[1] / 'research/solana/ml'
sys.path.insert(0, str(DIRECTORY))
try:
    spec = importlib.util.spec_from_file_location('rich_features', DIRECTORY / 'rich_features.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
finally:
    sys.path.pop(0)


def event(t, signature, wallets, kind='swap', price=1):
    return {'type': kind, 'timestamp': t, 'signature': signature, 'block_slot': t,
            'block_index': int(signature[-1]), 'trader_map': wallets,
            'price': price, 'sol_amount': -1, 'fee_amount': .001}


def test_all_enriched_features_invariant_to_future_events():
    rows = [event(100, 's0', {'a': 10}, 'mint&swap'), event(110, 's1', {'b': 2}, price=2)]
    before = module.enriched_features(rows)
    after = module.enriched_features(rows + [event(401, 's2', {'z': 100000}, price=100)], 300)
    assert before == after
    assert np.isfinite(list(before[1].values())).all()


def test_equal_time_buyer_cohort_includes_ties_and_is_order_independent():
    wallets = {f'w{i}': 1 for i in range(8)}
    rows = [event(100, 's0', wallets, 'mint&swap'), event(400, 's1', {'z': 2})]
    _, f = module.enriched_features(rows)
    assert f['rich_first_5_buyers_with_ties_count'] == 8
    assert f['rich_bin5_swap_count'] == 1
    assert module.enriched_features(rows[::-1]) == module.enriched_features(rows)


def test_prefix_drawdown_uses_observed_prices_only():
    rows = [event(100, 's0', {'a': 10}, 'mint&swap', 2), event(120, 's1', {'b': 2}, price=1)]
    _, f = module.enriched_features(rows)
    assert f['rich_prefix_max_drawdown'] == .5
    assert f['rich_bin3_swap_count'] == 0
    assert f['rich_bin3_log_return'] == 0
