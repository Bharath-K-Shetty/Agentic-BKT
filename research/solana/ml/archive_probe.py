"""Read selected public Parquet ranges without downloading whole daily tapes."""
import io
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[3]
REVISION = '6588cad2832e62be03972ac80d69c6af11d631c8'


class RangeFile(io.BufferedIOBase):
    def __init__(self, url, size, cache):
        self.url, self.size, self.cache = url, size, Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.position = 0
        self.session = requests.Session()
        self.ranges = {}

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        position = offset if whence == io.SEEK_SET else self.position + offset if whence == io.SEEK_CUR else self.size + offset
        if position < 0:
            raise ValueError('Negative position')
        self.position = position
        return position

    def read(self, n=-1):
        start = self.position
        end = self.size if n < 0 else min(self.size, start + n)
        if end <= start:
            return b''
        path = self.cache / f'{start}-{end}.bin'
        if not path.exists():
            url = self.url + f'?download=true&range_start={start}&range_end={end}'
            response = self.session.get(url, headers={'Range': f'bytes={start}-{end-1}', 'Accept-Encoding': 'identity'}, timeout=(15, 45))
            response.raise_for_status()
            expected = f'bytes {start}-{end-1}/{self.size}'
            if response.status_code != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError(f'Wrong HTTP range: {response.status_code}, {response.headers.get("Content-Range")} expected {expected}')
            if len(response.content) != end-start:
                raise ValueError('Truncated range')
            path.write_bytes(response.content)
        data = path.read_bytes()
        if len(data) != end-start:
            raise ValueError('Corrupt cached range')
        self.ranges[f'{start}:{end}'] = hashlib.sha256(data).hexdigest()
        self.position = end
        return data

    def close(self):
        self.session.close()
        super().close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='2025-11-01')
    parser.add_argument('--shard-index', type=int, default=0)
    args = parser.parse_args()
    raw = ROOT / 'data/raw/novelty_search'
    date = args.date
    index_path = raw / f'{date}_index.json'
    if not index_path.exists():
        response = requests.get(f'https://huggingface.co/datasets/solarchive/solarchive/resolve/{REVISION}/txs/{date}/index.json', timeout=30)
        response.raise_for_status()
        index_path.write_bytes(response.content)
    index = json.loads(index_path.read_text())
    entries = sorted(index['files'], key=lambda entry: entry['name'])
    entry = entries[args.shard_index]
    suffix = '' if args.shard_index == 0 else f'_shard{args.shard_index:04d}'
    url = f'https://huggingface.co/datasets/solarchive/solarchive/resolve/{REVISION}/txs/{date}/{entry["name"]}'
    stream = RangeFile(url, entry['size_bytes'], raw / 'archive_ranges' / date / entry['name'])
    parquet = pq.ParquetFile(stream)
    info = {'source': url, 'shard_index': args.shard_index, 'index_expected_sha256': entry['sha256'], 'full_file_hash_verified': False,
            'rows': parquet.metadata.num_rows, 'row_groups': parquet.num_row_groups,
            'schema': str(parquet.schema_arrow), 'first_group_n': parquet.metadata.row_group(0).num_rows}
    print(json.dumps(info, indent=2), flush=True)
    table = parquet.read_row_group(0, columns=['block_slot', 'block_timestamp', 'status', 'accounts', 'signature'], use_threads=False)
    info['preview'] = table.slice(0, 2).to_pylist()
    info['ranges_sha256'] = stream.ranges
    pq.write_table(table, raw / f'archive_preview_{date}{suffix}.parquet')
    (ROOT / f'docs/results/solana_transaction_source_probe_{date}{suffix}.json').write_text(json.dumps(info, indent=2, default=str)+'\n')
    print(json.dumps(info['preview'], default=str), flush=True)
    print('selected_rows', table.num_rows, flush=True)


if __name__ == '__main__':
    main()
