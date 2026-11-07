"""Fetch the declared-fee column for the same sampled row groups already used.

On Solana the charged fee is fixed before execution by the transaction's own
settings: a base fee per signature plus compute-unit price times the requested
compute-unit limit. It does not depend on success or consumed compute, so it
reveals the sender's priority-fee choice. Only `signature` and `fee` are read.

    .venv/bin/python research/solana/ml/fetch_fee_column.py
"""
import json
from pathlib import Path
import sys

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from archive_probe import REVISION, RangeFile, ROOT  # noqa: E402

RAW = ROOT / 'data/raw/novelty_search'
SHARDS = {'2025-11-01': 0, '2025-11-02': 0, '2025-11-03': 0, '2025-11-08': 0, '2025-11-09': 0, '2025-11-10': 0,
          '2025-11-22': 203, '2025-11-23': 60, '2025-11-24': 39, '2025-11-29': 91, '2025-11-30': 132,
          '2025-12-01': 24, '2025-12-03': 69, '2025-12-04': 135, '2025-12-05': 185,
          '2025-11-26': 143, '2025-11-27': 66, '2025-11-28': 93}


def fee_path(date):
    shard = SHARDS[date]
    return RAW / f"archive_fee_{date}{'' if shard == 0 else f'_shard{shard:04d}'}.parquet"


def main():
    for date, shard in SHARDS.items():
        out = fee_path(date)
        if out.exists():
            continue
        index = json.loads((RAW / f'{date}_index.json').read_text())
        entry = sorted(index['files'], key=lambda e: e['name'])[shard]
        url = f'https://huggingface.co/datasets/solarchive/solarchive/resolve/{REVISION}/txs/{date}/{entry["name"]}'
        parquet = pq.ParquetFile(RangeFile(url, entry['size_bytes'], RAW / 'archive_ranges' / date / entry['name']))
        table = parquet.read_row_group(0, columns=['signature', 'fee'], use_threads=False)
        pq.write_table(table, out)
        print(date, shard, table.num_rows, flush=True)


if __name__ == '__main__':
    main()
