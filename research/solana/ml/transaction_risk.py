"""Prospective-history features for included transaction failure screening.

No current execution metadata is read by the feature extractor. Histories are
sampled participation rates, not inferred ownership, real congestion or causes.
"""
from collections import defaultdict
import argparse
from datetime import datetime, timezone
import heapq
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

from prefix_baseline import ROOT, metrics, threshold_at_fpr
from robustness import paired_period_bootstrap

HERE = Path(__file__).resolve().parent
# These infrastructure accounts appear across unrelated transactions. Removing
# them from contextual history prevents a network-wide rate masquerading as a
# program-specific exposure. They are retained as static presence indicators.
INFRASTRUCTURE = {
    '11111111111111111111111111111111',
    'ComputeBudget111111111111111111111111111111',
    'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
    'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',
    'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',
    'AddressLookupTab1e1111111111111111111111111',
    'SysvarRent111111111111111111111111111111111',
    'SysvarC1ock11111111111111111111111111111111',
    'Sysvar1nstructions1111111111111111111111111',
    'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',
}


def declared_roles(accounts):
    if not accounts or not accounts[0]['signer']:
        raise ValueError('Missing first declared signer')
    payer = accounts[0]['pubkey']
    signers = {a['pubkey'] for a in accounts if a['signer']}
    writable = {a['pubkey'] for a in accounts if a['writable'] and not a['signer'] and a['pubkey'] not in INFRASTRUCTURE}
    readonly = {a['pubkey'] for a in accounts if not a['writable'] and not a['signer'] and a['pubkey'] not in INFRASTRUCTURE}
    return payer, signers, writable, readonly


class ParticipationHistory:
    def __init__(self, delay=3600, strength=20):
        self.delay, self.strength = delay, strength
        self.stats = {role: defaultdict(lambda: [0, 0]) for role in ['payer', 'writable', 'readonly', 'template']}
        self.pending = []
        self.total, self.failures, self.order, self.last_time = 0, 0, 0, -1

    def advance(self, now):
        if now < self.last_time:
            raise ValueError('Replay must be chronological')
        self.last_time = now
        while self.pending and self.pending[0][0] <= now:
            _, _, roles, label = heapq.heappop(self.pending)
            self.total += 1
            self.failures += label
            for role, keys in roles.items():
                for key in keys:
                    counts = self.stats[role][key]
                    counts[0] += 1
                    counts[1] += label

    def posterior(self, role, key):
        n, f = self.stats[role].get(key, [0, 0])
        base = (self.failures + 1) / (self.total + 2)
        return n, (f + self.strength * base) / (n + self.strength)

    def summarize(self, role, keys):
        values = [self.posterior(role, key) for key in keys]
        if not values:
            values = [(0, (self.failures+1)/(self.total+2))]
        n, rate = np.asarray(values).T
        return {f'{role}_seen_fraction': float(np.mean(n > 0)),
                f'{role}_log_count_mean': float(np.mean(np.log1p(n))),
                f'{role}_log_count_max': float(np.max(np.log1p(n))),
                f'{role}_risk_mean': float(np.mean(rate)), f'{role}_risk_max': float(np.max(rate)),
                f'{role}_risk_min': float(np.min(rate)), f'{role}_risk_std': float(np.std(rate))}

    def features(self, accounts, now):
        """Only accounts and checkpoint time are accepted, never current status."""
        self.advance(now)
        payer, signers, writable, readonly = declared_roles(accounts)
        template = tuple(sorted(readonly))
        n, risk = self.posterior('payer', payer)
        tn, trisk = self.posterior('template', template)
        f = {'structure_account_count': len(accounts), 'structure_signer_count': len(signers),
             'structure_writable_count': sum(a['writable'] for a in accounts),
             'structure_nonpayer_writable_count': len(writable), 'structure_readonly_count': len(readonly),
             'structure_duplicate_count': len(accounts) - len({a['pubkey'] for a in accounts}),
             'payer_risk': risk, 'payer_log_count': float(np.log1p(n)),
             'template_risk': trisk, 'template_log_count': float(np.log1p(tn))}
        keys = {a['pubkey'] for a in accounts}
        f.update({f'structure_infra_{i}': int(key in keys) for i, key in enumerate(sorted(INFRASTRUCTURE))})
        f.update(self.summarize('readonly', readonly))
        f.update(self.summarize('writable', writable))
        roles = {'payer': {payer}, 'readonly': readonly, 'writable': writable, 'template': {template}}
        return f, n == 0, roles

    def schedule(self, roles, label, now):
        if label not in (0, 1):
            raise ValueError('Unknown execution status')
        heapq.heappush(self.pending, (now + self.delay, self.order, roles, label))
        self.order += 1


