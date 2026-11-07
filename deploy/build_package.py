"""Create a minimal standalone deployment tree; never copy keys or study data."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/cloud/homie-demo'
FILES = [
    *['webapp/backend/'+n+'.py' for n in ('cloud','runtime_paths','replay','model_inference','transfer_check','live_history','prospective')],
    *['webapp/frontend/'+n+'.html' for n in ('replay','research','live','fee_proof','model_predict','transfer_check')],
    *['research/solana/ml/'+n+'.py' for n in ('transaction_risk','prefix_baseline','robustness')],
    *['data/processed/solana_ml/'+n for n in ('demo_models.joblib','demo_inference_test.parquet','replay_demo.json','transaction_features_fresh.parquet')],
    *['docs/results/'+n+'.json' for n in ('solana_local_fee_proof','solana_ml_fee_policy_summary','solana_transaction_audit_prospective','solana_transaction_audit_fresh')],
]

def build():
    missing = [n for n in FILES if not (ROOT/n).is_file()]
    if missing:
        raise FileNotFoundError(str(missing))
    # Only remove the dedicated generated staging directory.
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name in FILES:
        target = OUT/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name,target)
    for name in ('Dockerfile','render.yaml','requirements.txt','README.md'):
        shutil.copy2(ROOT/'deploy'/name, OUT/name)
    (OUT/'.dockerignore').write_text('.git\n.env*\n__pycache__\n*.sqlite3*\n')
    (OUT/'.gitignore').write_text('.env*\n__pycache__/\n*.sqlite3*\n')
    manifest = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive = OUT.parent/'homie-demo-cloud.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        tar.add(OUT,arcname='homie-demo')
    print(f'Packaged {len(FILES)} files; archive {archive.stat().st_size / 1024**2:.1f} MiB')

if __name__ == '__main__':
    build()
