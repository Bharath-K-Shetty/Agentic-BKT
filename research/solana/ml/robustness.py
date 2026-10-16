"""Disjoint-token confirmation of the exploratory Solana prefix pilot."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import warnings
import zipfile

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from prefix_baseline import COORD, ROOT, metrics, prefix_features, threshold_at_fpr

HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE / "robustness_protocol.json"


def epoch(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def calendar_split(frame, fold):
    a, b, c = map(epoch, (fold["train_end"], fold["validation_end"], fold["test_end"]))
    train = frame[(frame.decision_ts < a) & (frame.label_ready_ts < a)]
    val = frame[(frame.decision_ts >= a) & (frame.decision_ts < b) & (frame.label_ready_ts < b)]
    test = frame[(frame.decision_ts >= b) & (frame.decision_ts < c)]
    return train, val, test


def novel_fraction(wallets, seen):
    return len(set(wallets) - seen) / len(set(wallets)) if wallets else None


def confirmation_sample(candidates, seed, excluded, n):
    ordered = sorted(set(candidates), key=lambda a: hashlib.sha256(f"{seed}:{a}".encode()).hexdigest())
    return ordered[excluded:excluded+n]


def build_features(protocol, path):
    raw = ROOT / "data/raw/melt"
    labels = pd.read_csv(raw / "label.csv")
    target = labels.set_index("mint_address").min_ratio.lt(.3).astype(int).to_dict()
    sources = json.loads((ROOT / "docs/results/blockchain_ml_source_probe.json").read_text())
    source = next(r for r in sources["files"] if r["repository"] == "git-disl/MELT"
                  and r["path"] == "data/memecoin/memecoin_list.jsonl")
    migration = {r["token_address"]: int(r["timestamp"]) for r in map(json.loads,
                 (ROOT / "data/raw/solana_ml_probe" / source["sha256"]).read_text().splitlines())}
    records, skipped = [], Counter()
    with zipfile.ZipFile(raw / "pre_migration_tx.zip") as archive:
        members = {Path(p).stem: p for p in archive.namelist()
                   if p.startswith("pre_migration_tx/") and p.endswith(".jsonl")}
        sample = confirmation_sample(set(target) & set(migration) & set(members), protocol["sample_seed"],
                                     protocol["exclude_first_hash_ranked_tokens"], protocol["confirmation_tokens"])
        if len(sample) != protocol["confirmation_tokens"]:
            raise ValueError("Insufficient disjoint tokens")
        for index, mint in enumerate(sample):
            events = list(map(json.loads, archive.read(members[mint]).splitlines()))
            if any(e["mint"] != mint for e in events):
                raise ValueError("Archive mint mismatch")
            mints = [e for e in events if "mint" in e["type"]]
            if not mints:
                skipped["missing_mint"] += 1
                continue
            t0 = min(int(e["timestamp"]) for e in mints)
            for horizon in (60, 300):
                if migration[mint] <= t0 + horizon:
                    skipped[f"{horizon}:already_migrated"] += 1
                    continue
                try:
                    _, f = prefix_features(events, horizon)
                except (ValueError, TypeError, KeyError) as error:
                    skipped[f"{horizon}:{error}"] += 1
                    continue
                # Only early wallets are retained for the overlap diagnostic.
                wallets = sorted({w for e in events if t0 <= int(e["timestamp"]) <= t0 + horizon
                                  for w, v in e.get("trader_map", {}).items() if float(v) != 0})
                records.append({"mint_address": mint, "decision_ts": t0 + horizon,
                                "label_ready_ts": migration[mint] + 3600, "horizon": horizon,
                                "label": target[mint], "wallets": wallets, **f})
            if (index + 1) % 1000 == 0:
                print(f"parsed {index+1}/{len(sample)} confirmation tokens", flush=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    audit = {"selected_tokens": len(sample), "selected_token_sha256": hashlib.sha256("\n".join(sample).encode()).hexdigest(),
             "excluded_pilot_rank_count": protocol["exclude_first_hash_ranked_tokens"], "skipped": dict(skipped)}
    path.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def fit_model(name, params, seed):
    if name == "random_forest":
        return RandomForestClassifier(**params, random_state=seed, n_jobs=4)
    if name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(**params, random_state=seed)
    params = {k: v for k, v in params.items() if k != "seeds"}
    return make_pipeline(StandardScaler(), LogisticRegression(**params))


def paired_period_bootstrap(periods, metric, repetitions=500, seed=42):
    """Resample days inside each period, keeping model predictions paired."""
    rng = np.random.default_rng(seed)
    def score(period, idx):
        y, a, b = period["y"][idx], period["base"][idx], period["coord"][idx]
        return metric(y, b) - metric(y, a)
    weights = np.array([len(p["y"]) for p in periods], dtype=float)
    weights /= weights.sum()
    estimate = float(sum(w * score(p, np.arange(len(p["y"]))) for w, p in zip(weights, periods)))
    draws = []
    grouped = [[np.flatnonzero(p["days"] == day) for day in np.unique(p["days"])] for p in periods]
    for _ in range(repetitions):
        deltas = []
        for p, groups in zip(periods, grouped):
            idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
            if np.unique(p["y"][idx]).size < 2:
                break
            deltas.append(score(p, idx))
        if len(deltas) == len(periods):
            draws.append(float(np.dot(weights, deltas)))
    return {"weighted_delta": estimate, "ci95": np.quantile(draws, [.025, .975]).tolist(),
            "valid_bootstrap_draws": len(draws)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-features", action="store_true")
    args = parser.parse_args()
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes)
    processed = ROOT / "data/processed/solana_ml"
    path = processed / "confirmation_12000.jsonl"
    audit = (json.loads(path.with_suffix(".audit.json").read_text()) if args.reuse_features
             else build_features(protocol, path))
    frame = pd.read_json(path, lines=True)
    pilot = pd.read_json(processed / "prefix_price_drop_6000_42.jsonl", lines=True)
    overlap = set(frame.mint_address) & set(pilot.mint_address)
    if overlap:
        raise ValueError("Confirmation tokens overlap pilot")
    columns = sorted(set(frame) - {"mint_address", "decision_ts", "label_ready_ts", "horizon", "label", "wallets"})
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "protocol": protocol,
              "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(), "audit": audit,
              "pilot_token_overlap": len(overlap), "results": [], "comparisons": [],
              "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__},
              "limits": ["Same historical MELT source period; token-disjoint confirmation is not an external dataset.",
                         "Only eventual migrants; price collapse is not confirmed fraud.",
                         "Wallet overlap diagnostic does not identify creators or operators.",
                         "Different horizon cohorts; scores cannot quantify benefit of waiting.",
                         "Bootstrap is conditional on fitted models; secondary comparisons are exploratory.",
                         "Protocol specified after pilot exploration, not a public preregistration.",
                         "These fixed models do not exhaust tuned 119-feature coordination or graph baselines."]}
    predictions, pairings = [], {}
    for horizon in (60, 300):
        for fold in protocol["folds"]:
            train, val, test = calendar_split(frame[frame.horizon == horizon], fold)
            for f in (train, val, test):
                if len(f) < 100 or f.label.nunique() != 2:
                    raise ValueError("Insufficient calendar partition")
            seen = {w for ws in train.wallets for w in ws}
            novelty_val = np.array([novel_fraction(ws, seen) for ws in val.wallets])
            novelty_test = np.array([novel_fraction(ws, seen) for ws in test.wallets])
            boundary = float(np.median(novelty_val))
            summary = {"horizon": horizon, "period": fold["name"],
                       "counts": {n: {"n": len(f), "prevalence": float(f.label.mean())} for n, f in
                                  [("train", train), ("validation", val), ("test", test)]},
                       "wallet_novelty_validation_median": boundary, "models": []}
            local_predictions = {}
            for name, params in protocol["models"].items():
                seeds = params.get("seeds", protocol["model_seeds"])
                for scope in ("base", "coord"):
                    cols = [c for c in columns if scope == "coord" or c not in COORD]
                    pv_all, pt_all, warning_text = [], [], []
                    for seed in seeds:
                        model = fit_model(name, params, seed)
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter("always")
                            model.fit(train[cols], train.label)
                        warning_text.extend(str(w.message) for w in caught)
                        pv, pt = model.predict_proba(val[cols])[:, 1], model.predict_proba(test[cols])[:, 1]
                        pv_all.append(pv); pt_all.append(pt)
                    pv, pt = np.mean(pv_all, axis=0), np.mean(pt_all, axis=0)
                    threshold = threshold_at_fpr(val.label.to_numpy(), pv)
                    subgroups = {}
                    for group, idx in {"high_wallet_novelty": novelty_test >= boundary,
                                       "low_wallet_novelty": novelty_test < boundary}.items():
                        subgroups[group] = {"n": int(idx.sum()), "metrics":
                                            metrics(test.label.to_numpy()[idx], pt[idx], threshold)
                                            if idx.sum() and test.label.to_numpy()[idx].min() != test.label.to_numpy()[idx].max()
                                            else None}
                    result = {"model": name, "scope": scope, "seeds": seeds, "fit_warnings": warning_text,
                              "threshold": threshold, "validation": metrics(val.label.to_numpy(), pv, threshold),
                              "test": metrics(test.label.to_numpy(), pt, threshold), "subgroups": subgroups,
                              "seed_test_auroc": [float(roc_auc_score(test.label, p)) for p in pt_all]}
                    summary["models"].append(result)
                    local_predictions[(name, scope)] = pt
                    predictions.extend({"mint": mint, "horizon": horizon, "period": fold["name"], "model": name,
                                        "scope": scope, "label": int(y), "probability": float(p),
                                        "novel_wallet_fraction": float(n), "day": int(ts // 86400)}
                                       for mint, y, p, n, ts in zip(test.mint_address, test.label, pt, novelty_test, test.decision_ts))
                    print(horizon, fold["name"], name, scope, json.dumps(result["test"]), flush=True)
            for name in protocol["models"]:
                pairings.setdefault((horizon, name), []).append({"y": test.label.to_numpy(),
                     "base": local_predictions[(name, "base")], "coord": local_predictions[(name, "coord")],
                     "days": test.decision_ts.to_numpy() // 86400})
            report["results"].append(summary)
    for (horizon, name), periods in pairings.items():
        report["comparisons"].append({"horizon": horizon, "model": name,
            "primary": horizon == 300 and name == "random_forest",
            "ap": paired_period_bootstrap(periods, average_precision_score),
            "auroc": paired_period_bootstrap(periods, roc_auc_score)})
    (processed / "confirmation_predictions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in predictions))
    report["source_hashes"] = json.loads((ROOT / "docs/results/solana_prefix_baseline.json").read_text())["source_hashes"]
    for source_path in (path, HERE / "robustness.py", HERE / "prefix_baseline.py"):
        report["source_hashes"][str(source_path.relative_to(ROOT))] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    out = ROOT / "docs/results/solana_confirmation.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(out, flush=True)


if __name__ == "__main__":
    main()
