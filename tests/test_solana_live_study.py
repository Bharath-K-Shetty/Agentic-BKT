"""Live inputs must precede outcomes; receipts must match the checked message."""
import base64
import hashlib
import json
import sqlite3
import time

import pytest

from webapp.backend.live_history import live_features, block_records, HistoryRPC, score_live
from webapp.backend.prospective import StudyStore
from webapp.backend import prospective
from webapp.backend.transfer_check import transfer_message, SYSTEM, ALPHABET

SENDER='9nXDunV8eNvYSVys7JSBkm2hz9Q79Q3EYeko19srVeMC'
RECIPIENT='5SoF3RbNTMotKuWk2eCfU5bfLxpH47rpxFYgt89ruzEP'
ACCOUNTS=[{'pubkey':SENDER,'signer':True,'writable':True},
          {'pubkey':RECIPIENT,'signer':False,'writable':True},
          {'pubkey':SYSTEM,'signer':False,'writable':False}]


def snapshot():
    return {'network':'devnet','completed_ts':30000,
            'rows':[{'ts':1000,'accounts':ACCOUNTS,'label':1},
                    {'ts':24000,'accounts':ACCOUNTS,'label':0}]}


def test_live_feature_builder_matches_research_history_and_excludes_current_outcome():
    features,cold=live_features(snapshot(),ACCOUNTS,30001)
    assert not cold
    assert features['writable_seen_fraction']==1
    # Global (1+1)/(2+2)=.5, recipient (1+20*.5)/(2+20)=.5.
    assert features['writable_risk_mean']==.5
    assert features['payer_risk']==.5
    assert 'label' not in features and 'fee' not in features


@pytest.mark.parametrize('change,now', [('future_snapshot',29999),('stale',40000),('immature',30001),('unsorted',30001)])
def test_invalid_history_withholds_features(change,now):
    s=snapshot()
    if change=='immature':s['rows'][-1]['ts']=28000
    if change=='unsorted':s['rows'].reverse()
    with pytest.raises(ValueError):live_features(s,ACCOUNTS,now)


def test_other_network_history_never_produces_score(tmp_path):
    path=tmp_path/'history.json';path.write_text(json.dumps(snapshot()))
    result=score_live(SENDER,RECIPIENT,'mainnet',now=30001,path=path)
    assert result['status']=='unavailable' and not result['scores']


def test_incomplete_parsed_accounts_are_not_guessed():
    block={'blockTime':100,'transactions':[{'meta':{'err':None},
        'transaction':{'signatures':['s'],'message':{'accountKeys':[SENDER]}}}]}
    assert block_records(block,1)==[]
    block['transactions'][0]['transaction']['message']['accountKeys']=ACCOUNTS
    rows=block_records(block,1)
    assert rows[0]['label']==0 and rows[0]['accounts']==ACCOUNTS


def test_live_rpc_has_no_submission_method():
    with pytest.raises(ValueError):HistoryRPC('devnet').call('sendTransaction',[])


def base58(value):
    n=int.from_bytes(value,'big');out=''
    while n:n,remainder=divmod(n,58);out=ALPHABET[remainder]+out
    return '1'*(len(value)-len(value.lstrip(b'\0')))+out


def decision(message):
    return {'network':'devnet','check':{'candidate_message_sha256':hashlib.sha256(message).hexdigest(),
            'slot':10,'simulation':{'performed':True,'error':None}},'ml':{'status':'experimental'}}


class ReceiptRPC:
    def __init__(self,message,err=None):
        self.receipt={'slot':11,'blockTime':int(time.time())+2,
            'transaction':[base64.b64encode(b'\x01'+b'a'*64+message).decode(),'base64'],
            'meta':{'err':err,'fee':5000,'preBalances':[1000000000,0,1],
                    'postBalances':[999995000 if err else 999994999,0 if err else 1,1]}}
    def call(self,method,params):
        assert method=='getTransaction'
        return self.receipt


