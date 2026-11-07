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
    return pd.DataFrame([{'signature':'s'*88,'label':label,'feature':2.,'cold_payer':cold,'decision_ts':100,'structure_account_count':7,'structure_signer_count':1,'structure_writable_count':2,'writable_seen_fraction':.5,'readonly_seen_fraction':1.,'writable_log_count_mean':2.}]).set_index('signature')

def models():return {'models':{'context_hgb':{'model':Model(),'inputs':['feature'],'calibrator':Calibration(),'threshold':.3}}}

def test_changed_current_outcome_does_not_change_prediction(monkeypatch):
    monkeypatch.setattr(api,'artifacts',lambda:(models(),data(label=0)))
    a=api.model_predict(api.PredictRequest(signature='s'*88))
    monkeypatch.setattr(api,'artifacts',lambda:(models(),data(label=1)))
    b=api.model_predict(api.PredictRequest(signature='s'*88))
    assert a['context']==b['context']
    assert a['context']['structure_account_count']==7
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


def test_illustrations_cover_correct_decisions_and_errors_without_labels():
    class BatchModel:
        def predict_proba(self, frame):
            # The only model input is a feature; labels are inaccessible here.
            assert list(frame.columns) == ['feature']
            risk = frame.feature.to_numpy()
            return np.column_stack([1-risk, risk])

    saved = {'models': {'context_hgb': {'model': BatchModel(),
             'inputs': ['feature'], 'calibrator': Calibration(), 'threshold': .5}}}
    frame = pd.DataFrame([
        {'signature': str(i)*88, 'label': label, 'feature': score,
         'cold_payer': True, 'decision_ts': i}
        for i, (label, score) in enumerate([(0,.1),(0,.2),(1,.9),(0,.8),(1,.1)])
    ]).set_index('signature')
    result = api.select_illustrations(saved, frame)
    assert result == ['0'*88, '2'*88, '3'*88, '4'*88]
    assert all(isinstance(value, str) for value in result)
    assert api.select_illustrations(saved, frame.iloc[:0]) == []


def test_risk_ranking_measures_failures_in_riskiest_transactions():
    class BatchModel:
        def predict_proba(self, frame):
            risk = frame.feature.to_numpy()
            return np.column_stack([1-risk, risk])

    saved = {'test_date': '2025-12-05', 'models': {'context_hgb': {'model': BatchModel(), 'inputs': ['feature']}}}
    # Ten failures among 100 cold rows: five score highest, five score lowest.
    rows = [{'signature': f'{i:03d}', 'label': int(i < 5 or i >= 95), 'feature': (100-i)/101, 'cold_payer': True}
            for i in range(100)]
    rows.append({'signature': 'seen', 'label': 1, 'feature': .999, 'cold_payer': False})
    result = api.risk_ranking(saved, pd.DataFrame(rows).set_index('signature'))
    model = result['models']['context_hgb']
    assert (result['transactions'], result['failures'], result['failure_rate']) == (100, 10, .1)
    assert model['top_5'] == {'transactions': 5, 'failure_rate': 1., 'times_normal_rate': 10., 'share_of_failures': .5}
    assert model['top_1']['transactions'] == 1
    assert model['safest_half_failure_rate'] == .1
    assert api.risk_ranking(saved, pd.DataFrame(rows).set_index('signature').iloc[:0]) is None


def test_fee_measurement_is_optional_and_reports_saved_values(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(api, 'ROOT', tmp_path)
    assert api.fee_measurement() is None
    folder = tmp_path/'docs/results'
    folder.mkdir(parents=True)
    (folder/'solana_failure_fee_measurement.json').write_text(json.dumps({
        'all_failures': {'total_sol': .4}, 'top_5_failures': {'total_sol': .2},
        'top_5_share_of_failed_fees': .5, 'top_5_share_excluding_largest_program': .25}))
    assert api.fee_measurement() == {'failed_fees_sol': .4, 'top_5_failed_fees_sol': .2,
                                     'top_5_share': .5, 'top_5_share_excluding_largest_program': .25}


def test_story_data_scores_in_time_order_and_measures_fee_concentration():
    class BatchModel:
        def predict_proba(self, frame):
            risk = frame.feature.to_numpy()
            return np.column_stack([1-risk, risk])

    saved = {'test_date': '2025-12-05', 'models': {'context_hgb': {
        'model': BatchModel(), 'inputs': ['feature'], 'calibrator': Calibration(), 'threshold': .905}}}
    rows = [{'signature': f'{i:03d}'*30, 'label': int(i >= 95), 'feature': i/100, 'cold_payer': True,
             'decision_ts': 1000-i, 'structure_account_count': 3} for i in range(100)]
    frame = pd.DataFrame(rows).set_index('signature')
    fees = {f'{i:03d}'*30: 10 for i in range(95, 100)}
    story = api.story_data(saved, frame, fees)
    assert [r[0] for r in story['stream']] == sorted(r[0] for r in story['stream'])
    assert sum(r[2] for r in story['stream']) == 9 and sum(r[4] for r in story['stream']) == 50
    assert story['deciles'][-1] == .5 and story['deciles'][0] == 0
    five = next(p for p in story['curve'] if p['reviewed'] == .05)
    assert five == {'reviewed': .05, 'failures': 1., 'fees': 1.}
    assert api.story_data(saved, frame, {})['fees_measured'] is False
