import numpy as np
import pandas as pd

from src.models.wallet_risk_baseline import WalletRiskBaseline


def _synthetic_separable_table(n=40, seed=0):
    rng = np.random.default_rng(seed)
    risk_signal = rng.normal(size=n)
    noise = rng.normal(size=n)
    y = (risk_signal > 0).astype(int)
    X = pd.DataFrame({"risk_signal": risk_signal, "noise": noise})
    return X, pd.Series(y)


def test_fit_predict_shape_and_separability():
    X, y = _synthetic_separable_table()
    model = WalletRiskBaseline(estimator="logreg").fit(X, y)
    proba = model.predict_proba(X)
    assert proba.shape == (len(X),)
    assert ((proba >= 0) & (proba <= 1)).all()

    preds = (proba >= 0.5).astype(int)
    accuracy = (preds == y.values).mean()
    assert accuracy > 0.8


def test_feature_importances_indexed_by_column():
    X, y = _synthetic_separable_table()
    model = WalletRiskBaseline(estimator="gbdt").fit(X, y)
    importances = model.feature_importances()
    assert set(importances.index) == {"risk_signal", "noise"}
    assert importances["risk_signal"] >= importances["noise"]


def test_save_and_load_roundtrip(tmp_path):
    X, y = _synthetic_separable_table()
    model = WalletRiskBaseline(estimator="logreg").fit(X, y)
    path = tmp_path / "model.joblib"
    model.save(path)
    loaded = WalletRiskBaseline.load(path)
    np.testing.assert_allclose(loaded.predict_proba(X), model.predict_proba(X))
