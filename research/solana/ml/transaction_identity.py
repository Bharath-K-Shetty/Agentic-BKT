"""Post-result identity control with delayed prequential learning.

Both nonlinear controls receive the same identity score. This checks an obvious
alternative explanation; it is not a new preregistered primary comparison.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.sparse import vstack
from sklearn.feature_extraction import FeatureHasher
from sklearn.preprocessing import normalize
from sklearn.linear_model import SGDClassifier
from sklearn.ensemble import HistGradientBoostingClassifier

from transaction_risk import ROOT, HERE, declared_roles, bootstrap_comparison
from prefix_baseline import metrics, threshold_at_fpr


def identity_tokens(accounts):
    payer, signers, writable, readonly = declared_roles(accounts)
    # Namespace by role, so sharing a key is not assumed to imply ownership.
    return ([f'p:{payer}'] + [f's:{a}' for a in sorted(signers)]
            + [f'w:{a}' for a in sorted(writable)]
            + [f'r:{a}' for a in sorted(readonly)]
            + ['t:' + '|'.join(sorted(readonly))])


def prequential_scores(x, y, times, settings):
    """Predict a batch before fitting newly available labels from that batch."""
    if np.any(np.diff(times) < 0):
        raise ValueError('Identity replay must be chronological')
    model = SGDClassifier(loss='log_loss', alpha=settings['alpha'],
        random_state=settings['random_state'], shuffle=False)
    scores = np.full(len(y), .5)
    fitted, trained = False, 0
    checkpoints = times // settings['update_interval_seconds']
    ends = np.r_[np.flatnonzero(np.diff(checkpoints)) + 1, len(y)]
    start = 0
    for end in ends:
        now = checkpoints[start] * settings['update_interval_seconds']
        ready = int(np.searchsorted(times, now-settings['outcome_delay_seconds'], side='right'))
        ready = min(ready, start)
        if ready > trained:
            model.partial_fit(x[trained:ready], y[trained:ready], classes=np.array([0, 1]))
            trained, fitted = ready, True
        if fitted:
            scores[start:end] = model.predict_proba(x[start:end])[:, 1]
        start = end
    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=['pilot', 'confirmation', 'extension', 'prospective', 'fresh', 'third', 'fourth', 'fifth'], required=True)
    args = parser.parse_args()
    control_path = HERE / 'transaction_identity_protocol.json'
    settings = json.loads(control_path.read_text())
    primary_path = ROOT / f'docs/results/solana_transaction_risk_{args.cohort}.json'
    primary = json.loads(primary_path.read_text())
    protocol = primary['protocol']
    dates = [protocol[k] for k in ['train_date', 'validation_date', 'test_date']]
    folder = ROOT / 'data/processed/solana_ml'
    frame = pd.read_parquet(folder / f'transaction_features_{args.cohort}.parquet')
    signature_order = {s: i for i, s in enumerate(frame.signature)}
    hasher = FeatureHasher(n_features=settings['hash_dimensions'], input_type='string', alternate_sign=False)
    matrices = []
    signatures = []
    for date in dates:
        source = protocol.get('source_paths', {}).get(date, f'data/raw/novelty_search/archive_preview_{date}.parquet')
        rows = pq.read_table(ROOT / source).to_pylist()
        rows = {r['signature']: r for r in rows if r['signature'] in signature_order}
        ordered = sorted(rows, key=signature_order.get)
        matrices.append(hasher.transform(identity_tokens(rows[s]['accounts']) for s in ordered))
        signatures.extend(ordered)
        print('hashed', date, len(ordered), flush=True)
    if signatures != frame.signature.tolist():
        raise ValueError('Account/feature alignment mismatch')
    x = normalize(vstack(matrices).tocsr())
    times = frame.decision_ts.to_numpy()
    identity = prequential_scores(x, frame.label.to_numpy(), times, settings)
    frame['identity_all_risk'] = identity
    print('identity replay complete', args.cohort, flush=True)
    boundary = int(datetime.fromisoformat(dates[1]).replace(tzinfo=timezone.utc).timestamp())
    test_start = int(datetime.fromisoformat(dates[2]).replace(tzinfo=timezone.utc).timestamp())
    train = frame[frame.date.eq(dates[0]) & (times-frame.decision_ts.min() >= protocol['warmup_hours']*3600)
                  & (times+protocol['outcome_delay_seconds'] < boundary)]
    val = frame[frame.date.eq(dates[1]) & (times+protocol['outcome_delay_seconds'] < test_start)]
    test = frame[frame.date.eq(dates[2])]
    feature_cols = sorted(set(frame) - {'signature', 'date', 'decision_ts', 'label', 'cold_payer'})
    predictions, results = {}, []
    for name in ['identity_logistic', 'readonly_identity_hgb', 'context_identity_hgb']:
        if name == 'identity_logistic':
            pv, pt = val.identity_all_risk.to_numpy(), test.identity_all_risk.to_numpy()
        else:
            inputs = [c for c in feature_cols if name == 'context_identity_hgb' or not c.startswith('writable_')]
            model = HistGradientBoostingClassifier(**protocol['hgb'], random_state=42)
            model.fit(train[inputs], train.label)
            pv, pt = model.predict_proba(val[inputs])[:, 1], model.predict_proba(test[inputs])[:, 1]
        threshold = threshold_at_fpr(val.label.to_numpy(), pv, protocol['budget'])
        cold = test.cold_payer.to_numpy()
        result = {'model': name, 'threshold': threshold,
                  'validation': metrics(val.label.to_numpy(), pv, threshold),
                  'test': metrics(test.label.to_numpy(), pt, threshold),
                  'cold_payer': metrics(test.label.to_numpy()[cold], pt[cold], threshold)}
        predictions[name] = pt
        results.append(result)
        print(name, json.dumps(result['cold_payer']), flush=True)
    cold = test.cold_payer.to_numpy()
    delta = bootstrap_comparison(test.label.to_numpy()[cold], predictions['readonly_identity_hgb'][cold],
        predictions['context_identity_hgb'][cold], test.decision_ts.to_numpy()[cold])
    saved = test[['signature', 'label', 'decision_ts', 'cold_payer']].copy()
    for name, p in predictions.items():
        saved[name] = p
    saved.to_parquet(folder / f'transaction_identity_predictions_{args.cohort}.parquet', index=False)
    report = {'cohort': args.cohort, 'settings': settings, 'results': results,
              'cold_ap_comparison': delta, 'primary_report_sha256': hashlib.sha256(primary_path.read_bytes()).hexdigest(),
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'control_protocol_sha256': hashlib.sha256(control_path.read_bytes()).hexdigest(),
              'limitations': ['Post-result diagnostic on previously inspected cohorts.',
                 'Linear hashed identity model with fixed settings; not an exhaustive identity-model search.',
                 'Identity labels delayed one hour plus up to ten minutes batching, history features exact one hour.',
                 'Identity is trained once on every matured sample including warmup; HGB fit uses original purged train partition.',
                 'Same hourly bootstrap and conditional-inclusion limitations as the primary experiment.']}
    path = ROOT / f'docs/results/solana_transaction_identity_{args.cohort}.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(path, flush=True)


if __name__ == '__main__':
    main()