def test_decision_is_immutable_and_receipt_does_not_overwrite_it(tmp_path):
    store=StudyStore(tmp_path/'study.db')
    message=transfer_message(SENDER,RECIPIENT,SYSTEM,1)
    identity=store.record(decision(message))['decision_id']
    original,_=store.decision(identity)
    assert store.summary()['decisions'][0]['verified_outcome'] is None
    result=store.attach(identity,base58(b'a'*64),ReceiptRPC(message,err={'InstructionError':[0,'x']}))
    assert result['outcome']=='Failed' and result['fee_paid_lamports']==5000
    assert result['measured_fee_savings_lamports'] is None
    assert store.decision(identity)[0]==original
    with store.connect() as db,pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE decisions SET payload=? WHERE id=?',('{}',identity))
    with pytest.raises(ValueError):store.attach(identity,base58(b'a'*64),ReceiptRPC(message))


def test_unrelated_or_old_receipt_is_rejected(tmp_path):
    store=StudyStore(tmp_path/'study.db');message=transfer_message(SENDER,RECIPIENT,SYSTEM,1)
    identity=store.record(decision(message))['decision_id']
    with pytest.raises(ValueError,match='different transaction'):
        store.attach(identity,base58(b'a'*64),ReceiptRPC(transfer_message(SENDER,RECIPIENT,SYSTEM,2)))
    old=ReceiptRPC(message);old.receipt['slot']=10
    with pytest.raises(ValueError,match='predates'):
        store.attach(identity,base58(b'a'*64),old)
    assert store.summary()['verified_receipts']==0


def test_missing_receipt_is_unknown_not_saved_fee(tmp_path):
    store=StudyStore(tmp_path/'study.db');message=transfer_message(SENDER,RECIPIENT,SYSTEM,1)
    identity=store.record(decision(message))['decision_id'];rpc=ReceiptRPC(message);rpc.receipt=None
    result=store.attach(identity,base58(b'a'*64),rpc)
    assert result['outcome'] is None and result['fee_paid_lamports'] is None
    assert store.summary()['verified_receipts']==0


def test_signed_observation_verifies_original_signature_without_replacing_blockhash(tmp_path):
    message=transfer_message(SENDER,RECIPIENT,SYSTEM,1)
    wire=b'\x01'+b'a'*64+message
    calls=[]
    class RPC:
        def call(self,method,params):
            calls.append(method)
            if method=='getSlot':return 10
            if method=='getFeeForMessage':return {'value':5000}
            if method=='getBalance':return {'value':1000000000}
            if method=='simulateTransaction':
                assert base64.b64decode(params[0])==wire
                assert params[1]['sigVerify'] is True and params[1]['replaceRecentBlockhash'] is False
                return {'value':{'err':None,'unitsConsumed':150}}
            raise AssertionError('Unexpected RPC method')
    request=prospective.SignedObservation(network='devnet',transaction_base64=base64.b64encode(wire).decode())
    result=prospective.observe_signed(request,rpc=RPC(),store=StudyStore(tmp_path/'signed.db'),
        scorer=lambda *args:{'status':'unavailable','scores':{}})
    assert result['check']['candidate_message_sha256']==hashlib.sha256(message).hexdigest()
    assert result['check']['simulation']['signature_verification'] is True
    assert 'sendTransaction' not in calls and not result['check']['broadcast']


def test_unsigned_candidate_is_refused_by_signed_observer():
    wire=b'\x01'+bytes(64)+transfer_message(SENDER,RECIPIENT,SYSTEM,1)
    request=prospective.SignedObservation(network='devnet',transaction_base64=base64.b64encode(wire).decode())
    with pytest.raises(ValueError,match='signed transaction'):prospective.observe_signed(request)


def test_history_refresh_deduplicates_running_jobs(monkeypatch):
    tasks=[]
    class Thread:
        def __init__(self,**kw):self.target=kw['target']
        def start(self):tasks.append(self.target)
    monkeypatch.setattr(prospective,'_history_jobs',{})
    monkeypatch.setattr(prospective.threading,'Thread',Thread)
    assert prospective.refresh_history('devnet')['status']=='running'
    assert prospective.refresh_history('devnet')['status']=='running'
    assert len(tasks)==1
