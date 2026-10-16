import csv
import io
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest
import torch

from src.eval.run_ednet_skills import fit_priors, run, target_features
from src.features.prepare_ednet import prepare
from src.features.skill_tags import parse_tags, tag_mapping
from src.models.dkt import DKTDataset, DKT, _collate, _step_logits


def sample(learners=1):
    return pd.DataFrame([dict(student_id=f"u{s}",timestamp=t,skill_id=t%3,part=t%3+1,
                              question_id=f"q{t}",tags=["10;11","11","-1","12"][t%4],
                              correct=(s+t)%2,duration_ms=1000*(t+1),revision_count=t%3)
                         for s in range(learners) for t in range(8)])


def test_canonical_tags_keep_all_skills_and_separate_unknown():
    assert parse_tags("11;10;11;-1") == (10,11)
    assert parse_tags("-1") == (-1,)
    assert tag_mapping(["10;11","-1","12"]) == {"-1":0,"10":1,"11":2,"12":3}
    with pytest.raises(ValueError):
        parse_tags("-2")


def test_multitag_response_is_one_step_with_unit_weight_and_one_target():
    df = sample()
    mapping = tag_mapping(df.tags)
    data = DKTDataset(df,4,tag_mapping=mapping)
    assert len(data) == 1
    x,targets,y,length = data[0]
    assert length == 7 and x.shape == (7,8) and y.shape == (7,)
    np.testing.assert_allclose(x.sum(axis=1),1)
    np.testing.assert_allclose(targets.sum(axis=1),1)
    assert x[0,1] == .5 and x[0,2] == .5
    # Second target is the unknown-metadata question, not a fabricated skill.
    assert targets[1,0] == 1
    batch = _collate([data[0]])
    model = DKT(4,hidden_dim=4)
    logits = model(batch[0],batch[-1])
    np.testing.assert_allclose(_step_logits(model,batch[0],batch[1],batch[-1]).detach(),(logits*batch[1]).sum(-1).detach())


def test_single_tag_multitag_encoding_matches_original():
    df = sample()
    df["tags"] = df.skill_id.astype(str)
    mapping = {str(i):i for i in range(3)}
    original,tagged = DKTDataset(df,3)[0],DKTDataset(df,3,tag_mapping=mapping)[0]
    for a,b in zip(original,tagged):
        np.testing.assert_array_equal(a,b)


def test_original_tag_features_are_past_only():
    df = sample()
    mapping = tag_mapping(df.tags)
    priors,counts = fit_priors(df,4,mapping)
    rows,plain,enriched,prior_scores = target_features(df,priors,mapping,counts)
    assert len(rows) == 7 and plain.shape == (7,9)
    assert np.allclose(plain[:,:4].sum(axis=1),1)
    changed = df.copy()
    changed.loc[7,["duration_ms","revision_count","correct"]] = [999999,99,1-int(df.iloc[7].correct)]
    other = target_features(changed,priors,mapping,counts)
    np.testing.assert_array_equal(plain,other[1])
    np.testing.assert_array_equal(enriched,other[2])
    np.testing.assert_array_equal(prior_scores,other[3])
    # Unknown-target indicator is explicit and can be analyzed separately.
    assert rows.unknown_tags.sum() == 2


def test_preparation_excludes_previous_learners(tmp_path):
    raw,contents = tmp_path/"kt2.zip",tmp_path/"contents.zip"
    previous = tmp_path/"old.csv"
    pd.DataFrame({"student_id":["u0","u1","u2"]}).to_csv(previous,index=False)
    with ZipFile(contents,"w") as z:
        z.writestr("contents/questions.csv","question_id,bundle_id,correct_answer,part,tags\nq1,b1,a,1,10;11\n")
    with ZipFile(raw,"w") as z:
        for i in range(10):
            f = io.StringIO()
            writer = csv.DictWriter(f,fieldnames=["timestamp","action_type","item_id","user_answer"])
            writer.writeheader()
            for t in range(3):
                for offset,action,item,answer in [(0,"enter","b1",""),(1,"respond","q1","a"),(2,"submit","b1","")]:
                    writer.writerow(dict(timestamp=3*t+offset,action_type=action,item_id=item,user_answer=answer))
            z.writestr(f"KT2/u{i}.csv",f.getvalue())
    manifest = prepare(raw,contents,tmp_path/"prepared",learners=6,minimum=2,maximum=3,exclude_input=previous)
    new = pd.read_csv(tmp_path/"prepared/interactions.csv")
    assert not set(new.student_id) & {"u0","u1","u2"}
    assert manifest["excluded_prior_learners"] == 3
    assert manifest["tag_mapping"] == {"-1":0,"10":1,"11":2}


def test_small_replication_and_overlap_guard(tmp_path):
    df = sample(10)
    manifest = {"tag_mapping":tag_mapping(df.tags)}
    with pytest.raises(ValueError,match="overlaps"):
        run(df,manifest,pd.DataFrame({"student_id":["u0"]}),tmp_path,seeds=[7],epochs=1)
    report = run(df,manifest,pd.DataFrame({"student_id":["u99"]}),tmp_path,seeds=[7],epochs=1)
    assert report["prior_cohort_overlap"] == 0 and len(report["paired_comparisons"]) == 1
    for rep in ["parts","tags"]:
        models = report["representations"][rep]["runs"][0]["models"]
        assert models["behavior_dkt"]["parameters"] == models["zero_telemetry_dkt"]["parameters"]
        assert models["correctness_dkt"]["metrics"]["test"]["all"]["n_predictions"] == 14
    assert (tmp_path/"predictions.csv.gz").exists()
