"""Chronological label-maturity replay; experimental weighting, no coverage theorem."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from prefix_baseline import ROOT, threshold_at_fpr
from rich_features import enriched_features
from robustness import calendar_split, confirmation_sample, epoch, fit_model, paired_period_bootstrap

HERE = Path(__file__).resolve().parent


def visible_negatives(history, now, window=None, buffer=0, oracle=False):
    """Exclude all simultaneous decisions even if supplied malformed early labels."""
    mask = (history.decision_ts < now - buffer) & history.label.eq(0)
    if window is not None:
        mask &= history.decision_ts >= now - buffer - window
    if not oracle:
        mask &= history.label_ready_ts <= now
    return history.loc[mask]


def tail_probability(scores, score, weights=None):
    weights = np.ones(len(scores)) if weights is None else np.asarray(weights)
    # Conservative unit mass for the new observation. This does NOT confer a
    # weighted-conformal guarantee with an estimated observation propensity.
    return float((1 + weights[np.asarray(scores) >= score].sum()) / (1 + weights.sum()))


def delay_weights(reference, calibration, now, floor=.1, bins=3):
    edges = np.unique(np.quantile(reference.probability, np.linspace(0, 1, bins + 1)[1:-1]))
    rb = np.searchsorted(edges, reference.probability)
    cb = np.searchsorted(edges, calibration.probability)
    delay = (reference.label_ready_ts - reference.decision_ts).to_numpy()
    weights = []
    for group, age in zip(cb, now - calibration.decision_ts.to_numpy()):
        d = delay[rb == group]
        if len(d) < 10:
            d = delay
        propensity = (1 + np.sum(d <= age)) / (len(d) + 2)
        weights.append(1 / max(floor, propensity))
    return np.asarray(weights)


def replay(history, test, reference, threshold, protocol):
    names = protocol['controls']
    alerts = {name: [] for name in names}
    diagnostics = {name: Counter() for name in names}
    static = history[history.label.eq(0)].probability.to_numpy()
    combined = pd.concat([history, test], ignore_index=True)
    window, buffer = protocol['window_hours'] * 3600, protocol['buffer_hours'] * 3600
    for row in test.itertuples():
        now, score = row.decision_ts, row.probability
        visible = visible_negatives(combined, now)
        pools = {
            'recent_negative_tail': visible_negatives(combined, now, window),
            'delay_weighted_tail': visible_negatives(combined, now, window),
            'buffered_negative_tail': visible_negatives(combined, now, window, buffer),
            'arrival_negative_tail': visible.sort_values(['label_ready_ts', 'mint_address']).tail(protocol['arrival_count']),
            'oracle_immediate_tail': visible_negatives(combined, now, window, oracle=True),
        }
        for name in names:
            d = diagnostics[name]
            if name == 'frozen_empirical':
                alert = score >= threshold
            elif name == 'static_negative_tail':
                alert = tail_probability(static, score) <= protocol['budget']
            else:
                pool = pools[name]
                d['pool_size_sum'] += len(pool)
                if len(pool) < protocol['min_calibration_negatives']:
                    d['fallback_count'] += 1
                    alert = tail_probability(static, score) <= protocol['budget']
                else:
                    weights = None
                    if name == 'delay_weighted_tail':
                        weights = delay_weights(reference, pool, now, protocol['propensity_floor'], protocol['delay_score_bins'])
                        d['effective_sample_size_sum'] += float(weights.sum() ** 2 / (weights @ weights))
                        d['clipped_weight_count'] += int(np.sum(weights >= 1 / protocol['propensity_floor']))
                    alert = tail_probability(pool.probability, score, weights) <= protocol['budget']
            alerts[name].append(int(alert))
            d['decisions'] += 1
    return {k: np.asarray(v) for k, v in alerts.items()}, {k: dict(v) for k, v in diagnostics.items()}


def recall(y, alert):
    return float(np.mean(alert[y == 1]))


def fpr(y, alert):
    return float(np.mean(alert[y == 0]))


def build_cohort(protocol):
    sources = json.loads((ROOT / 'docs/results/blockchain_ml_source_probe.json').read_text())
    source = next(r for r in sources['files'] if r['repository'] == 'git-disl/MELT' and r['path'] == 'data/memecoin/memecoin_list.jsonl')
    migration = {r['token_address']: int(r['timestamp']) for r in map(json.loads,
        (ROOT / 'data/raw/solana_ml_probe' / source['sha256']).read_text().splitlines())}
    labels = pd.read_csv(ROOT / 'data/raw/melt/label.csv')
    target = labels.set_index('mint_address').min_ratio.lt(.3).astype(int).to_dict()
    records, skipped = [], Counter()
    with zipfile.ZipFile(ROOT / 'data/raw/melt/pre_migration_tx.zip') as archive:
        members = {Path(p).stem: p for p in archive.namelist() if p.startswith('pre_migration_tx/') and p.endswith('.jsonl')}
        sample = confirmation_sample(set(target) & set(migration) & set(members), protocol['sample_seed'], protocol['excluded_prior_hash_ranks'], protocol['sample_tokens'])
        if len(sample) != protocol['sample_tokens']:
            raise ValueError('Insufficient new tokens')
        for index, mint in enumerate(sample):
            events = list(map(json.loads, archive.read(members[mint]).splitlines()))
            if any(e['mint'] != mint for e in events):
                raise ValueError('Archive mint mismatch')
            mints = [e for e in events if 'mint' in e['type']]
            if not mints:
                skipped['missing_mint'] += 1
                continue
            launch = min(int(e['timestamp']) for e in mints)
            if migration[mint] <= launch + protocol['horizon']:
                skipped['already_migrated'] += 1
                continue
            try:
                t0, features = enriched_features(events, protocol['horizon'])
            except (ValueError, KeyError, TypeError) as error:
                skipped[str(error)] += 1
                continue
            records.append({'mint_address': mint, 'decision_ts': t0 + protocol['horizon'],
                            'label_ready_ts': migration[mint] + 3600, 'label': target[mint], **features})
            if (index + 1) % 1000 == 0:
                print(f'parsed {index+1}/{len(sample)}', flush=True)
    path = ROOT / 'data/processed/solana_ml/delayed_cohort_8000.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in records))
    return pd.DataFrame(records), path, dict(skipped)


def main():
    protocol_path = HERE / 'delayed_protocol.json'
    protocol = json.loads(protocol_path.read_text())
    old_path = ROOT / 'data/processed/solana_ml/strong_cohort_10000.jsonl'
    old = pd.read_json(old_path, lines=True)
    new, path, skipped = build_cohort(protocol)
    previous = set(old.mint_address)
    for p in ['prefix_price_drop_6000_42.jsonl', 'confirmation_12000.jsonl']:
        previous.update(pd.read_json(path.parent / p, lines=True).mint_address)
    if previous & set(new.mint_address):
        raise ValueError('Prior-token overlap')
    cols = sorted(set(old) - {'mint_address', 'decision_ts', 'label_ready_ts', 'label'})
    strong = json.loads((ROOT / 'docs/results/solana_strong_baselines.json').read_text())
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'protocol': protocol,
              'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              'eligible': len(new), 'skipped': skipped, 'prior_token_overlap': 0,
              'results': [], 'comparisons': [], 'delay_by_outcome': {},
              'limits': ['Same historical period; not independent-period confirmation.',
                         'Outcome readiness is a conservative assumed schedule, not verified publication time.',
                         'Availability weighting is established prior art; this is an empirical intervention test.',
                         'Static negative-tail guarantee requires exchangeability; temporal drift may violate it.',
                         'Estimated weights and buffer have no proved coverage guarantee.',
                         'Bootstrap is conditional on models, clustered by decision day, not wallet operator.']}
    for label, group in new.groupby('label'):
        delay = (group.label_ready_ts - group.decision_ts) / 3600
        report['delay_by_outcome'][str(label)] = {'n': len(group), 'median_hours': float(delay.median()),
            'available_at_6h': float(delay.le(6).mean()), 'available_at_24h': float(delay.le(24).mean()),
            'exceeds_buffer': int(delay.gt(protocol['buffer_hours']).sum())}
    paired = {name: [] for name in protocol['controls'] if name != 'recent_negative_tail'}
    predictions = []
    for fold, result in zip(strong['protocol']['folds'], strong['results']):
        train, val, _ = calendar_split(old, fold)
        _, _, test = calendar_split(new, fold)
        test = test.sort_values(['decision_ts', 'mint_address']).copy()
        selected = next(m for m in result['models'] if m['model'] == 'random_forest' and m['scope'] == 'enriched')
        pv, pt = [], []
        for seed in protocol['seeds']:
            model = fit_model('random_forest', selected['parameters'], seed)
            model.fit(train[cols], train.label)
            pv.append(model.predict_proba(val[cols])[:, 1])
            pt.append(model.predict_proba(test[cols])[:, 1])
        val = val.copy()
        val['probability'] = np.mean(pv, axis=0)
        test['probability'] = np.mean(pt, axis=0)
        threshold = threshold_at_fpr(val.label.to_numpy(), val.probability.to_numpy(), protocol['budget'])
        reference = visible_negatives(val, epoch(fold['validation_end']), buffer=protocol['buffer_hours'] * 3600)
        if len(reference) < 30:
            raise ValueError('Insufficient past negative delay reference')
        alerts, diagnostics = replay(val, test, reference, threshold, protocol)
        y = test.label.to_numpy()
        section = {'period': fold['name'], 'test_n': len(test), 'negative_n': int(sum(y == 0)),
                   'positive_n': int(sum(y == 1)), 'reference_n': len(reference), 'parameters': selected['parameters'],
                   'auroc': float(roc_auc_score(y, test.probability)), 'ap': float(average_precision_score(y, test.probability)),
                   'methods': {name: {'recall': recall(y, a), 'fpr': fpr(y, a),
                        'alert_fraction': float(a.mean()), 'diagnostics': diagnostics[name]} for name, a in alerts.items()}}
        report['results'].append(section)
        for name in paired:
            paired[name].append({'y': y, 'base': alerts['recent_negative_tail'], 'coord': alerts[name], 'days': test.decision_ts.to_numpy() // 86400})
        predictions.extend({'mint': row.mint_address, 'period': fold['name'], 'decision_ts': int(row.decision_ts),
            'label_ready_ts': int(row.label_ready_ts), 'label': int(row.label), 'probability': float(row.probability),
            'alerts': {name: int(a[i]) for name, a in alerts.items()}} for i, row in enumerate(test.itertuples()))
        print(json.dumps(section), flush=True)
    for name, periods in paired.items():
        report['comparisons'].append({'candidate': name, 'reference': 'recent_negative_tail',
            'primary': name == 'delay_weighted_tail', 'recall_delta': paired_period_bootstrap(periods, recall),
            'fpr_delta': paired_period_bootstrap(periods, fpr)})
    primary = next(c for c in report['comparisons'] if c['primary'])
    report['primary_success'] = bool(primary['recall_delta']['ci95'][0] > 0 and primary['fpr_delta']['ci95'][1] <= 0
        and all(r['methods']['delay_weighted_tail']['fpr'] <= protocol['budget'] for r in report['results']))
    report['source_hashes'] = strong['source_hashes'] | {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [old_path, path, protocol_path, HERE / 'delayed_replay.py']}
    (path.parent / 'delayed_predictions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in predictions))
    output = ROOT / 'docs/results/solana_delayed_replay.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(output, flush=True)


if __name__ == '__main__':
    main()
