import numpy as np
import pandas as pd
import pytest

from src.eval.run_item_control import QuestionRates


def training():
    return pd.DataFrame({"student_id":["a","a","a","b","b","c"],
                         "question_id":["q1","q1","q2","q1","q2","q2"],
                         "correct":[1,0,1,0,1,0]})


def test_question_encoding_excludes_whole_learners_including_future_labels():
    df = training()
    rows = pd.DataFrame({"student_id":["a","a"],"question_id":["q1","q2"]})
    first = QuestionRates(df).transform(rows,exclude_learner=True)
    changed = df.copy()
    changed.loc[changed.student_id.eq('a'),'correct'] = 1-df.loc[df.student_id.eq('a'),'correct']
    second = QuestionRates(changed).transform(rows,exclude_learner=True)
    for a,b in zip(first,second):
        np.testing.assert_array_equal(a,b)
    np.testing.assert_array_equal(first[2],[1,2])
    np.testing.assert_allclose(first[3],.4) # remaining labels 0,1,0 with +1/+2 smoothing
    np.testing.assert_allclose(first[0],[2/6,3/7])


def test_unseen_questions_use_training_global_prior_without_target_labels():
    df = training()
    rows = pd.DataFrame({'student_id':['new','new'],'question_id':['absent','q1'],'correct':[0,0]})
    encoder = QuestionRates(df)
    first = encoder.transform(rows)
    rows['correct'] = 1
    second = encoder.transform(rows)
    for a,b in zip(first,second):
        np.testing.assert_array_equal(a,b)
    assert first[2].tolist() == [0,3]
    assert first[0][0] == .5
    assert np.isfinite(first[1]).all()


def test_invalid_strength_and_single_learner_fallback():
    df = training().query("student_id == 'a'")
    with pytest.raises(ValueError):
        QuestionRates(df,strength=0)
    values,features,counts,prior = QuestionRates(df).transform(df,exclude_learner=True)
    assert np.all(counts==0) and np.all(values==.5) and np.all(prior==.5)
    assert np.isfinite(features).all()
