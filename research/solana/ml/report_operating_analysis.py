"""Descriptive follow-up on frozen first-appearance identity predictions.

Budgets and coverage bins are fixed here before inspecting this analysis.
No refitting, calibration, or deployment-threshold selection is performed.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / 'output/latex/homie_report/assets'
BUDGETS = (0.01, 0.05, 0.10)
MODELS = ('readonly_identity_hgb', 'context_identity_hgb')

def main():
    output = {'status': 'Post-result descriptive analysis of existing test sets',
              'budgets': BUDGETS, 'ranking': 'Descending score; ties by ascending signature',
              'coverage_bins': ['No eligible accounts', 'Eligible but unseen (0%)', 'Limited (0%, 50%]', 'Higher (50%, 100%]'],
              'files': {}, 'cohorts': {}}
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.3))
    fig2, axes2 = plt.subplots(1, 2, figsize=(8, 3.5))
    for ci, cohort in enumerate(('prospective', 'fresh')):
        def read(name):
            path = ROOT / name
            output['files'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
            return path
        report = json.loads(read(f'docs/results/solana_transaction_risk_{cohort}.json').read_text())
        audit = json.loads(read(f'docs/results/solana_transaction_audit_{cohort}.json').read_text())
        f = pd.read_parquet(read(f'data/processed/solana_ml/transaction_features_{cohort}.parquet'))
        payer = {}
        for src in report['sources']:
            path = read(src['path'])
            for batch in pq.ParquetFile(path).iter_batches(columns=['signature', 'accounts'], batch_size=8192):
                payer.update({r['signature']: r['accounts'][0]['pubkey'] for r in batch.to_pylist()})
        signers = f.signature.map(payer)
        assert signers.notna().all() and f.signature.is_unique
        assert f.decision_ts.is_monotonic_increasing
        f['first_appearance'] = ~signers.duplicated()
        p = pd.read_parquet(read(f'data/processed/solana_ml/transaction_identity_predictions_{cohort}.parquet'))
        p = p.merge(f[['signature','first_appearance','writable_seen_fraction','structure_nonpayer_writable_count']], on='signature', validate='one_to_one')
        p = p[p.first_appearance].copy()
        assert len(p) == audit['first_appearance_n']
        assert p[list(MODELS)].notna().all().all()
        for m in MODELS:
            assert abs(average_precision_score(p.label, p[m])-audit['first_appearance_identity_results'][m]['ap_positive']) < 1e-12
        n, failures = len(p), int(p.label.sum())
        result = {'date': report['protocol']['test_date'], 'n': n, 'failures': failures, 'budgets': [], 'coverage': []}
        for fraction in BUDGETS:
            k = max(1, int(np.floor(n*fraction)))
            row = {'fraction': fraction, 'k': k, 'models': {}}
            for m in MODELS:
                ranked = p.sort_values([m, 'signature'], ascending=[False, True], kind='stable')
                top = ranked.iloc[:k]
                tp = int(top.label.sum())
                boundary = float(top[m].iloc[-1])
                above = p[p[m].gt(boundary)]
                tied = p[p[m].eq(boundary)]
                slots = k-len(above)
                lo = int(above.label.sum()) + max(0, slots-int((tied.label == 0).sum()))
                hi = int(above.label.sum()) + min(slots, int(tied.label.sum()))
                row['models'][m] = {'tp': tp, 'fp': k-tp, 'precision': tp/k, 'recall': tp/failures,
                                    'tp_range_over_boundary_ties': [lo, hi],
                                    'boundary_score': boundary, 'boundary_tie_size': int(p[m].eq(boundary).sum())}
            result['budgets'].append(row)
        cov = p.writable_seen_fraction
        assert cov.between(0,1).all()
        eligible = p.structure_nonpayer_writable_count.gt(0)
        masks = [~eligible, eligible & cov.eq(0), eligible & cov.gt(0) & cov.le(.5), eligible & cov.gt(.5)]
        assert sum(int(m.sum()) for m in masks) == n
        for label, mask in zip(output['coverage_bins'], masks):
            g = p[mask]
            row = {'group': label, 'n': len(g), 'failures': int(g.label.sum()),
                   'prevalence': float(g.label.mean()) if len(g) else None, 'ap': {}}
            for m in MODELS:
                row['ap'][m] = float(average_precision_score(g.label, g[m])) if g.label.nunique() == 2 else None
            row['delta_ap'] = row['ap'][MODELS[1]]-row['ap'][MODELS[0]] if all(v is not None for v in row['ap'].values()) else None
            result['coverage'].append(row)
        assert sum(r['failures'] for r in result['coverage']) == failures
        output['cohorts'][cohort] = result
        ax = axes[ci]
        for m, name, col in zip(MODELS, ['Baseline','Writable context'], ['#74839a','#19765b']):
            ax.plot([100*b for b in BUDGETS], [100*r['models'][m]['recall'] for r in result['budgets']], 'o-', label=name, color=col)
        ax.set(title=result['date'], xlabel='Reviewed fraction of test set (%)', ylabel='Failures captured (%)', xticks=[1,5,10], ylim=(0,100))
        ax.grid(axis='y', alpha=.2);ax.legend(fontsize=8)
        ax = axes2[ci]
        x = np.arange(4)
        for j,(m,name,col) in enumerate(zip(MODELS,['Baseline','Writable context'],['#74839a','#19765b'])):
            values=[r['ap'][m] if r['ap'][m] is not None else np.nan for r in result['coverage']]
            ax.bar(x+(j-.5)*.32, values, .32, label=name, color=col)
        ax.set(title=result['date'], ylabel='Average precision', xticks=x, xticklabels=['No eligible','Unseen','0–50%','>50%'])
        ax.tick_params(axis='x',labelsize=8);ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    for figure, name in [(fig,'review_budget'),(fig2,'coverage_ap')]:
        figure.tight_layout()
        figure.savefig(ASSETS/f'{name}.png', dpi=220)
        figure.savefig(ASSETS/f'{name}.pdf')
        plt.close(figure)
    dest = ROOT/'docs/results/solana_operating_followup.json'
    dest.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output['cohorts'],indent=2))

if __name__ == '__main__':
    main()
