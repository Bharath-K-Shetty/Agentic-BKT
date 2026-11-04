"""Exploratory MELT baseline: only transaction prefixes are model inputs.

Run from the repo root: .venv/bin/python research/solana/ml/prefix_baseline.py
No upstream code or pickle is executed. Price collapse is not fraud proof.
"""
import argparse
from collections import Counter, defaultdict
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
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
COORD = {"multiwallet_swap_fraction", "multiwallet_volume_fraction", "largest_component_fraction",
         "component_holding_hhi", "top_component_holding_share", "component_count_per_wallet"}


def prefix_features(events, horizon):
    """Future rows must not affect features. Explicit mint is required for t0.

    Co-participation edges are observations, not verified common ownership.
    Parsed price signs are inconsistent across create/swaps; absolute price is used.
    """
    mints = [e for e in events if "mint" in e["type"]]
    if not mints:
        raise ValueError("missing mint event")
    t0 = min(int(e["timestamp"]) for e in mints)
    prefix = [e for e in events if t0 <= int(e["timestamp"]) <= t0 + horizon]
    prefix.sort(key=lambda e: (int(e["block_slot"]), int(e["block_index"]), e["signature"]))
    # Duplicate signatures would double-count balances and are rejected.
    if len({e["signature"] for e in prefix}) != len(prefix):
        raise ValueError("duplicate prefix signature")
    swaps = [e for e in prefix if "swap" in e["type"]]
    if not swaps:
        raise ValueError("no prefix swaps")
    holdings, traded = defaultdict(float), defaultdict(float)
    buys, sells = 0, 0
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    multi, multi_volume, total_volume = 0, 0.0, 0.0
    for e in prefix:
        traders = e.get("trader_map", {})
        for a, amount in traders.items():
            amount = float(amount)
            if not np.isfinite(amount):
                raise ValueError("nonfinite balance change")
            holdings[a] += amount
            find(a)
            if "swap" in e["type"]:
                traded[a] += abs(amount)
                buys += amount > 0
                sells += amount < 0
        if "swap" in e["type"]:
            volume = abs(float(e["sol_amount"]))
            total_volume += volume
            active = [a for a, v in traders.items() if float(v) != 0]
            if len(active) > 1:
                multi += 1
                multi_volume += volume
                for a in active[1:]:
                    parent[find(a)] = find(active[0])

    prices = np.array([abs(float(e["price"])) for e in swaps])
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("invalid prefix prices")
    positive = np.array([max(v, 0) for v in holdings.values()])
    if positive.sum() <= 0:
        raise ValueError("no positive holdings")
    shares = positive / positive.sum()
    activity = np.array(list(traded.values()), dtype=float)
    activity = activity / activity.sum() if activity.sum() else np.zeros_like(activity)
    components = defaultdict(float)
    sizes = Counter()
    for a, v in holdings.items():
        components[find(a)] += max(v, 0)
        sizes[find(a)] += 1
    cs = np.array(list(components.values())) / positive.sum()
    logs = np.diff(np.log(prices))
    times = np.array([int(e["timestamp"]) for e in swaps])
    fees = np.array([float(e["fee_amount"]) for e in swaps])
    f = {
        "tx_count": len(prefix), "swap_count": len(swaps),
        "transfer_count": sum("transfer" in e["type"] for e in prefix),
        "zero_type_count": sum("zero" in e["type"] for e in prefix),
        "unique_wallets": len(holdings), "positive_holders": int((positive > 0).sum()),
        "buy_count": buys, "sell_count": sells, "sell_fraction": sells / max(buys + sells, 1),
        "sol_volume": total_volume, "wallet_activity_hhi": float((activity ** 2).sum()),
        "holding_hhi": float((shares ** 2).sum()), "top1_share": float(shares.max()),
        "top10_share": float(np.sort(shares)[-10:].sum()),
        "log_price_return": float(np.log(prices[-1] / prices[0])),
        "log_price_range": float(np.log(prices.max() / prices.min())),
        "price_change_std": float(logs.std()) if len(logs) else 0.0,
        "recent_swap_fraction": float((times > t0 + horizon / 2).mean()),
        "active_seconds_fraction": len(set(times)) / (horizon + 1),
        "fee_mean": float(fees.mean()), "fee_max": float(fees.max()),
        "multiwallet_swap_fraction": multi / len(swaps),
        "multiwallet_volume_fraction": multi_volume / max(total_volume, 1e-12),
        "largest_component_fraction": max(sizes.values()) / len(holdings),
        "component_holding_hhi": float((cs ** 2).sum()),
        "top_component_holding_share": float(cs.max()),
        "component_count_per_wallet": len(sizes) / len(holdings),
    }
    if not np.isfinite(list(f.values())).all():
        raise ValueError("nonfinite features")
    return t0, f


