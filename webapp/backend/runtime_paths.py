"""Writable cloud state is separate from immutable model artifacts."""
import os
from pathlib import Path


def state_directory(root: Path) -> Path:
    return Path(os.environ.get('HOMIE_STATE_DIR', str(root / 'data/processed/solana_ml')))
