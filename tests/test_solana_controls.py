"""Local runtime controls; build the ELF before executing these tests."""
import pytest

pytest.importorskip("solders", reason="Install research/solana/requirements.txt")
from solders.system_program import transfer
from research.solana.run_controls import DEFAULT_BINARY, Lab, PAYER, VICTIM, TRUSTED, key, run_controls


@pytest.fixture
def binary():
    if not DEFAULT_BINARY.exists():
        pytest.skip("Build research/solana/runtime-controls with cargo build-sbf first")
    return DEFAULT_BINARY


def test_capability_gate_rejects_unavailable_signer_before_execution(binary):
    lab = Lab(binary)
    receiver = key("gate-receiver").pubkey()
    ix = transfer({"from_pubkey": VICTIM.pubkey(), "to_pubkey": receiver, "lamports": 2_000_000})
    before = lab.svm.get_balance(VICTIM.pubkey())
    with pytest.raises(ValueError, match="Unavailable signers"):
        lab.send([ix], [PAYER, VICTIM], "attack", [str(PAYER.pubkey())])
    assert lab.svm.get_balance(VICTIM.pubkey()) == before
    assert lab.svm.get_balance(receiver) is None
    assert lab.events == []


def test_runtime_controls_preserve_invalid_witness_distinction(binary):
    cases = {c["id"]: c for c in run_controls(binary)}
    assert all(c["check_passed"] for c in cases.values())
    assert not cases["signature-outsider"]["observed_property"]
    assert cases["signature-skipped"]["witness_status"] == "invalid_witness_signature_bypass"
    assert cases["signature-controlled"]["observed_property"]
    assert cases["owner-check-missing"]["observed_property"]
    assert not cases["owner-check-patched"]["observed_property"]
    assert cases["owner-check-trusted-positive"]["observed_property"]
    assert cases["protected-record-injected"]["witness_status"] == "invalid_witness_harness_mutation"
    assert not cases["protected-record-legal-attempt"]["observed_property"]
    assert cases["return-producer-unchecked"]["observed_property"]
    assert not cases["return-producer-checked"]["observed_property"]


def test_outsider_cannot_initialize_a_record_through_trusted_writer(binary):
    lab = Lab(binary)
    target = key("outsider-trusted-record")
    with pytest.raises(RuntimeError, match="Record construction failed"):
        lab.create_record(target, 999, "attack", owner=TRUSTED)
    # Creation and initialization are atomic; the failed attempt leaves no record.
    assert lab.svm.get_account(target.pubkey()) is None
