"""Execute authored local controls; never connect to a cluster or wallet.

These are harness regression controls, not independent audit findings. Each case
uses a fresh VM. Direct state injection and skipped signatures are labelled, and
are never counted as valid attacker witnesses.
"""
import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import platform

from solders.account import Account
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.litesvm import LiteSVM
from solders.message import Message
from solders.null_signer import NullSigner
from solders.system_program import create_account, transfer
from solders.transaction import VersionedTransaction
from solders.transaction_metadata import FailedTransactionMetadata

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BINARY = ROOT / "research/solana/target/deploy/homie_runtime_controls.so"
DEFAULT_OUTPUT = ROOT / "docs/results/solana/runtime_controls.json"


def key(label):
    # Public deterministic lab identities only; never use for real funds.
    return Keypair.from_seed(sha256(("homie-local-control:" + label).encode()).digest())


PAYER = key("payer")
VICTIM = key("victim")
RECORD = key("record")
PROTECTED = key("protected-record")
WRITER = key("writer-program").pubkey()
CONSUMER = key("consumer-program").pubkey()
TRUSTED = key("trusted-program").pubkey()
EVIL = key("evil-program").pubkey()


class Lab:
    def __init__(self, binary, sigverify=True):
        self.svm = LiteSVM().with_sigverify(sigverify)
        self.sigverify = sigverify
        self.events = []
        for program in [WRITER, CONSUMER, TRUSTED, EVIL]:
            self.svm.add_program_from_file(program, binary)
        for actor in [PAYER, VICTIM]:
            result = self.svm.airdrop(actor.pubkey(), 100_000_000)
            if isinstance(result, FailedTransactionMetadata):
                raise RuntimeError(f"Fixture funding failed: {result}")

    def send(self, instructions, signers, phase, controlled_keys=None):
        signer_keys = {str(s.pubkey()) for s in signers}
        if phase == "attack" and controlled_keys is not None:
            unavailable = signer_keys - set(controlled_keys)
            if unavailable:
                raise ValueError(f"Unavailable signers: {sorted(unavailable)}")
        msg = Message.new_with_blockhash(instructions, PAYER.pubkey(), self.svm.latest_blockhash())
        tx = VersionedTransaction(msg, signers)
        result = self.svm.send_transaction(tx)
        failed = isinstance(result, FailedTransactionMetadata)
        meta = result.meta() if failed else result
        event = {"phase": phase, "signer_keys": sorted(signer_keys),
                 "transaction_sha256": sha256(bytes(tx)).hexdigest(),
                 "transaction_base64": base64.b64encode(bytes(tx)).decode(),
                 "signature_verification": self.sigverify,
                 "success": not failed, "error": str(result.err()) if failed else None,
                 "logs": meta.logs(), "compute_units": meta.compute_units_consumed()}
        self.events.append(event)
        return event

    def create_record(self, target, amount, phase, owner=WRITER):
        data = bytes(PAYER.pubkey()) + amount.to_bytes(8, "little")
        create = create_account({"from_pubkey": PAYER.pubkey(), "to_pubkey": target.pubkey(),
                                 "lamports": self.svm.minimum_balance_for_rent_exemption(40),
                                 "space": 40, "owner": owner})
        accounts = [AccountMeta(target.pubkey(), True, True)]
        signers = [PAYER, target]
        if owner == TRUSTED and phase == "fixture":
            accounts.append(AccountMeta(VICTIM.pubkey(), True, False))
            signers.append(VICTIM)
        write = Instruction(owner, b"\x00" + data, accounts)
        result = self.send([create, write], signers, phase,
                           [str(PAYER.pubkey()), str(target.pubkey())] if phase == "attack" else None)
        if not result["success"]:
            raise RuntimeError(f"Record construction failed: {result}")

    def consume(self, target, patched=False):
        instruction = Instruction(CONSUMER, bytes([2 if patched else 1]), [
            AccountMeta(target, False, False), AccountMeta(PAYER.pubkey(), True, False),
            AccountMeta(TRUSTED, False, False)])
        return self.send([instruction], [PAYER], "attack", [str(PAYER.pubkey())])


