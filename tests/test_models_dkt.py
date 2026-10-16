import math

from src.models.synthetic_quiz_data import generate_synthetic_interactions
from src.models.dkt import train_dkt, evaluate_dkt


def test_synthetic_interactions_schema():
    df = generate_synthetic_interactions(n_students=5, n_skills=3, interactions_per_student=10, seed=0)
    assert list(df.columns) == ["student_id", "skill_id", "correct", "timestamp"]
    assert len(df) == 50
    assert df["skill_id"].between(0, 2).all()
    assert df["correct"].isin([0, 1]).all()


def test_train_and_evaluate_smoke():
    df = generate_synthetic_interactions(n_students=8, n_skills=3, interactions_per_student=12, seed=1)
    model, history = train_dkt(df, n_skills=3, epochs=2, batch_size=4, hidden_dim=8)
    assert len(history["loss"]) == 2
    assert all(math.isfinite(l) for l in history["loss"])

    metrics = evaluate_dkt(model, df, n_skills=3, batch_size=4)
    assert metrics["n_predictions"] > 0
    assert 0.0 <= metrics["acc"] <= 1.0
