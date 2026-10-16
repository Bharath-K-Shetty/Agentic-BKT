"""Observe a signed plain transfer without signing or submitting it."""
import argparse
import json
from pathlib import Path
import requests

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--network',choices=['devnet','mainnet'],default='devnet')
    parser.add_argument('--transaction-file',type=Path,required=True,
                        help='Text file containing base64 of an already signed plain SOL transfer, never a keypair')
    args=parser.parse_args()
    response=requests.post('http://127.0.0.1:8430/api/live/signed-observe',json={
        'network':args.network,'transaction_base64':args.transaction_file.read_text().strip()},timeout=60)
    print(json.dumps(response.json(),indent=2))
    response.raise_for_status()
