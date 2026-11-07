"""Upgrade features: recent activity, network conditions and declared fees.

The existing ParticipationHistory uses outcomes that matured at least one hour
earlier. This extension adds three groups, all computable before sending:

* activity_: counts of earlier *included* transactions in short windows (60 s,
  10 min) for the fee payer, its writable accounts (crowding), its read-only
  program template and the sampled network, plus the network failure rate over
  outcomes that matured in the last hour. Inclusion counts need no outcomes.
* fee_: the transaction's declared priority fee, and how it compares with
  priority fees of transactions included in the previous 60 s. On Solana the
  charged fee is set before execution by the transaction's own compute-unit
  price and requested limit; it does not depend on success or consumed compute.

Only transactions with a strictly earlier timestamp enter activity or fee
context, so same-second ordering inside a block cannot leak. Counts come from
the sampled archive, not the full chain. No status, error, consumed compute,
balance or block position is read as an input.

Development (default) trains on each protocol's training date and scores its
validation date only; test dates are never loaded:

    .venv/bin/python research/solana/ml/activity_features.py

Fresh mode runs a frozen protocol once on its own train/validation/test dates:

    .venv/bin/python research/solana/ml/activity_features.py --fresh research/solana/ml/activity_fresh_protocol.json
"""
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import heapq
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import transaction_risk as tr  # noqa: E402
from prefix_baseline import ROOT  # noqa: E402
from robustness import paired_period_bootstrap  # noqa: E402

WINDOWS = (60, 600)
ROLES = ('payer', 'writable', 'template')
BASE_FEE_PER_SIGNATURE = 5000
DEVELOPMENT = ['transaction_protocol.json', 'transaction_confirmation_protocol.json',
               'transaction_extension_protocol.json', 'transaction_prospective_protocol.json',
               'transaction_fresh_protocol.json']
COMPARISONS = ['homie_activity', 'homie_fee', 'homie_all']


class ActivityHistory(tr.ParticipationHistory):
    def __init__(self, delay=3600, strength=20):
        super().__init__(delay, strength)
        self.staged = deque()
        self.windows = {w: (deque(), {r: Counter() for r in ROLES}) for w in WINDOWS}
        self.ever = Counter()
        self.matured = deque()
        self.matured_failures = 0
        self._priority = None

    def advance(self, now):
        """Parent logic, also keeping outcomes that matured within the last hour."""
        if now < self.last_time:
            raise ValueError('Replay must be chronological')
        self.last_time = now
        while self.pending and self.pending[0][0] <= now:
            matured_at, _, roles, label = heapq.heappop(self.pending)
            self.total += 1
            self.failures += label
            for role, keys in roles.items():
                for key in keys:
                    counts = self.stats[role][key]
                    counts[0] += 1
                    counts[1] += label
            self.matured.append((matured_at, label))
            self.matured_failures += label
        while self.matured and self.matured[0][0] < now - 3600:
            self.matured_failures -= self.matured.popleft()[1]

    def _advance_activity(self, now):
        while self.staged and self.staged[0][0] < now:
            item = self.staged.popleft()
            self.ever[item[1]] += 1
            for queue, counts in self.windows.values():
                queue.append(item)
                for role, key in zip(ROLES, item[2:5]):
                    for k in key:
                        counts[role][k] += 1
        for width, (queue, counts) in self.windows.items():
            while queue and queue[0][0] < now - width:
                item = queue.popleft()
                for role, key in zip(ROLES, item[2:5]):
                    for k in key:
                        counts[role][k] -= 1
                        if not counts[role][k]:
                            del counts[role][k]

    def features(self, accounts, now, fee=None):
        f, cold, roles = super().features(accounts, now)
        self._advance_activity(now)
        payer, = roles['payer']
        template, = roles['template']
        writable = roles['writable']
        for width, (queue, counts) in self.windows.items():
            f[f'activity_payer_{width}'] = float(np.log1p(counts['payer'][payer]))
            values = [counts['writable'][k] for k in writable] or [0]
            f[f'activity_writable_max_{width}'] = float(np.log1p(max(values)))
            f[f'activity_writable_mean_{width}'] = float(np.mean(np.log1p(values)))
            f[f'activity_template_{width}'] = float(np.log1p(counts['template'][template]))
            f[f'activity_network_{width}'] = float(np.log1p(len(queue)))
        f['activity_payer_ever'] = float(np.log1p(self.ever[payer]))
        f['activity_network_failure_rate_1h'] = (self.matured_failures + 1) / (len(self.matured) + 2)
        f['meta_first_appearance'] = int(self.ever[payer] == 0)
        f['meta_payer'] = payer
        self._priority = None
        if fee is not None:
            priority = max(0, int(fee) - BASE_FEE_PER_SIGNATURE * f['structure_signer_count'])
            recent = [item[5] for item in self.windows[60][0] if item[5] is not None]
            median = float(np.median(recent)) if recent else 0.
            f['fee_priority_log'] = float(np.log1p(priority))
            f['fee_has_priority'] = int(priority > 0)
            f['fee_network_median_60'] = float(np.log1p(median))
            f['fee_vs_network_60'] = f['fee_priority_log'] - f['fee_network_median_60']
            f['fee_rank_60'] = float(np.mean(np.asarray(recent) < priority)) if recent else .5
            self._priority = priority
        return f, cold, roles

    def schedule(self, roles, label, now):
        super().schedule(roles, label, now)
        payer, = roles['payer']
        template, = roles['template']
        self.staged.append((now, payer, (payer,), tuple(roles['writable']), (template,), self._priority))


