"""Information-boundary checks for the replay and follow-up calibration."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

HERE=Path(__file__).resolve().parents[1]/'research/solana/ml'
sys.path.insert(0,str(HERE))
try:
    spec=importlib.util.spec_from_file_location('build_replay_demo',HERE/'build_replay_demo.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
finally:
    sys.path.pop(0)


def test_later_validation_labels_do_not_fit_calibration_mapping():
    n=600
    times=np.arange(n)
    y=np.tile([0,0,0,0,1],n//5)
    scores=np.tile(np.linspace(0,1,100),n//100)
    cold=np.ones(n,dtype=bool)
    a,_,split=mod.calibrate_validation(y,scores,times,cold,300)
    changed=y.copy();changed[300:]=1-changed[300:]
    b,_,_=mod.calibrate_validation(changed,scores,times,cold,300)
    np.testing.assert_array_equal(a.predict(scores),b.predict(scores))
    assert split['last_calibration_ts']<split['first_threshold_ts']


def test_calibration_refuses_single_class_or_tiny_groups():
    with pytest.raises(ValueError,match='Insufficient'):
        mod.calibrate_validation(np.zeros(300),np.linspace(0,1,300),np.arange(300),np.ones(300,dtype=bool),150)


def test_replay_outcome_is_separate_and_unknown_ids_fail(monkeypatch):
    from webapp.backend import replay
    from fastapi import HTTPException
    case={'id':'sample','illustration':'Example','checkpoint':'date','outcome':'Failed','scores':{'model':.2}}
    monkeypatch.setattr(replay,'bundle',lambda:{'cases':[case],'summary':{'status':'test'}})
    assert 'outcome' not in replay.case('sample')
    assert replay.outcome('sample')=={'outcome':'Failed'}
    assert replay.summary()=={'status':'test'}
    with pytest.raises(HTTPException) as error:replay.case('missing')
    assert error.value.status_code==404
