import json
from itertools import product

import pandas as pd
import pytest
import torch

from src.eval.run_simulator import behavioral_benchmark, synthetic_decisions
from src.learning.scenarios import BANKS, BEHAVIOR_COLUMNS, BY_ID, LEGACY_VERSION, SCENARIOS, VERSION, score
from src.learning.simulator import SimulatorService
from src.models.dkt import DKTDataset, normalize_behavior


def test_simulator_complete_coaching_transfer_and_export(tmp_path):
    service = SimulatorService(tmp_path / "study.sqlite3")
    state = service.start(True)
    sid = state["session_id"]
    while state["scenario"]:
        public = state["scenario"]
        s = BY_ID[public["id"]]
        assert "rubric" not in public and "feedback" not in public
        assert all("body" not in e for e in public["evidence"])
        if public["setting"]:
            assert "safe_max" not in public["setting"]
        state = service.inspect(sid, s["id"], "card-0")
        assert len(state["inspected"]) == 1
        service.inspect(sid, s["id"], "card-0")
        if s["phase"] == "practice":
            assert service.hint(sid, s["id"])["hint"]
        else:
            with pytest.raises(ValueError): service.hint(sid, s["id"])
        service.decide(sid, s["id"], "reject", 0, s["setting"]["initial"] if s["setting"] else None)
        value = s["setting"]["safe_max"] if s["setting"] else None
        state = service.decide(sid, s["id"], s["rubric"]["action"], s["rubric"]["reason"], value, True)
        if s["phase"] == "practice":
            assert state["feedback"]["correct"] == 1
        else:
            assert state["feedback"] == {"recorded": True}
            if state["scenario"] and state["scenario"]["phase"] != "practice":
                assert state["skills"] == []
    assert state["scores"]["transfer"] == {"correct": 5, "total": 5}
    assert state["scores"]["diagnostic"] == {"correct": 5, "total": 5}
    assert service.state(sid)["answered"] == len(SCENARIOS)
    out = tmp_path / "decisions.csv"
    assert service.export(out, True) == len(SCENARIOS)
    df = pd.read_csv(out)
    assert df.inspection_count.eq(1).all()  # duplicates are not independent inspections
    assert df.timestamp.is_monotonic_increasing
    assert df.duration_ms.ge(0).all()
    events = out.with_name("decisions_events.csv")
    assert sid not in out.read_text() and sid not in events.read_text()
    assert set(BEHAVIOR_COLUMNS) <= set(df.columns)
    service.delete(sid)
    with pytest.raises(KeyError): service.state(sid)
    with service.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM sim_events").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM sim_runs").fetchone()[0] == 0


def commit_answer(service, state, correct=True):
    scenario = BY_ID[state["scenario"]["id"]]
    reason = scenario["rubric"]["reason"]
    return service.decide(state["session_id"], scenario["id"], scenario["rubric"]["action"],
                          reason if correct else (reason + 1) % len(scenario["reasons"]),
                          scenario["setting"]["safe_max"] if scenario["setting"] else None, True)


def assigned_session(service, monkeypatch, condition):
    monkeypatch.setattr("src.learning.simulator.secrets.choice", lambda choices: condition)
    return service.start(True)


def test_every_diagnostic_pattern_guides_adaptation_and_exposure_matches(tmp_path, monkeypatch):
    service = SimulatorService(tmp_path / "study.sqlite3")
    first_orders = {"adaptive": set(), "fixed": set()}
    fixed_orders = set()
    for pattern in product([False, True], repeat=5):
        practice_orders = {}
        for condition in ["adaptive", "fixed"]:
            state = assigned_session(service, monkeypatch, condition)
            sid = state["session_id"]
            for skill, correct in enumerate(pattern):
                scenario = state["scenario"]
                assert scenario["phase"] == "diagnostic" and scenario["skill_id"] == skill
                assert state["skills"] == [] and state["hint"] is None
                state = commit_answer(service, state, correct)
                assert state["feedback"] == {"recorded": True}
            expected = pattern.index(False) if False in pattern else 0
            first_orders[condition].add(state["scenario"]["skill_id"])
            assert state["scenario"]["skill_id"] == (expected if condition == "adaptive" else 0)
            order = []
            while state["scenario"]["phase"] == "practice":
                order.append(state["scenario"]["id"])
                # Reading/resuming must not replace an already offered task.
                assert service.state(sid)["scenario"]["id"] == order[-1]
                state = commit_answer(service, state)
            assert state["scenario"]["phase"] == "transfer"
            assert len(order) == 10 and len(set(order)) == 10
            practice_orders[condition] = order
            if condition == "fixed":
                fixed_orders.add(tuple(order))
            service.delete(sid)
        assert set(practice_orders["adaptive"]) == set(practice_orders["fixed"])
        if pattern[0] and not all(pattern):
            assert practice_orders["adaptive"] != practice_orders["fixed"]
    assert first_orders == {"adaptive": set(range(5)), "fixed": {0}}
    assert len(fixed_orders) == 1


def test_practice_mistake_updates_remaining_skill_priority(tmp_path, monkeypatch):
    service = SimulatorService(tmp_path / "study.sqlite3")
    next_skills = {}
    for correct in [False, True]:
        state = assigned_session(service, monkeypatch, "adaptive")
        for _ in range(5):
            state = commit_answer(service, state, correct=True)
        first = state["scenario"]
        assert first["skill_id"] == 0
        state = commit_answer(service, state, correct=correct)
        next_skills[correct] = state["scenario"]["skill_id"]
        assert state["scenario"]["id"] != first["id"]
    # A mistake keeps skill 0 first; success shifts practice to another skill.
    assert next_skills == {False: 0, True: 1}


