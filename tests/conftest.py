"""Shared fixture builders for offline tests. Nothing here makes network
calls; FakeSolanaRPCClient returns canned data in place of SolanaRPCClient.
"""
from __future__ import annotations

SOL_MINT = "SOL"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def _account_keys(pubkeys: list[str]) -> list[dict]:
    return [{"pubkey": p, "signer": i == 0, "source": "transaction", "writable": True} for i, p in enumerate(pubkeys)]


def make_transfer_tx(slot, block_time, sender, receiver, lamports, err=None):
    keys = [sender, receiver]
    pre = [10_000_000_000, 1_000_000_000]
    post = [pre[0] - lamports, pre[1] + lamports] if err is None else list(pre)
    return {
        "slot": slot,
        "blockTime": block_time,
        "transaction": {
            "signatures": [f"sig-{sender}-{receiver}-{slot}"],
            "message": {"accountKeys": _account_keys(keys), "instructions": []},
        },
        "meta": {
            "err": err,
            "fee": 5000,
            "preBalances": pre,
            "postBalances": post,
            "preTokenBalances": [],
            "postTokenBalances": [],
            "logMessages": [],
            "innerInstructions": [],
        },
    }


def make_token_swap_tx(
    slot,
    block_time,
    wallet,
    mint_in,
    amount_in,
    mint_out,
    amount_out,
    tx_index=None,
    err=None,
    sig=None,
):
    """A swap for `wallet`: mint_in leg valued via SOL preBalances/postBalances
    if mint_in/mint_out == SOL_MINT, otherwise via token balances at
    accountIndex 1 (in-mint) / 2 (out-mint). Covers SOL<->token and
    token<->token cases used across the test suite."""
    keys = [wallet, f"{wallet}-acct-in", f"{wallet}-acct-out"]
    pre_token_balances = []
    post_token_balances = []
    pre_sol = [10_000_000_000, 0, 0]
    post_sol = list(pre_sol)

    def add_token_leg(idx, mint, pre_ui, post_ui):
        pre_token_balances.append(
            {"accountIndex": idx, "mint": mint, "owner": wallet, "uiTokenAmount": {"uiAmount": pre_ui}}
        )
        post_token_balances.append(
            {"accountIndex": idx, "mint": mint, "owner": wallet, "uiTokenAmount": {"uiAmount": post_ui}}
        )

    if mint_in == SOL_MINT:
        post_sol[0] = pre_sol[0] - int(amount_in * 1e9)
    else:
        add_token_leg(1, mint_in, amount_in, 0.0)

    if mint_out == SOL_MINT:
        post_sol[0] = post_sol[0] + int(amount_out * 1e9)
    else:
        add_token_leg(2, mint_out, 0.0, amount_out)

    return {
        "slot": slot,
        "blockTime": block_time,
        "transactionIndex": tx_index if tx_index is not None else 0,
        "transaction": {
            "signatures": [sig or f"sig-{wallet}-{slot}-{tx_index}"],
            "message": {"accountKeys": _account_keys(keys), "instructions": []},
        },
        "meta": {
            "err": err,
            "fee": 5000,
            "preBalances": pre_sol,
            "postBalances": post_sol,
            "preTokenBalances": pre_token_balances,
            "postTokenBalances": post_token_balances,
            "logMessages": [],
            "innerInstructions": [],
        },
    }


def make_block(slot, txs: list[dict]) -> dict:
    block_txs = []
    for i, tx in enumerate(txs):
        t = dict(tx)
        t["transactionIndex"] = i
        block_txs.append(t)
    return {"parentSlot": slot - 1, "blockTime": txs[0]["blockTime"] if txs else 0, "transactions": block_txs}


SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"


class FakeSolanaRPCClient:
    def __init__(
        self,
        blocks: dict[int, dict] | None = None,
        signatures: dict[str, list[dict]] | None = None,
        account_owners: dict[str, str] | None = None,
    ):
        self._blocks = blocks or {}
        self._signatures = signatures or {}
        # default: any account not listed here is treated as a wallet (System-Program-owned)
        self._account_owners = account_owners or {}

    def get_block(self, slot: int) -> dict | None:
        return self._blocks.get(slot)

    def get_signatures_for_address(self, address: str, limit: int = 1000, before: str | None = None) -> list[dict]:
        return self._signatures.get(address, [])

    def get_account_info(self, address: str) -> dict | None:
        owner = self._account_owners.get(address, SYSTEM_PROGRAM_ID)
        return {"value": {"owner": owner}}
