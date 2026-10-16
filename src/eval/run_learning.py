"""Compare next-answer predictors with disjoint learner holdouts.

python -m src.eval.run_learning --synthetic --epochs 5
python -m src.eval.run_learning --input data/processed/learning/interactions.csv
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.learning.content import BANK_VERSION, SKILLS
from src.learning.tracing import bkt_update
from src.models.dkt import DKTDataset, _collate, _step_logits, train_dkt
from src.models.synthetic_quiz_data import generate_synthetic_interactions
from torch.utils.data import DataLoader


def validate_interactions(df, n_skills):
    required = {"student_id", "skill_id", "correct", "timestamp"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(df.columns))}")
    df = df.copy()
    if df[list(required)].isna().any().any():
        raise ValueError("Required interaction fields cannot be missing")
    for col in ["skill_id", "correct", "timestamp"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    if not df.skill_id.isin(range(n_skills)).all() or not df.correct.isin([0, 1]).all():
        raise ValueError("skill_id must be in range and correct must be 0 or 1")
    if not np.isfinite(df.timestamp).all():
        raise ValueError("timestamps must be finite numeric ordering values")
    df["student_id"] = df.student_id.astype(str)
    if df.duplicated(["student_id", "timestamp"]).any():
        raise ValueError("Each learner needs unique timestamps for unambiguous order")
    df["skill_id"] = df.skill_id.astype(int)
    df["correct"] = df.correct.astype(int)
    counts = df.groupby("student_id").size()
    if (counts < 2).any():
        raise ValueError("Every evaluated learner needs at least two responses")
    return df.sort_values(["student_id", "timestamp"], kind="stable").reset_index(drop=True)


def learner_split(df, seed=42):
    ids = np.array(sorted(df.student_id.unique()))
    if len(ids) < 6:
        raise ValueError("At least six learners are needed for train/validation/test splits")
    np.random.default_rng(seed).shuffle(ids)
    holdout = max(1, int(len(ids) * 0.2))
    groups = {"train": ids[2 * holdout:], "validation": ids[:holdout], "test": ids[holdout:2 * holdout]}
    return {name: df[df.student_id.isin(students)].copy() for name, students in groups.items()}, groups


def prior_rates(train, n_skills):
    return np.array([(train.loc[train.skill_id == s, "correct"].sum() + 1) /
                     (len(train[train.skill_id == s]) + 2) for s in range(n_skills)])


def historical_features(history, skill, n_skills, priors):
    same = [int(r["correct"]) for r in history if int(r["skill_id"]) == skill]
    total = sum(int(r["correct"]) for r in history)
    return [int(skill == s) for s in range(n_skills)] + [
        len(same), (sum(same) + 2 * priors[skill]) / (len(same) + 2),
        len(history), (total + 1) / (len(history) + 2), int(history[-1]["correct"]),
    ]


def prediction_rows(df, n_skills, priors, bkt_params):
    rows, features = [], []
    for student, group in df.groupby("student_id", sort=True):
        history = []
        mastery = np.array([p[0] for p in bkt_params], dtype=float)
        for row in group.to_dict("records"):
            skill = int(row["skill_id"])
            if history:
                same = [r["correct"] for r in history if r["skill_id"] == skill]
                rows.append({"student_id": student, "timestamp": row["timestamp"], "skill_id": skill,
                             "correct": int(row["correct"]), "prior": float(priors[skill]),
                             "history": float((sum(same) + 2 * priors[skill]) / (len(same) + 2)),
                             "bkt": float(mastery[skill] * (1 - bkt_params[skill][3]) + (1 - mastery[skill]) * bkt_params[skill][2])})
                for field in ["phase", "scenario_id"]:
                    if field in row:
                        rows[-1][field] = row[field]
                features.append(historical_features(history, skill, n_skills, priors))
            history.append(row)
            _, learn, guess, slip = bkt_params[skill]
            mastery[skill] = bkt_update(mastery[skill], row["correct"], learn, guess, slip)
    return pd.DataFrame(rows), np.array(features)


def fit_bkt(train, n_skills):
    params = []
    for skill in range(n_skills):
        sequences = [g[g.skill_id == skill].correct.tolist() for _, g in train.groupby("student_id")]
        sequences = [seq for seq in sequences if seq]
        best, best_loss = (0.3, 0.15, 0.2, 0.1), float("inf")
        if sequences:
            for candidate in itertools.product([0.1, 0.3, 0.6], [0.05, 0.15, 0.3], [0.1, 0.2, 0.33], [0.05, 0.1, 0.2]):
                initial, learn, guess, slip = candidate
                loss = 0.0
                for sequence in sequences:
                    mastery = initial
                    for correct in sequence:
                        prob = mastery * (1 - slip) + (1 - mastery) * guess
                        loss -= np.log(prob if correct else 1 - prob)
                        mastery = bkt_update(mastery, correct, learn, guess, slip)
                if loss < best_loss:
                    best, best_loss = candidate, loss
        params.append(best)
    return params


def dkt_scores(model, df, n_skills, behavior_columns=(), tag_mapping=None):
    model.eval()
    scores = []
    with torch.no_grad():
        for x, target_skill, _, mask, lengths in DataLoader(DKTDataset(df, n_skills, behavior_columns, tag_mapping), batch_size=32, collate_fn=_collate):
            scores.extend(torch.sigmoid(_step_logits(model, x, target_skill, lengths))[mask.bool()].tolist())
    return np.array(scores)


def metrics(y, score):
    return {"roc_auc": float(roc_auc_score(y, score)) if len(np.unique(y)) > 1 else None,
            "accuracy": float(accuracy_score(y, score >= 0.5)),
            "log_loss": float(log_loss(y, np.clip(score, 1e-7, 1 - 1e-7), labels=[0, 1])),
            "brier_score": float(brier_score_loss(y, score)), "n_predictions": len(y)}


def benchmark(df, n_skills=5, epochs=10, seed=42, hidden_dim=32):
    df = validate_interactions(df, n_skills)
    splits, ids = learner_split(df, seed)
    priors = prior_rates(splits["train"], n_skills)
    bkt_params = fit_bkt(splits["train"], n_skills)
    train_rows, train_x = prediction_rows(splits["train"], n_skills, priors, bkt_params)
    if train_rows.correct.nunique() < 2:
        raise ValueError("Training predictions need both correct and incorrect responses")
    logistic = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
    logistic.fit(train_x, train_rows.correct)
    model, history = train_dkt(splits["train"], n_skills, epochs=epochs, hidden_dim=hidden_dim, seed=seed)
    result = {"seed": seed, "n_skills": n_skills, "epochs": epochs, "split_learners": {k: list(v) for k, v in ids.items()},
              "training_loss": history["loss"], "bkt_parameters": bkt_params,
              "protocol": "Disjoint learner holdouts; ordered responses; first response excluded for every predictor; train-only parameter fitting; no test tuning.",
              "metrics": {}}
    predictions = []
    for split in ["validation", "test"]:
        rows, features = prediction_rows(splits[split], n_skills, priors, bkt_params)
        rows["logistic"] = logistic.predict_proba(features)[:, 1]
        rows["dkt"] = dkt_scores(model, splits[split], n_skills)
        result["metrics"][split] = {name: metrics(rows.correct.to_numpy(), rows[name].to_numpy())
                                   for name in ["prior", "history", "bkt", "logistic", "dkt"]}
        rows["split"] = split
        predictions.append(rows)
    # Resample learners, retaining their complete response sequences.
    test = predictions[-1]
    students = test.student_id.unique()
    rng = np.random.default_rng(seed)
    result["test_auc_95pct_learner_bootstrap"] = {}
    for name in ["prior", "history", "bkt", "logistic", "dkt"]:
        values = []
        for _ in range(200):
            sample = pd.concat([test[test.student_id == sid] for sid in rng.choice(students, len(students), replace=True)])
            if sample.correct.nunique() == 2:
                values.append(roc_auc_score(sample.correct, sample[name]))
        result["test_auc_95pct_learner_bootstrap"][name] = {
            "interval": np.quantile(values, [0.025, 0.975]).tolist() if values else None,
            "valid_resamples": len(values), "warning": "Small learner counts can yield unstable intervals."}
    result["test_auc_difference_dkt_minus_bkt"] = {}
    differences = []
    for _ in range(200):
        sample = pd.concat([test[test.student_id == sid] for sid in rng.choice(students, len(students), replace=True)])
        if sample.correct.nunique() == 2:
            differences.append(roc_auc_score(sample.correct, sample.dkt) - roc_auc_score(sample.correct, sample.bkt))
    result["test_auc_difference_dkt_minus_bkt"] = {
        "paired_95pct_interval": np.quantile(differences, [0.025, 0.975]).tolist() if differences else None,
        "valid_resamples": len(differences)}
    return model, result, pd.concat(predictions, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/processed/learning/benchmark"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-skills", type=int, default=len(SKILLS), help="Number of zero-indexed skill categories (default: HOMIE's five)")
    parser.add_argument("--dataset-manifest", type=Path, help="Optional preprocessing manifest; validates dataset hash and category count")
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("epochs must be positive")
    if args.n_skills < 1:
        parser.error("n-skills must be positive")
    if args.synthetic and (args.n_skills != len(SKILLS) or args.dataset_manifest):
        parser.error("Synthetic demo uses five skills and no external manifest")
    if args.synthetic:
        df = generate_synthetic_interactions(n_students=100, n_skills=len(SKILLS), interactions_per_student=30, seed=args.seed)
        data_source = "synthetic"
    else:
        df = pd.read_csv(args.input)
        if "consent" in df and not df.consent.eq(1).all():
            parser.error("Research exports must contain only consenting participants")
        data_source = "learner_export" if "bank_version" in df and df.bank_version.eq(BANK_VERSION).all() else "external_csv"
    provenance = None
    if args.dataset_manifest:
        from src.data_collection.fetch_ednet import sha256
        provenance = json.loads(args.dataset_manifest.read_text())
        if provenance["n_skills"] != args.n_skills or provenance["output_sha256"] != sha256(args.input):
            parser.error("Dataset hash or skill count differs from preprocessing manifest")
        data_source = provenance["data_source"]
    model, result, predictions = benchmark(df, args.n_skills, args.epochs, args.seed)
    result["data_source"] = data_source
    result["bank_version"] = "synthetic-generator-v1" if args.synthetic else BANK_VERSION if data_source == "learner_export" else "unspecified"
    result["limitation"] = "Synthetic results are a software demonstration, not evidence about real learners." if args.synthetic else "Exploratory evaluation; educator review, adequate sample size, and an independent study are required for learning-benefit claims."
    if provenance:
        result["dataset_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    predictions.to_csv(args.output / "predictions.csv", index=False)
    torch.save({"state_dict": model.state_dict(), "n_skills": args.n_skills, "hidden_dim": 32,
                "source": data_source, "bank_version": result["bank_version"], "seed": args.seed}, args.output / "dkt.pt")
    print(json.dumps({"data_source": data_source, "test_metrics": result["metrics"]["test"], "limitation": result["limitation"]}, indent=2))
    print(f"Artifacts: {args.output}")


if __name__ == "__main__":
    main()
