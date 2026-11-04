"""Local append-only decisions and independently verified matching receipts."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import threading
import uuid
import struct

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from webapp.backend.transfer_check import (TransferRequest,check_transfer,RpcUnavailable,ALPHABET,
    RPC_URLS,decode_plain_transfer,sol)
from webapp.backend.live_history import HistoryRPC, score_live, collect_snapshot, snapshot_path
from webapp.backend.runtime_paths import state_directory

ROOT=Path(__file__).resolve().parents[2]
router=APIRouter()
_history_jobs={}
_history_lock=threading.Lock()


@router.get('/api/live/history/{network}')
def history_status(network:str):
    if network not in ('devnet','mainnet'):raise HTTPException(422,'Choose devnet or mainnet.')
    with _history_lock:job=dict(_history_jobs.get(network,{'status':'idle'}))
    path=snapshot_path(network)
    if path.exists():
        try:
            snapshot=json.loads(path.read_text())
            job['snapshot']={'records':len(snapshot['rows']),'blocks':len(snapshot['sampled_blocks']),
                'age_seconds':max(0,int(time.time())-snapshot['completed_ts'])}
        except (OSError,ValueError,KeyError):job['snapshot']=None
    return job


@router.post('/api/live/history/{network}/refresh')
def refresh_history(network:str):
    if network not in ('devnet','mainnet'):raise HTTPException(422,'Choose devnet or mainnet.')
    with _history_lock:
        if _history_jobs.get(network,{}).get('status')=='running':return {'status':'running'}
        _history_jobs[network]={'status':'running'}
    def collect():
        try:
            summary=collect_snapshot(network,16 if network=='devnet' else 8)
            result={'status':'completed','records':summary['row_count'],'blocks':len(summary['sampled_blocks'])}
        except Exception as error:
            result={'status':'failed','reason':str(error)}
        with _history_lock:_history_jobs[network]=result
    threading.Thread(target=collect,daemon=True,name=f'history-{network}').start()
    return {'status':'running'}


class StudyStore:
    def __init__(self,path=None):
        self.path=path or state_directory(ROOT)/'prospective.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL, recorded_ts REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(decision_id TEXT PRIMARY KEY REFERENCES decisions(id),
                    signature TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, recorded_ts REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS abstentions(decision_id TEXT PRIMARY KEY REFERENCES decisions(id),
                    reason TEXT NOT NULL, recorded_ts REAL NOT NULL);
                CREATE TRIGGER IF NOT EXISTS freeze_decisions_update BEFORE UPDATE ON decisions
                    BEGIN SELECT RAISE(ABORT,'Decisions are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS freeze_decisions_delete BEFORE DELETE ON decisions
                    BEGIN SELECT RAISE(ABORT,'Decisions are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS freeze_receipts_update BEFORE UPDATE ON receipts
                    BEGIN SELECT RAISE(ABORT,'Receipts are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS freeze_receipts_delete BEFORE DELETE ON receipts
                    BEGIN SELECT RAISE(ABORT,'Receipts are immutable'); END;
            ''')

    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def record(self,payload):
        identity=str(uuid.uuid4())
        text=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)
        digest=hashlib.sha256(text.encode()).hexdigest()
        with self.connect() as db:
            db.execute('INSERT INTO decisions VALUES(?,?,?,?)',(identity,text,digest,time.time()))
        return {'decision_id':identity,'decision_sha256':digest}

    def decision(self,identity):
        with self.connect() as db:
            row=db.execute('SELECT payload,payload_sha256,recorded_ts FROM decisions WHERE id=?',(identity,)).fetchone()
        if not row:raise ValueError('Unknown study decision.')
        if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('Stored decision hash mismatch.')
        return json.loads(row[0]),row[2]

    def attach(self,identity,signature,rpc=None):
        decision,recorded_ts=self.decision(identity)
        if not isinstance(signature,str) or not 64<=len(signature)<=88 or any(c not in ALPHABET for c in signature):
            raise ValueError('Enter a valid transaction signature.')
        rpc=rpc or HistoryRPC(decision['network'])
        receipt=rpc.call('getTransaction',[signature,{'encoding':'base64','commitment':'confirmed',
                                                     'maxSupportedTransactionVersion':0}])
        if receipt is None:return {'status':'pending_or_unavailable','fee_paid_lamports':None,'outcome':None}
        encoded=receipt.get('transaction')
        if not isinstance(encoded,list) or encoded[1]!='base64':raise ValueError('Receipt transaction encoding is unavailable.')
        wire=base64.b64decode(encoded[0],validate=True)
        # This study supports the checker's one-signature plain legacy transfer only.
        if len(wire)!=215 or wire[0]!=1:raise ValueError('Receipt is not a supported plain transfer.')
        message=wire[65:]
        expected=decision['check']['candidate_message_sha256']
        if hashlib.sha256(message).hexdigest()!=expected:
            raise ValueError('This receipt belongs to a different transaction message. No outcome was attached.')
        n=0
        for c in signature:n=n*58+ALPHABET.index(c)
        decoded=b'\0'*(len(signature)-len(signature.lstrip('1')))+n.to_bytes((n.bit_length()+7)//8,'big')
        if len(decoded)!=64 or decoded!=wire[1:65]:raise ValueError('Receipt signature does not match the requested signature.')
        if receipt['slot']<=decision['check']['slot'] or not isinstance(receipt.get('blockTime'),int) or receipt['blockTime']<int(recorded_ts):
            raise ValueError('Receipt predates the recorded decision; it cannot be prospective evidence.')
        meta=receipt.get('meta')
        if not isinstance(meta,dict) or 'err' not in meta or not isinstance(meta.get('fee'),int):
            raise ValueError('Receipt has incomplete execution evidence.')
        if meta['fee']<0:raise ValueError('Invalid paid fee in receipt.')
        pre,post=meta.get('preBalances'),meta.get('postBalances')
        if not isinstance(pre,list) or not isinstance(post,list) or len(pre)!=3 or len(post)!=3:
            raise ValueError('Receipt lacks the three account balance measurements.')
        amount=struct.unpack('<Q',message[142:150])[0]
        delivered=amount if meta['err'] is None else 0
        if pre[0]-post[0]!=meta['fee']+delivered or post[1]-pre[1]!=delivered:
            raise ValueError('Receipt balances do not agree with the fee and transfer outcome.')
        observed={'signature':signature,'outcome':'Failed' if meta['err'] is not None else 'Succeeded',
                  'fee_paid_lamports':meta['fee'],'error':meta['err'],'receipt':receipt,
                  'receipt_sha256':hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()).hexdigest(),
                  'measured_fee_savings_lamports':None,'measured_time_saved_seconds':None,
                  'elapsed_from_decision_to_block_seconds':receipt['blockTime']-recorded_ts,
                  'timing_scope':'Observation interval includes user delay; not network latency or time saved.'}
        try:
            with self.connect() as db:
                db.execute('INSERT INTO receipts VALUES(?,?,?,?)',
                    (identity,signature,json.dumps(observed,sort_keys=True),time.time()))
        except sqlite3.IntegrityError as error:raise ValueError('This decision or receipt has already been linked.') from error
        return {'status':'verified',**observed}

    def summary(self):
        with self.connect() as db:
            decisions=db.execute('SELECT id,payload,recorded_ts FROM decisions ORDER BY recorded_ts DESC').fetchall()
            receipts={r[0]:json.loads(r[1]) for r in db.execute('SELECT decision_id,payload FROM receipts')}
        rows=[]
        for identity,payload,ts in decisions:
            data=json.loads(payload);outcome=receipts.get(identity)
            rows.append({'decision_id':identity,'network':data['network'],
                'recorded_at_utc':datetime.fromtimestamp(ts,timezone.utc).isoformat(),
                'simulation_performed':data['check']['simulation']['performed'],
                'simulation_error':data['check']['simulation']['error'],
                'ml_status':data['ml']['status'],
                'verified_outcome':outcome['outcome'] if outcome else None,
                'fee_paid_lamports':outcome['fee_paid_lamports'] if outcome else None})
        return {'decisions':rows,'recorded_decisions':len(rows),'verified_receipts':len(receipts),
                'measured_fee_savings_lamports':None,'measured_time_saved_seconds':None,
                'scope':'Observational study; missing receipts are unknown outcomes, never successes or savings.'}


@router.post('/api/live/analyze')
def analyze(request:TransferRequest):
    try:
        check=check_transfer(request.sender.strip(),request.recipient.strip(),request.amount_sol.strip(),request.network)
        ml=score_live(request.sender.strip(),request.recipient.strip(),request.network)
        decision={'network':request.network,'sender':request.sender.strip(),'recipient':request.recipient.strip(),
                  'amount_sol':request.amount_sol.strip(),'check':check,'ml':ml,
                  'simulation_scope':'Unsigned simulation with sigVerify=false; not signed submission preflight.',
                  'recorded_at_utc':datetime.now(timezone.utc).isoformat()}
        study=StudyStore().record(decision)
        return {**decision,**study,'next_action':check['action'],
                'fee_savings_claim':'Unproven; quote and paid receipt fees are not savings.'}
    except ValueError as error:raise HTTPException(422,str(error)) from error
    except RpcUnavailable as error:raise HTTPException(503,str(error)) from error
    except (KeyError,TypeError,IndexError,OSError) as error:raise HTTPException(503,'Incomplete network or history data. No transaction was sent.') from error


class ReceiptRequest(BaseModel):
    signature:str=Field(min_length=64,max_length=88)


class SignedObservation(BaseModel):
    network:str='devnet'
    transaction_base64:str=Field(min_length=280,max_length=400)


def observe_signed(request:SignedObservation,rpc=None,store=None,scorer=score_live):
    if request.network not in RPC_URLS:raise ValueError('Choose devnet or mainnet.')
    wire=base64.b64decode(request.transaction_base64,validate=True)
    sender,recipient,amount,message=decode_plain_transfer(wire)
    if wire[1:65]==bytes(64):raise ValueError('This observation requires a signed transaction, not an empty signature.')
    rpc=rpc or HistoryRPC(request.network)
    slot=rpc.call('getSlot',[{'commitment':'confirmed'}])
    config={'commitment':'confirmed','minContextSlot':slot}
    quote=rpc.call('getFeeForMessage',[base64.b64encode(message).decode(),config])['value']
    if not isinstance(quote,int) or isinstance(quote,bool) or quote<0:
        raise RpcUnavailable('No fee quote is available; the candidate blockhash may have expired.')
    balance=rpc.call('getBalance',[sender,config])['value']
    simulation=rpc.call('simulateTransaction',[request.transaction_base64,
        {**config,'encoding':'base64','sigVerify':True,'replaceRecentBlockhash':False}])
    if 'err' not in simulation.get('value',{}):raise RpcUnavailable('Signed simulation returned incomplete data.')
    error=simulation['value']['err']
    check={'status':'simulation_passed' if error is None else 'needs_attention','slot':slot,
        'candidate_message_base64':base64.b64encode(message).decode(),
        'candidate_message_sha256':hashlib.sha256(message).hexdigest(),
        'simulation':{'performed':True,'error':error,'signature_verification':True,
                      'units_consumed':simulation['value'].get('unitsConsumed')},
        'transfer_sol':sol(amount),'balance_sol':sol(balance),'estimated_fee_sol':sol(quote),
        'broadcast':False,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    payload={'network':request.network,'sender':sender,'recipient':recipient,'amount_sol':sol(amount),
        'check':check,'ml':scorer(sender,recipient,request.network),
        'simulation_scope':'Signed simulation with signature verification; equivalent checks, but not a sendTransaction submission/preflight event.'}
    return {**payload,**(store or StudyStore()).record(payload)}


@router.post('/api/live/signed-observe')
def signed_observation(request:SignedObservation):
    try:return observe_signed(request)
    except ValueError as error:raise HTTPException(422,str(error)) from error
    except RpcUnavailable as error:raise HTTPException(503,str(error)) from error
    except (KeyError,TypeError,IndexError,OSError) as error:raise HTTPException(503,'Incomplete observation; no transaction was submitted.') from error


@router.post('/api/study/{identity}/receipt')
def attach_receipt(identity:str,request:ReceiptRequest):
    try:return StudyStore().attach(identity,request.signature)
    except ValueError as error:raise HTTPException(422,str(error)) from error
    except RpcUnavailable as error:raise HTTPException(503,str(error)) from error
    except (KeyError,TypeError,IndexError) as error:raise HTTPException(503,'Incomplete receipt data; no outcome was attached.') from error


@router.get('/api/study')
def study_summary():return StudyStore().summary()


@router.get('/api/study/{identity}')
def study_decision(identity:str):
    try:
        payload,_=StudyStore().decision(identity)
        return payload
    except ValueError as error:raise HTTPException(404,str(error)) from error
