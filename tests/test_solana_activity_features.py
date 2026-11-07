"""Recent-activity features count only strictly earlier inclusions and never outcomes."""
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'research/solana/ml'))
import activity_features as af  # noqa: E402


def tx(payer, writable='pool'):
    return [{'pubkey': payer, 'signer': True, 'writable': True},
            {'pubkey': writable, 'signer': False, 'writable': True}]


def step(history, accounts, now, label=0):
    f, cold, roles = history.features(accounts, now)
    history.schedule(roles, label, now)
    return f


def test_same_second_and_later_transactions_are_not_counted():
    h = af.ActivityHistory()
    step(h, tx('bot'), 100)
    same_second = step(h, tx('bot'), 100)
    assert same_second['activity_payer_60'] == 0 and same_second['meta_first_appearance'] == 1
    later = step(h, tx('bot'), 101)
    assert later['activity_payer_60'] == np.log1p(2)
    assert later['activity_writable_max_60'] == np.log1p(2)
    assert later['activity_network_60'] == np.log1p(2)
    assert later['meta_first_appearance'] == 0


def test_windows_expire_and_outcomes_do_not_change_activity():
    def run(label):
        h = af.ActivityHistory()
        step(h, tx('bot'), 0, label)
        return step(h, tx('bot'), 61), step(h, tx('new', 'other'), 650)
    (a_61, a_700), (b_61, b_700) = run(0), run(1)
    assert a_61['activity_payer_60'] == 0 and a_61['activity_payer_600'] == np.log1p(1)
    assert a_700['activity_network_600'] == np.log1p(1) and a_700['activity_writable_max_600'] == 0
    for key in a_61:
        if key.startswith('activity_'):
            assert a_61[key] == b_61[key] and a_700[key] == b_700[key]


def test_model_inputs_keep_comparisons_matched():
    cols = ['structure_a', 'payer_risk', 'readonly_risk_mean', 'template_risk', 'writable_risk_mean',
            'activity_payer_60', 'meta_first_appearance', 'label']
    inputs = af.model_inputs(cols)
    assert inputs['homie'] == inputs['baseline'] + ['writable_risk_mean']
    assert inputs['homie_activity'] == inputs['homie'] + ['activity_payer_60']
    assert not any(c.startswith(('meta_', 'label')) for v in inputs.values() for c in v)


def test_fee_context_uses_only_earlier_transactions_and_declared_fee():
    h = af.ActivityHistory()
    first = h.features(tx('a'), 100, fee=5000)
    h.schedule(first[2], 1, 100)
    f1 = first[0]
    assert f1['fee_priority_log'] == 0 and f1['fee_has_priority'] == 0 and f1['fee_rank_60'] == .5
    same, _, roles = h.features(tx('b'), 100, fee=105000)
    h.schedule(roles, 0, 100)
    assert same['fee_network_median_60'] == 0
    later, _, _ = h.features(tx('c'), 101, fee=55000)
    assert later['fee_network_median_60'] == np.log1p(50000)
    assert later['fee_rank_60'] == .5


def test_network_failure_rate_waits_for_maturity():
    h = af.ActivityHistory(delay=3600)
    f, _, roles = h.features(tx('a'), 0)
    h.schedule(roles, 1, 0)
    assert h.features(tx('b'), 3599)[0]['activity_network_failure_rate_1h'] == .5
    assert h.features(tx('c'), 3600)[0]['activity_network_failure_rate_1h'] == 2/3
    assert h.features(tx('d'), 7201)[0]['activity_network_failure_rate_1h'] == .5
