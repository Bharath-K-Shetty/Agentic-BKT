"""Export actual fitted models and validation-only calibration for inference."""
import json
import hashlib
from datetime import datetime,timezone
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from prefix_baseline import ROOT
from build_replay_demo import calibrate_validation

def main():
    cohort='fresh'
    p=json.loads((ROOT/'research/solana/ml/transaction_fresh_protocol.json').read_text())
    folder=ROOT/'data/processed/solana_ml'
    frame=pd.read_parquet(folder/f'transaction_features_{cohort}.parquet')
    epoch=lambda d:int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp())
    train=frame[frame.date.eq(p['train_date']) & (frame.decision_ts-frame.decision_ts.min()>=21600)
        & (frame.decision_ts+3600<epoch(p['validation_date']))]
    val=frame[frame.date.eq(p['validation_date']) & (frame.decision_ts+3600<epoch(p['test_date']))]
    test=frame[frame.date.eq(p['test_date'])]
    cols=sorted(set(frame)-{'signature','date','decision_ts','label','cold_payer'})
    saved=pd.read_parquet(folder/'transaction_predictions_fresh.parquet')
    exported={}
    for name in ['payer_readonly_hgb','context_hgb']:
        inputs=[c for c in cols if name=='context_hgb' or not c.startswith('writable_')]
        model=HistGradientBoostingClassifier(**p['hgb'],random_state=42).fit(train[inputs],train.label)
        pv=model.predict_proba(val[inputs])[:,1]
        assert np.allclose(model.predict_proba(test[inputs])[:,1],saved[name],rtol=1e-10,atol=1e-12)
        cal,threshold,split=calibrate_validation(val.label.to_numpy(),pv,val.decision_ts.to_numpy(),
            val.cold_payer.to_numpy(),epoch(p['validation_date'])+43200)
        exported[name]={'model':model,'inputs':inputs,'calibrator':cal,'threshold':threshold,'validation_split':split}
    output=folder/'demo_models.joblib'
    joblib.dump({'cohort':cohort,'models':exported,'test_date':p['test_date']},output)
    # Stored features are built chronologically. No labels are exposed by prediction API.
    test.to_parquet(folder/'demo_inference_test.parquet',index=False)
    metadata={'cohort':cohort,'test_date':p['test_date'],'test_rows':len(test),
        'model_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'feature_source_sha256':hashlib.sha256((folder/'transaction_features_fresh.parquet').read_bytes()).hexdigest(),
        'scope':'Actual model inference on held-out historical feature rows; no live ML guarantee; no retraining on test rows.'}
    (ROOT/'docs/results/solana_demo_model_export.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata),flush=True)

if __name__=='__main__':main()
