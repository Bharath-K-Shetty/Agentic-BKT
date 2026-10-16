"""Behavioral KT comparison on future decisions from disjoint learners."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score

from src.eval.run_learning import benchmark, learner_split, metrics, validate_interactions, dkt_scores
from src.learning.scenarios import BEHAVIOR_COLUMNS, VERSION
from src.models.dkt import normalize_behavior, train_dkt


def synthetic_decisions(seed=42, learners=60):
    """Engineering-only generator with artificial behavior/ability correlations."""
    rng = np.random.default_rng(seed)
    rows = []
    for student in range(learners):
        ability = rng.normal(size=5)
        for t in range(20):
            skill = t % 5
            p = 1 / (1 + np.exp(-(ability[skill] + 0.12 * t)))
            rows.append({"student_id": str(student), "skill_id": skill, "timestamp": t,
                         "correct": int(rng.random() < p), "inspection_count": int(rng.binomial(3, p)),
                         "hint_count": int(rng.random() > p), "revision_count": int(rng.integers(0, 4)),
                         "duration_ms": int(rng.integers(3000, 90000)), "phase": "practice" if t < 10 else "transfer"})
    return pd.DataFrame(rows)


def behavioral_benchmark(df, epochs=5, seed=42):
    df = validate_interactions(df, 5)
    normalize_behavior(df, BEHAVIOR_COLUMNS)
    base, report, predictions = benchmark(df, 5, epochs, seed)
    splits, _ = learner_split(df, seed)
    models = {"dkt": base}
    # Fixed ablations use the same learners, ordering, seed, hidden size, and epochs.
    variants = {"behavior_dkt": BEHAVIOR_COLUMNS,
                "without_inspection": [c for c in BEHAVIOR_COLUMNS if c != "inspection_count"],
                "without_hints": [c for c in BEHAVIOR_COLUMNS if c != "hint_count"],
                "zero_behavior_control": BEHAVIOR_COLUMNS}
    report["behavior_columns"] = BEHAVIOR_COLUMNS
    report["behavior_training_loss"] = {}
    for name, columns in variants.items():
        variant_splits = {key: value.copy() for key, value in splits.items()}
        if name == "zero_behavior_control":
            for frame in variant_splits.values():
                frame[BEHAVIOR_COLUMNS] = 0
        model, history = train_dkt(variant_splits["train"], 5, epochs=epochs, hidden_dim=32, seed=seed, behavior_columns=columns)
        models[name] = model
        report["behavior_training_loss"][name] = history["loss"]
        for split in ["validation", "test"]:
            mask = predictions.split == split
            predictions.loc[mask, name] = dkt_scores(model, variant_splits[split], 5, columns)
            report["metrics"][split][name] = metrics(predictions.loc[mask, "correct"].to_numpy(), predictions.loc[mask, name].to_numpy())
    test = predictions[predictions.split == "test"]
    report["transfer_metrics"] = {}
    if "phase" in test:
        transfer = test[test.phase == "transfer"]
        if len(transfer):
            report["transfer_metrics"] = {
                name: metrics(transfer.correct.to_numpy(), transfer[name].to_numpy())
                for name in ["prior", "history", "bkt", "logistic", "dkt", *variants]}
    values = []
    rng = np.random.default_rng(seed)
    students = test.student_id.unique()
    for _ in range(200):
        sample = pd.concat([test[test.student_id == sid] for sid in rng.choice(students, len(students), replace=True)])
        if sample.correct.nunique() == 2:
            values.append(roc_auc_score(sample.correct, sample.behavior_dkt) - roc_auc_score(sample.correct, sample.dkt))
    report["behavior_minus_correctness_dkt_auc"] = {"paired_95pct_interval": np.quantile(values, [.025, .975]).tolist() if values else None,
                                                   "valid_resamples": len(values)}
    report["protocol"] += " Behavior from completed historical scenarios only; current decision behavior is excluded. Same holdouts and fixed training budget for ablations."
    report["parameter_counts"] = {name: sum(p.numel() for p in model.parameters()) for name, model in models.items()}
    return models["behavior_dkt"], report, predictions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--synthetic", action="store_true")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", type=Path, default=Path("data/processed/simulator/benchmark"))
    a = p.parse_args()
    if a.epochs < 1:
        p.error("epochs must be positive")
    df = synthetic_decisions(a.seed) if a.synthetic else pd.read_csv(a.input)
    if not a.synthetic and ("consent" not in df or not df.consent.eq(1).all() or "bank_version" not in df or not df.bank_version.eq(VERSION).all()):
        p.error("Use a version-compatible opt-in simulator export")
    model, report, predictions = behavioral_benchmark(df, a.epochs, a.seed)
    report["data_source"] = "synthetic" if a.synthetic else "simulator_export"
    report["limitation"] = "Synthetic behavior correlations are engineered and cannot establish educational value." if a.synthetic else "Draft rubric; exploratory learner evaluation, not established learning benefit."
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    predictions.to_csv(a.output / "predictions.csv", index=False)
    torch.save({"state_dict": model.state_dict(), "n_skills": 5, "hidden_dim": 32,
                "behavior_columns": BEHAVIOR_COLUMNS, "bank_version": VERSION,
                "source": report["data_source"]}, a.output / "behavior_dkt.pt")
    print(json.dumps({"test_metrics": report["metrics"]["test"], "transfer_metrics": report["transfer_metrics"], "limitation": report["limitation"]}, indent=2))


if __name__ == "__main__":
    main()
