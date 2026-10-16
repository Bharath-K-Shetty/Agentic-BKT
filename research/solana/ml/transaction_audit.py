"""Post-result first-appearance and signer-dependence diagnostics."""
import argparse
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from transaction_risk import ROOT, bootstrap_comparison
from prefix_baseline import metrics


def cluster_delta(y, base, candidate, groups, draws=500):
    from sklearn.metrics import average_precision_score
    _, inverse = np.unique(groups, return_inverse=True)
    n = int(inverse.max()) + 1
    rng = np.random.default_rng(42)
    results = []
    for _ in range(draws):
        counts = np.bincount(rng.integers(0, n, n), minlength=n)
        weights = counts[inverse]
        if np.unique(y[weights > 0]).size == 2:
            results.append(average_precision_score(y, candidate, sample_weight=weights)
                           - average_precision_score(y, base, sample_weight=weights))
    return {'delta': float(average_precision_score(y, candidate)-average_precision_score(y, base)),
            'ci95': np.quantile(results, [.025, .975]).tolist(), 'draws': len(results), 'signer_clusters': n}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', required=True)
    args = parser.parse_args()
    report = json.loads((ROOT / f'docs/results/solana_transaction_risk_{args.cohort}.json').read_text())
    protocol = report['protocol']
    folder = ROOT / 'data/processed/solana_ml'
    frame = pd.read_parquet(folder / f'transaction_features_{args.cohort}.parquet')
    payers = {}
    for date in [protocol[k] for k in ['train_date', 'validation_date', 'test_date']]:
        path = ROOT / protocol.get('source_paths', {}).get(date, f'data/raw/novelty_search/archive_preview_{date}.parquet')
        table = pq.read_table(path, columns=['signature', 'accounts'])
        payers.update({r['signature']: r['accounts'][0]['pubkey'] for r in table.to_pylist()})
    frame['signer'] = frame.signature.map(payers)
    if frame.signer.isna().any():
        raise ValueError('Missing declared signer')
    frame['first_appearance'] = ~frame.signer.duplicated()
    saved = pd.read_parquet(folder / f'transaction_predictions_{args.cohort}.parquet')
    test = saved.merge(frame[['signature', 'signer', 'first_appearance']], on='signature', validate='one_to_one')
    cold = test[test.cold_payer]
    first = test[test.first_appearance]
    models = {r['model']: r for r in report['results']}
    output = {'cohort': args.cohort, 'status': 'Post-result diagnostic; original primary endpoint unchanged',
        'test_n': len(test), 'cold_n': len(cold), 'cold_unique_signers': int(cold.signer.nunique()),
        'cold_max_rows_one_signer': int(cold.signer.value_counts().max()),
        'first_appearance_n': len(first), 'first_appearance_prevalence': float(first.label.mean()),
        'cold_signer_bootstrap': cluster_delta(cold.label.to_numpy(), cold.payer_readonly_hgb.to_numpy(),
                                               cold.context_hgb.to_numpy(), cold.signer.to_numpy()),
        'first_appearance_hour_bootstrap': bootstrap_comparison(first.label.to_numpy(), first.payer_readonly_hgb.to_numpy(),
                                              first.context_hgb.to_numpy(), first.decision_ts.to_numpy()),
        'first_appearance_results': {name: metrics(first.label.to_numpy(), first[name].to_numpy(), models[name]['threshold'])
            for name in ['payer_history', 'payer_readonly_hgb', 'context_hgb']},
        'limits': ['First appearance is in these sampled days, not the first transaction of an operator or on the whole chain.',
                   'Signer clusters are declared addresses, not independently identified humans/operators.',
                   'First-appearance analysis is exploratory and has fewer failures than the primary cold-history group.']}
    identity_path = folder / f'transaction_identity_predictions_{args.cohort}.parquet'
    if identity_path.exists():
        identity = pd.read_parquet(identity_path).merge(
            frame[['signature', 'first_appearance']], on='signature', validate='one_to_one')
        identity_first = identity[identity.first_appearance]
        output['first_appearance_identity_hour_bootstrap'] = bootstrap_comparison(
            identity_first.label.to_numpy(), identity_first.readonly_identity_hgb.to_numpy(),
            identity_first.context_identity_hgb.to_numpy(), identity_first.decision_ts.to_numpy())
        identity_report = json.loads((ROOT / f'docs/results/solana_transaction_identity_{args.cohort}.json').read_text())
        identity_thresholds = {r['model']: r['threshold'] for r in identity_report['results']}
        output['first_appearance_identity_results'] = {
            name: metrics(identity_first.label.to_numpy(), identity_first[name].to_numpy(), identity_thresholds[name])
            for name in ['readonly_identity_hgb', 'context_identity_hgb']}
    if 'refined_primary' in protocol:
        if 'first_appearance_identity_hour_bootstrap' not in output:
            raise ValueError('Refined primary identity predictions are required')
        output['status'] = 'First-appearance identity comparison specified in protocol before this cohort outcomes'
        delta = output['first_appearance_identity_hour_bootstrap']
        output['refined_primary'] = protocol['refined_primary']
        output['refined_success'] = delta['weighted_delta'] > 0 and delta['ci95'][0] > 0
        output['limits'][-1] = 'Refined endpoint specified before this cohort; previous first-appearance diagnostics are exploratory.'
    path = ROOT / f'docs/results/solana_transaction_audit_{args.cohort}.json'
    path.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output, indent=2), flush=True)


if __name__ == '__main__':
    main()