def temporal_split(frame):
    """Decision-time 60/20/20 split with label maturation at migration + 1h.

    Launches can precede their decision by different horizons. Purging is based
    on the first decision in the next partition, not on rank alone.
    """
    frame = frame.sort_values(["decision_ts", "mint_address"]).reset_index(drop=True)
    n = len(frame)
    val_start = int(frame.iloc[int(n * .6)].decision_ts)
    test_start = int(frame.iloc[int(n * .8)].decision_ts)
    train = frame[(frame.decision_ts < val_start) & (frame.label_ready_ts < val_start)]
    val = frame[(frame.decision_ts >= val_start) & (frame.decision_ts < test_start)
                & (frame.label_ready_ts < test_start)]
    test = frame[frame.decision_ts >= test_start]
    return train, val, test, {"validation_start": val_start, "test_start": test_start,
                             "purged": n - len(train) - len(val) - len(test)}


def metrics(y, p, threshold):
    negative = y == 0
    pred = p >= threshold
    return {"auroc": float(roc_auc_score(y, p)),
            "ap_positive": float(average_precision_score(y, p)),
            "ap_negative": float(average_precision_score(1-y, 1-p)),
            "brier": float(brier_score_loss(y, p)),
            "recall": float(pred[y == 1].mean()), "fpr": float(pred[negative].mean()),
            "precision": float(y[pred].mean()) if pred.any() else None,
            "alert_fraction": float(pred.mean())}


def threshold_at_fpr(y, p, budget=.05):
    # Include a no-alert candidate; ties cannot evade the FPR constraint.
    candidates = np.unique(np.r_[p, np.nextafter(p.max(), np.inf)])
    negatives = np.sort(p[y == 0])
    if not len(negatives):
        raise ValueError('FPR requires negative validation outcomes')
    # Identical minimal-candidate rule, without scanning all negatives at every
    # candidate. This matters for the 100k-row transaction study.
    fpr = (len(negatives) - np.searchsorted(negatives, candidates, side='left')) / len(negatives)
    return float(candidates[np.flatnonzero(fpr <= budget)[0]])


def day_bootstrap(y, p, timestamps, seed=42, repetitions=300, reference=None):
    """Calendar-day blocks, fixed predictions; not operator independence."""
    groups = timestamps // 86400
    days = np.unique(groups)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(repetitions):
        selected = rng.choice(days, len(days), replace=True)
        idx = np.concatenate([np.flatnonzero(groups == d) for d in selected])
        if len(np.unique(y[idx])) == 2:
            score = roc_auc_score(y[idx], p[idx])
            if reference is not None:
                score -= roc_auc_score(y[idx], reference[idx])
            vals.append(score)
    return np.quantile(vals, [.025, .975]).tolist() if vals else None


