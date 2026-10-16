"""Meaningful pre-send boundaries, serialization, and failure-state checks."""
import base64
import struct
import pytest
from webapp.backend.transfer_check import (public_key,amount_lamports,transfer_message,
    check_transfer,ReadOnlyRPC,RpcUnavailable,SYSTEM)

SENDER='9nXDunV8eNvYSVys7JSBkm2hz9Q79Q3EYeko19srVeMC'
RECIPIENT='5SoF3RbNTMotKuWk2eCfU5bfLxpH47rpxFYgt89ruzEP'

class FakeRPC:
    def __init__(self,balance=1_000_000_000,error=None,fee=5000):
        self.balance=balance;self.error=error;self.fee=fee;self.calls=[]
    def call(self,method,params):
        self.calls.append((method,params))
        if method=='getLatestBlockhash':return {'context':{'slot':100},'value':{'blockhash':SYSTEM}}
        if method=='getFeeForMessage':return {'value':self.fee}
        if method=='getBalance':return {'value':self.balance}
        if method=='simulateTransaction':return {'value':{'err':self.error,'unitsConsumed':150}}
        raise AssertionError('Unexpected method')

def test_sol_transfer_message_encodes_accounts_and_amount_exactly():
    message=transfer_message(SENDER,RECIPIENT,SYSTEM,123456789)
    assert message[:4]==b'\x01\x00\x01\x03'
    assert message[4:36]==public_key(SENDER)
    assert message[36:68]==public_key(RECIPIENT)
    assert message[68:100]==bytes(32)
    assert message[132:138]==b'\x01\x02\x02\x00\x01\x0c'
    assert struct.unpack('<IQ',message[138:])==(2,123456789)

@pytest.mark.parametrize('value',['0','-1','NaN','Infinity','0.0000000001','text','18446744074'])
def test_reject_bad_or_oversized_amounts(value):
    with pytest.raises(ValueError):amount_lamports(value)

def test_decimal_amounts_do_not_use_float_rounding():
    assert amount_lamports('0.000000001')==1
    assert amount_lamports('0.100000001')==100000001

def test_insufficient_balance_reports_shortfall_without_simulating():
    rpc=FakeRPC(balance=1_000_000)
    r=check_transfer(SENDER,RECIPIENT,'0.01','devnet',rpc)
    assert r['status']=='needs_attention' and r['shortfall_sol']=='0.009005'
    assert not r['simulation']['performed'] and not r['broadcast']
    assert r['measured_fee_savings_sol'] is None
    assert all(method!='simulateTransaction' for method,_ in rpc.calls)

def test_passing_simulation_is_unsigned_and_never_broadcasts():
    rpc=FakeRPC();r=check_transfer(SENDER,RECIPIENT,'0.01','devnet',rpc)
    assert r['status']=='simulation_passed' and r['actual_fee_paid_sol']=='0'
    method,(encoded,config)=rpc.calls[-1]
    assert method=='simulateTransaction'
    assert config['sigVerify'] is False and config['replaceRecentBlockhash'] is False
    tx=base64.b64decode(encoded)
    assert tx[:65]==b'\x01'+bytes(64)
    assert tx[65:]==transfer_message(SENDER,RECIPIENT,SYSTEM,10000000)
    assert all(name in ReadOnlyRPC.ALLOWED for name,_ in rpc.calls)

def test_execution_error_is_not_reported_as_success():
    r=check_transfer(SENDER,RECIPIENT,'0.01','devnet',FakeRPC(error={'InsufficientFundsForRent':{'account_index':1}}))
    assert r['status']=='needs_attention' and 'minimum balance' in r['action']

def test_unavailable_fee_is_not_invented():
    with pytest.raises(RpcUnavailable):check_transfer(SENDER,RECIPIENT,'0.01','devnet',FakeRPC(fee=None))

def test_invalid_inputs_do_not_contact_network():
    rpc=FakeRPC()
    with pytest.raises(ValueError):check_transfer(SENDER,SENDER,'0.01','devnet',rpc)
    with pytest.raises(ValueError):check_transfer('bad',RECIPIENT,'0.01','devnet',rpc)
    with pytest.raises(ValueError):check_transfer(SENDER,RECIPIENT,'0.01','custom',rpc)
    assert not rpc.calls

def test_rpc_does_not_allow_submission_even_if_called_accidentally():
    with pytest.raises(ValueError):ReadOnlyRPC('devnet').call('sendTransaction',[])
