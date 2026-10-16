"""The proof must fail if its claimed fee does not match independent balances."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip('solders')
spec = importlib.util.spec_from_file_location('fee_proof_run', ROOT/'research/solana/fee_proof/run.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def evidence():
    return json.loads((ROOT/'docs/results/solana_local_fee_proof.json').read_text())


def test_recorded_receipts_agree_with_balances(evidence):
    module.verify(evidence)


@pytest.mark.parametrize('case_index,field,value', [
    (0, 'payer_after', 999995000),  # A fee on the stopped attempt invalidates avoidance.
    (1, 'payer_after', 999995000),  # Preflight rejection must not be counted as paid.
    (2, 'recipient_after', 1),      # Failed transfer must not credit its recipient.
    (3, 'recipient_after', 0),      # Successful transfer must deliver the principal.
])
def test_inconsistent_balance_evidence_is_rejected(evidence, case_index, field, value):
    changed = copy.deepcopy(evidence)
    changed['cases'][case_index][field] = value
    with pytest.raises(AssertionError):
        module.verify(changed)


def test_invented_fee_is_rejected(evidence):
    evidence['cases'][2]['receipt']['meta']['fee'] += 1
    with pytest.raises(AssertionError):
        module.verify(evidence)
