"""Controls for delayed execution-risk history and declared account roles."""
import importlib.util
from pathlib import Path
import sys

DIRECTORY = Path(__file__).resolve().parents[1] / 'research/solana/ml'
sys.path.insert(0, str(DIRECTORY))
try:
    spec = importlib.util.spec_from_file_location('transaction_risk', DIRECTORY / 'transaction_risk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
finally:
    sys.path.pop(0)


def accounts(payer='payer', shared='shared', writable=True):
    return [{'pubkey': payer, 'signer': True, 'writable': True},
            {'pubkey': shared, 'signer': False, 'writable': writable}]


def test_pending_outcomes_cannot_change_current_or_simultaneous_features():
    a, b = module.ParticipationHistory(delay=10), module.ParticipationHistory(delay=10)
    for h, label in [(a, 0), (b, 1)]:
        _, _, roles = h.features(accounts(), 100)
        h.schedule(roles, label, 100)
    assert a.features(accounts('new'), 100) == b.features(accounts('new'), 100)
    assert a.features(accounts('new'), 109) == b.features(accounts('new'), 109)
    assert a.features(accounts('new'), 110)[0] != b.features(accounts('new'), 110)[0]


def test_shared_account_transfers_history_to_cold_payer_without_ownership_claim():
    h = module.ParticipationHistory(delay=10)
    _, _, roles = h.features(accounts(), 100)
    h.schedule(roles, 1, 100)
    f, cold, _ = h.features(accounts('unknown'), 110)
    assert cold
    assert f['payer_log_count'] == 0
    assert f['writable_seen_fraction'] == 1
    assert f['readonly_seen_fraction'] == 0


def test_history_counts_once_per_transaction_and_separates_roles():
    h = module.ParticipationHistory(delay=10)
    rows = accounts() + [accounts()[1]]
    _, _, roles = h.features(rows, 100)
    h.schedule(roles, 1, 100)
    h.advance(110)
    assert h.stats['writable']['shared'] == [1, 1]
    f, _, _ = h.features(accounts('other', writable=False), 110)
    assert f['readonly_seen_fraction'] == 0
    assert f['writable_seen_fraction'] == 0


def test_unavailable_history_cannot_be_replayed_out_of_order():
    import pytest
    h = module.ParticipationHistory()
    h.features(accounts(), 100)
    with pytest.raises(ValueError, match='chronological'):
        h.features(accounts(), 99)


def test_fast_fpr_rule_matches_exhaustive_search_with_ties_and_zero_budget():
    import numpy as np
    rng = np.random.default_rng(42)
    for _ in range(40):
        y = np.r_[0, 1, rng.integers(0, 2, 100)]
        probability = np.round(rng.random(len(y)), 1)
        candidates = np.unique(np.r_[probability, np.nextafter(probability.max(), np.inf)])
        for budget in [0, .01, .05, .5, 1]:
            expected = min(t for t in candidates if (probability[y == 0] >= t).mean() <= budget)
            assert module.threshold_at_fpr(y, probability, budget) == expected


def test_identity_replay_ignores_unavailable_labels_and_batch_order():
    import numpy as np
    from scipy.sparse import csr_matrix
    sys.path.insert(0, str(DIRECTORY))
    try:
        from transaction_identity import prequential_scores
    finally:
        sys.path.pop(0)
    settings = {'alpha': .0001, 'random_state': 42,
                'update_interval_seconds': 10, 'outcome_delay_seconds': 20}
    x = csr_matrix(np.ones((5, 2)))
    times = np.array([0, 1, 10, 20, 30])
    a = prequential_scores(x, np.array([0, 1, 0, 0, 0]), times, settings)
    b = prequential_scores(x, np.array([1, 1, 1, 1, 1]), times, settings)
    np.testing.assert_array_equal(a[:3], b[:3])
    assert a[3] != b[3]
    # Changing the current batch and still-pending labels cannot change its score.
    c = prequential_scores(x, np.array([0, 1, 1, 1, 1]), times, settings)
    np.testing.assert_array_equal(a[:4], c[:4])