def build_features(dates, protocol):
    history = ParticipationHistory(protocol['outcome_delay_seconds'], protocol['prior_strength'])
    records, sources, skipped = [], [], defaultdict(int)
    seen_signatures = {}
    for date in dates:
        path = ROOT / protocol.get('source_paths', {}).get(date, f'data/raw/novelty_search/archive_preview_{date}.parquet')
        rows = pq.read_table(path).to_pylist()
        rows.sort(key=lambda r: (r['block_timestamp'], r['block_slot'], r['signature']))
        for row in rows:
            payload_hash = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).digest()
            if row['signature'] in seen_signatures:
                if seen_signatures[row['signature']] != payload_hash:
                    raise ValueError('Conflicting duplicate transaction')
                skipped['identical_duplicate_transaction'] += 1
                continue
            seen_signatures[row['signature']] = payload_hash
            if row['block_timestamp'].strftime('%Y-%m-%d') != date:
                raise ValueError('Partition date mismatch')
            status = row['status']
            if status not in ('Success', 'Fail'):
                raise ValueError(f'Unrecognized source status: {status}')
            ts = int(row['block_timestamp'].replace(tzinfo=timezone.utc).timestamp())
            try:
                f, cold, roles = history.features(row['accounts'], ts)
            except ValueError as error:
                if str(error) != 'Missing first declared signer':
                    raise
                skipped[str(error)] += 1
                continue
            label = int(status == 'Fail')
            records.append({'signature': row['signature'], 'date': date, 'decision_ts': ts,
                            'label': label, 'cold_payer': cold, **f})
            history.schedule(roles, label, ts)
        sources.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'n': len(rows), 'first_ts': str(rows[0]['block_timestamp']), 'last_ts': str(rows[-1]['block_timestamp'])})
        print('features', date, len(rows), 'observed_accounts', {role: len(counts) for role, counts in history.stats.items()}, flush=True)
    frame = pd.DataFrame(records)
    return frame, sources, dict(skipped)


