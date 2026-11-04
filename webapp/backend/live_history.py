"""Live, matured block-history features using the research feature extractor.

Sampling differs from the archive: scores are explicitly experimental, never a
validated probability or automatic transaction-blocking decision.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import joblib
import numpy as np
import pandas as pd

from webapp.backend.transfer_check import ReadOnlyRPC, SYSTEM
from webapp.backend.runtime_paths import state_directory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'research/solana/ml'))
from transaction_risk import ParticipationHistory


class HistoryRPC(ReadOnlyRPC):
    ALLOWED = ReadOnlyRPC.ALLOWED | {'getSlot','getBlockTime','getBlock','getBlocksWithLimit','getGenesisHash','getTransaction'}


def snapshot_path(network):
    return state_directory(ROOT)/f'live_history_{network}.json'


def block_records(block, slot):
    """Use declared parsed roles (including resolved lookup keys), not balances."""
    if not block or not isinstance(block.get('blockTime'), int):
        return []
    records = []
    for tx in block.get('transactions', []):
        meta = tx.get('meta')
        if not isinstance(meta, dict) or 'err' not in meta:
            continue
        message = tx.get('transaction', {}).get('message', {})
        accounts = message.get('accountKeys', [])
        if not accounts or not all(isinstance(a, dict) and isinstance(a.get('signer'), bool)
                and isinstance(a.get('writable'), bool) and isinstance(a.get('pubkey'), str) for a in accounts):
            continue
        signatures = tx['transaction'].get('signatures', [])
        if not signatures or not accounts[0]['signer']:
            continue
        records.append({'signature': signatures[0], 'block_slot': slot, 'ts': block['blockTime'],
                        'label': int(meta['err'] is not None),
                        'accounts': [{k:a[k] for k in ('pubkey','signer','writable')} for a in accounts]})
    return records


def collect_snapshot(network, blocks=16, rpc=None):
    if network not in ('devnet','mainnet') or not 8 <= blocks <= 64:
        raise ValueError('Choose devnet/mainnet and 8 to 64 sampled blocks.')
    rpc = rpc or HistoryRPC(network)
    started = int(time.time())
    tip = rpc.call('getSlot', [{'commitment':'confirmed'}])
    genesis = rpc.call('getGenesisHash', [])
    tip_time = rpc.call('getBlockTime',[tip])
    earlier_time = rpc.call('getBlockTime',[max(0,tip-10000)])
    if not isinstance(tip_time,int) or not isinstance(earlier_time,int) or tip_time<=earlier_time:
        raise ValueError('Cannot estimate a historical slot range from network timestamps.')
    slots_per_second = 10000/(tip_time-earlier_time)
    # Slot spacing is only a proposal; actual blockTime still enforces maturity.
    proposals = np.linspace(max(0, tip-10*3600*slots_per_second),
                            max(0,tip-2*3600*slots_per_second), blocks).astype(int)
    records = {}
    sampled, skipped = [], []
    for proposal in proposals:
        try:
            slots = rpc.call('getBlocksWithLimit', [int(proposal), 1, {'commitment':'confirmed'}])
            if not slots:
                continue
            slot = slots[0]
            time.sleep(.8)
            block = rpc.call('getBlock', [slot, {'encoding':'jsonParsed','transactionDetails':'full',
                'rewards':False,'maxSupportedTransactionVersion':1,'commitment':'confirmed'}])
            rows = block_records(block,slot)
            if not rows or rows[0]['ts']+3600 > started:
                skipped.append({'slot':slot,'reason':'Missing data or outcome not yet mature'})
                continue
            for row in rows:
                records[row['signature']] = row
            sampled.append({'slot':slot,'timestamp':rows[0]['ts'],'rows':len(rows)})
        except Exception as error:
            # Partial coverage stays explicit; never fill missing blocks with invented rows.
            skipped.append({'proposal':int(proposal),'reason':type(error).__name__})
        time.sleep(1.0)
    rows = sorted(records.values(), key=lambda r:(r['ts'],r['block_slot'],r['signature']))
    if not rows:
        raise ValueError('No mature blocks available. Existing snapshot was not replaced.')
    result = {'network':network,'genesis_hash':genesis,'collected_at_utc':datetime.now(timezone.utc).isoformat(),
              'collection_started_ts':started,'completed_ts':int(time.time()),'rows':rows,'sampled_blocks':sampled,
              'skipped':skipped,'sampling':'Evenly spaced proposed slots; first available block per proposal; actual timestamps enforce 1h label maturity',
              'limits':['Sparse sampled history, not complete account history.',
                        'Different source and sampling from training archive; live predictive validity unproven.']}
    path = snapshot_path(network)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, separators=(',',':')))
    temporary.replace(path)
    return {k:v for k,v in result.items() if k!='rows'} | {'row_count':len(rows),'path':str(path)}


def live_features(snapshot, accounts, now):
    if snapshot['completed_ts'] > now:
        raise ValueError('History snapshot was collected after this prediction.')
    if now-snapshot['completed_ts'] > 3600:
        raise ValueError('History snapshot is older than one hour; refresh it.')
    history = ParticipationHistory(delay=3600,strength=20)
    previous = None
    for row in snapshot['rows']:
        if row['ts']+3600 > now:
            raise ValueError('Snapshot contains an outcome that is not yet mature.')
        if previous is not None and row['ts'] < previous:
            raise ValueError('History is not chronological.')
        _, _, roles = history.features(row['accounts'],row['ts'])
        history.schedule(roles,row['label'],row['ts'])
        previous = row['ts']
    features, cold, _ = history.features(accounts,now)
    return features, cold


def score_live(sender,recipient,network,now=None,path=None):
    now = int(time.time()) if now is None else now
    path = path or snapshot_path(network)
    unavailable = {'status':'unavailable','scores':{},'automatic_block':False}
    if not path.exists():
        return unavailable | {'reason':'Collect a recent mature-history snapshot first.'}
    contents = path.read_bytes()
    snapshot = json.loads(contents)
    if snapshot['network'] != network:
        return unavailable | {'reason':'History belongs to a different network.'}
    accounts = [{'pubkey':sender,'signer':True,'writable':True},
                {'pubkey':recipient,'signer':False,'writable':True},
                {'pubkey':SYSTEM,'signer':False,'writable':False}]
    try:
        features,cold = live_features(snapshot,accounts,now)
    except ValueError as error:
        return unavailable | {'reason':str(error)}
    if len(snapshot['rows']) < 100 or snapshot['rows'][-1]['ts']-snapshot['rows'][0]['ts'] < 21600:
        return unavailable | {'reason':'Need at least 100 mature records spanning six hours.'}
    model_path = ROOT/'data/processed/solana_ml/demo_models.joblib'
    if not model_path.exists():
        return unavailable | {'reason':'Export the trained models first.'}
    saved = joblib.load(model_path)
    frame = pd.DataFrame([features])
    scores = {}
    for name,artifact in saved['models'].items():
        raw = float(artifact['model'].predict_proba(frame[artifact['inputs']])[0,1])
        scores[name] = {'raw_model_score':raw,'validated_live_probability':None}
    # Training ranges are a diagnostic, never evidence that in-range rows generalise.
    reference = pd.read_parquet(ROOT/'data/processed/solana_ml/transaction_features_fresh.parquet')
    train = reference[reference.date.eq('2025-12-03')]
    outside = [name for name,value in features.items()
               if value < train[name].quantile(.001) or value > train[name].quantile(.999)]
    reasons = ['Live sampling differs from training; economic value and calibration are unvalidated.',
               'ML uses account roles and history, not the transfer amount; network checks handle amount-specific problems.']
    if network == 'devnet':reasons.append('Devnet differs from the mainnet archive used for training.')
    if outside:reasons.append('Some inputs fall outside the central training ranges.')
    if not cold:reasons.append('Historical demo calibration was restricted to missing signer history.')
    return {'status':'experimental','scores':scores,'automatic_block':False,'warning_recommendation':None,
            'cold_history':cold,'feature_values':features,'feature_sha256':hashlib.sha256(json.dumps(features,sort_keys=True).encode()).hexdigest(),
            'history_sha256':hashlib.sha256(contents).hexdigest(),'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
            'history_records':len(snapshot['rows']),'history_blocks':len(snapshot['sampled_blocks']),
            'history_completed_ts':snapshot['completed_ts'],'out_of_range_features':outside,'limits':reasons,
            'source':'Actual fitted HGB predict_proba on freshly constructed live-history features; no current outcome used'}
