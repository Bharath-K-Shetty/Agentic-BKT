"""Alarm-level follow-up: set the warning threshold on the population it is used for.

Rules and pass criteria are fixed in threshold_policy_protocol.json, written
before the fresh 2025-11-19..21 window was downloaded. Identity-controlled
boosting scores are reproduced deterministically and checked against the saved
test predictions; models and features are unchanged.

    .venv/bin/python research/solana/ml/threshold_policy.py --cohort fourth
    (retrospective: prospective, fresh, third)
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.sparse import vstack
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import FeatureHasher
from sklearn.metrics import precision_recall_curve, recall_score
from sklearn.preprocessing import normalize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from transaction_risk import ROOT  # noqa: E402
from transaction_identity import identity_tokens, prequential_scores  # noqa: E402
from prefix_baseline import threshold_at_fpr  # noqa: E402
from robustness import paired_period_bootstrap  # noqa: E402

MODELS = {'baseline': 'readonly_identity_hgb', 'homie': 'context_identity_hgb'}
LABELS = {'prospective': 'Dec 1', 'fresh': 'Dec 5', 'third': 'Nov 28', 'fourth': 'Nov 21'}
FOLDER = ROOT / 'data/processed/solana_ml'
PROTOCOL = HERE / 'threshold_policy_protocol.json'
TARGET_FPR = .05


def day(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def reproduce(cohort):
    """Rebuild the identity-controlled validation and test scores exactly as transaction_identity.py does."""
    primary = json.loads((ROOT / f'docs/results/solana_transaction_risk_{cohort}.json').read_text())
    protocol = primary['protocol']
    dates = [protocol[k] for k in ['train_date', 'validation_date', 'test_date']]
    settings = json.loads((HERE / 'transaction_identity_protocol.json').read_text())
    frame = pd.read_parquet(FOLDER / f'transaction_features_{cohort}.parquet')
    order = {s: i for i, s in enumerate(frame.signature)}
    hasher = FeatureHasher(n_features=settings['hash_dimensions'], input_type='string', alternate_sign=False)
    matrices, signatures, payers = [], [], {}
    for date in dates:
        source = protocol.get('source_paths', {}).get(date, f'data/raw/novelty_search/archive_preview_{date}.parquet')
        rows = {r['signature']: r for r in pq.read_table(ROOT / source).to_pylist() if r['signature'] in order}
        ordered = sorted(rows, key=order.get)
        matrices.append(hasher.transform(identity_tokens(rows[s]['accounts']) for s in ordered))
        signatures.extend(ordered)
        payers.update({s: rows[s]['accounts'][0]['pubkey'] for s in ordered})
    assert signatures == frame.signature.tolist()
    times = frame.decision_ts.to_numpy()
    frame['identity_all_risk'] = prequential_scores(normalize(vstack(matrices).tocsr()), frame.label.to_numpy(), times, settings)
    cols = sorted(set(frame) - {'signature', 'date', 'decision_ts', 'label', 'cold_payer'})
    frame['first'] = ~frame.signature.map(payers).duplicated()
    train = frame[frame.date.eq(dates[0]) & (times - frame.decision_ts.min() >= protocol['warmup_hours'] * 3600)
                  & (times + protocol['outcome_delay_seconds'] < day(dates[1]))]
    val = frame[frame.date.eq(dates[1]) & (times + protocol['outcome_delay_seconds'] < day(dates[2]))]
    test = frame[frame.date.eq(dates[2])]
    scores = {}
    for key, name in MODELS.items():
        inputs = [c for c in cols if name == 'context_identity_hgb' or not c.startswith('writable_')]
        model = HistGradientBoostingClassifier(**protocol['hgb'], random_state=42).fit(train[inputs], train.label)
        scores[key] = (model.predict_proba(val[inputs])[:, 1], model.predict_proba(test[inputs])[:, 1])
    saved = pd.read_parquet(FOLDER / f'transaction_identity_predictions_{cohort}.parquet')
    assert saved.signature.tolist() == test.signature.tolist()
    for key, name in MODELS.items():
        assert np.allclose(saved[name].to_numpy(), scores[key][1], rtol=1e-9, atol=1e-12), f'{name} not reproduced'
    return protocol, val, test, scores


def f1_threshold(y, p):
    precision, recall, thresholds = precision_recall_curve(y, p)
    f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    return float(thresholds[np.flatnonzero(f1 == f1.max()).max()])


def evaluate(y, p, threshold):
    flag = p >= threshold
    tp, fp = int((flag & (y == 1)).sum()), int((flag & (y == 0)).sum())
    fn, tn = int((~flag & (y == 1)).sum()), int((~flag & (y == 0)).sum())
    recall, fpr = tp / (tp + fn), fp / (fp + tn)
    return {'threshold': threshold, 'flagged': tp + fp, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'recall': recall, 'fpr': fpr, 'precision': tp / (tp + fp) if tp + fp else None,
            'accuracy': (tp + tn) / len(y), 'balanced_accuracy': (recall + 1 - fpr) / 2,
            'f1': 2 * tp / (2 * tp + fp + fn)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=list(LABELS), required=True)
    args = parser.parse_args()
    output = ROOT / f'docs/results/solana_threshold_policy_{args.cohort}.json'
    if args.cohort == 'fourth' and output.exists():
        raise SystemExit(f'{output} exists: the fresh evaluation runs once.')
    protocol, val, test, scores = reproduce(args.cohort)
    identity_report = json.loads((ROOT / f'docs/results/solana_transaction_identity_{args.cohort}.json').read_text())
    saved_thresholds = {r['model']: r['threshold'] for r in identity_report['results']}
    vf, tf = val['first'].to_numpy(), test['first'].to_numpy()
    yv, yt = val.label.to_numpy(), test.label.to_numpy()
    rules, flags = {}, {}
    for key, name in MODELS.items():
        pv, pt = scores[key]
        thresholds = {'inherited': threshold_at_fpr(yv, pv, protocol['budget']),
                      'matched': threshold_at_fpr(yv[vf], pv[vf], TARGET_FPR),
                      'f1_matched': f1_threshold(yv[vf], pv[vf])}
        assert thresholds['inherited'] == saved_thresholds[name]
        rules[key] = {rule: {'validation_first_appearance': evaluate(yv[vf], pv[vf], t),
                             'test_first_appearance': evaluate(yt[tf], pt[tf], t)} for rule, t in thresholds.items()}
        flags[key] = {rule: (pt[tf] >= t).astype(int) for rule, t in thresholds.items()}
    times = test.decision_ts.to_numpy()[tf] // 3600
    recall_gap = {rule: paired_period_bootstrap([{'y': yt[tf], 'base': flags['baseline'][rule], 'coord': flags['homie'][rule], 'days': times}],
                                                lambda y, f: recall_score(y, f, zero_division=0))
                  for rule in ['inherited', 'matched', 'f1_matched']}
    distance = {key: {rule: abs(rules[key][rule]['test_first_appearance']['fpr'] - TARGET_FPR) for rule in ['inherited', 'matched']}
                for key in MODELS}
    endpoints = {'E1_stability_passed': all(d['matched'] < d['inherited'] for d in distance.values()),
                 'E1_distance_from_5pct': distance,
                 'E2_recall_gap_matched': recall_gap['matched'],
                 'E2_passed': recall_gap['matched']['weighted_delta'] > 0 and recall_gap['matched']['ci95'][0] > 0}
    report = {'cohort': args.cohort, 'test_date': protocol['test_date'], 'label': LABELS[args.cohort],
              'role': 'primary fresh confirmation' if args.cohort == 'fourth' else 'retrospective (test day previously inspected)',
              'test_first_appearances': int(tf.sum()), 'test_failures': int(yt[tf].sum()),
              'validation_first_appearances': int(vf.sum()), 'validation_failures': int(yv[vf].sum()),
              'rules': rules, 'recall_gap_homie_minus_baseline': recall_gap, 'endpoints': endpoints,
              'protocol_sha256': hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'created_at': datetime.now(timezone.utc).isoformat()}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(LABELS[args.cohort], json.dumps(endpoints))
    for key in MODELS:
        for rule, r in rules[key].items():
            t = r['test_first_appearance']
            print(f"  {key:8s} {rule:10s} flagged={t['flagged']:5d} recall={t['recall']:.3f} fpr={t['fpr']:.3f} precision={t['precision']} accuracy={t['accuracy']:.4f}")


if __name__ == '__main__':
    main()