def run_controls(binary):
    results = []

    def record(case_id, lab, expectation, observed, witness, limitations):
        results.append({"id": case_id, "kind": "authored_runtime_control",
                        "expected_property_observation": expectation,
                        "observed_property": observed, "check_passed": expectation == observed,
                        "witness_status": witness, "limitations": limitations,
                        "events": lab.events})

    for verify, owned, case_id in [(True, False, "signature-outsider"),
                                  (False, False, "signature-skipped"),
                                  (True, True, "signature-controlled")]:
        lab = Lab(binary, verify)
        receiver = key("receiver").pubkey()
        before = lab.svm.get_balance(receiver) or 0
        ix = transfer({"from_pubkey": VICTIM.pubkey(), "to_pubkey": receiver, "lamports": 2_000_000})
        signers = [PAYER, VICTIM if owned else NullSigner(VICTIM.pubkey())]
        # Raw runtime probe: bypass capability gate deliberately to test signatures.
        event = lab.send([ix], signers, "attack")
        moved = (lab.svm.get_balance(receiver) or 0) - before == 2_000_000
        observed = event["success"] and moved
        record(case_id, lab, not verify or owned, observed,
               "validated_local_control" if owned else ("invalid_witness_signature_bypass" if observed else "attempt_rejected"),
               "Same transfer; actor control differs. Skipped-signature success is an intentionally invalid outsider witness.")

    for patched in [False, True]:
        lab = Lab(binary)
        lab.create_record(RECORD, 999, "attack")
        event = lab.consume(RECORD.pubkey(), patched)
        accepted = event["success"] and any("accepted fabricated balance" in s for s in event["logs"])
        record("owner-check-patched" if patched else "owner-check-missing", lab,
               not patched, accepted, "attempt_rejected" if patched else "validated_local_control",
               "Attacker account creation and writes use signed transactions; deployment and funding are declared fixtures. Custom record, not SPL Token or an upstream example.")

    lab = Lab(binary)
    lab.create_record(RECORD, 999, "fixture", owner=TRUSTED)
    event = lab.consume(RECORD.pubkey(), patched=True)
    record("owner-check-trusted-positive", lab, True, event["success"], "positive_control",
           "The checked consumer accepts a correctly owned record; this guards against an always-rejecting patch. Not an exploit.")

    for inject in [False, True]:
        lab = Lab(binary)
        lab.create_record(PROTECTED, 7, "fixture")
        data = bytes(PAYER.pubkey()) + (999).to_bytes(8, "little")
        if inject:
            old = lab.svm.get_account(PROTECTED.pubkey())
            lab.svm.set_account(PROTECTED.pubkey(), Account(old.lamports, data, old.owner, old.executable, old.rent_epoch))
            lab.events.append({"phase": "attack", "operation": "set_account",
                               "harness_only": True, "address": str(PROTECTED.pubkey()),
                               "reason": "Intentional invalid witness control; actor lacks target signing key"})
        else:
            write = Instruction(WRITER, b"\x00" + data, [AccountMeta(PROTECTED.pubkey(), False, True)])
            attempt = lab.send([write], [PAYER], "attack", [str(PAYER.pubkey())])
            if attempt["success"]:
                raise AssertionError("Protected target unexpectedly writable")
        event = lab.consume(PROTECTED.pubkey())
        accepted = event["success"] and any("accepted fabricated balance" in s for s in event["logs"])
        record("protected-record-injected" if inject else "protected-record-legal-attempt", lab,
               inject, accepted, "invalid_witness_harness_mutation" if inject else "attempt_rejected",
               "Only this writer attempt is tested; rejection is not a proof that every possible exploit chain is impossible.")

    for patched in [False, True]:
        lab = Lab(binary)
        ix = Instruction(CONSUMER, bytes([6 if patched else 5]), [
            AccountMeta(TRUSTED, False, False), AccountMeta(EVIL, False, False)])
        event = lab.send([ix], [PAYER], "attack", [str(PAYER.pubkey())])
        accepted = event["success"] and any("accepted substituted return data" in s for s in event["logs"])
        record("return-producer-checked" if patched else "return-producer-unchecked", lab,
               not patched, accepted, "attempt_rejected" if patched else "validated_local_control",
               "Native model of return-data producer validation; both CPI targets are fixture-loaded. Does not execute the Anchor patch or establish application reachability.")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cases = run_controls(args.binary)
    result = {"schema_version": 1, "executed_at": datetime.now(timezone.utc).isoformat(),
              "scope": "Authored runtime controls only; no mainnet, upstream reproduction, new bug, or research accuracy estimate",
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "solders": importlib.metadata.version("solders")},
              "binary_sha256": sha256(args.binary.read_bytes()).hexdigest(),
              "source_hashes": {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                                for path in [Path(__file__).resolve(),
                                             ROOT / "research/solana/runtime-controls/src/lib.rs",
                                             ROOT / "research/solana/runtime-controls/Cargo.lock",
                                             ROOT / "research/solana/cases/source_manifest.json"]},
              "initial_state": "Fresh local LiteSVM per case; four program identities loaded from the same authored ELF; payer and victim each receive 100 million fixture lamports",
              "cases": cases, "checks_passed": sum(c["check_passed"] for c in cases),
              "checks_total": len(cases)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['checks_passed']}/{len(cases)} runtime control checks passed; {args.output}")
    if not all(c["check_passed"] for c in cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
