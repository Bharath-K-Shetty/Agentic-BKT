"""Audit ML warning usefulness without fabricating actual fee savings."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'research/solana/ml'))


def counts(y, alert):
    y = np.asarray(y, dtype=bool)
    alert = np.asarray(alert, dtype=bool)
    if y.shape != alert.shape or y.ndim != 1:
        raise ValueError('Outcome and warning arrays must be aligned vectors')
    tp = int((y & alert).sum())
    fp = int((~y & alert).sum())
    fn = int((y & ~alert).sum())
    tn = int((~y & ~alert).sum())
    return {'flagged_failures': tp, 'flagged_successes': fp, 'missed_failures': fn,
            'unflagged_successes': tn, 'warnings': tp+fp,
            'precision': tp/(tp+fp) if tp+fp else None,
            'failure_recall': tp/(tp+fn) if tp+fn else None,
            'false_positive_rate': fp/(fp+tn) if fp+tn else None,
            'break_even_blocked_success_cost_over_failed_fee': tp/fp if fp else None,
            'hypothetical_net_units': {str(r): tp-r*fp for r in (0, 1, 5, 10)}}


def paired_intervals(y, baseline, context, hours):
    # Cluster counts once rather than resampling individual transactions.
    groups = np.unique(hours)
    differences = []
    for hour in groups:
        mask = hours == hour
        a, b = counts(y[mask], baseline[mask]), counts(y[mask], context[mask])
        differences.append([b['hypothetical_net_units'][str(r)]-a['hypothetical_net_units'][str(r)]
                            for r in (0, 1, 5, 10)])
    differences = np.asarray(differences)
    rng = np.random.default_rng(1729)
    samples = differences[rng.integers(0, len(groups), (1000, len(groups)))].sum(axis=1)
    return {str(r): {'delta_net_units': int(differences[:, i].sum()),
                    'paired_hour_bootstrap_ci95': np.quantile(samples[:, i], [.025, .975]).tolist()}
            for i, r in enumerate((0, 1, 5, 10))}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cohort(cohort):
    folder = ROOT/'data/processed/solana_ml'
    if cohort == 'fresh':
        return joblib.load(folder/'demo_models.joblib'), pd.read_parquet(folder/'demo_inference_test.parquet')
    from sklearn.ensemble import HistGradientBoostingClassifier
    from build_replay_demo import calibrate_validation
    p = json.loads((ROOT/f'docs/results/solana_transaction_risk_{cohort}.json').read_text())['protocol']
    frame = pd.read_parquet(folder/f'transaction_features_{cohort}.parquet')
    epoch = lambda date: int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())
    train = frame[frame.date.eq(p['train_date']) & (frame.decision_ts-frame.decision_ts.min() >= 21600)
                  & (frame.decision_ts+3600 < epoch(p['validation_date']))]
    val = frame[frame.date.eq(p['validation_date']) & (frame.decision_ts+3600 < epoch(p['test_date']))]
    test = frame[frame.date.eq(p['test_date'])].copy()
    cols = sorted(set(frame)-{'signature', 'date', 'decision_ts', 'label', 'cold_payer'})
    saved = {'test_date': p['test_date'], 'models': {}}
    original = pd.read_parquet(folder/f'transaction_predictions_{cohort}.parquet')
    assert np.array_equal(original.signature, test.signature)
    for name in ('payer_readonly_hgb', 'context_hgb'):
        inputs = [c for c in cols if name == 'context_hgb' or not c.startswith('writable_')]
        model = HistGradientBoostingClassifier(**p['hgb'], random_state=42).fit(train[inputs], train.label)
        assert np.allclose(model.predict_proba(test[inputs])[:, 1], original[name], rtol=1e-10, atol=1e-12)
        cal, threshold, split = calibrate_validation(val.label.to_numpy(), model.predict_proba(val[inputs])[:, 1],
            val.decision_ts.to_numpy(), val.cold_payer.to_numpy(), epoch(p['validation_date'])+43200)
        saved['models'][name] = {'model': model, 'inputs': inputs, 'calibrator': cal, 'threshold': threshold}
    return saved, test


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=['fresh','pilot','confirmation','extension','prospective'], default='fresh')
    args = parser.parse_args()
    cohort = args.cohort
    protocol_path = HERE/'ml_policy_protocol.json'
    protocol = json.loads(protocol_path.read_text())
    folder = ROOT/'data/processed/solana_ml'
    saved, frame = load_cohort(cohort)
    frame = frame[frame.cold_payer].copy()
    if frame.signature.duplicated().any():
        raise ValueError('Duplicate held-out signatures')
    y = frame.label.to_numpy(dtype=bool)
    predictions = {}
    results = {}
    cost_policies = {}
    for name in protocol['models']:
        artifact = saved['models'][name]
        if {'label', 'cold_payer', 'signature'} & set(artifact['inputs']):
            raise ValueError('Non-feature field in model inputs')
        raw = artifact['model'].predict_proba(frame[artifact['inputs']])[:, 1]
        scores = artifact['calibrator'].predict(raw)
        warning = scores >= artifact['threshold']
        predictions[name] = warning
        results[name] = {'threshold': float(artifact['threshold']), **counts(y, warning)}
        cost_policies[name] = {str(r): {'threshold': r/(1+r), **counts(y, scores >= r/(1+r))}
                               for r in (1, 5, 10)}
    p = json.loads((ROOT/f'docs/results/solana_transaction_risk_{cohort}.json').read_text())['protocol']
    source = ROOT/p.get('source_paths', {}).get(p['test_date'], f'data/raw/novelty_search/archive_preview_{p["test_date"]}.parquet')
    columns = pq.ParquetFile(source).schema_arrow.names
    result = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'protocol': protocol, 'protocol_sha256': digest(protocol_path),
        'cohort': cohort,
        'protocol_overrides': {'cohort': cohort, 'population': f'All cold_payer rows in held-out {saved["test_date"]} sample'},
        'model_sha256': digest(folder/'demo_models.joblib') if cohort == 'fresh' else None,
        'test_features_sha256': digest(folder/f'transaction_features_{cohort}.parquet'),
        'source_schema': columns, 'source_sha256': digest(source),
        'test_date': saved['test_date'], 'rows': len(frame), 'failures': int(y.sum()),
        'successes': int((~y).sum()), 'models': results,
        'exploratory_cost_based_thresholds': cost_policies,
        'context_minus_baseline': paired_intervals(y, predictions['payer_readonly_hgb'],
                                                   predictions['context_hgb'], frame.decision_ts.to_numpy()//3600),
        'actual_fee_savings_proven': False, 'incremental_benefit_over_preflight_proven': False,
        'measured_fee_savings_lamports': None,
        'missing_evidence': ['Per-candidate preflight result at real decision time',
                             'Signed-message identity and simulation/submission timestamps',
                             'Paid fee from confirmed receipt and contemporaneous balances',
                             'ML prediction using only available live history',
                             'Outcomes and costs for warned successful transactions',
                             'Prospective comparison against standard preflight alone'],
        'interpretation': 'These are observed historical warnings and counterfactual cost scenarios. Warnings do not establish prevented transactions or saved fees. All warned failures might also be caught by preflight.',
    }
    output = ROOT/('docs/results/solana_ml_fee_policy.json' if cohort == 'fresh'
                  else f'docs/results/solana_ml_fee_policy_{cohort}.json')
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ['rows', 'failures', 'models', 'context_minus_baseline', 'exploratory_cost_based_thresholds']}, indent=2))
    print(f'Evidence: {output}')


if __name__ == '__main__':
    main()
