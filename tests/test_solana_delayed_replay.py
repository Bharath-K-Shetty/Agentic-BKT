"""Replay controls: unavailable outcomes and simultaneous decisions cannot leak."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

DIRECTORY = Path(__file__).resolve().parents[1] / 'research/solana/ml'
sys.path.insert(0, str(DIRECTORY))
try:
    spec = importlib.util.spec_from_file_location('delayed_replay', DIRECTORY / 'delayed_replay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
finally:
    sys.path.pop(0)


def test_unavailable_labels_do_not_affect_prospective_alerts():
    protocol = json.loads((DIRECTORY / 'delayed_protocol.json').read_text())
    history = pd.DataFrame([{'mint_address': str(i), 'decision_ts': i, 'label_ready_ts': i+1,
                             'label': 0, 'probability': i / 100} for i in range(20)])
    test = pd.DataFrame([{'mint_address': 'pending', 'decision_ts': 100, 'label_ready_ts': 1000,
                         'label': 0, 'probability': .95},
                        {'mint_address': 'later', 'decision_ts': 200, 'label_ready_ts': 1001,
                         'label': 0, 'probability': .9}])
    before, _ = module.replay(history, test, history, .5, protocol)
    altered = test.copy()
    altered['label'] = 1
    after, _ = module.replay(history, altered, history, .5, protocol)
    for name in protocol['controls']:
        if name != 'oracle_immediate_tail':
            assert np.array_equal(before[name], after[name])
    assert before['oracle_immediate_tail'][1] != after['oracle_immediate_tail'][1]


def test_maturity_boundary_and_simultaneous_decision_exclusion():
    frame = pd.DataFrame({'decision_ts': [1, 2, 10, 3], 'label_ready_ts': [10, 11, 10, 10],
                          'label': [0, 0, 0, 1]})
    assert list(module.visible_negatives(frame, 10).index) == [0]
    assert list(module.visible_negatives(frame, 10, oracle=True).index) == [0, 1]


def test_future_reference_changes_are_not_part_of_delay_estimation_input():
    history = pd.DataFrame({'decision_ts': [0, 0, 90], 'label_ready_ts': [2, 3, 200],
                           'label': [0, 0, 0], 'probability': [.1, .2, .9]})
    reference = module.visible_negatives(history, 100, buffer=36)
    changed = history.copy()
    changed.loc[2, ['label_ready_ts', 'probability']] = [10000, .01]
    other = module.visible_negatives(changed, 100, buffer=36)
    pd.testing.assert_frame_equal(reference, other)
    assert module.tail_probability([.5] * 20, .5) == 1