def fee_lookup(path):
    """Declared fee by signature from the companion file, if it has been fetched."""
    stem = path.name.replace('archive_preview_', 'archive_fee_')
    fee_file = path.with_name(stem)
    if not fee_file.exists():
        return None
    table = pq.read_table(fee_file, columns=['signature', 'fee']).to_pydict()
    return dict(zip(table['signature'], table['fee']))


def build_features(dates, protocol, use_fees):
    """transaction_risk.build_features with the same cleaning, plus optional declared fees."""
    history = ActivityHistory(protocol['outcome_delay_seconds'], protocol['prior_strength'])
    records, sources, skipped, seen = [], [], defaultdict(int), {}
    for date in dates:
        path = ROOT / protocol.get('source_paths', {}).get(date, f'data/raw/novelty_search/archive_preview_{date}.parquet')
        fees = fee_lookup(path) if use_fees else None
        if use_fees and fees is None:
            raise SystemExit(f'Missing fee column for {date}: run fetch_fee_column.py')
        rows = pq.read_table(path).to_pylist()
        rows.sort(key=lambda r: (r['block_timestamp'], r['block_slot'], r['signature']))
        for row in rows:
            payload_hash = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).digest()
            if row['signature'] in seen:
                if seen[row['signature']] != payload_hash:
                    raise ValueError('Conflicting duplicate transaction')
                skipped['identical_duplicate_transaction'] += 1
                continue
            seen[row['signature']] = payload_hash
            if row['block_timestamp'].strftime('%Y-%m-%d') != date:
                raise ValueError('Partition date mismatch')
            if row['status'] not in ('Success', 'Fail'):
                raise ValueError(f"Unrecognized source status: {row['status']}")
            ts = int(row['block_timestamp'].replace(tzinfo=timezone.utc).timestamp())
            fee = fees.get(row['signature']) if fees is not None else None
            if fees is not None and fee is None:
                raise ValueError('Fee missing for a sampled transaction')
            try:
                f, cold, roles = history.features(row['accounts'], ts, fee)
            except ValueError as error:
                if str(error) != 'Missing first declared signer':
                    raise
                skipped[str(error)] += 1
                continue
            label = int(row['status'] == 'Fail')
            records.append({'signature': row['signature'], 'date': date, 'decision_ts': ts,
                            'label': label, 'cold_payer': cold, **f})
            history.schedule(roles, label, ts)
        sources.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'n': len(rows)})
        print('features', date, len(rows), flush=True)
    return pd.DataFrame(records), sources, dict(skipped)


def model_inputs(columns):
    base = [c for c in columns if c.startswith(('structure_', 'payer_', 'readonly_', 'template_'))]
    writable = [c for c in columns if c.startswith('writable_')]
    activity = [c for c in columns if c.startswith('activity_')]
    fee = [c for c in columns if c.startswith('fee_')]
    models = {'baseline': base, 'homie': base + writable, 'homie_activity': base + writable + activity}
    if fee:
        models.update({'homie_fee': base + writable + fee, 'homie_all': base + writable + activity + fee,
                       'baseline_all': base + activity + fee})
    return models


