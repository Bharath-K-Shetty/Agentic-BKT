"""Question-difficulty controls; see docs/ITEM_CONTROL_PROTOCOL.md."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.data_collection.fetch_ednet import sha256
from src.eval.run_ednet_audit import paired_auc
from src.eval.run_ednet_skills import fit_priors, target_features
from src.eval.run_learning import learner_split, metrics, validate_interactions


class QuestionRates:
    """Cross-fitted item outcomes: learner-level leave-one-out on training rows."""
    def __init__(self, train, strength=5):
        if strength <= 0:
            raise ValueError("Smoothing strength must be positive")
        self.strength = strength
        self.count = len(train)
        self.success = int(train.correct.sum())
        self.items = train.groupby("question_id").correct.agg(["sum","count"])
        self.students = train.groupby("student_id").correct.agg(["sum","count"])
        self.student_items = train.groupby(["student_id","question_id"]).correct.agg(["sum","count"])

    def transform(self, rows, exclude_learner=False):
        counts = rows.question_id.map(self.items['count']).fillna(0).to_numpy(dtype=float)
        successes = rows.question_id.map(self.items['sum']).fillna(0).to_numpy(dtype=float)
        total = np.full(len(rows),self.count,dtype=float)
        global_success = np.full(len(rows),self.success,dtype=float)
        if exclude_learner:
            idx = pd.MultiIndex.from_frame(rows[["student_id","question_id"]])
            own = self.student_items.reindex(idx).fillna(0)
            counts -= own['count'].to_numpy()
            successes -= own['sum'].to_numpy()
            total -= rows.student_id.map(self.students['count']).fillna(0).to_numpy()
            global_success -= rows.student_id.map(self.students['sum']).fillna(0).to_numpy()
        rate = (global_success+1)/(total+2)
        prior = (successes+self.strength*rate)/(counts+self.strength)
        features = np.column_stack([np.log(prior/(1-prior)),np.log1p(counts)])
        return prior,features,counts,rate


def summarize(rows, scores, counts):
    result = {"all":metrics(rows.correct.to_numpy(),scores),"question_support":{}}
    masks = {"unseen":counts==0,"seen":counts>0,"seen_1_to_4":(counts>0)&(counts<5),"seen_5_plus":counts>=5}
    for name,mask in masks.items():
        result["question_support"][name] = metrics(rows.correct.to_numpy()[mask],scores[mask]) if mask.any() else {"n_predictions":0}
    return result


def run(df,manifest,output):
    df = validate_interactions(df,7)
    splits,ids = learner_split(df,42)
    mapping = manifest["tag_mapping"]
    priors,attempts = fit_priors(splits["train"],len(mapping),mapping)
    designs = {s:target_features(frame,priors,mapping,attempts) for s,frame in splits.items()}
    encoder = QuestionRates(splits["train"])
    extras = {s:encoder.transform(designs[s][0],exclude_learner=s=="train") for s in splits}
    X = {s:{"tag_history_logistic":designs[s][1],"tag_history_behavior_logistic":designs[s][2],
            "item_tag_static_logistic":np.column_stack([designs[s][1][:,:len(mapping)],extras[s][1]]),
            "item_tag_history_logistic":np.column_stack([designs[s][1],extras[s][1]]),
            "item_tag_history_behavior_logistic":np.column_stack([designs[s][2],extras[s][1]])}
         for s in splits}
    models = {}
    for name,values in X["train"].items():
        print(f"Fitting {name}",flush=True)
        model = make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=42))
        model.fit(values,designs["train"][0].correct)
        models[name] = model
    report = {"protocol":"docs/ITEM_CONTROL_PROTOCOL.md","protocol_sha256":sha256(Path('docs/ITEM_CONTROL_PROTOCOL.md')),
              "dataset_provenance":manifest,"split_seed":42,"smoothing_strength":5,
              "training_question_encoder":"Leave-one-learner-out; validation/test use only full training learners",
              "split_learner_counts":{k:len(v) for k,v in ids.items()},"metrics":{},"paired_test_auc":{},
              "limitations":["Exploratory follow-up on an already inspected cohort", "Same dataset as preceding EdNet studies",
                              "Question-rate control is not a full IRT/LKT implementation", "No educational-effect or novelty claim",
                              "Learner-bootstrap intervals do not capture item-population uncertainty"]}
    predictions, test_scores = [],None
    for split in ['validation','test']:
        rows = designs[split][0]
        scores = {"question_prior_only":extras[split][0],"global_prior":extras[split][3]}
        scores.update({name:model.predict_proba(X[split][name])[:,1] for name,model in models.items()})
        report["metrics"][split] = {name:summarize(rows,values,extras[split][2]) for name,values in scores.items()}
        frame = rows.copy()
        frame['split'],frame['training_question_count'] = split,extras[split][2]
        for name,values in scores.items():
            frame[name] = values
        predictions.append(frame)
        if split == 'test':
            test_scores = scores
    test_rows = designs['test'][0]
    for left,right in [('item_tag_history_logistic','tag_history_logistic'),
                       ('item_tag_history_behavior_logistic','item_tag_history_logistic'),
                       ('item_tag_history_logistic','item_tag_static_logistic')]:
        report['paired_test_auc'][f'{left}_minus_{right}'] = paired_auc(test_rows,test_scores[left],test_scores[right])
    output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.concat(predictions,ignore_index=True).to_csv(output/'predictions.csv.gz',index=False)
    print(json.dumps({'test_auc':{k:v['all']['roc_auc'] for k,v in report['metrics']['test'].items()},
                      'paired_test_auc':report['paired_test_auc']},indent=2))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path('data/processed/ednet/replication/interactions.csv'))
    p.add_argument('--manifest',type=Path,default=Path('data/processed/ednet/replication/manifest.json'))
    p.add_argument('--output',type=Path,default=Path('data/processed/ednet/item_control'))
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text())
    if manifest['output_sha256'] != sha256(a.input):
        p.error('Input does not match preprocessing manifest')
    report = run(pd.read_csv(a.input),manifest,a.output)
    snapshot = Path('docs/results/ednet_item_control.json')
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    snapshot.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
