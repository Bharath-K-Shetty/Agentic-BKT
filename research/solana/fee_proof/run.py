"""Reproduce fee avoidance on an isolated local Solana validator; no real SOL.

Run from repository root: .venv/bin/python research/solana/fee_proof/run.py
Requires solana-test-validator and solders==0.26.0 or newer.
The browser's read-only checker never gains permission to broadcast.
"""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import requests
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import Message
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from webapp.backend.transfer_check import check_transfer


class LocalRPC:
    """Fixed loopback only. Signing and sending exist only in this experiment."""
    def __init__(self, port):
        self.url = f'http://127.0.0.1:{port}'
        self.session = requests.Session()
        self.session.trust_env = False

    def raw(self, method, params):
        response = self.session.post(self.url, json={
            'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}, timeout=8)
        response.raise_for_status()
        return response.json()

    def call(self, method, params):
        result = self.raw(method, params)
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result['result']

    def balance(self, address):
        return self.call('getBalance', [str(address), {'commitment': 'confirmed'}])['value']

    def receipt(self, signature):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            value = self.call('getTransaction', [signature, {
                'encoding': 'json', 'commitment': 'confirmed', 'maxSupportedTransactionVersion': 0}])
            if value is not None:
                return value
            time.sleep(.25)
        raise TimeoutError(f'No confirmed receipt: {signature}')

    def transaction(self, payer, recipient, amount):
        blockhash = self.call('getLatestBlockhash', [{'commitment': 'confirmed'}])['value']['blockhash']
        tx = Transaction.new_signed_with_payer([
            transfer(TransferParams(from_pubkey=payer.pubkey(), to_pubkey=recipient, lamports=amount))
        ], payer.pubkey(), [payer], Hash.from_string(blockhash))
        return base64.b64encode(bytes(tx)).decode()


def verify(result):
    """Fail the run unless independent balance changes and receipts agree."""
    checked, rejected, failed, success = result['cases']
    assert checked['check']['simulation']['error'] is not None
    assert checked['payer_before'] == checked['payer_after']
    assert checked['recipient_before'] == checked['recipient_after']
    assert checked['actual_fee_lamports'] == 0 and not checked['submitted']
    assert rejected['rpc_error']['code'] == -32002
    assert rejected['payer_before'] == rejected['payer_after']
    assert rejected['recipient_before'] == rejected['recipient_after']
    assert rejected['receipt'] is None
    assert rejected['actual_fee_lamports'] == 0
    meta = failed['receipt']['meta']
    assert meta['err'] is not None and meta['fee'] > 0
    assert failed['actual_fee_lamports'] == meta['fee']
    assert failed['payer_before'] - failed['payer_after'] == meta['fee']
    assert failed['recipient_before'] == failed['recipient_after']
    assert meta['preBalances'][0] - meta['postBalances'][0] == meta['fee']
    assert failed['receipt']['transaction']['signatures'][0] == failed['signature']
    meta = success['receipt']['meta']
    assert meta['err'] is None
    assert success['actual_fee_lamports'] == meta['fee']
    assert success['payer_before'] - success['payer_after'] == meta['fee'] + success['amount_lamports']
    assert success['recipient_after'] - success['recipient_before'] == success['amount_lamports']
    assert checked['payer_before'] == failed['payer_before']
    assert checked['amount_lamports'] == failed['amount_lamports']
    assert checked['recipient_before'] == failed['recipient_before'] == 0
    assert checked['check']['simulation']['error'] == failed['receipt']['meta']['err']


def experiment(rpc):
    payers = [Keypair() for _ in range(2)]
    recipients = [Keypair().pubkey() for _ in range(3)]
    for payer in payers:
        signature = rpc.call('requestAirdrop', [str(payer.pubkey()), 1_000_000_000])
        rpc.receipt(signature)
    cases = []

    def before(name, payer, recipient, amount):
        return {'name': name, 'payer': str(payer.pubkey()), 'recipient': str(recipient),
                'amount_lamports': amount, 'payer_before': rpc.balance(payer.pubkey()),
                'recipient_before': rpc.balance(recipient)}

    def after(case):
        case.update(payer_after=rpc.balance(case['payer']), recipient_after=rpc.balance(case['recipient']))
        cases.append(case)
        print(f"Completed: {case['name']}", flush=True)

    # Same production checker function, local RPC injected; deliberately unfunded recipient.
    case = before('Check and stop', payers[0], recipients[0], 1)
    case.update(check=check_transfer(case['payer'], case['recipient'], '0.000000001', 'devnet', rpc=rpc),
                submitted=False, actual_fee_lamports=0)
    case['check']['network'] = 'local-validator'
    after(case)

    # Normal preflight rejects the matched transaction. No fee is charged here either.
    encoded = rpc.transaction(payers[1], recipients[1], 1)
    case = before('Normal preflight rejection', payers[1], recipients[1], 1)
    response = rpc.raw('sendTransaction', [encoded, {'encoding': 'base64',
        'skipPreflight': False, 'preflightCommitment': 'confirmed'}])
    if 'error' not in response:
        raise AssertionError('Expected preflight rejection')
    signature = str(Transaction.from_bytes(base64.b64decode(encoded)).signatures[0])
    time.sleep(1)
    receipt = rpc.call('getTransaction', [signature, {'commitment': 'confirmed'}])
    case.update(rpc_error=response['error'], receipt=receipt, signature=signature,
                actual_fee_lamports=0, broadcast_accepted=False)
    after(case)

    # Test-only bypass forces the failure into a block, so its receipt proves the fee.
    case = before('Submitted execution failure', payers[1], recipients[1], 1)
    signature = rpc.call('sendTransaction', [encoded, {'encoding': 'base64',
        'skipPreflight': True, 'preflightCommitment': 'confirmed', 'maxRetries': 0}])
    receipt = rpc.receipt(signature)
    case.update(signature=signature, receipt=receipt, submitted=True,
                skip_preflight=True, actual_fee_lamports=receipt['meta']['fee'])
    after(case)

    case = before('Successful transfer', payers[1], recipients[2], 10_000_000)
    signature = rpc.call('sendTransaction', [rpc.transaction(payers[1], recipients[2], case['amount_lamports']),
        {'encoding': 'base64', 'skipPreflight': False, 'preflightCommitment': 'confirmed'}])
    receipt = rpc.receipt(signature)
    case.update(signature=signature, receipt=receipt, submitted=True,
                actual_fee_lamports=receipt['meta']['fee'])
    after(case)
    return cases


def verify_prospective_store(rpc,run_dir):
    """Exercise the real decision-to-receipt flow, not just a mocked RPC."""
    from webapp.backend.prospective import StudyStore
    payer=Keypair();recipient=Keypair().pubkey()
    rpc.receipt(rpc.call('requestAirdrop',[str(payer.pubkey()),1_000_000_000]))
    check=check_transfer(str(payer.pubkey()),str(recipient),'0.01','devnet',rpc=rpc)
    message=base64.b64decode(check['candidate_message_base64'])
    tx=Transaction.populate(Message.from_bytes(message),[payer.sign_message(message)])
    signed_sim=rpc.call('simulateTransaction',[base64.b64encode(bytes(tx)).decode(),
        {'encoding':'base64','sigVerify':True,'replaceRecentBlockhash':False,'commitment':'confirmed'}])
    assert signed_sim['value']['err'] is None
    check['simulation']['signature_verification']=True
    store=StudyStore(run_dir/'observations.sqlite3')
    decision={'network':'local-validator','check':check,
              'ml':{'status':'unavailable','reason':'No validated local-network ML model'}}
    identity=store.record(decision)['decision_id']
    assert store.summary()['decisions'][0]['verified_outcome'] is None
    # Ensure a strictly later block and timestamp for the prospective receipt check.
    time.sleep(2)
    signature=rpc.call('sendTransaction',[base64.b64encode(bytes(tx)).decode(),
        {'encoding':'base64','skipPreflight':False,'preflightCommitment':'confirmed'}])
    rpc.receipt(signature)
    verified=store.attach(identity,signature,rpc=rpc)
    assert verified['status']=='verified' and verified['outcome']=='Succeeded'
    assert verified['measured_fee_savings_lamports'] is None
    assert store.decision(identity)[0]==decision
    result={'network':'local-validator','decision_id':identity,'prediction_recorded_before_submission':True,
            'signed_simulation_verified_before_submission':True,
            'matching_message_verified':True,'decision_unchanged_after_receipt':True,
            'receipt':verified,'scope':'Functional verification only; not evidence of ML benefit.'}
    (ROOT/'docs/results/solana_prospective_local_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Completed: prospective decision and matching real receipt',flush=True)


def main():
    executable = shutil.which('solana-test-validator')
    if not executable:
        raise RuntimeError('Install the Solana CLI (solana-test-validator) first.')
    # Reserve-check fixed experiment ports; refuse to attach to another validator.
    for port in (8897, 8898, 9917):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_dir = ROOT / 'data/raw/fee_proof' / run_id
    run_dir.mkdir(parents=True)
    rpc = LocalRPC(8897)
    command = [executable, '--ledger', str(run_dir/'ledger'), '--rpc-port', '8897',
               '--faucet-port', '9917', '--bind-address', '127.0.0.1',
               '--dynamic-port-range', '12000-12100', '--mint', str(Keypair().pubkey()), '--quiet']
    with (run_dir/'validator.log').open('w') as log:
        process = subprocess.Popen(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 50
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f'Validator exited. See {run_dir}/validator.log')
                try:
                    if rpc.call('getHealth', []) == 'ok':
                        break
                except (requests.RequestException, RuntimeError):
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError(f'Validator not ready. See {run_dir}/validator.log')
                time.sleep(.4)
            result = {'schema_version': 1, 'run_id': run_id, 'network': 'local-validator',
                      'validator_version': subprocess.check_output([executable, '--version'], text=True).strip(),
                      'rpc_url': rpc.url, 'real_funds_used': False, 'cases': experiment(rpc)}
            verify(result)
            verify_prospective_store(rpc,run_dir)
            result['verification'] = 'passed'
            result['avoided_fee_lamports_in_matched_local_comparison'] = result['cases'][2]['actual_fee_lamports']
            result['limits'] = [
                'Local test SOL only; no measured mainnet savings or time savings.',
                'Paid failure deliberately bypassed normal preflight for this experiment.',
                'Normal preflight also rejected this problem at zero cost; no incremental saving over preflight shown.',
                'Simulation and balance checks caused the stop; no ML contribution to savings demonstrated.',
                'Matched independent wallets, equal starting balances, same amount and unfunded-recipient condition.',
                'One controlled run is a functional proof, not a statistical economic evaluation.']
            output = ROOT/'docs/results/solana_local_fee_proof.json'
            output.write_text(json.dumps(result, indent=2)+'\n')
            (run_dir/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            print(f'PASS — local avoided fee: {result["avoided_fee_lamports_in_matched_local_comparison"]} lamports')
            print(f'Evidence: {output}')
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
