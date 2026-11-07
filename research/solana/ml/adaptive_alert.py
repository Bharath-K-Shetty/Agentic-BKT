"""Self-adjusting alarm: flag a transaction when its score is in the top q of recent scores.

The cut-off is the (1-q) quantile of the scores of the previous W first-appearance
transactions with a strictly earlier timestamp. Only scores are used, never
outcomes, so the rule is available in real time and follows day-to-day shifts.
Before W earlier scores exist, the transaction is scored against whatever
earlier scores are available (none: not flagged).

Development mode uses the saved identity-controlled predictions of already
inspected test days. Fresh mode is reserved for a protocol-fixed, never-used window.

    .venv/bin/python research/solana/ml/adaptive_alert.py            # development
    .venv/bin/python research/solana/ml/adaptive_alert.py --fresh research/solana/ml/adaptive_alert_protocol.json
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import bisect
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import recall_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prefix_baseline import ROOT  # noqa: E402
from robustness import paired_period_bootstrap  # noqa: E402

FOLDER = ROOT / 'data/processed/solana_ml'
MODELS = {'baseline': 'readonly_identity_hgb', 'homie': 'context_identity_hgb'}
DEVELOPMENT = {'prospective': 'Dec 1', 'fresh': 'Dec 5', 'third': 'Nov 28', 'fourth': 'Nov 21'}
GRID = [(q, w) for q in (.02, .05, .10) for w in (500, 2000)]


def first_appearance_test(cohort):
    risk = json.loads((ROOT / f'docs/results/solana_transaction_risk_{cohort}.json').read_text())
    features = pd.read_parquet(FOLDER / f'transaction_features_{cohort}.parquet', columns=['signature'])
    payers = {}
    for src in risk['sources']:
        for batch in pq.ParquetFile(ROOT / src['path']).iter_batches(columns=['signature', 'accounts'], batch_size=8192):
            for row in batch.to_pylist():
                payers[row['signature']] = row['accounts'][0]['pubkey']
    first = pd.DataFrame({'signature': features.signature, 'first': ~features.signature.map(payers).duplicated()})
    saved = pd.read_parquet(FOLDER / f'transaction_identity_predictions_{cohort}.parquet').merge(first, on='signature', validate='one_to_one')
    return saved[saved['first']].sort_values(['decision_ts', 'signature'], kind='stable').reset_index(drop=True)


def rolling_flags(times, scores, q, window):
    """Flag when the score reaches the (1-q) quantile of the previous `window` scores with earlier timestamps."""
    recent, ordered, flags = deque(), [], np.zeros(len(scores), dtype=int)
    staged, i = deque(), 0
    for idx, (t, s) in enumerate(zip(times, scores)):
        while staged and staged[0][0] < t:
            _, value = staged.popleft()
            recent.append(value)
            bisect.insort(ordered, value)
            if len(recent) > window:
                ordered.pop(bisect.bisect_left(ordered, recent.popleft()))
        if ordered:
            cut = ordered[min(len(ordered) - 1, int(np.floor((1 - q) * len(ordered))))]
            flags[idx] = int(s >= cut)
        staged.append((t, s))
    return flags


def summarize(y, flags):
    tp = int((flags & (y == 1)).sum()); fp = int((flags & (y == 0)).sum())
    fn = int(((1 - flags) & (y == 1)).sum()); tn = int(((1 - flags) & (y == 0)).sum())
    recall, fpr = tp / (tp + fn), fp / (fp + tn)
    return {'flag_rate': (tp + fp) / len(y), 'tp': tp, 'fp': fp, 'recall': recall, 'fpr': fpr,
            'precision': tp / (tp + fp) if tp + fp else None, 'accuracy': (tp + tn) / len(y),
            'balanced_accuracy': (recall + 1 - fpr) / 2}


def evaluate(frame, q, window):
    y, times = frame.label.to_numpy(), frame.decision_ts.to_numpy()
    flags = {k: rolling_flags(times, frame[m].to_numpy(), q, window) for k, m in MODELS.items()}
    gap = paired_period_bootstrap([{'y': y, 'base': flags['baseline'], 'coord': flags['homie'], 'days': times // 3600}],
                                  lambda yy, ff: recall_score(yy, ff, zero_division=0))
    return {'q': q, 'window': window, 'n': len(y), 'failures': int(y.sum()),
            'models': {k: summarize(y, f) for k, f in flags.items()}, 'recall_gap_homie_minus_baseline': gap}


def development():
    frames = {c: first_appearance_test(c) for c in DEVELOPMENT}
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'mode': 'Development on already-inspected test days; not a confirmation.', 'results': []}
    for q, window in GRID:
        rows = {DEVELOPMENT[c]: evaluate(f, q, window) for c, f in frames.items()}
        report['results'].append({'q': q, 'window': window, 'days': rows})
        line = ' | '.join(f"{d}: rate {r['models']['homie']['flag_rate']:.3f} fpr B/H {r['models']['baseline']['fpr']:.3f}/{r['models']['homie']['fpr']:.3f} "
                          f"recall B/H {r['models']['baseline']['recall']:.3f}/{r['models']['homie']['recall']:.3f} gap {r['recall_gap_homie_minus_baseline']['weighted_delta']:+.3f} "
                          f"[{r['recall_gap_homie_minus_baseline']['ci95'][0]:+.3f},{r['recall_gap_homie_minus_baseline']['ci95'][1]:+.3f}]"
                          for d, r in rows.items())
        print(f'q={q:.2f} W={window}: {line}', flush=True)
    report['code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (ROOT / 'docs/results/solana_adaptive_alert_development.json').write_text(json.dumps(report, indent=2) + '\n')


def fresh(path):
    protocol = json.loads(path.read_text())
    output = ROOT / f"docs/results/solana_adaptive_alert_fresh_{protocol['cohort']}.json"
    if output.exists():
        raise SystemExit(f'{output} exists: the fresh evaluation runs once.')
    result = evaluate(first_appearance_test(protocol['cohort']), protocol['q'], protocol['window'])
    result.update({'protocol': protocol, 'protocol_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'created_at': datetime.now(timezone.utc).isoformat()})
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k in ('models', 'recall_gap_homie_minus_baseline')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', type=Path)
    args = parser.parse_args()
    fresh(args.fresh.resolve()) if args.fresh else development()
