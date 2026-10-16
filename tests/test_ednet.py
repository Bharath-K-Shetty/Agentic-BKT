import csv
import io
from zipfile import ZipFile

import pandas as pd
import pytest

from src.features.prepare_ednet import learner_rows, prepare
from src.eval.run_learning import prediction_rows, validate_interactions
from src.learning.tracing import bkt_predictions


QUESTIONS = {
    "q1": {"bundle_id": "b1", "part": 1, "tags": "1;2", "correct_answer": "b"},
    "q2": {"bundle_id": "b1", "part": 2, "tags": "3", "correct_answer": "a"},
}


def event(t, action, item, answer=""):
    return dict(timestamp=str(t), action_type=action, item_id=item, user_answer=answer, platform="mobile")


def test_bundle_one_target_choice_independent_of_outcome():
    events = [event(1,"enter","b1"), event(2,"respond","q1","a"), event(2,"respond","q2","a"),
              event(3,"respond","q1","a"), event(4,"respond","q1","b"), event(5,"submit","b1")]
    rows, counts = learner_rows(events, QUESTIONS, "u1")
    changed = [{**e, "user_answer": "c"} if e["action_type"] == "respond" else e for e in events]
    other, _ = learner_rows(changed, QUESTIONS, "u1")
    assert len(rows) == 1 and rows[0]["question_id"] == other[0]["question_id"]
    assert counts["other_answers_excluded"] == 1
    assert rows[0]["correct"] == 1 and other[0]["correct"] == 0
    assert rows[0]["duration_ms"] == 4


def test_revisions_incomplete_bundles_and_invalid_responses():
    events = [event(1,"enter","b1"), event(2,"respond","q1","a"), event(3,"respond","q1","a"),
              event(4,"respond","q1","b"), event(5,"respond","q999","b"), event(6,"submit","b1"),
              event(7,"enter","b1"), event(8,"respond","q1","c")]
    rows, counts = learner_rows(events, QUESTIONS, "u1")
    assert len(rows) == 1 and rows[0]["revision_count"] == 1
    assert rows[0]["correct"] == 1
    assert counts["abandoned_bundle"] == 1 and counts["ignored_response"] == 1
    with pytest.raises(ValueError, match="Unordered"):
        learner_rows([event(2,"enter","b1"),event(1,"submit","b1")], QUESTIONS, "u1")


def test_reproducible_archive_subset(tmp_path):
    kt2, contents = tmp_path / "kt2.zip", tmp_path / "contents.zip"
    with ZipFile(contents, "w") as z:
        z.writestr("contents/questions.csv", "question_id,bundle_id,correct_answer,part,tags\nq1,b1,b,1,1;2\n")
    with ZipFile(kt2,"w") as z:
        for learner in range(10):
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(event(0,"enter","b1")))
            writer.writeheader()
            for t in range(3):
                writer.writerows([event(3*t,"enter","b1"),event(3*t+1,"respond","q1","b"),event(3*t+2,"submit","b1")])
            z.writestr(f"KT2/u{learner}.csv",stream.getvalue())
    a = prepare(kt2, contents, tmp_path/"a", learners=6, minimum=2, maximum=2)
    b = prepare(kt2, contents, tmp_path/"b", learners=6, minimum=2, maximum=2)
    assert a == b and a["responses"] == 12
    df = pd.read_csv(tmp_path/"a/interactions.csv")
    validate_interactions(df, 7)
    assert df.student_id.nunique() == 6
    assert "hint_count" not in df and "inspection_count" not in df


def test_incremental_bkt_matches_history_replay():
    df = pd.DataFrame([{"student_id":"u1","skill_id":s,"correct":c,"timestamp":t}
                       for t,(s,c) in enumerate([(0,1),(1,0),(0,0),(1,1),(0,1)])])
    params = [(0.3,0.15,0.2,0.1),(0.6,0.05,0.33,0.2)]
    rows, _ = prediction_rows(df, 2, [0.5,0.5], params)
    history = df.to_dict("records")
    for t, row in enumerate(rows.to_dict("records"), 1):
        assert row["bkt"] == pytest.approx(bkt_predictions(history[:t], 2, params)[row["skill_id"]])
