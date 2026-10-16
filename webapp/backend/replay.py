"""Independent local replay app. Run uvicorn webapp.backend.replay:app --port 8430."""
import json
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from webapp.backend.transfer_check import router as transfer_router
from webapp.backend.model_inference import router as inference_router
from webapp.backend.prospective import router as prospective_router

ROOT=Path(__file__).resolve().parents[2]
app=FastAPI(title='Solana account-context research replay')
app.include_router(transfer_router)
app.include_router(inference_router)
app.include_router(prospective_router)

@app.get('/live')
def live_home():return FileResponse(ROOT/'webapp/frontend/live.html')

@app.get('/fee-proof')
def fee_proof_home():return FileResponse(ROOT/'webapp/frontend/fee_proof.html')

@app.get('/api/fee-proof')
def fee_proof():
    path=ROOT/'docs/results/solana_local_fee_proof.json'
    if not path.exists():raise HTTPException(503,'Run research/solana/fee_proof/run.py first.')
    return json.loads(path.read_text())

@app.get('/api/fee-proof/ml-policy')
def ml_fee_policy():
    path=ROOT/'docs/results/solana_ml_fee_policy_summary.json'
    if not path.exists():raise HTTPException(503,'Run the ML fee-policy evaluation first.')
    return json.loads(path.read_text())

@app.get('/predict')
def prediction_home():return FileResponse(ROOT/'webapp/frontend/model_predict.html')

@app.get('/check')
def transfer_home():return FileResponse(ROOT/'webapp/frontend/transfer_check.html')

@lru_cache(maxsize=1)
def bundle():
    path=ROOT/'data/processed/solana_ml/replay_demo.json'
    if not path.exists():raise HTTPException(503,'Build replay data first: research/solana/ml/build_replay_demo.py')
    return json.loads(path.read_text())

@app.get('/')
def home():return FileResponse(ROOT/'webapp/frontend/replay.html')

@app.get('/api/summary')
def summary():return bundle()['summary']

@app.get('/api/cases')
def cases():
    # Labels identify illustrative selection, but outcomes require separate reveal.
    return [{'id':c['id'],'illustration':c['illustration'],'checkpoint':c['checkpoint']} for c in bundle()['cases']]

def lookup(case_id):
    case=next((c for c in bundle()['cases'] if c['id']==case_id),None)
    if case is None:raise HTTPException(404,'Unknown replay case')
    return case

@app.get('/api/cases/{case_id}')
def case(case_id:str):return {k:v for k,v in lookup(case_id).items() if k!='outcome'}

@app.get('/api/cases/{case_id}/outcome')
def outcome(case_id:str):return {'outcome':lookup(case_id)['outcome']}
