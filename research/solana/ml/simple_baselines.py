"""Simple and linear baselines for the three identity-controlled test windows.

Settings were fixed before running and are not tuned on any test date:
* Rules (no fitting): rank by `writable_risk_max` (riskiest writable account's
  smoothed failure rate) and by `template_risk` (read-only program-set rate).
* Logistic regression on the same 27 baseline and 34 context inputs used by the
  boosting models: standardised inputs, L2, C=1.0, lbfgs, max_iter=2000.
* Boosting results are the saved three-seed predictions; nothing is refitted.
Training rows follow transaction_risk.py (warm-up and boundary purging). Groups
are the test date's cold-history and first-appearance transactions. Paired
one-hour block bootstrap (500 draws, seed 42) compares context with baseline.

    .venv/bin/python research/solana/ml/simple_baselines.py
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prefix_baseline import ROOT  # noqa: E402
from robustness import paired_period_bootstrap  # noqa: E402

COHORTS = {'prospective': 'Dec. 1', 'fresh': 'Dec. 5', 'third': 'Nov. 28'}
FOLDER = ROOT / 'data/processed/solana_ml'


def day_start(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def first_appearance(frame, sources):
    payers = {}
    for src in sources:
        for batch in pq.ParquetFile(ROOT / src['path']).iter_batches(columns=['signature', 'accounts'], batch_size=8192):
            for row in batch.to_pylist():
                payers[row['signature']] = row['accounts'][0]['pubkey']
    signers = frame.signature.map(payers)
    assert signers.notna().all()
    return ~signers.duplicated()


def score(y, p):
    return {'ap': float(average_precision_score(y, p)), 'auroc': float(roc_auc_score(y, p))}


def compare(y, a, b, times):
    return paired_period_bootstrap([{'y': y, 'base': a, 'coord': b, 'days': times // 3600}], average_precision_score)


def main():
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'settings': __doc__.split('\n\n')[0].strip(), 'cohorts': {}}
    hashes = {}
    for cohort, label in COHORTS.items():
        risk = json.loads((ROOT / f'docs/results/solana_transaction_risk_{cohort}.json').read_text())
        protocol = risk['protocol']
        dates = [protocol[k] for k in ['train_date', 'validation_date', 'test_date']]
        path = FOLDER / f'transaction_features_{cohort}.parquet'
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        frame = pd.read_parquet(path)
        frame['first'] = first_appearance(frame, risk['sources'])
        cols = sorted(set(frame) - {'signature', 'date', 'decision_ts', 'label', 'cold_payer', 'first'})
        base = [c for c in cols if c.startswith(('structure_', 'payer_', 'readonly_', 'template_'))]
        context = base + [c for c in cols if c.startswith('writable_')]
        assert (len(base), len(context)) == (27, 34)
        train = frame[frame.date.eq(dates[0]) & ((frame.decision_ts - frame.decision_ts.min()) >= protocol['warmup_hours'] * 3600)]
        train = train[train.decision_ts + protocol['outcome_delay_seconds'] < day_start(dates[1])]
        test = frame[frame.date.eq(dates[2])].copy()
        for name, inputs in [('logistic_baseline', base), ('logistic_context', context)]:
            model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
            model.fit(train[inputs], train.label)
            test[name] = model.predict_proba(test[inputs])[:, 1]
        saved = pd.read_parquet(FOLDER / f'transaction_predictions_{cohort}.parquet')
        test = test.merge(saved[['signature', 'payer_readonly_hgb', 'context_hgb']], on='signature', validate='one_to_one')
        test['rule_writable'] = test.writable_risk_max
        test['rule_template'] = test.template_risk
        models = ['rule_template', 'rule_writable', 'logistic_baseline', 'logistic_context', 'payer_readonly_hgb', 'context_hgb']
        out = {'label': label, 'test_date': dates[2], 'groups': {}}
        for group, mask in [('first_appearance', test['first'].to_numpy()), ('cold_history', test.cold_payer.to_numpy())]:
            part = test[mask]
            y, times = part.label.to_numpy(), part.decision_ts.to_numpy()
            out['groups'][group] = {
                'n': int(len(part)), 'failures': int(y.sum()), 'prevalence': float(y.mean()),
                'models': {m: score(y, part[m].to_numpy()) for m in models},
                'logistic_context_vs_baseline': compare(y, part.logistic_baseline.to_numpy(), part.logistic_context.to_numpy(), times),
                'hgb_context_vs_logistic_context': compare(y, part.logistic_context.to_numpy(), part.context_hgb.to_numpy(), times),
                'hgb_context_vs_rule_writable': compare(y, part.rule_writable.to_numpy(), part.context_hgb.to_numpy(), times)}
            print(label, group, {m: round(v['ap'], 4) for m, v in out['groups'][group]['models'].items()}, flush=True)
        report['cohorts'][cohort] = out
    report['input_sha256'] = hashes
    report['code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    target = ROOT / 'docs/results/solana_simple_baselines.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(target)


if __name__ == '__main__':
    main()
