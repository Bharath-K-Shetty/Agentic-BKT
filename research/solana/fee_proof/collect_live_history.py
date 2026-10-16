"""Read-only public-RPC sampler for the integrated live research demo."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from webapp.backend.live_history import collect_snapshot

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--network',choices=['devnet','mainnet'],default='devnet')
    parser.add_argument('--blocks',type=int,default=16)
    args=parser.parse_args()
    print(json.dumps(collect_snapshot(args.network,args.blocks),indent=2))
