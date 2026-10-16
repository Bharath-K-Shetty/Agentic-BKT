"""Post-result calibration diagnostic and offline replay presentation bundle.

No test label selects a model, calibrator or threshold. Test outcomes select
explicitly illustrative cases only after evaluation. Original reports untouched.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from prefix_baseline import ROOT, metrics, threshold_at_fpr


def calibrate_validation(y, scores, times, cold, midpoint):
    early = (times < midpoint) & cold
    late = (times >= midpoint) & cold
    if min(early.sum(), late.sum()) < 100 or len(np.unique(y[early])) < 2 or len(np.unique(y[late])) < 2:
        raise ValueError('Insufficient chronological cold validation observations')
    calibrator = IsotonicRegression(out_of_bounds='clip').fit(scores[early], y[early])
    threshold = threshold_at_fpr(y[late], calibrator.predict(scores[late]), .05)
    return calibrator, threshold, {'calibration_rows': int(early.sum()), 'threshold_rows': int(late.sum()),
        'last_calibration_ts': int(times[early].max()), 'first_threshold_ts': int(times[late].min())}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cohort',choices=['pilot','confirmation','extension','prospective','fresh'])
    args=parser.parse_args()
    folder = ROOT/'data/processed/solana_ml'
    report = {'status': 'Post-result diagnostic on previously inspected test periods, not independent confirmation',
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'protocol': 'Fixed HGB seed42; isotonic fit on cold validation first12hours; threshold on remaining purged cold validation under5%FPR; no test tuning.',
        'model_scope': 'Original structure/signer/read-only HGB versus writable-context HGB; excludes learned identity score. Not the refined identity-controlled endpoint.',
        'limitations': ['All test periods previously inspected; fresh evaluation still required.',
            'One-hour labels and conditional inclusion apply.', 'Threshold budget is validation-only, not a test guarantee.',
            'Isotonic calibration can create ties and alter AP.', 'One row group per date from one provider; no independent-source validation.'],
        'cohorts': []}
    bundle = None
    for cohort in ([args.cohort] if args.cohort else ['pilot','confirmation','extension','prospective']):
        primary_path = ROOT/f'docs/results/solana_transaction_risk_{cohort}.json'
        primary = json.loads(primary_path.read_text()); p=primary['protocol']
        f=pd.read_parquet(folder/f'transaction_features_{cohort}.parquet')
        start=lambda date:int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())
        train=f[f.date.eq(p['train_date']) & (f.decision_ts-f.decision_ts.min()>=21600)
                & (f.decision_ts+3600<start(p['validation_date']))]
        val=f[f.date.eq(p['validation_date']) & (f.decision_ts+3600<start(p['test_date']))]
        test=f[f.date.eq(p['test_date'])].copy()
        cols=sorted(set(f)-{'signature','date','decision_ts','label','cold_payer'})
        results=[]; scores={}; thresholds={}
        for name in ['payer_readonly_hgb','context_hgb']:
            inputs=[c for c in cols if name=='context_hgb' or not c.startswith('writable_')]
            model=HistGradientBoostingClassifier(**p['hgb'],random_state=42).fit(train[inputs],train.label)
            pv=model.predict_proba(val[inputs])[:,1];pt=model.predict_proba(test[inputs])[:,1]
            original=next(r for r in primary['results'] if r['model']==name)
            saved=pd.read_parquet(folder/f'transaction_predictions_{cohort}.parquet')
            if not np.allclose(pt,saved[name].to_numpy(),rtol=1e-10,atol=1e-12):
                raise ValueError('Refit differs from original predictions')
            cal,threshold,counts=calibrate_validation(val.label.to_numpy(),pv,val.decision_ts.to_numpy(),
                val.cold_payer.to_numpy(),start(p['validation_date'])+43200)
            calibrated=cal.predict(pt);cold=test.cold_payer.to_numpy()
            results.append({'model':name,'split':counts,'threshold':threshold,
                'original_cold':metrics(test.label.to_numpy()[cold],pt[cold],original['threshold']),
                'followup_cold':metrics(test.label.to_numpy()[cold],calibrated[cold],threshold)})
            scores[name]=(pt,calibrated);thresholds[name]=(original['threshold'],threshold)
        report['cohorts'].append({'cohort':cohort,'results':results,'primary_sha256':hashlib.sha256(primary_path.read_bytes()).hexdigest()})
        print(cohort,[(r['model'],r['followup_cold']['fpr'],r['followup_cold']['recall']) for r in results],flush=True)
        if cohort!='prospective':continue
        c=test.cold_payer.to_numpy();score=scores['context_hgb'][1];alert=score>=thresholds['context_hgb'][1]
        # Outcomes are used ONLY to choose transparently named illustration cases.
        categories=[('Flagged failure',c & alert & test.label.eq(1).to_numpy()),
                    ('Unflagged success',c & ~alert & test.label.eq(0).to_numpy()),
                    ('False alarm',c & alert & test.label.eq(0).to_numpy()),
                    ('Missed failure',c & ~alert & test.label.eq(1).to_numpy())]
        selected={}
        for label,mask in categories:
            ids=np.flatnonzero(mask)
            if len(ids):selected[int(ids[0])]=label
        for i in np.flatnonzero(c)[:30]:selected.setdefault(int(i),'Chronological sample')
        signatures={test.iloc[i].signature for i in selected}
        raw=ROOT/p['source_paths'][p['test_date']]
        raw_rows={r['signature']:r for r in pq.read_table(raw,columns=['signature','accounts']).to_pylist() if r['signature'] in signatures}
        cases=[]
        for i,label in selected.items():
            row=test.iloc[i];ts=int(row.decision_ts)
            cases.append({'id':str(i),'illustration':label,'signature':row.signature,
                'checkpoint':datetime.fromtimestamp(ts,timezone.utc).isoformat(),
                'history_cutoff':datetime.fromtimestamp(ts-3600,timezone.utc).isoformat(),
                'cold_history':bool(row.cold_payer),'accounts':raw_rows[row.signature]['accounts'],
                'history':{k:float(row[k]) for k in ['payer_log_count','payer_risk','writable_seen_fraction','writable_risk_mean','readonly_seen_fraction']},
                'scores':{name:{'original':float(v[0][i]),'calibrated':float(v[1][i]),
                    'threshold':float(thresholds[name][1]),'alert':bool(v[1][i]>=thresholds[name][1])} for name,v in scores.items()},
                'outcome':'Failed' if row.label else 'Succeeded'})
        bundle={'summary':report,'cases':cases}
    suffix='_'+args.cohort if args.cohort else ''
    if args.cohort=='fresh':
        report['status']='Unused-date evaluation of a fixed calibration recipe, specified before December3–5 transaction outcomes were loaded'
        report['limitations'][0]='One additional unused test day; not an independent provider or broad regime validation.'
    path=ROOT/f'docs/results/solana_transaction_calibration_followup{suffix}.json'
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    if args.cohort=='fresh':
        demo_path=folder/'replay_demo.json'
        if demo_path.exists():
            demo=json.loads(demo_path.read_text())
            demo['summary']['fresh_evaluation']=report
            demo_path.write_text(json.dumps(demo,indent=2,allow_nan=False)+'\n')
    if bundle is not None:
        bundle['summary']=report
        fresh_path=ROOT/'docs/results/solana_transaction_calibration_followup_fresh.json'
        if fresh_path.exists():bundle['summary']['fresh_evaluation']=json.loads(fresh_path.read_text())
        (folder/'replay_demo.json').write_text(json.dumps(bundle,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