def write_readable_report(report):
    lines = ["# First Solana transaction-prefix ML experiment", "",
             "This is an executed feasibility baseline, not a publication-ready contribution.", "",
             f"Target: {report['target']}.", "",
             "Data: Hu et al., [MELT](https://arxiv.org/html/2602.13480v2), "
             "[author release](https://github.com/git-disl/MELT), CC BY-NC 4.0. "
             "Source and derived-file hashes are in the machine-readable report.", "",
             f"Sampled {report['audit']['sampled_tokens']:,} tokens by address hash without using labels "
             f"from {report['audit']['eligible_intersection']:,} joinable released tokens. "
             "Only eventual migrants are represented.", "",
             "Models use prefix transactions only. Chronological decisions define train, validation and test; "
             "migration + one hour defines outcome maturity. All training/validation outcomes must mature "
             "before the next partition starts. Calendar/migration times and label-source fields are not inputs.", ""]
    for section in report["results"]:
        lines += [f"## {section['horizon_seconds']}-second prefix", ""]
        for name, c in section["counts"].items():
            lines.append(f"- {name}: {c['n']:,} tokens; positive prevalence {c['positive_prevalence']:.1%}.")
        lines += [f"- Boundary label-maturity exclusions: {section['split']['purged']:,}.", "",
                  "| Model | Features | Test AUROC | AP positive | AP negative | Recall | Test FPR |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for m in section["models"]:
            t = m["test"]
            lines.append(f"| {m['model']} | {m['feature_scope']} | {t['auroc']:.3f} | "
                         f"{t['ap_positive']:.3f} | {t['ap_negative']:.3f} | {t['recall']:.1%} | {t['fpr']:.1%} |")
        selected = max(section["models"], key=lambda m: m["validation"]["auroc"])
        lines += ["", f"Highest validation AUROC: {selected['model']} with {selected['feature_scope']}. "
                  f"Its test AUROC is {selected['test']['auroc']:.3f}; selection used validation, not test.", "",
                  "Thresholds were chosen separately using a 5% validation FPR budget; test FPR is reported "
                  "without adjusting thresholds to test labels. Constant-score AUROC is 0.5; its AP equals "
                  "test class prevalence.", "", "Co-participation ablation, added minus base test AUROC:", ""]
        for a in section["coparticipation_ablation"]:
            lo, hi = a["paired_day_block_delta_ci95"]
            lines.append(f"- {a['model']}: {a['test_auroc_delta']:+.4f}; paired day-block 95% interval [{lo:+.4f}, {hi:+.4f}].")
        warnings_list = [(m["model"], m["feature_scope"], w) for m in section["models"] for w in m["fit_warnings"]]
        if warnings_list:
            lines += ["", "Fit limitations:", ""]
            lines += [f"- {name}, {scope}: {warning}" for name, scope, warning in warnings_list]
        lines.append("")
    lines += ["## Limits and next decision", ""]
    lines += [f"- {limit}" for limit in report["limits"]]
    lines += ["", "Price-collapse prediction has potential practical use as one risk signal, but these "
              "results do not establish profitability, fraud detection or general deployment reliability. "
              "Fixed-prefix models and wallet coordination already overlap prior work; this pilot adds "
              "evidence of feasibility, not evidence of novelty.", "",
              "The next research gate is a prespecified experiment on additional periods and stronger "
              "coordination baselines, followed by a distinct method only if it addresses a demonstrated "
              "failure. True operator holdouts require defensible identities. A graph architecture alone "
              "does not satisfy that requirement.", "",
              "Reproduction and exact controls: [experiment README](../research/solana/ml/README.md). "
              "Detailed metrics: [JSON report](results/solana_prefix_baseline.json).", ""]
    (ROOT / "docs/SOLANA_PREFIX_BASELINE_RESULTS.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target", choices=("price_drop", "high_risk"), default="price_drop")
    parser.add_argument("--reuse-features", action="store_true")
    args = parser.parse_args()
    raw = ROOT / "data/raw/melt"
    processed = ROOT / "data/processed/solana_ml"
    processed.mkdir(parents=True, exist_ok=True)
    output = ROOT / "docs/results/solana_prefix_baseline.json"
    labels = pd.read_csv(raw / "label.csv")
    if labels.mint_address.duplicated().any() or not set(labels.label) <= {"high", "medium", "low"}:
        raise ValueError("invalid labels")
    # Price-only endpoint has an explicit 20-minute outcome window. The released
    # high-risk label additionally uses manual trajectory judgments, whose actual
    # annotation availability is not established by the public CSV.
    label_map = (labels.set_index("mint_address").min_ratio.lt(.3).astype(int).to_dict()
                 if args.target == "price_drop" else
                 labels.set_index("mint_address").label.eq("high").astype(int).to_dict())
    manifest = json.loads((ROOT / "docs/results/blockchain_ml_source_probe.json").read_text())
    meta = next(r for r in manifest["files"] if r["repository"] == "git-disl/MELT"
                and r["path"] == "data/memecoin/memecoin_list.jsonl")
    migration = {r["token_address"]: int(r["timestamp"]) for r in
                 map(json.loads, (ROOT / "data/raw/solana_ml_probe" / meta["sha256"]).read_text().splitlines())}
    feature_path = processed / f"prefix_{args.target}_{args.sample}_{args.seed}.jsonl"
    audit_path = feature_path.with_suffix(".audit.json")
    if not args.reuse_features:
        rows, skipped = [], Counter()
        with zipfile.ZipFile(raw / "pre_migration_tx.zip") as archive:
            members = {Path(p).stem: p for p in archive.namelist()
                       if p.startswith("pre_migration_tx/") and p.endswith(".jsonl")}
            candidates = sorted(set(label_map) & set(migration) & set(members),
                                key=lambda a: hashlib.sha256(f"{args.seed}:{a}".encode()).hexdigest())[:args.sample]
            for index, mint in enumerate(candidates):
                try:
                    events = [json.loads(line) for line in archive.read(members[mint]).splitlines() if line.strip()]
                    if any(e["mint"] != mint for e in events):
                        raise ValueError("mint mismatch")
                    mints = [e for e in events if "mint" in e["type"]]
                    if not mints:
                        raise ValueError("missing mint event")
                    launch = min(int(e["timestamp"]) for e in mints)
                    for horizon in (60, 300):
                        if migration[mint] <= launch + horizon:
                            skipped[f"{horizon}:already_migrated"] += 1
                            continue
                        try:
                            t0, features = prefix_features(events, horizon)
                        except (ValueError, KeyError, TypeError) as exc:
                            skipped[f"{horizon}:{exc}"] += 1
                            continue
                        rows.append({"mint_address": mint, "t0": t0, "horizon": horizon,
                                     "decision_ts": t0 + horizon, "label_ready_ts": migration[mint] + 3600,
                                     "label": label_map[mint], **features})
                except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    skipped[str(exc)] += 1
                if (index + 1) % 500 == 0:
                    print(f"parsed {index + 1}/{len(candidates)} tokens", flush=True)
        feature_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        audit = {"archive_token_files": len(members), "labeled_tokens": len(labels),
                 "eligible_intersection": len(set(label_map) & set(migration) & set(members)),
                 "sampled_tokens": len(candidates), "skipped": dict(skipped)}
        audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    else:
        audit = json.loads(audit_path.read_text())
    frame = pd.read_json(feature_path, lines=True)
    feature_cols = sorted(set(frame) - {"mint_address", "t0", "horizon", "decision_ts", "label_ready_ts", "label"})
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "seed": args.seed,
              "sample_policy": "SHA256(seed:mint), independent of labels; migrated-token population only",
              "target": ("min_ratio < 0.3 within 20 minutes after migration; price-collapse proxy, not confirmed fraud"
                         if args.target == "price_drop" else
                         "MELT high=1, medium/low=0; manual label availability unverified, exploratory retrospective only"),
              "audit": audit, "features": feature_cols, "results": [],
              "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__},
              "limits": ["Single training seed and exploratory sample; not publication evidence.",
                         "Only eventual migrants; no all-launch deployment claim.",
                         "Horizon cohorts differ due to migration eligibility; score differences do not quantify the value of waiting.",
                         "No true operator identities or operator-disjoint evaluation.",
                         "Co-participation is not evidence of common wallet ownership.",
                         "No graph neural model, external replication, or first-harm-time evaluation.",
                         "Labels and parsed transaction correctness inherited from MELT, not independently verified.",
                         "Multiple exploratory model/feature comparisons; bootstrap intervals are not adjusted for multiplicity."]}
    if args.target == "high_risk":
        report["limits"].append("Migration + 1h maturity is only an assumption for manually judged risk labels.")
    predictions = []
    for horizon in (60, 300):
        train, val, test, split = temporal_split(frame[frame.horizon == horizon])
        if min(len(train), len(val), len(test)) < 50 or any(f.label.nunique() != 2 for f in (train, val, test)):
            raise ValueError("insufficient split for meaningful evaluation")
        summary = {"horizon_seconds": horizon, "split": split,
                   "counts": {name: {"n": len(f), "positive_prevalence": float(f.label.mean()),
                                     "decision_min": int(f.decision_ts.min()), "decision_max": int(f.decision_ts.max())}
                              for name, f in [("train", train), ("validation", val), ("test", test)]}, "models": []}
        constant = np.full(len(test), train.label.mean())
        summary["constant_baseline"] = metrics(test.label.to_numpy(), constant, 1.01)
        test_probabilities = {}
        for scope in ("activity_holdings", "plus_coparticipation"):
            cols = [c for c in feature_cols if scope != "activity_holdings" or c not in COORD]
            models = {
                "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1)),
                "random_forest": RandomForestClassifier(n_estimators=250, min_samples_leaf=10, max_features=.8,
                                                        random_state=args.seed, n_jobs=4),
                "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15,
                                                                         l2_regularization=2, early_stopping=False,
                                                                         random_state=args.seed),
                "mlp": make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(32, 16), alpha=.1,
                                                                     max_iter=150, early_stopping=False,
                                                                     random_state=args.seed))}
            for name, model in models.items():
                with warnings.catch_warnings(record=True) as fit_warnings:
                    warnings.simplefilter("always", ConvergenceWarning)
                    model.fit(train[cols], train.label)
                pv = model.predict_proba(val[cols])[:, 1]
                pt = model.predict_proba(test[cols])[:, 1]
                test_probabilities[(scope, name)] = pt
                threshold = threshold_at_fpr(val.label.to_numpy(), pv)
                result = {"model": name, "feature_scope": scope, "feature_count": len(cols),
                          "fit_warnings": [str(w.message) for w in fit_warnings],
                          "validation_fpr_budget": .05, "validation_threshold": threshold,
                          "validation": metrics(val.label.to_numpy(), pv, threshold),
                          "test": metrics(test.label.to_numpy(), pt, threshold),
                          "test_auroc_day_block_ci95": day_bootstrap(test.label.to_numpy(), pt,
                                                                    test.decision_ts.to_numpy(), args.seed)}
                summary["models"].append(result)
                for part, f, ps in [("validation", val, pv), ("test", test, pt)]:
                    predictions.extend({"mint": mint, "horizon": horizon, "partition": part, "model": name,
                                        "scope": scope, "label": int(y), "probability": float(p)}
                                       for mint, y, p in zip(f.mint_address, f.label, ps))
                print(horizon, scope, name, json.dumps(result["test"]), flush=True)
        summary["coparticipation_ablation"] = []
        for name in models:
            base = test_probabilities[("activity_holdings", name)]
            added = test_probabilities[("plus_coparticipation", name)]
            summary["coparticipation_ablation"].append({
                "model": name,
                "test_auroc_delta": float(roc_auc_score(test.label, added) - roc_auc_score(test.label, base)),
                "paired_day_block_delta_ci95": day_bootstrap(test.label.to_numpy(), added,
                                                             test.decision_ts.to_numpy(), args.seed, reference=base)})
        report["results"].append(summary)
    report["source_hashes"] = {}
    report["source_provenance"] = {
        "label_revision": "0732bcfab54f508c27becd6d9b2b10b1b6ac2517",
        "label_url": "https://raw.githubusercontent.com/git-disl/MELT/0732bcfab54f508c27becd6d9b2b10b1b6ac2517/data/label/label.csv",
        "archive_url": "https://drive.google.com/file/d/1rqzkaVoc1FG8XRp-hBxECjiG_PxAn5Cp/view",
        "archive_version": "Unversioned author Drive release; exact local bytes hashed below",
        "metadata_sha256": meta["sha256"],
        "paper": "https://arxiv.org/html/2602.13480v2",
        "license": "CC BY-NC 4.0, academic noncommercial use with attribution"}
    for p in [raw / "label.csv", raw / "pre_migration_tx.zip", feature_path]:
        digest = hashlib.sha256()
        with p.open("rb") as stream:
            for b in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(b)
        report["source_hashes"][str(p.relative_to(ROOT))] = digest.hexdigest()
    (processed / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in predictions))
    output.write_text(json.dumps(report, indent=2) + "\n")
    write_readable_report(report)
    print(output, flush=True)


if __name__ == "__main__":
    main()
