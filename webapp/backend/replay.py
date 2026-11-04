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

@app.get('/research')
def research_home():return FileResponse(ROOT/'webapp/frontend/research.html')

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

@app.get('/api/research-evidence')
def research_evidence():
    """Serve the saved first-appearance audit, separate from calibrated replay."""
    reports=[]
    for cohort,date in [('prospective','2025-12-01'),('fresh','2025-12-05')]:
        path=ROOT/f'docs/results/solana_transaction_audit_{cohort}.json'
        if not path.exists():raise HTTPException(503,'First-appearance audit is unavailable.')
        report=json.loads(path.read_text())
        reports.append({'date':date,'rows':report['first_appearance_n'],
            'prevalence':report['first_appearance_prevalence'],
            'models':report['first_appearance_identity_results'],
            'comparison':report['first_appearance_identity_hour_bootstrap'],
            'source':path.name})
    return {'reports':reports}
