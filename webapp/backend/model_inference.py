"""Actual inference from locally trained artifacts, never uploaded pickle files."""
from functools import lru_cache
from pathlib import Path
from datetime import datetime,timezone
import time
import joblib
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

@router.get('/api/model/examples')
def model_examples():
    saved,frame=artifacts()
    sample=frame[frame.cold_payer].head(20)
    return {'test_date':saved['test_date'],'examples':list(sample.index),'total_heldout_rows':len(frame)}

@router.post('/api/model/predict')
def model_predict(request:PredictRequest):
    start=time.perf_counter()
    saved,frame=artifacts()
    if request.signature not in frame.index:raise HTTPException(404,'This signature is not in the held-out historical sample. No live prediction is available.')
    row=frame.loc[[request.signature]]
    if not bool(row.iloc[0].cold_payer):
        raise HTTPException(422,'This transaction has available signer history. The demo calibration is restricted to the cold-history subgroup.')
    result={'signature':request.signature,'checkpoint':datetime.fromtimestamp(int(row.iloc[0].decision_ts),timezone.utc).isoformat(),
        'cold_history':bool(row.iloc[0].cold_payer),'scores':{},'source':'Fitted model predict_proba, executed for this request',
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
