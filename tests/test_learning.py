import json

import numpy as np
import pandas as pd
import pytest
import torch

from src.eval.run_learning import benchmark, learner_split, prediction_rows, validate_interactions
from src.learning.content import BANK_VERSION, BY_ID, QUESTIONS, SKILLS
from src.learning.service import LearningService
from src.models.dkt import DKT
from src.models.synthetic_quiz_data import generate_synthetic_interactions


def test_bank_has_unique_parallel_checks_and_balanced_practice():
    assert len(BY_ID) == len(QUESTIONS) == 20
    for skill in SKILLS:
        phases = [q["phase"] for q in QUESTIONS if q["skill_id"] == skill["id"]]
        assert phases.count("diagnostic") == phases.count("assessment") == 1
        assert phases.count("practice") == 2
    assert all(0 <= q["answer"] < len(q["options"]) for q in QUESTIONS)


def test_entire_learning_loop_resume_export_and_delete(tmp_path):
    service = LearningService(tmp_path / "sessions.sqlite3")
    state = service.start(consent=True)
    sid = state["session_id"]
    assert "answer" not in state["question"] and "explanation" not in state["question"]
    order = []
    while state["question"]:
        question = state["question"]
        order.append(question["id"])
        if state["lesson"]:
            service.lesson(sid, state["lesson"]["id"])
        state = service.answer(sid, question["id"], BY_ID[question["id"]]["answer"])
        assert service.state(sid)["answered"] == len(order)
        if question["phase"] != "practice":
            assert state["feedback"] == {"recorded": True}
    assert len(order) == len(set(order)) == 20
    assert state["phase_scores"]["assessment"]["correct"] == 5
    assert len(state["review"]) == 20
    output = tmp_path / "export.csv"
    assert service.export(output) == 20
    exported = pd.read_csv(output)
    assert sid not in output.read_text()
    assert exported.timestamp.is_monotonic_increasing
    assert exported[exported.phase == "practice"].lesson_seen.eq(1).all()
    service.delete(sid)
    with pytest.raises(KeyError):
        service.state(sid)
    assert service.export(output) == 0
    with service.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] == 0


def test_demo_records_not_exported_and_submission_guards(tmp_path):
    service = LearningService(tmp_path / "sessions.sqlite3")
    state = service.start()
    sid = state["session_id"]
    qid = state["question"]["id"]
    for choice in [-1, 3, True, "1"]:
        with pytest.raises(ValueError):
            service.answer(sid, qid, choice)
    with pytest.raises(ValueError):
        service.answer(sid, "safety-post", 0)
    with pytest.raises(ValueError):
        service.lesson(sid, 0)
    service.answer(sid, qid, 0)
    assert service.state(sid)["phase_scores"]["diagnostic"]["correct"] is None
    assert all("correct" not in skill for skill in service.state(sid)["skills"])
    with pytest.raises(ValueError):
        service.answer(sid, qid, 0)
    assert service.export(tmp_path / "export.csv") == 0


def test_completed_export_excludes_partial_consent(tmp_path):
    service = LearningService(tmp_path / "sessions.sqlite3")
    state = service.start(True)
    service.answer(state["session_id"], state["question"]["id"], 0)
    assert service.export(tmp_path / "all.csv") == 1
    assert service.export(tmp_path / "complete.csv", completed_only=True) == 0
    assert "student_id" in pd.read_csv(tmp_path / "complete.csv").columns


def test_synthetic_dkt_used_only_for_demo(tmp_path):
    model = DKT(5, hidden_dim=8)
    path = tmp_path / "demo.pt"
    torch.save({"state_dict": model.state_dict(), "n_skills": 5, "hidden_dim": 8,
                "source": "synthetic", "bank_version": "synthetic-generator-v1"}, path)
    service = LearningService(tmp_path / "sessions.sqlite3", path)
    demo = service.start(False)
    assert demo["predictor"] == "dkt" and demo["model_source"] == "synthetic"
    demo = service.answer(demo["session_id"], demo["question"]["id"], 0)
    assert all(0 <= skill["probability"] <= 1 for skill in demo["skills"])
    study = service.start(True)
    assert study["predictor"] == "bkt"


def test_split_by_learner_and_predictions_exclude_current_answer():
    df = validate_interactions(generate_synthetic_interactions(10, 3, 8), 3)
    splits, ids = learner_split(df)
    assert not set(ids["train"]) & set(ids["test"])
    assert not set(ids["validation"]) & set(ids["test"])
    params = [(0.3, 0.15, 0.2, 0.1)] * 3
    priors = np.array([0.5] * 3)
    one = splits["test"][splits["test"].student_id == ids["test"][0]].copy()
    rows, features = prediction_rows(one, 3, priors, params)
    changed = one.copy()
    changed.loc[changed.index[-1], "correct"] = 1 - changed.iloc[-1].correct
    new_rows, new_features = prediction_rows(changed, 3, priors, params)
    assert np.array_equal(features, new_features)
    assert np.array_equal(rows.bkt, new_rows.bkt)
    assert len(rows) == len(one) - 1


def test_bad_data_rejected():
    df = generate_synthetic_interactions(10, 3, 8)
    for column, value in [("skill_id", 1.5), ("correct", 2), ("timestamp", float("inf"))]:
        bad = df.copy()
        bad[column] = bad[column].astype(float)
        bad.loc[0, column] = value
        with pytest.raises(ValueError):
            validate_interactions(bad, 3)
    bad = df.copy()
    bad.loc[1, "timestamp"] = bad.loc[0, "timestamp"]
    with pytest.raises(ValueError):
        validate_interactions(bad, 3)


def test_benchmark_metrics_align_and_serialize():
    df = generate_synthetic_interactions(10, 3, 8, seed=3)
    _, result, predictions = benchmark(df, n_skills=3, epochs=1, hidden_dim=8)
    test = predictions[predictions.split == "test"]
    assert len(test) == 14
    assert set(result["metrics"]["test"]) == {"prior", "history", "bkt", "logistic", "dkt"}
    assert all(m["n_predictions"] == len(test) for m in result["metrics"]["test"].values())
    assert np.isfinite(test[["prior", "history", "bkt", "logistic", "dkt"]]).all().all()
    json.dumps(result, allow_nan=False)
