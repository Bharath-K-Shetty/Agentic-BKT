"""Do not mistake correct warnings for measured fee savings."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('ml_fee_policy',
    Path(__file__).resolve().parents[1]/'research/solana/fee_proof/evaluate_ml_policy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_costs_include_blocked_successes_and_missed_failures():
    result = module.counts([1, 1, 0, 0], [1, 0, 1, 0])
    assert result['flagged_failures'] == result['flagged_successes'] == 1
    assert result['missed_failures'] == result['unflagged_successes'] == 1
    assert result['precision'] == result['failure_recall'] == .5
    assert result['hypothetical_net_units']['1'] == 0
    assert result['hypothetical_net_units']['5'] == -4


def test_no_warnings_does_not_invent_precision_or_benefit():
    result = module.counts([1, 0], [0, 0])
    assert result['precision'] is None
    assert result['warnings'] == 0 and result['missed_failures'] == 1
    assert all(v == 0 for v in result['hypothetical_net_units'].values())


def test_misaligned_arrays_fail():
    with pytest.raises(ValueError):
        module.counts([1, 0], [1])


def test_identical_policies_have_zero_paired_difference():
    y = np.array([1, 0, 0, 1])
    alert = np.array([1, 1, 0, 0])
    result = module.paired_intervals(y, alert, alert, np.array([1, 1, 2, 2]))
    assert all(r['delta_net_units'] == 0 and r['paired_hour_bootstrap_ci95'] == [0, 0]
               for r in result.values())
