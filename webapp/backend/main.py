"""HOMIE demo backend: a thin API over the real src/ analysis pipeline
(swap/rug-pull/slippage detection + feature extraction) for a live college
presentation. Deliberately does NOT execute any real transaction, and does
NOT present the Part 1 GBDT model's probability as a trustworthy
prediction (current AUC ~0.48 at N=127, see docs/RESEARCH_NOTES.md) --
the risk analysis shown here is built from real, concretely-detected
on-chain events instead, which is honest and still substantive.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.data_collection.fetch_wallet_history import fetch_signatures, fetch_transactions
from src.data_collection.solana_client import SolanaRPCClient
from src.features.wallet_features import extract_wallet_features
from src.labels.build_labels import compute_all_labels
from webapp.backend.learning import router as learning_router

RAW_DIR = ROOT / "data" / "raw"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

WALLET_RE = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")

DEMO_WALLETS = [
    {
        "address": "9nXDunV8eNvYSVys7JSBkm2hz9Q79Q3EYeko19srVeMC",
        "label": "High-risk wallet",
    },
    {
        "address": "5SoF3RbNTMotKuWk2eCfU5bfLxpH47rpxFYgt89ruzEP",
        "label": "Active, clean-history wallet",
    },
]

app = FastAPI(title="HOMIE demo API")
app.include_router(learning_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8420", "http://localhost:8420"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    wallet: str


class ChatRequest(BaseModel):
    message: str


def _load_raw(wallet: str, max_txs: int = 40) -> list[dict]:
    path = RAW_DIR / f"{wallet}.json"
    if path.exists():
        return json.loads(path.read_text())
    client = SolanaRPCClient()
    signatures = fetch_signatures(client, wallet, max_txs)
    if not signatures:
        raise HTTPException(status_code=404, detail="No on-chain activity found for this address.")
    return fetch_transactions(client, signatures)


def _risk_score(summary: dict, total_rug_loss_sol: float) -> tuple[int, str]:
    """Transparent, rule-based score from real detected events -- not the
    ML model's probability output, which isn't trustworthy yet at current
    N (see docs/RESEARCH_NOTES.md)."""
    score = 0
    score += summary["n_rugpull_realized_dump"] * 15
    score += summary["n_rugpull_abandoned_bag"] * 5
    score += summary["n_sandwich_victim"] * 20
    score += min(20, total_rug_loss_sol * 2)
    score = min(100, round(score))
    if score >= 50:
        level = "high"
    elif score >= 15:
        level = "medium"
    else:
        level = "low"
    return score, level


def _explanations(summary: dict, features: dict, total_rug_loss_sol: float) -> list[str]:
    lines = []
    if summary["n_rugpull_realized_dump"] > 0:
        lines.append(
            f"Found {summary['n_rugpull_realized_dump']} realized rug-pull dump(s) "
            f"in this wallet's swap history, totaling ~{total_rug_loss_sol:.3f} SOL in realized losses."
        )
    if summary["n_sandwich_victim"] > 0:
        lines.append(f"This wallet was sandwich-attacked {summary['n_sandwich_victim']} time(s).")
    if summary["n_rugpull_abandoned_bag"] > 0:
        lines.append(f"{summary['n_rugpull_abandoned_bag']} token(s) were bought and never sold (abandoned bags).")
    avg_slip = features.get("avg_slippage_vs_history")
    if avg_slip == avg_slip and avg_slip is not None:  # not NaN
        direction = "worse" if avg_slip < 0 else "better"
        lines.append(f"Average swap price ran {abs(avg_slip) * 100:.1f}% {direction} than this wallet's own trading history.")
    if not lines:
        lines.append("No rug-pull dumps or sandwich-attack victimhood detected in the analyzed window.")
    lines.append(f"Analysis covers {int(features['tx_count'])} transactions, {int(features['swap_count'])} of them swaps.")
    return lines


def _analyze(wallet: str) -> dict:
    raw_txs = _load_raw(wallet)
    labels = compute_all_labels(wallet, raw_txs, client=None)
    features = extract_wallet_features(wallet, raw_txs, labels=labels)
    summary = labels["summary"]
    total_rug_loss_sol = features["total_realized_rug_loss_sol"]
    score, level = _risk_score(summary, total_rug_loss_sol)

    return {
        "wallet": wallet,
        "risk_score": score,
        "risk_level": level,
        "summary": summary,
        "features": features,
        "explanations": _explanations(summary, features, total_rug_loss_sol),
        "rugpull_events": labels["rugpull_events"][:5],
    }


@app.get("/api/demo-wallets")
def demo_wallets():
    out = []
    for w in DEMO_WALLETS:
        try:
            analysis = _analyze(w["address"])
        except Exception:
            continue
        out.append({**w, "risk_score": analysis["risk_score"], "risk_level": analysis["risk_level"]})
    return out


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    wallet = req.wallet.strip()
    if not WALLET_RE.fullmatch(wallet):
        raise HTTPException(status_code=400, detail="That doesn't look like a valid Solana wallet address.")
    try:
        return _analyze(wallet)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't fetch on-chain data: {exc}") from exc


@app.post("/api/chat")
def chat(req: ChatRequest):
    message = req.message.strip()
    match = WALLET_RE.search(message)
    if match:
        try:
            analysis = _analyze(match.group(0))
        except HTTPException as exc:
            return {"reply": exc.detail, "analysis": None}
        risk_line = {
            "high": "This wallet looks high-risk.",
            "medium": "This wallet has some risk signals worth noting.",
            "low": "This wallet looks relatively clean.",
        }[analysis["risk_level"]]
        reply = risk_line + " " + " ".join(analysis["explanations"])
        return {"reply": reply, "analysis": analysis}

    lowered = message.lower()
    if any(k in lowered for k in ["what can you do", "help", "what are you"]):
        reply = (
            "I'm HOMIE's on-chain risk analysis assistant. Paste a Solana wallet address "
            "and I'll look through its real transaction history for rug-pull losses, "
            "sandwich-attack victimhood, and abnormal slippage -- all detected from live "
            "on-chain data, not guessed."
        )
    else:
        reply = "Paste a Solana wallet address and I'll analyze its real on-chain risk history."
    return {"reply": reply, "analysis": None}


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
