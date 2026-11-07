"""Measure actual on-chain fees for the riskiest-ranked transactions and all failures.

Read-only: fetches public receipts for the held-out cold-history sample of the
exported demo model. The result is the fee paid by transactions HOMIE ranked as
risky. It is money at stake, not money saved: no warning was shown to the senders.

    .venv/bin/python research/solana/fee_proof/measure_failure_fees.py

Reruns resume from the cache and retry anything not yet retrieved.
"""
import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from webapp.backend.model_inference import artifacts  # noqa: E402

RPC = 'https://api.mainnet-beta.solana.com'
CACHE = ROOT / 'data/processed/solana_ml/failure_fees.jsonl'
OUTPUT = ROOT / 'docs/results/solana_failure_fee_measurement.json'
BASE_FEE_PER_SIGNATURE = 5000
LAMPORTS_PER_SOL = 1_000_000_000


def targets():
    """Return (signature, recorded label, in riskiest 5%) in rank order."""
    saved, frame = artifacts()
    sample = frame[frame.cold_payer]
    artifact = saved['models']['context_hgb']
    raw = artifact['model'].predict_proba(sample[artifact['inputs']])[:, 1]
    ranked = sample.iloc[np.argsort(-raw, kind='stable')]
    cutoff = len(ranked) * 5 // 100
    rows = [(sig, int(label), position < cutoff)
            for position, (sig, label) in enumerate(zip(ranked.index, ranked.label))]
    return [row for row in rows if row[2] or row[1]], len(ranked)


def fetch(session, signature, attempts=6):
    params = [signature, {'encoding': 'json', 'maxSupportedTransactionVersion': 1}]
    body = {'jsonrpc': '2.0', 'id': 1, 'method': 'getTransaction', 'params': params}
    for attempt in range(attempts):
        try:
            response = session.post(RPC, json=body, timeout=30)
            if response.status_code == 200:
                payload = response.json()
                if 'error' not in payload:
                    return payload.get('result')
        except (requests.RequestException, ValueError):
            pass
        time.sleep(min(60, 3 * 2 ** attempt))
    return None


def failing_program(result):
    """Name the program whose instruction failed, when the error identifies one."""
    err = result['meta']['err']
    if not (isinstance(err, dict) and 'InstructionError' in err):
        return None
    message = result['transaction']['message']
    loaded = result['meta'].get('loadedAddresses') or {}
    keys = message['accountKeys'] + loaded.get('writable', []) + loaded.get('readonly', [])
    index = err['InstructionError'][0]
    if index >= len(message['instructions']):
        return None
    return keys[message['instructions'][index]['programIdIndex']]


def record(signature, label, top, result):
    row = {'signature': signature, 'label': label, 'top_5': top, 'retrieved': result is not None}
    if result:
        fee = result['meta']['fee']
        signatures = len(result['transaction']['signatures'])
        row.update(fee=fee, signatures=signatures, slot=result['slot'],
                   payer=result['transaction']['message']['accountKeys'][0],
                   onchain_failed=result['meta']['err'] is not None,
                   program=failing_program(result),
                   above_base_fee=max(0, fee - BASE_FEE_PER_SIGNATURE * signatures))
    return row


def collect(rows, delay):
    known = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            saved = json.loads(line)
            if saved['retrieved']:
                known[saved['signature']] = saved
    pending = [row for row in rows if row[0] not in known]
    print(f'{len(known)} cached, {len(pending)} to fetch', flush=True)
    session = requests.Session()
    with CACHE.open('a') as cache:
        for count, (signature, label, top) in enumerate(pending, 1):
            row = record(signature, label, top, fetch(session, signature))
            cache.write(json.dumps(row) + '\n')
            cache.flush()
            if row['retrieved']:
                known[signature] = row
            if count % 100 == 0:
                print(f'{count}/{len(pending)}', flush=True)
            time.sleep(delay)
    return known


def fees(rows):
    values = [row['fee'] for row in rows]
    if not values:
        return {'transactions': 0}
    payers = Counter(row['payer'] for row in rows)
    programs = Counter(row['program'] for row in rows if row['program'])
    spend = Counter()
    for row in rows:
        spend[row['payer']] += row['fee']
    return {'transactions': len(values), 'total_lamports': sum(values),
            'total_sol': sum(values) / LAMPORTS_PER_SOL,
            'mean_lamports': statistics.fmean(values),
            'median_lamports': statistics.median(values),
            'max_lamports': max(values),
            'above_base_fee_lamports': sum(row['above_base_fee'] for row in rows),
            'unique_payers': len(payers),
            'largest_payer_share_of_transactions': payers.most_common(1)[0][1] / len(values),
            'largest_payer_share_of_fees': spend.most_common(1)[0][1] / sum(values) if sum(values) else None,
            'top_failing_programs': programs.most_common(5)}


def summarize(rows, known, sample_size):
    retrieved = [known[row[0]] for row in rows if row[0] in known]
    failures = [row for row in retrieved if row['label']]
    top = [row for row in retrieved if row['top_5']]
    top_failures = [row for row in top if row['label']]
    total = sum(row['fee'] for row in failures)
    by_program = Counter()
    for row in failures:
        by_program[row['program']] += row['fee']
    largest = by_program.most_common(1)[0][0] if by_program else None
    others = [row for row in failures if row['program'] != largest]
    others_total = sum(row['fee'] for row in others)
    wanted = {'all_targets': len(rows), 'all_failures': sum(1 for row in rows if row[1]),
              'top_5': sum(1 for row in rows if row[2])}
    return {
        'status': 'Measured on-chain fees. Money at stake, not money saved: no warning reached these senders.',
        'test_date': artifacts()[0]['test_date'], 'model': 'context_hgb', 'sample_size': sample_size,
        'requested': wanted, 'retrieved': len(retrieved),
        'label_mismatches': sum(row['label'] != int(row['onchain_failed']) for row in retrieved),
        'all_failures': fees(failures), 'top_5_failures': fees(top_failures),
        'top_5_successes': fees([row for row in top if not row['label']]),
        'top_5_share_of_failed_fees': sum(row['fee'] for row in top_failures) / total if total else None,
        'random_5_percent_share_for_comparison': .05,
        'largest_program_by_failed_fees': largest,
        'top_5_share_excluding_largest_program':
            sum(row['fee'] for row in others if row['top_5']) / others_total if others_total else None,
        'limitations': ['Fees only: separately paid validator tips and lost trade value are not included.',
                        'One test date from one sampled archive.',
                        'Standard preflight may have caught some failures, so this is not an incremental saving.',
                        'Warnings on the successful transactions in this group have a cost that is not priced here.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int)
    parser.add_argument('--delay', type=float, default=1.0)
    args = parser.parse_args()
    rows, sample_size = targets()
    known = collect(rows[:args.limit] if args.limit else rows, args.delay)
    report = summarize(rows, known, sample_size)
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
