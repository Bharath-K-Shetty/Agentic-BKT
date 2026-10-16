"""Baseline evaluation metrics, guarded against the near-guaranteed
single-class-y_true case at Month 1's small N."""
from __future__ import annotations

import warnings

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_binary(y_true, y_score) -> dict:
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    y_pred = (y_score >= 0.5).astype(int)

    if len(np.unique(y_true)) < 2:
        warnings.warn("evaluate_binary: y_true has a single class, AUC is undefined")
        auc = float("nan")
        pr_auc = float("nan")
    else:
        auc = roc_auc_score(y_true, y_score)
        pr_auc = average_precision_score(y_true, y_score)

    return {
        "auc": auc,
        "pr_auc": pr_auc,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
    }


def naive_baseline_rate(y_true) -> float:
    y_true = np.asarray(y_true)
    return float(y_true.mean()) if len(y_true) else float("nan")
