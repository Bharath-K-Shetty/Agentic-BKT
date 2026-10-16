"""Shared parsing helpers over the raw `jsonParsed` Solana transaction schema
saved by `src.data_collection.fetch_wallet_history`.

DEX/AMM instruction data (Raydium, Orca, Jupiter, Pump.fun, ...) is not
decodable without each program's IDL, which this project does not fetch. All
label/feature logic therefore infers what happened from balance deltas
(`meta.preBalances`/`postBalances` for SOL, `meta.preTokenBalances`/
`postTokenBalances` for SPL tokens) rather than from decoding instructions.
`KNOWN_PROGRAM_IDS` is used only as a classification hint, never as a
correctness requirement.
"""
from __future__ import annotations

from dataclasses import dataclass

SOL = "SOL"  # pseudo-mint used for native SOL balance deltas
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"

KNOWN_PROGRAM_IDS = {
    "11111111111111111111111111111111": "system",
    "Vote111111111111111111111111111111111111111": "vote",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "spl_token",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "assoc_token_account",
    "ComputeBudget111111111111111111111111111111": "compute_budget",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "raydium_amm_v4",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "orca_whirlpool",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "jupiter_v6",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pump_fun",
}


@dataclass(frozen=True)
class TokenDelta:
    owner: str
    mint: str
    pre_ui: float
    post_ui: float

    @property
    def delta(self) -> float:
        return self.post_ui - self.pre_ui


def is_failed(tx: dict) -> bool:
    return tx.get("meta", {}).get("err") is not None


def signature(tx: dict) -> str:
    sigs = tx.get("transaction", {}).get("signatures", [])
    return sigs[0] if sigs else ""


def account_keys(tx: dict) -> list[str]:
    return [a["pubkey"] for a in tx["transaction"]["message"]["accountKeys"]]


def signer_keys(tx: dict) -> set[str]:
    return {
        a["pubkey"]
        for a in tx["transaction"]["message"]["accountKeys"]
        if a.get("signer")
    }


def program_ids(tx: dict) -> set[str]:
    msg = tx["transaction"]["message"]
    ids = {ix["programId"] for ix in msg.get("instructions", [])}
    for inner in tx.get("meta", {}).get("innerInstructions", []):
        ids |= {ix["programId"] for ix in inner.get("instructions", []) if "programId" in ix}
    return ids


def token_deltas(tx: dict) -> list[TokenDelta]:
    """One TokenDelta per (accountIndex) touched by pre/postTokenBalances,
    joined on accountIndex (the only stable key jsonParsed guarantees)."""
    meta = tx.get("meta", {})
    pre = {b["accountIndex"]: b for b in meta.get("preTokenBalances", [])}
    post = {b["accountIndex"]: b for b in meta.get("postTokenBalances", [])}
    deltas = []
    for idx in set(pre) | set(post):
        entry = post.get(idx) or pre.get(idx)
        owner = entry.get("owner")
        mint = entry["mint"]
        pre_ui = (pre[idx]["uiTokenAmount"]["uiAmount"] or 0.0) if idx in pre and pre[idx]["uiTokenAmount"]["uiAmount"] is not None else 0.0
        post_ui = (post[idx]["uiTokenAmount"]["uiAmount"] or 0.0) if idx in post and post[idx]["uiTokenAmount"]["uiAmount"] is not None else 0.0
        if owner is None:
            continue
        deltas.append(TokenDelta(owner=owner, mint=mint, pre_ui=pre_ui, post_ui=post_ui))
    return deltas


def sol_deltas(tx: dict) -> dict[str, float]:
    """pubkey -> ui SOL delta (post - pre) / 1e9, indexed by accountKeys position."""
    meta = tx.get("meta", {})
    pre = meta.get("preBalances", [])
    post = meta.get("postBalances", [])
    keys = account_keys(tx)
    out: dict[str, float] = {}
    for i, key in enumerate(keys):
        if i >= len(pre) or i >= len(post):
            continue
        delta_lamports = post[i] - pre[i]
        out[key] = out.get(key, 0.0) + delta_lamports / 1e9
    return out


def wallet_net_deltas(tx: dict, wallet: str) -> dict[str, float]:
    """{mint_or_SOL: ui delta} for a single owner, merging SOL + all SPL
    mints they hold a balance-changing account for in this tx. SOL delta
    excludes tx fee attribution nuance (fee payer's SOL delta includes fee)
    intentionally left in — swap-detection thresholds are amount-scale, not
    exact-zero-sensitive.

    Wrapped SOL (`WRAPPED_SOL_MINT`) is folded into the same `SOL` bucket as
    native SOL: without this, a plain wrap/unwrap (or a multi-hop route that
    passes through wSOL) shows up as a false-positive "swap" between SOL and
    itself, since native SOL and wSOL are tracked through entirely different
    fields (`preBalances`/`postBalances` vs. `preTokenBalances`/
    `postTokenBalances`) in the raw transaction."""
    out: dict[str, float] = {}
    sol = sol_deltas(tx).get(wallet)
    if sol is not None and abs(sol) > 0:
        out[SOL] = sol
    for td in token_deltas(tx):
        if td.owner != wallet:
            continue
        if abs(td.delta) > 0:
            mint = SOL if td.mint == WRAPPED_SOL_MINT else td.mint
            out[mint] = out.get(mint, 0.0) + td.delta
    return out
