"""Actual inference from locally trained artifacts, never uploaded pickle files."""
from functools import lru_cache
from pathlib import Path
from datetime import datetime,timezone
import json
import time
import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field

ROOT=Path(__file__).resolve().parents[2]
router=APIRouter()

@lru_cache(maxsize=1)
def artifacts():
    folder=ROOT/'data/processed/solana_ml'
    paths=[folder/'demo_models.joblib',folder/'demo_inference_test.parquet']
    if not all(p.exists() for p in paths):raise HTTPException(503,'Export the trained demo models first.')
    return joblib.load(paths[0]),pd.read_parquet(paths[1]).set_index('signature',verify_integrity=True)

class PredictRequest(BaseModel):
    signature:str=Field(min_length=64,max_length=100)

def select_illustrations(saved, frame):
    """Select one example per context-model confusion category, for demonstration only.

    Outcomes affect selection, never features or model fitting. Return signatures
    in checkpoint order without exposing outcome categories before reveal.
    """
    sample = frame[frame.cold_payer].sort_values('decision_ts', kind='stable')
    if sample.empty:
        return []
    artifact = saved['models']['context_hgb']
    raw = artifact['model'].predict_proba(sample[artifact['inputs']])[:, 1]
    scores = artifact['calibrator'].predict(raw)
    selected = []
    seen = set()
    for signature, label, score in zip(sample.index, sample.label, scores):
        category = (bool(label), bool(score >= artifact['threshold']))
        if category not in seen:
            selected.append(signature)
            seen.add(category)
        if len(seen) == 4:
            break
    return selected


@lru_cache(maxsize=1)
def illustrative_signatures():
    return select_illustrations(*artifacts())


