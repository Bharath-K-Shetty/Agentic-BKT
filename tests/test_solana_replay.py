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


def test_research_evidence_uses_identity_first_appearance_audit(tmp_path, monkeypatch):
    import json
    from webapp.backend import replay
    from fastapi import HTTPException
    folder=tmp_path/'docs/results'
    folder.mkdir(parents=True)
    report={'first_appearance_n':123,'first_appearance_prevalence':.1,
            'first_appearance_identity_results':{'readonly_identity_hgb':{'ap_positive':.2}},
            'first_appearance_identity_hour_bootstrap':{'weighted_delta':.03,'ci95':[.01,.05]},
            'first_appearance_results':{'wrong_comparison':True}}
    for cohort in ['prospective','fresh']:
        (folder/f'solana_transaction_audit_{cohort}.json').write_text(json.dumps(report))
    monkeypatch.setattr(replay,'ROOT',tmp_path)
    rows=replay.research_evidence()['reports']
    assert [r['date'] for r in rows]==['2025-12-01','2025-12-05']
    assert rows[0]['models']==report['first_appearance_identity_results']
    assert rows[0]['rows']==123
    (folder/'solana_transaction_audit_fresh.json').unlink()
    with pytest.raises(HTTPException) as error:replay.research_evidence()
    assert error.value.status_code==503
