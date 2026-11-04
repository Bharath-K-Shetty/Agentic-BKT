"""Read-only pre-send checks for a plain SOL transfer.

No keys, signing, airdrops, retries of payments, or broadcast RPCs. This product
feature is simulation-based and distinct from the historical ML experiment.
"""
import base64
import hashlib
from decimal import Decimal, InvalidOperation, localcontext
from datetime import datetime,timezone
import struct
import time

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router=APIRouter()
RPC_URLS={'devnet':'https://api.devnet.solana.com','mainnet':'https://api.mainnet-beta.solana.com'}
ALPHABET='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
SYSTEM='11111111111111111111111111111111'
LAMPORTS=1_000_000_000


def public_key(value):
    if not isinstance(value,str) or not 32<=len(value)<=44 or any(c not in ALPHABET for c in value):
        raise ValueError('Enter a valid 32-byte Solana address.')
    n=0
    for c in value:n=n*58+ALPHABET.index(c)
    decoded=b'\0'*(len(value)-len(value.lstrip('1')))+(n.to_bytes((n.bit_length()+7)//8,'big') if n else b'')
    if len(decoded)!=32:raise ValueError('Enter a valid 32-byte Solana address.')
    return decoded


def amount_lamports(value):
    try:
        amount=Decimal(value)
    except (InvalidOperation,TypeError,ValueError):raise ValueError('Enter a positive amount in SOL.')
    if not amount.is_finite() or amount<=0 or amount>Decimal(2**64-1)/LAMPORTS:
        raise ValueError('Enter a positive amount within the transfer limit.')
    with localcontext() as ctx:
        ctx.prec=80
        scaled=amount*LAMPORTS
    if scaled!=scaled.to_integral_value():raise ValueError('SOL amounts support at most 9 decimal places.')
    return int(scaled)


def sol(value):
    return format(Decimal(value)/LAMPORTS,'f')


def base58_encode(value):
    n=int.from_bytes(value,'big');out=''
    while n:n,remainder=divmod(n,58);out=ALPHABET[remainder]+out
    return '1'*(len(value)-len(value.lstrip(b'\0')))+out


def decode_plain_transfer(wire):
    if len(wire)!=215 or wire[0]!=1:
        raise ValueError('Only a single-signature legacy plain SOL transfer is supported.')
    message=wire[65:]
    sender=base58_encode(message[4:36]);recipient=base58_encode(message[36:68])
    blockhash=base58_encode(message[100:132]);amount=struct.unpack('<Q',message[142:150])[0]
    if amount==0 or message!=transfer_message(sender,recipient,blockhash,amount):
        raise ValueError('Transaction message is not the supported plain SOL transfer format.')
    return sender,recipient,amount,message


def transfer_message(sender,recipient,blockhash,amount):
    if sender==recipient:raise ValueError('Use different sender and recipient addresses for this check.')
    if SYSTEM in (sender,recipient):raise ValueError('Use wallet addresses, not the System Program address.')
    keys=public_key(sender)+public_key(recipient)+public_key(SYSTEM)
    # Legacy message: one writable signer, writable destination, read-only System.
    instruction=b'\x02\x02\x00\x01\x0c'+struct.pack('<IQ',2,amount)
    return b'\x01\x00\x01\x03'+keys+public_key(blockhash)+b'\x01'+instruction


class RpcUnavailable(Exception):pass


class ReadOnlyRPC:
    ALLOWED={'getLatestBlockhash','getFeeForMessage','getBalance','simulateTransaction'}
    def __init__(self,network):self.url=RPC_URLS[network]
    def call(self,method,params):
        if method not in self.ALLOWED:raise ValueError('Unsupported read-only method')
        try:
            r=requests.post(self.url,json={'jsonrpc':'2.0','id':1,'method':method,'params':params},timeout=(4,10))
            r.raise_for_status();body=r.json()
        except (requests.RequestException,ValueError) as e:raise RpcUnavailable('The public network endpoint is unavailable or busy. Try the check again later.') from e
        if 'error' in body:raise RpcUnavailable('The network endpoint could not complete this check. No transaction was sent.')
        if 'result' not in body:raise RpcUnavailable('The endpoint returned an incomplete response.')
        return body['result']


def instruction_advice(error):
    text=str(error)
    if 'InsufficientFundsForRent' in text:return 'The transfer may leave an account below its required minimum balance. Review the amount and recipient account.'
    if 'InsufficientFunds' in text or 'AccountNotFound' in text:return 'Check that the sender is funded on the selected network and can cover the transfer plus fees.'
    if 'BlockhashNotFound' in text:return 'The network could not use this recent block reference. Run a fresh check.'
    if 'InvalidAccount' in text:return 'Check that both addresses are suitable for this transfer.'
    return 'Simulation reported an execution problem. Review the transfer details before trying to send.'


def check_transfer(sender,recipient,amount,network,rpc=None):
    started=time.monotonic()
    if network not in RPC_URLS:raise ValueError('Choose devnet or mainnet.')
    public_key(sender);public_key(recipient)
    lamports=amount_lamports(amount)
    # Validate before making any network call.
    transfer_message(sender,recipient,SYSTEM,lamports)
    client=rpc or ReadOnlyRPC(network)
    config={'commitment':'confirmed'}
    latest=client.call('getLatestBlockhash',[config])
    blockhash=latest['value']['blockhash'];slot=latest['context']['slot']
    ctx={**config,'minContextSlot':slot}
    message=transfer_message(sender,recipient,blockhash,lamports)
    quoted=client.call('getFeeForMessage',[base64.b64encode(message).decode(),ctx])
    fee=quoted['value']
    if not isinstance(fee,int) or isinstance(fee,bool) or fee<0:
        raise RpcUnavailable('No fee quote is available for this block reference. Run a fresh check.')
    balance=client.call('getBalance',[sender,ctx])['value']
    if not isinstance(balance,int) or isinstance(balance,bool) or balance<0:raise RpcUnavailable('No valid balance was returned.')
    shortfall=max(0,lamports+fee-balance)
    simulation=None
    if not shortfall:
        # One deliberately empty signature; server never signs or broadcasts.
        transaction=base64.b64encode(b'\x01'+bytes(64)+message).decode()
        simulation=client.call('simulateTransaction',[transaction,{**ctx,'encoding':'base64',
            'sigVerify':False,'replaceRecentBlockhash':False}])
        if not isinstance(simulation.get('value'),dict) or 'err' not in simulation['value']:
            raise RpcUnavailable('Simulation returned an incomplete response.')
    error=simulation['value']['err'] if simulation is not None else None
    if shortfall:
        status='needs_attention';headline='Balance is too low for this transfer'
        action=f'Add at least {sol(shortfall)} SOL or reduce the amount, then check again. Confirm the selected network.'
    elif error is not None:
        status='needs_attention';headline='Simulation found a problem';action=instruction_advice(error)
    else:
        status='simulation_passed';headline='Simulation passed at the checked state'
        action='No execution error was found in this unsigned simulation. Check again if the amount, addresses or network state changes.'
    return {'status':status,'headline':headline,'action':action,'network':network,
        'candidate_message_base64':base64.b64encode(message).decode(),
        'candidate_message_sha256':hashlib.sha256(message).hexdigest(),
        'unsigned_transaction_base64':base64.b64encode(b'\x01'+bytes(64)+message).decode(),
        'last_valid_block_height':latest['value'].get('lastValidBlockHeight'),
        'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'transfer_sol':sol(lamports),'balance_sol':sol(balance),'estimated_fee_sol':sol(fee),
        'required_sol':sol(lamports+fee),'shortfall_sol':sol(shortfall),
        'simulation':{'performed':simulation is not None,'error':error,
            'units_consumed':simulation['value'].get('unitsConsumed') if simulation else None,
            'signature_verification':False},
        'slot':slot,'checked_ms':round((time.monotonic()-started)*1000),
        'broadcast':False,'actual_fee_paid_sol':'0','measured_fee_savings_sol':None,'measured_time_saved_seconds':None,
        'limits':['Fee quote covers this plain transfer message; required balance may be affected by account minimums.',
            'Simulation does not verify signatures and cannot guarantee later execution.',
            'The historical ML model is not used for this live check.',
            'No fee savings or retry-time savings have been measured. A failed submission may not incur the quoted fee.']}


class TransferRequest(BaseModel):
    sender:str=Field(min_length=32,max_length=44)
    recipient:str=Field(min_length=32,max_length=44)
    amount_sol:str=Field(min_length=1,max_length=32)
    network:str='devnet'


@router.post('/api/transfer-check')
def transfer_check(request:TransferRequest):
    try:return check_transfer(request.sender.strip(),request.recipient.strip(),request.amount_sol.strip(),request.network)
    except ValueError as e:raise HTTPException(422,str(e)) from e
    except RpcUnavailable as e:raise HTTPException(503,str(e)) from e
    except (KeyError,TypeError,IndexError) as e:raise HTTPException(503,'The network returned incomplete check data. No transaction was sent.') from e