def risk_ranking(saved, frame):
    """Measure how real failures concentrate in each model's riskiest-ranked transactions."""
    sample = frame[frame.cold_payer]
    if sample.empty:
        return None
    labels = sample.label.to_numpy()
    base_rate = float(labels.mean())
    models = {}
    for name, artifact in saved['models'].items():
        raw = artifact['model'].predict_proba(sample[artifact['inputs']])[:, 1]
        ordered = labels[np.argsort(-raw, kind='stable')]
        groups = {}
        for percent in (1, 5, 10):
            top = ordered[:len(ordered) * percent // 100]
            rate = float(top.mean()) if len(top) else 0.0
            groups[f'top_{percent}'] = {
                'transactions': len(top), 'failure_rate': rate,
                'times_normal_rate': rate / base_rate if base_rate else None,
                'share_of_failures': float(top.sum() / labels.sum()) if labels.sum() else None}
        models[name] = {**groups, 'safest_half_failure_rate': float(ordered[len(ordered) // 2:].mean())}
    return {'test_date': saved['test_date'], 'transactions': len(sample),
            'failures': int(labels.sum()), 'failure_rate': base_rate, 'models': models}


@lru_cache(maxsize=1)
def cached_risk_ranking():
    return risk_ranking(*artifacts())


def fee_measurement():
    """Return measured on-chain fees for the riskiest group, if that study has been run."""
    path = ROOT/'docs/results/solana_failure_fee_measurement.json'
    if not path.exists():
        return None
    report = json.loads(path.read_text())
    return {'failed_fees_sol': report['all_failures']['total_sol'],
            'top_5_failed_fees_sol': report['top_5_failures']['total_sol'],
            'top_5_share': report['top_5_share_of_failed_fees'],
            'top_5_share_excluding_largest_program': report['top_5_share_excluding_largest_program']}


def measured_failure_fees():
    """Signature -> fee in lamports for failed transactions measured on chain."""
    path = ROOT/'data/processed/solana_ml/failure_fees.jsonl'
    if not path.exists():
        return {}
    fees = {}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row['retrieved'] and row['label']:
            fees[row['signature']] = row['fee']
    return fees


CURVE_PERCENTS = (0, 1, 2, 3, 4, 5, 7.5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100)


def story_data(saved, frame, fees):
    """Everything the presentation page draws, computed from the fitted model."""
    sample = frame[frame.cold_payer].sort_values('decision_ts', kind='stable')
    if sample.empty:
        return None
    artifact = saved['models']['context_hgb']
    raw = artifact['model'].predict_proba(sample[artifact['inputs']])[:, 1]
    calibrated = artifact['calibrator'].predict(raw)
    alerts = calibrated >= artifact['threshold']
    labels = sample.label.to_numpy().astype(int)
    fee = np.array([fees.get(sig, 0) if label else 0 for sig, label in zip(sample.index, labels)])
    fees_complete = all(sig in fees for sig, label in zip(sample.index, labels) if label)
    safest_first = np.argsort(raw, kind='stable')
    deciles = [float(group.mean()) for group in np.array_split(labels[safest_first], 10)]
    riskiest_first = safest_first[::-1]
    failures, wasted = np.cumsum(labels[riskiest_first]), np.cumsum(fee[riskiest_first])
    curve = []
    for percent in CURVE_PERCENTS:
        k = round(len(labels) * percent / 100)
        curve.append({'reviewed': percent / 100,
                      'failures': float(failures[k-1] / failures[-1]) if k else 0.,
                      'fees': (float(wasted[k-1] / wasted[-1]) if k else 0.) if fees_complete and wasted[-1] else None})
    stream = [[int(ts), round(float(score), 4), int(alert), int(label), int(cost), sig[:6], int(accounts)]
              for ts, score, alert, label, cost, sig, accounts in zip(
                  sample.decision_ts, calibrated, alerts, labels, fee, sample.index, sample.structure_account_count)]
    return {'test_date': saved['test_date'], 'transactions': len(labels), 'failures': int(labels.sum()),
            'failure_rate': float(labels.mean()), 'threshold': float(artifact['threshold']),
            'fees_measured': fees_complete, 'deciles': deciles, 'curve': curve,
            'stream_fields': ['time', 'score', 'flagged', 'failed', 'fee_lamports', 'signature_prefix', 'accounts'],
            'stream': stream}


@lru_cache(maxsize=1)
def cached_story():
    return story_data(*artifacts(), measured_failure_fees())


@router.get('/api/model/story')
def model_story():
    result = cached_story()
    if result is None:
        raise HTTPException(503, 'No held-out transactions are available.')
    return result


@router.get('/api/model/results')
def model_results():
    result = cached_risk_ranking()
    if result is None:
        raise HTTPException(503, 'No held-out transactions are available.')
    return {**result, 'fees': fee_measurement()}


@router.get('/api/model/examples')
def model_examples():
    saved,frame=artifacts()
    sample=frame[frame.cold_payer].head(20)
    return {'test_date':saved['test_date'],'examples':list(sample.index),'illustrations':illustrative_signatures(),
        'illustration_selection':'Selected after evaluation to include correct decisions and errors; not a representative performance sample.',
        'total_heldout_rows':len(frame)}

@router.post('/api/model/predict')
def model_predict(request:PredictRequest):
    start=time.perf_counter()
    saved,frame=artifacts()
    if request.signature not in frame.index:raise HTTPException(404,'This signature is not in the held-out historical sample. No live prediction is available.')
    row=frame.loc[[request.signature]]
    if not bool(row.iloc[0].cold_payer):
        raise HTTPException(422,'This transaction has available signer history. The demo calibration is restricted to the cold-history subgroup.')
    result={'signature':request.signature,'checkpoint':datetime.fromtimestamp(int(row.iloc[0].decision_ts),timezone.utc).isoformat(),
        'cold_history':bool(row.iloc[0].cold_payer),
        'context':{key:float(row.iloc[0][key]) for key in ['structure_account_count','structure_signer_count','structure_writable_count','writable_seen_fraction','readonly_seen_fraction','writable_log_count_mean']},'scores':{},'source':'Fitted model predict_proba, executed for this request',
        'scope':'Held-out historical transaction; not a fresh live transaction'}
    for name,artifact in saved['models'].items():
        raw=float(artifact['model'].predict_proba(row[artifact['inputs']])[0,1])
        score=float(artifact['calibrator'].predict([raw])[0])
        result['scores'][name]={'original':raw,'calibrated':score,'alert':score>=artifact['threshold'],
            'threshold':float(artifact['threshold'])}
    result['inference_ms']=round((time.perf_counter()-start)*1000,2)
    return result

@router.get('/api/model/outcome/{signature}')
def model_outcome(signature:str):
    _,frame=artifacts()
    if signature not in frame.index:raise HTTPException(404,'Unknown held-out signature')
    return {'outcome':'Failed' if frame.loc[signature,'label'] else 'Succeeded'}
