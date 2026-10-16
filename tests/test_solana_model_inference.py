"""Inference must not read current outcome as an input or claim live coverage."""
import pandas as pd
import numpy as np
import pytest
from fastapi import HTTPException
from webapp.backend import model_inference as api

class Model:
    def predict_proba(self,frame):
        assert list(frame.columns)==['feature']
        return np.array([[.8,.2]])

class Calibration:
    def predict(self,x):return np.array(x)

def data(label=0,cold=True):
    return pd.DataFrame([{'signature':'s'*88,'label':label,'feature':2.,'cold_payer':cold,'decision_ts':100}]).set_index('signature')

def models():return {'models':{'context_hgb':{'model':Model(),'inputs':['feature'],'calibrator':Calibration(),'threshold':.3}}}

def test_changed_current_outcome_does_not_change_prediction(monkeypatch):
    monkeypatch.setattr(api,'artifacts',lambda:(models(),data(label=0)))
    a=api.model_predict(api.PredictRequest(signature='s'*88))
    monkeypatch.setattr(api,'artifacts',lambda:(models(),data(label=1)))
    b=api.model_predict(api.PredictRequest(signature='s'*88))
    assert a['scores']==b['scores'] and 'outcome' not in a and 'label' not in a
    assert api.model_outcome('s'*88)=={'outcome':'Failed'}

def test_unknown_signature_has_no_invented_live_prediction(monkeypatch):
    monkeypatch.setattr(api,'artifacts',lambda:(models(),data()))
    with pytest.raises(HTTPException) as e:api.model_predict(api.PredictRequest(signature='u'*88))
    assert e.value.status_code==404

def test_cold_calibration_not_used_for_seen_signer(monkeypatch):
    monkeypatch.setattr(api,'artifacts',lambda:(models(),data(cold=False)))
    with pytest.raises(HTTPException) as e:api.model_predict(api.PredictRequest(signature='s'*88))
    assert e.value.status_code==422
