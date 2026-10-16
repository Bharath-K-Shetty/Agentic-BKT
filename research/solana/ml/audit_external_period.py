"""Audit pinned external snapshots against the existing transaction-min endpoint.

This is not model validation and does not relabel missing follow-up as safe.
"""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import pyarrow

ROOT = Path(__file__).resolve().parents[3]
REVISION = '13bec2bf3089d56d50c35e602616d1b993bb37f5'
REPO = 'Slinky21/Pumpfun_Memecoin_Corpus'


def main():
    raw = ROOT / 'data/raw/external_ml'
    raw.mkdir(parents=True, exist_ok=True)
    files = ('migrations.parquet', 'postgard_outcomes.parquet', 'postgard_snapshots.parquet')
    sources = []
    for name in files:
        path = raw / name
        url = f'https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{name}'
        if not path.exists():
            subprocess.run(['curl', '-sS', '-L', '--fail', '--max-time', '180', '-o', str(path), url], check=True)
        sources.append({'file': name, 'url': url, 'revision': REVISION, 'bytes': path.stat().st_size,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    migration = pd.read_parquet(raw / files[0])
    outcomes = pd.read_parquet(raw / files[1])
    snapshots = pd.read_parquet(raw / files[2])
    if migration.mint.duplicated().any():
        raise ValueError('Ambiguous migration anchor')
    valid = snapshots[snapshots.seconds_since_graduation.between(0, 1200)
                      & snapshots.price_native.gt(0) & np.isfinite(snapshots.price_native)
                      & snapshots.incomplete_data.eq(False)].copy()
    grouped = valid.groupby('mint').seconds_since_graduation.agg(['min', 'max', 'count'])
    gaps = valid.sort_values(['mint', 'seconds_since_graduation']).groupby('mint').seconds_since_graduation.diff()
    joined = valid.merge(migration[['mint', 'migrated_at']], on='mint', validate='many_to_one')
    elapsed = (pd.to_datetime(joined.snapshot_time, utc=True) - pd.to_datetime(joined.migrated_at, utc=True)).dt.total_seconds()
    discrepancy = (elapsed - joined.seconds_since_graduation).abs()
    sentinels = migration.pool_address.isin(['synthetic_graduation_queue', 'backfilled_from_pumpswap_trade'])
    real_pool = set(migration.loc[~sentinels, 'mint'])
    broad_coverage = grouped['min'].le(30) & grouped['max'].ge(1170)
    report = {'repository': REPO, 'revision': REVISION, 'sources': sources,
              'pyarrow': pyarrow.__version__,
              'observations': {'migrations': len(migration), 'outcomes': len(outcomes),
                  'snapshot_rows': len(snapshots), 'snapshot_mints': int(snapshots.mint.nunique()),
                  'valid_native_prices_in_first_20_minutes': len(valid),
                  'tokens_with_valid_early_prices': len(grouped),
                  'first_price_seconds_quantiles': {str(q): float(v) for q, v in grouped['min'].quantile([0,.25,.5,.75,1]).items()},
                  'first_price_at_or_before_5s': int(grouped['min'].le(5).sum()),
                  'first_price_at_or_before_30s': int(grouped['min'].le(30).sum()),
                  'early_start_and_late_end_observed': int(broad_coverage.sum()),
                  'early_and_late_with_nonsentinel_pool': int(sum(broad_coverage.loc[m] for m in grouped.index if m in real_pool)),
                  'within_token_snapshot_gap_quantiles': {str(q): float(v) for q, v in gaps.dropna().quantile([.5,.9,.99,1]).items()},
                  'synthetic_or_backfilled_pool_records': int(sentinels.sum()),
                  'native_price_anchor_in_outcome_table': 'price_at_grad_native' in outcomes.columns,
                  'explicit_20minute_minimum_in_outcomes': any('min' in c and '20m' in c for c in outcomes.columns),
                  'snapshot_to_migration_elapsed_abs_error_median': float(discrepancy.median()),
                  'snapshot_to_migration_elapsed_abs_error_above_5s': int(discrepancy.gt(5).sum()),
                  'snapshot_period_start': str(snapshots.snapshot_time.min()),
                  'snapshot_period_end': str(snapshots.snapshot_time.max())},
              'decision': 'Inspected external assets not accepted as exact validation of the MELT transaction-minimum collapse endpoint',
              'reasons': ['Periodic snapshots do not observe every transaction; negative labels can miss short collapses.',
                          'The migration-price native-unit anchor is not directly supplied in the outcome table.',
                          'Only some tokens have observations near both ends of the 20-minute window.',
                          'Collection/sentinel/unit issues require further reconciliation before feature transfer.'],
              'not_done': ['No external model accuracy reported.', 'No missing outcomes relabeled as safe.',
                           'No complete external trade corpus or prefix feature transfer evaluated.'],
              'licensing_note': 'Pinned card metadata says MIT; prose says CC BY 4.0. No raw data redistributed.'}
    shard = raw / 'trades-00000.parquet'
    if shard.exists():
        trades = pd.read_parquet(shard, columns=['mint', 'event_time', 'source', 'price_sol'])
        matched = trades.merge(migration[['mint', 'migrated_at']], on='mint', validate='many_to_one')
        age = (pd.to_datetime(matched.event_time, utc=True) - pd.to_datetime(matched.migrated_at, utc=True)).dt.total_seconds()
        post = matched.loc[age.between(0,1200)]
        report['single_trade_shard_probe'] = {
            'rows': len(trades), 'tokens': int(trades.mint.nunique()),
            'source_counts': {str(k): int(v) for k, v in trades.source.value_counts().items()},
            'missing_price_rows': int(trades.price_sol.isna().sum()),
            'mints_matching_migration_table': int(matched.mint.nunique()),
            'post_migration_first_20minute_rows': len(post),
            'event_start': str(trades.event_time.min()), 'event_end': str(trades.event_time.max()),
            'scope': 'One shard only; no inference of zero post-migration trades across uninspected shards'}
        report['sources'].append({'file': shard.name,
            'url': f'https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/trades/trades-00000.parquet',
            'revision': REVISION, 'bytes': shard.stat().st_size, 'sha256': hashlib.sha256(shard.read_bytes()).hexdigest()})
    out = ROOT / 'docs/results/solana_external_period_audit.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['observations'], indent=2)); print(out)


if __name__ == '__main__':
    main()
