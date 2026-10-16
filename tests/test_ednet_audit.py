import numpy as np
import pandas as pd
import pytest
import torch

from src.eval.run_ednet_audit import (
    BEHAVIOR, SCENARIOS, audit_policy, choose, design, neural_vectors, perturb, run,
)
from src.eval.run_learning import historical_features
from src.models.dkt import DKT


def example(learners=1):
    return pd.DataFrame([dict(student_id=f"u{s}",timestamp=t,skill_id=t%3,
                              correct=(t+s)%2,duration_ms=1234+1000*t,
                              revision_count=t%4)
                         for s in range(learners) for t in range(8)])


def test_recording_changes_preserve_answers_order_and_source():
    df = example()
    for name in SCENARIOS:
        other = perturb(df,name)
        protected = [c for c in df if c not in BEHAVIOR]
        pd.testing.assert_frame_equal(other[protected],df[protected])
        assert (other[BEHAVIOR] >= 0).all().all()
    pd.testing.assert_frame_equal(perturb(df,"identity"),df)
    assert perturb(df,"revisions_binary").revision_count.max() == 1
    assert perturb(df,"telemetry_missing_zero")[BEHAVIOR].eq(0).all().all()
    with pytest.raises(ValueError,match="Unknown"):
        perturb(df,"bad")


def test_design_uses_past_only_and_matches_logistic_history():
    df = example()
    priors = np.array([.3,.5,.7])
    rows, plain, enriched, candidates = design(df,3,priors)
    for t in range(7):
        for category in range(3):
            np.testing.assert_allclose(plain[t,category],historical_features(df.iloc[:t+1].to_dict("records"),category,3,priors))
    changed = df.copy()
    changed.loc[changed.timestamp>=4,BEHAVIOR] = 0
    _, other_plain, other_enriched, other_candidates = design(changed,3,priors)
    np.testing.assert_array_equal(plain,other_plain)
    np.testing.assert_array_equal(enriched[:4],other_enriched[:4])
    np.testing.assert_array_equal(candidates,other_candidates)
    assert not candidates[0,1] and rows.iloc[0].skill_id == 1
    # Telemetry for the final target is never consumed by any prediction.
    changed = df.copy()
    changed.loc[len(df)-1,BEHAVIOR] = 99999
    np.testing.assert_array_equal(enriched,design(changed,3,priors)[2])


def test_neural_controls_and_future_telemetry_do_not_change_prefix():
    df = example()
    torch.manual_seed(7)
    plain = DKT(3,hidden_dim=4)
    augmented = DKT(3,hidden_dim=4,n_behavior=2)
    np.testing.assert_array_equal(neural_vectors(plain,df,3,[]),neural_vectors(plain,perturb(df,"telemetry_missing_zero"),3,[]))
    clean = neural_vectors(augmented,df,3,BEHAVIOR)
    changed = df.copy()
    changed.loc[changed.timestamp>=4,BEHAVIOR] = 0
    np.testing.assert_array_equal(clean[:4],neural_vectors(augmented,changed,3,BEHAVIOR)[:4])


def test_policy_excludes_unseen_categories_and_gate_is_not_unseen_guarantee():
    scores = np.array([[.8,.2,.01],[.4,.5,.01],[.6,.3,.01]])
    candidates = np.array([[True,False,False],[True,True,False],[True,True,False]])
    choices, _, eligible = choose(scores,candidates)
    assert choices.tolist() == [-1,0,1] and eligible.tolist() == [False,True,True]
    rows = pd.DataFrame({"student_id":["u1"]*3,"correct":[0,1,0]})
    vectors = {s:{name:scores.copy() for name in SCENARIOS} for s in ["validation","test"]}
    # Agreement on gate scenarios does not guarantee agreement on an unseen one.
    vectors["test"]["duration_plus_30s"][1,:2] = [.9,.1]
    report = audit_policy({"validation":rows,"test":rows},vectors,{"validation":candidates,"test":candidates})
    policy = report["splits"]["test"]["policies"]["consistency_gate"]
    assert policy["coverage_among_eligible"] == 1
    assert policy["scenarios"]["duration_plus_30s"]["flip_rate"] == .5
    assert policy["scenarios"]["duration_plus_5s"]["flip_rate"] == 0
    assert report["splits"]["test"]["excluded_single_category_prefixes"] == 1


def test_tiny_complete_audit(tmp_path):
    report = run(example(10),{"n_skills":3},tmp_path,seeds=[7],epochs=1)
    assert len(report["runs"]) == 1
    result = report["runs"][0]
    assert result["parameter_counts"]["behavior_dkt"] == result["parameter_counts"]["zero_telemetry_dkt"]
    for model in ["correctness_dkt","zero_telemetry_dkt","logistic"]:
        assert all(v["max_abs_any_category_probability_change"] == 0
                   for v in result["models"][model]["sensitivity"]["test"].values())
    assert (tmp_path/"clean_predictions.csv.gz").exists()
    assert result["models"]["behavior_dkt"]["prediction"]["test"]["n_predictions"] == 14
