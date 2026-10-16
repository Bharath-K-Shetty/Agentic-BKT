"""Part 1 baseline: a tabular classifier over wallet features predicting
forward-looking rug-pull/sandwich exposure. Deliberately GBT/logreg, not a
transformer -- appropriately scoped for a Month 1 first baseline.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression


class WalletRiskBaseline:
    def __init__(self, estimator: str = "gbdt"):
        self.estimator_name = estimator
        if estimator == "gbdt":
            self._model = GradientBoostingClassifier(random_state=42)
        elif estimator == "logreg":
            self._model = LogisticRegression(max_iter=1000)
        else:
            raise ValueError(f"unknown estimator: {estimator}")
        self._feature_names: list[str] | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "WalletRiskBaseline":
        X_filled = X.fillna(0.0)
        self._feature_names = list(X_filled.columns)
        self._model.fit(X_filled, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_filled = X.fillna(0.0)[self._feature_names]
        return self._model.predict_proba(X_filled)[:, 1]

    def feature_importances(self) -> pd.Series:
        if hasattr(self._model, "feature_importances_"):
            values = self._model.feature_importances_
        else:
            values = np.abs(self._model.coef_[0])
        return pd.Series(values, index=self._feature_names).sort_values(ascending=False)

    def save(self, path: Path) -> None:
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> "WalletRiskBaseline":
        return joblib.load(path)
