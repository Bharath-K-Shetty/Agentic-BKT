"""Stronger ordinary feature baselines on a third, untouched token cohort."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import warnings
import zipfile

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from prefix_baseline import ROOT, metrics, threshold_at_fpr
from rich_features import enriched_features
from robustness import calendar_split, confirmation_sample, fit_model, paired_period_bootstrap

HERE = Path(__file__).resolve().parent


def main():
    protocol_path = HERE / 'strong_baseline_protocol.json'
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    sources = json.loads((ROOT / 'docs/results/blockchain_ml_source_probe.json').read_text())
    metadata = next(r for r in sources['files'] if r['repository'] == 'git-disl/MELT'
                    and r['path'] == 'data/memecoin/memecoin_list.jsonl')
    migration = {r['token_address']: int(r['timestamp']) for r in map(json.loads,
        (ROOT / 'data/raw/solana_ml_probe' / metadata['sha256']).read_text().splitlines())}
    labels = pd.read_csv(ROOT / 'data/raw/melt/label.csv')
    target = labels.set_index('mint_address').min_ratio.lt(.3).astype(int).to_dict()
    records, skipped = [], Counter()
    with zipfile.ZipFile(ROOT / 'data/raw/melt/pre_migration_tx.zip') as archive:
        members = {Path(p).stem: p for p in archive.namelist()
                   if p.startswith('pre_migration_tx/') and p.endswith('.jsonl')}
        sample = confirmation_sample(set(target) & set(migration) & set(members), protocol['sample_seed'],
                                     protocol['excluded_prior_hash_ranks'], protocol['sample_tokens'])
        if len(sample) != protocol['sample_tokens']:
            raise ValueError('Insufficient third-cohort tokens')
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
                t0, f = enriched_features(events, protocol['horizon'])
            except (ValueError, KeyError, TypeError) as error:
                skipped[str(error)] += 1
                continue
            records.append({'mint_address': mint, 'decision_ts': t0 + protocol['horizon'],
                            'label_ready_ts': migration[mint] + 3600, 'label': target[mint], **f})
            if (index + 1) % 1000 == 0:
                print(f'processed {index+1}/{len(sample)} sample tokens', flush=True)
    processed = ROOT / 'data/processed/solana_ml'
    path = processed / 'strong_cohort_10000.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in records))
    frame = pd.DataFrame(records)
    old = set()
    for p in (processed / 'prefix_price_drop_6000_42.jsonl', processed / 'confirmation_12000.jsonl'):
        old.update(pd.read_json(p, lines=True).mint_address)
    if set(frame.mint_address) & old:
        raise ValueError('Third cohort overlaps earlier token cohorts')
    cols = sorted(set(frame) - {'mint_address', 'decision_ts', 'label_ready_ts', 'label'})
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'protocol': protocol,
              'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(), 'sampled': len(sample),
              'eligible': len(frame), 'skipped': dict(skipped), 'prior_token_overlap': 0,
              'feature_count': {'pilot_27': sum(not c.startswith('rich_') for c in cols), 'enriched': len(cols)},
              'feature_names': cols, 'results': [], 'comparisons': [],
              'limits': ['Same historical MELT data; not independent-period validation.',
                         'Price-collapse proxy on eventual migrants, not verified fraud.',
                         'New ordinary features, not a novel algorithm or exact upstream replication.',
                         'No retrospective funder/Jito links or verified creator identity.',
                         'Validation used for configuration selection and threshold selection; test untouched.',
                         'Bootstrap conditional on fitted models; secondary comparisons exploratory.']}
    predictions, paired = [], {}
    for fold in protocol['folds']:
        train, val, test = calendar_split(frame, fold)
        for data in (train, val, test):
            if len(data) < 100 or data.label.nunique() != 2:
                raise ValueError('Insufficient third-cohort calendar partition')
        section = {'period': fold['name'], 'counts': {name: {'n': len(d), 'prevalence': float(d.label.mean())}
                   for name, d in [('train', train), ('validation', val), ('test', test)]}, 'models': []}
        local = {}
        for name in ('random_forest', 'hist_gradient_boosting'):
            for scope in protocol['scopes']:
                inputs = [c for c in cols if scope == 'enriched' or not c.startswith('rich_')]
                candidates = []
                warnings_text = []
                for params in protocol[name + '_grid']:
                    model = fit_model(name, params, protocol['seeds'][0])
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always')
                        model.fit(train[inputs], train.label)
                    warnings_text.extend(str(w.message) for w in caught)
                    pv = model.predict_proba(val[inputs])[:, 1]
                    candidates.append((float(average_precision_score(val.label, pv)), params, model, pv))
                score, params, selected, pv = max(candidates, key=lambda c: c[0])
                pv_all, pt_all = [pv], [selected.predict_proba(test[inputs])[:, 1]]
                for seed in protocol['seeds'][1:]:
                    model = fit_model(name, params, seed)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always')
                        model.fit(train[inputs], train.label)
                    warnings_text.extend(str(w.message) for w in caught)
                    pv_all.append(model.predict_proba(val[inputs])[:, 1])
                    pt_all.append(model.predict_proba(test[inputs])[:, 1])
                pv, pt = np.mean(pv_all, axis=0), np.mean(pt_all, axis=0)
                threshold = threshold_at_fpr(val.label.to_numpy(), pv)
                result = {'model': name, 'scope': scope, 'parameters': params, 'validation_grid_ap':
                          [{'params': c[1], 'ap': c[0]} for c in candidates], 'threshold': threshold,
                          'validation': metrics(val.label.to_numpy(), pv, threshold),
                          'test': metrics(test.label.to_numpy(), pt, threshold), 'fit_warnings': warnings_text,
                          'seed_test_auroc': [float(roc_auc_score(test.label, p)) for p in pt_all]}
                section['models'].append(result)
                local[(name, scope)] = pt
                predictions.extend({'mint': mint, 'period': fold['name'], 'model': name, 'scope': scope,
                                    'label': int(y), 'probability': float(p), 'day': int(ts // 86400)}
                                   for mint, y, p, ts in zip(test.mint_address, test.label, pt, test.decision_ts))
                print(fold['name'], name, scope, json.dumps(result['test']), flush=True)
            paired.setdefault(name, []).append({'y': test.label.to_numpy(),
                'base': local[(name, 'pilot_27')], 'coord': local[(name, 'enriched')],
                'days': test.decision_ts.to_numpy() // 86400})
        report['results'].append(section)
    for name, periods in paired.items():
        report['comparisons'].append({'model': name, 'primary': name == 'random_forest',
                                     'ap': paired_period_bootstrap(periods, average_precision_score),
                                     'auroc': paired_period_bootstrap(periods, roc_auc_score)})
    report['source_hashes'] = json.loads((ROOT / 'docs/results/solana_prefix_baseline.json').read_text())['source_hashes']
    for p in (path, HERE / 'rich_features.py', HERE / 'strong_baselines.py', HERE / 'robustness.py'):
        report['source_hashes'][str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (processed / 'strong_predictions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in predictions))
    out = ROOT / 'docs/results/solana_strong_baselines.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(out, flush=True)


if __name__ == '__main__':
    main()