def test_versioned_resume_and_session_export_keep_dropout_denominators(tmp_path, monkeypatch):
    service = SimulatorService(tmp_path / "study.sqlite3")
    with service.connect() as db:
        db.execute("INSERT INTO sim_sessions VALUES (?, 1, 'fixed', ?)", ("legacy-session", LEGACY_VERSION))
    state = service.state("legacy-session")
    assert state["total"] == 10 and state["version"] == LEGACY_VERSION
    assert state["scenario"]["phase"] == "practice"
    while state["scenario"]:
        state = commit_answer(service, state)
    assert "diagnostic" not in state["scores"]
    empty = assigned_session(service, monkeypatch, "fixed")
    demo = service.start(False)
    output = tmp_path / "export.csv"
    assert service.export(output, completed_only=True) == len(BANKS[LEGACY_VERSION])
    sessions = pd.read_csv(tmp_path / "export_sessions.csv")
    assert len(sessions) == 2  # includes the opt-in zero-answer session, excludes demo
    assert set(sessions.bank_version) == {LEGACY_VERSION, VERSION}
    assert sessions.loc[sessions.bank_version == VERSION, "answered"].item() == 0
    assert sessions.loc[sessions.bank_version == VERSION, "completed"].item() == False
    assert sessions.loc[sessions.bank_version == LEGACY_VERSION, "completed"].item() == True
    assert set(pd.read_csv(output).student_id) <= set(sessions.student_id)
    for path in tmp_path.glob("export*.csv"):
        assert all(sid not in path.read_text() for sid in ["legacy-session", empty["session_id"], demo["session_id"]])
    with service.connect() as db:
        db.execute("UPDATE sim_sessions SET version = 'unknown' WHERE id = ?", (empty["session_id"],))
    with pytest.raises(ValueError, match="Unsupported simulator bank version"):
        service.state(empty["session_id"])


def test_bank_structure_and_preview_rules_match_scoring():
    assert len(BY_ID) == len(SCENARIOS) == 20
    for skill in range(5):
        for phase, count in [("diagnostic", 1), ("practice", 2), ("transfer", 1)]:
            assert sum(s["skill_id"] == skill and s["phase"] == phase for s in SCENARIOS) == count
    for s in SCENARIOS:
        setting = s["setting"]
        assert score(s, s["rubric"]["action"], s["rubric"]["reason"], setting["safe_max"] if setting else None)["correct"] == 1
        if setting and setting["key"] == "order_size":
            assert setting["preview"]["size_limit"] == setting["safe_max"]
    assert BY_ID["slippage-practice-2"]["setting"]["preview"]["quote"] == 400


def test_blanket_rejection_is_not_success_and_settings_matter():
    successes = sum(score(s, "reject", 0, s["setting"]["initial"] if s["setting"] else None)["correct"] for s in SCENARIOS)
    assert successes < len(SCENARIOS) / 2
    s = BY_ID["slippage-practice"]
    assert score(s, "modify", s["rubric"]["reason"], 20)["correct"] == 0
    assert score(s, "modify", s["rubric"]["reason"], 1)["correct"] == 1
    assert score(s, "modify", 1, 1)["correct"] == 0


def test_submission_guards_and_demo_not_exported(tmp_path):
    service = SimulatorService(tmp_path / "study.sqlite3")
    state = service.start()
    sid = state["session_id"]
    qid = state["scenario"]["id"]
    with pytest.raises(ValueError): service.inspect(sid, qid, "wrong")
    with pytest.raises(ValueError): service.decide(sid, qid, "approve", True)
    with pytest.raises(ValueError): service.decide(sid, qid, "unknown", 0)
    setting = BY_ID[qid]["setting"]
    service.decide(sid, qid, "reject", 0, setting["initial"] if setting else None, commit=True)
    with pytest.raises(ValueError): service.decide(sid, qid, "reject", 0, commit=True)
    assert service.export(tmp_path / "demo.csv") == 0


def test_behavior_features_never_include_target_or_future_actions():
    df = synthetic_decisions(learners=6)
    original = DKTDataset(df, 5, BEHAVIOR_COLUMNS)[0]
    changed = df.copy()
    learner = changed.student_id.iloc[0]
    index = changed[changed.student_id == learner].index[-1]
    changed.loc[index, BEHAVIOR_COLUMNS] = [0, 50, 100, 900000]
    changed.loc[index, "correct"] = 1 - changed.loc[index, "correct"]
    altered = DKTDataset(changed, 5, BEHAVIOR_COLUMNS)[0]
    assert torch.equal(original[0], altered[0])
    assert not torch.equal(original[2], altered[2])
    # Modifying t=4 cannot affect any input through t=3.
    changed = df.copy()
    changed.loc[4, BEHAVIOR_COLUMNS] = [0, 50, 100, 900000]
    altered = DKTDataset(changed, 5, BEHAVIOR_COLUMNS)[0]
    assert torch.equal(original[0][:4], altered[0][:4])
    bad = df.copy()
    bad.loc[0, "hint_count"] = -1
    with pytest.raises(ValueError): normalize_behavior(bad, BEHAVIOR_COLUMNS)


def test_behavior_benchmark_shared_holdouts_and_parameter_control():
    _, report, predictions = behavioral_benchmark(synthetic_decisions(learners=6), epochs=1)
    assert report["parameter_counts"]["behavior_dkt"] == report["parameter_counts"]["zero_behavior_control"]
    assert set(["behavior_dkt", "dkt", "zero_behavior_control"]) <= set(report["transfer_metrics"])
    assert predictions.behavior_dkt.between(0, 1).all()
    assert report["metrics"]["test"]["behavior_dkt"]["n_predictions"] == report["metrics"]["test"]["dkt"]["n_predictions"]
    json.dumps(report, allow_nan=False)
