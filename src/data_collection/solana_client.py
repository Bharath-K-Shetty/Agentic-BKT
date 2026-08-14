"""Minimal Solana JSON-RPC client for pulling public wallet transaction history.

No API key required by default (uses the public mainnet-beta RPC), but that
endpoint is aggressively rate-limited. Set SOLANA_RPC_URL to point at a
dedicated provider (Helius/QuickNode/etc) once real data collection starts.
"""
from __future__ import annotations

import os
import time

import requests

DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com"


class SolanaRPCError(RuntimeError):
    pass


class SolanaRPCClient:
    def __init__(self, rpc_url: str | None = None, min_interval_s: float = 0.4, max_retries: int = 5):
        self.rpc_url = rpc_url or os.environ.get("SOLANA_RPC_URL", DEFAULT_RPC_URL)
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self._last_call_ts = 0.0
        self._session = requests.Session()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call_ts
        wait = self.min_interval_s - elapsed
        if wait > 0:
            time.sleep(wait)

    def _call(self, method: str, params: list) -> dict:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            self._throttle()
            self._last_call_ts = time.monotonic()
            try:
                resp = self._session.post(self.rpc_url, json=payload, timeout=30)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            body = resp.json()
            if "error" in body:
                raise SolanaRPCError(f"{method} failed: {body['error']}")
            return body["result"]
        raise SolanaRPCError(f"{method} failed after {self.max_retries} retries") from last_exc

    def get_signatures_for_address(self, address: str, limit: int = 1000, before: str | None = None) -> list[dict]:
        params: list = [address, {"limit": limit}]
        if before:
            params[1]["before"] = before
        return self._call("getSignaturesForAddress", params)

    def get_transaction(self, signature: str) -> dict | None:
        params = [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
        ]
        return self._call("getTransaction", params)