def day_start(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def score(y, p):
    if len(y) < 50 or len(np.unique(y)) < 2:
        return None
    return {'n': int(len(y)), 'failures': int(y.sum()), 'prevalence': float(y.mean()),
            'ap': float(average_precision_score(y, p)), 'auroc': float(roc_auc_score(y, p))}


def evaluate(protocol, dates, seeds, use_fees):
    """Train on dates[0]; return scored frame for the final date."""
    frame, sources, skipped = build_features(dates, protocol, use_fees)
    train = frame[frame.date.eq(dates[0]) & ((frame.decision_ts - frame.decision_ts.min()) >= protocol['warmup_hours'] * 3600)]
    train = train[train.decision_ts + protocol['outcome_delay_seconds'] < day_start(dates[1])]
    target = frame[frame.date.eq(dates[-1])].copy()
    if len(dates) == 2:
        nxt = (datetime.fromisoformat(dates[-1]) + timedelta(days=1)).strftime('%Y-%m-%d')
        target = target[target.decision_ts + protocol['outcome_delay_seconds'] < day_start(nxt)]
    inputs = model_inputs(frame.columns)
    for name, cols in inputs.items():
        probs = []
        for seed in seeds:
            model = HistGradientBoostingClassifier(**protocol['hgb'], random_state=seed)
            model.fit(train[cols], train.label)
            probs.append(model.predict_proba(target[cols])[:, 1])
        target[name] = np.mean(probs, axis=0)
    return target, inputs, sources, len(train), skipped


def summarize(target, inputs):
    y = target.label.to_numpy()
    groups = {'all': np.ones(len(target), bool), 'cold_history': target.cold_payer.to_numpy(),
              'first_appearance': target.meta_first_appearance.to_numpy().astype(bool)}
    out = {}
    for group, mask in groups.items():
        out[group] = {'models': {name: score(y[mask], target[name].to_numpy()[mask]) for name in inputs}, 'vs_homie': {}}
        if len(np.unique(y[mask])) < 2:
            continue
        for candidate in COMPARISONS:
            if candidate in inputs:
                data = [{'y': y[mask], 'base': target.homie.to_numpy()[mask], 'coord': target[candidate].to_numpy()[mask],
                         'days': target.decision_ts.to_numpy()[mask] // 3600}]
                out[group]['vs_homie'][candidate] = paired_period_bootstrap(data, average_precision_score)
        if 'meta_payer' in target:
            # Concentration check: does the gain survive without the fee payer that has the most failures?
            payers = target.meta_payer.to_numpy()[mask]
            failing = Counter(payers[y[mask] == 1])
            top, count = failing.most_common(1)[0]
            keep = payers != top
            out[group]['concentration'] = {'top_failing_payer_share_of_failures': count / int(y[mask].sum()),
                'without_top_payer': {c: float(average_precision_score(y[mask][keep], target[c].to_numpy()[mask][keep])
                                               - average_precision_score(y[mask][keep], target.homie.to_numpy()[mask][keep]))
                                      for c in COMPARISONS if c in inputs}}
    return out


def development(use_fees):
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'fees_used': use_fees,
              'mode': 'Development on validation dates only. Test dates were not loaded.',
              'seeds': [42], 'windows_seconds': list(WINDOWS), 'cohorts': []}
    for name in DEVELOPMENT:
        protocol = json.loads((HERE / name).read_text())
        dates = [protocol['train_date'], protocol['validation_date']]
        started = time.monotonic()
        target, inputs, sources, n_train, skipped = evaluate(protocol, dates, [42], use_fees)
        result = {'protocol': name, 'train_date': dates[0], 'validation_date': dates[1], 'train_n': n_train,
                  'validation_n': len(target), 'skipped': skipped, 'results': summarize(target, inputs),
                  'seconds': round(time.monotonic() - started, 1)}
        report['cohorts'].append(result)
        for group in ('cold_history', 'first_appearance'):
            models = result['results'][group]['models']
            print(name, group, {k: round(v['ap'], 4) for k, v in models.items() if v}, flush=True)
    report['code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = ROOT / f"docs/results/solana_activity_development{'_fees' if use_fees else ''}.json"
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(out)


def fresh(path):
    protocol_bytes = path.read_bytes()
    protocol = json.loads(protocol_bytes)
    dates = [protocol['train_date'], protocol['validation_date'], protocol['test_date']]
    output = ROOT / f"docs/results/solana_activity_fresh_{protocol['test_date']}.json"
    if output.exists():
        raise SystemExit(f'{output} exists: the fresh test runs once.')
    target, inputs, sources, n_train, skipped = evaluate(protocol, dates, protocol['seeds'], protocol['use_fees'])
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'protocol': protocol,
              'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(), 'sources': sources, 'skipped': skipped,
              'train_n': n_train, 'test_n': len(target), 'results': summarize(target, inputs),
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.write_text(json.dumps(report, indent=2) + '\n')
    keep = ['signature', 'decision_ts', 'label', 'cold_payer', 'meta_first_appearance', 'meta_payer', *inputs]
    target[keep].to_parquet(ROOT / f"data/processed/solana_ml/activity_fresh_predictions_{protocol['test_date']}.parquet", index=False)
    print(json.dumps(report['results'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', type=Path)
    parser.add_argument('--fees', action='store_true', help='include declared-fee features (needs fetch_fee_column.py)')
    args = parser.parse_args()
    fresh(args.fresh.resolve()) if args.fresh else development(args.fees)