def bootstrap_comparison(y, a, b, times):
    if len(y) < 100 or len(np.unique(y)) < 2:
        return None
    return paired_period_bootstrap([{'y': y, 'base': a, 'coord': b, 'days': times // 3600}], average_precision_score)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', type=Path, default=HERE / 'transaction_protocol.json')
    parser.add_argument('--output-name', default='pilot')
    args = parser.parse_args()
    protocol_path = args.protocol.resolve()
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    started = time.monotonic()
    dates = [protocol[k] for k in ['train_date', 'validation_date', 'test_date']]
    frame, sources, skipped = build_features(dates, protocol)
    train = frame[frame.date.eq(dates[0]) & ((frame.decision_ts - frame.decision_ts.min()) >= protocol['warmup_hours']*3600)]
    boundary = int(datetime.fromisoformat(dates[1]).replace(tzinfo=timezone.utc).timestamp())
    train = train[train.decision_ts + protocol['outcome_delay_seconds'] < boundary]
    val = frame[frame.date.eq(dates[1])].copy()
    test = frame[frame.date.eq(dates[2])].copy()
    test_start = int(datetime.fromisoformat(dates[2]).replace(tzinfo=timezone.utc).timestamp())
    val = val[val.decision_ts + protocol['outcome_delay_seconds'] < test_start]
    cols = sorted(set(frame) - {'signature', 'date', 'decision_ts', 'label', 'cold_payer'})
    predictions = {}
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'protocol': protocol,
              'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(), 'sources': sources,
              'skipped': skipped, 'partition_counts': {}, 'results': [], 'comparisons': [],
              'limitations': ['One shard row group per day, not complete or verified random chain samples.',
                 'Conditional on inclusion; unlanded attempts and actual submission times absent.',
                 'Role participation is not causal attribution, ownership or account contention.',
                 'Historical outcomes assumed available after one hour; no current post-execution features.',
                 'Test-time history updates use earlier matured test labels; explicitly online, not frozen evaluation.',
                 'Cold first signer means unseen in sampled matured history, not a new operator.',
                 'Ordinary history aggregation and boosting; empirical contribution candidate, not a new algorithm.']}
    for name, part in [('train', train), ('validation', val), ('test', test)]:
        report['partition_counts'][name] = {'n': len(part), 'prevalence': float(part.label.mean()), 'cold_payer_n': int(part.cold_payer.sum())}
    for name in protocol['models']:
        if name.endswith('_history'):
            key = {'payer_history': 'payer_risk', 'readonly_history': 'readonly_risk_mean', 'template_history': 'template_risk'}[name]
            pv, pt = val[key].to_numpy(), test[key].to_numpy()
        else:
            inputs = [c for c in cols if c.startswith('structure_') or name == 'context_hgb'
                or name == 'payer_structural_hgb' and c.startswith('payer_')
                or name == 'payer_readonly_hgb' and c.startswith(('payer_', 'readonly_', 'template_'))]
            pv_all, pt_all = [], []
            for seed in protocol['seeds']:
                model = HistGradientBoostingClassifier(**protocol['hgb'], random_state=seed)
                model.fit(train[inputs], train.label)
                pv_all.append(model.predict_proba(val[inputs])[:, 1])
                pt_all.append(model.predict_proba(test[inputs])[:, 1])
            pv, pt = np.mean(pv_all, axis=0), np.mean(pt_all, axis=0)
        threshold = threshold_at_fpr(val.label.to_numpy(), pv, protocol['budget'])
        predictions[name] = pt
        result = {'model': name, 'threshold': threshold, 'validation': metrics(val.label.to_numpy(), pv, threshold),
                  'test': metrics(test.label.to_numpy(), pt, threshold), 'subgroups': {}}
        for subgroup, mask in [('cold_payer', test.cold_payer.to_numpy()), ('seen_payer', ~test.cold_payer.to_numpy())]:
            if len(np.unique(test.label.to_numpy()[mask])) == 2:
                result['subgroups'][subgroup] = {'n': int(mask.sum()), 'prevalence': float(test.label.to_numpy()[mask].mean()),
                    **metrics(test.label.to_numpy()[mask], pt[mask], threshold)}
        report['results'].append(result)
        print('model', name, json.dumps(result['test']), 'cold', json.dumps(result['subgroups'].get('cold_payer')), flush=True)
    for group, mask in [('all', np.ones(len(test), dtype=bool)), ('cold_payer', test.cold_payer.to_numpy())]:
        delta = bootstrap_comparison(test.label.to_numpy()[mask], predictions['payer_readonly_hgb'][mask], predictions['context_hgb'][mask], test.decision_ts.to_numpy()[mask])
        report['comparisons'].append({'group': group, 'primary': group == 'cold_payer', 'base': 'payer_readonly_hgb', 'candidate': 'context_hgb', 'ap': delta})
    report['elapsed_seconds'] = time.monotonic() - started
    processed = ROOT / 'data/processed/solana_ml'
    frame.to_parquet(processed / f'transaction_features_{args.output_name}.parquet', index=False)
    saved = test[['signature', 'decision_ts', 'label', 'cold_payer']].copy()
    for name, probability in predictions.items():
        saved[name] = probability
    saved.to_parquet(processed / f'transaction_predictions_{args.output_name}.parquet', index=False)
    report['code_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [protocol_path, HERE / 'transaction_risk.py', HERE / 'archive_probe.py', HERE / 'prefix_baseline.py', HERE / 'robustness.py']}
    output = ROOT / f'docs/results/solana_transaction_risk_{args.output_name}.json'
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(output, flush=True)


if __name__ == '__main__':
    main()
