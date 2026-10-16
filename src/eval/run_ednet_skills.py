"""Paired part/tag replication; see docs/EDNET_SKILL_PROTOCOL.md."""
import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.data_collection.fetch_ednet import sha256
from src.eval.run_ednet_audit import BEHAVIOR, paired_auc
from src.eval.run_learning import dkt_scores, learner_split, metrics, validate_interactions
from src.features.skill_tags import parse_tags, tag_indices
from src.models.dkt import normalize_behavior, train_dkt


def encode(df, mapping=None):
    return ([tag_indices(v,mapping) for v in df.tags] if mapping is not None
            else [(int(v),) for v in df.skill_id])


def fit_priors(df, n_skills, mapping=None):
    attempts, correct = np.zeros(n_skills), np.zeros(n_skills)
    for indices,y in zip(encode(df,mapping),df.correct):
        attempts[list(indices)] += 1
        correct[list(indices)] += int(y)
    return (correct+1)/(attempts+2), attempts


def target_features(df, priors, mapping=None, training_counts=None):
    """One target row per response; target tags are known, target telemetry isn't."""
    df = df.reset_index(drop=True)
    n = len(priors)
    encoded, behavior = encode(df,mapping), normalize_behavior(df,BEHAVIOR)
    rows, features, augmented, prior_scores = [], [], [], []
    for sid,group in df.groupby("student_id",sort=True):
        counts, corrects, total, telemetry_sum = np.zeros(n),np.zeros(n),0,np.zeros(2)
        records = group.to_dict("records")
        for t,current in enumerate(records[:-1]):
            indices = list(encoded[group.index[t]])
            counts[indices] += 1
            corrects[indices] += int(current["correct"])
            total += int(current["correct"])
            last_behavior = behavior[group.index[t]]
            telemetry_sum += last_behavior
            target = records[t+1]
            following = list(encoded[group.index[t+1]])
            x = np.zeros(n+5,dtype=np.float32)
            x[following] = 1/len(following)
            x[n:] = [counts[following].mean(), ((corrects[following]+2*priors[following])/(counts[following]+2)).mean(),
                     t+1,(total+1)/(t+3),int(current["correct"])]
            features.append(x)
            augmented.append(np.r_[x,last_behavior,telemetry_sum/(t+1)].astype(np.float32))
            prior_scores.append(float(priors[following].mean()))
            raw_tags = parse_tags(target["tags"])
            rows.append({"student_id":sid,"timestamp":target["timestamp"],"question_id":target["question_id"],
                         "part":int(target["part"]),"correct":int(target["correct"]),
                         "unknown_tags":int(raw_tags == (-1,)),"tag_count":len(raw_tags),
                         "has_unseen_training_tag":int(any(training_counts[i]==0 for i in following)) if training_counts is not None else 0})
    return pd.DataFrame(rows),np.asarray(features),np.asarray(augmented),np.asarray(prior_scores)


def diagnostics(rows, scores):
    result = {"all":metrics(rows.correct.to_numpy(),scores),"by_part":{},"by_tag_status":{}}
    for field,key in [("part","by_part"),("unknown_tags","by_tag_status"),("has_unseen_training_tag","by_training_support")]:
        result[key] = {}
        for value,group in rows.groupby(field):
            indices = group.index.to_numpy()
            result[key][str(value)] = metrics(group.correct.to_numpy(),scores[indices])
    return result


def run(df, manifest, previous, output, seeds=(42,43,44), epochs=10):
    df = validate_interactions(df,7)
    overlap = set(df.student_id) & set(previous.student_id.astype(str))
    if overlap:
        raise ValueError(f"Replication overlaps previous cohort: {len(overlap)} learners")
    mapping = manifest["tag_mapping"]
    splits,ids = learner_split(df,42)
    splits = {k:v.reset_index(drop=True) for k,v in splits.items()}
    report = {"protocol":"docs/EDNET_SKILL_PROTOCOL.md","protocol_sha256":sha256(Path("docs/EDNET_SKILL_PROTOCOL.md")),
              "dataset_provenance":manifest,"prior_cohort_overlap":len(overlap),
              "split_seed":42,"split_learners":{k:list(v) for k,v in ids.items()},
              "configuration":{"model_seeds":list(seeds),"epochs":epochs,"hidden_dim":32,"batch_size":32,"learning_rate":.001,
                               "tag_input":"unit-weight bag","tag_readout":"sigmoid(mean target-tag logits)","device":"cpu"},
              "environment":{"python":platform.python_version(),**{p:version(p) for p in ["numpy","pandas","scikit-learn","torch"]}},
              "representations":{},"paired_comparisons":[],
              "limitations":["Independent learner cohort from the same EdNet platform, not an independent dataset",
                              "Exploratory follow-up, one selected sample and fixed training budget",
                              "Different representation widths imply different parameter counts",
                              "Multi-tag mean-logit model is an explicit extension of single-tag DKT",
                              "Predictive performance is not evidence of learning benefit or novelty"]}
    output.mkdir(parents=True,exist_ok=True)
    all_predictions, test_rows, test_scores = [],None,{}
    for representation,tag_map,n in [("parts",None,7),("tags",mapping,len(mapping))]:
        print(f"Building {representation} features ({n} categories)",flush=True)
        priors,training_counts = fit_priors(splits["train"],n,tag_map)
        designs = {s:target_features(frame,priors,tag_map,training_counts) for s,frame in splits.items()}
        rows = {s:designs[s][0] for s in ["validation","test"]}
        if test_rows is None:
            test_rows = rows["test"]
        else:
            keys = ["student_id","timestamp","question_id","part","correct","unknown_tags","tag_count"]
            if not test_rows[keys].equals(rows["test"][keys]):
                raise AssertionError("Representations must use identical target responses")
        entry = {"n_categories":n,"training_category_counts":training_counts.tolist(),"logistic":{},"runs":[]}
        report["representations"][representation] = entry
        scores = {s:{} for s in rows}
        for name,col in [("logistic",1),("behavior_logistic",2)]:
            model = make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=42))
            model.fit(designs["train"][col],designs["train"][0].correct)
            entry["logistic"][name] = {}
            for split in rows:
                values = model.predict_proba(designs[split][col])[:,1]
                scores[split][name] = values
                entry["logistic"][name][split] = diagnostics(rows[split],values)
        for split in rows:
            scores[split]["prior"] = designs[split][3]
        # Logistic models are deterministic controls fitted once per encoding.
        for seed in seeds:
            run_result = {"seed":seed,"models":{},"paired_test_auc":{}}
            for name,columns in [("correctness_dkt",[]),("behavior_dkt",BEHAVIOR),("zero_telemetry_dkt",BEHAVIOR)]:
                print(f"{representation}, seed {seed}: training {name}",flush=True)
                train = splits["train"].copy()
                if name == "zero_telemetry_dkt":
                    train[BEHAVIOR] = 0
                model,history = train_dkt(train,n,epochs=epochs,hidden_dim=32,seed=seed,behavior_columns=columns,tag_mapping=tag_map)
                model_result = {"parameters":sum(p.numel() for p in model.parameters()),"training_loss":history["loss"],"metrics":{}}
                for split in rows:
                    frame = splits[split].copy()
                    if name == "zero_telemetry_dkt":
                        frame[BEHAVIOR] = 0
                    values = dkt_scores(model,frame,n,columns,tag_map)
                    scores[split][name] = values
                    model_result["metrics"][split] = diagnostics(rows[split],values)
                run_result["models"][name] = model_result
                torch.save({"state_dict":model.state_dict(),"n_skills":n,"hidden_dim":32,"tag_mapping":tag_map,
                            "behavior_columns":columns,"source":"ednet_skill_replication","bank_version":f"ednet-{representation}-v1",
                            "seed":seed,"zero_telemetry":name=="zero_telemetry_dkt"},output/f"{representation}_{name}_{seed}.pt")
            for left,right in [("behavior_dkt","correctness_dkt"),("behavior_dkt","zero_telemetry_dkt"),
                               ("behavior_dkt","behavior_logistic"),("behavior_logistic","logistic")]:
                run_result["paired_test_auc"][f"{left}_minus_{right}"] = paired_auc(rows["test"],scores["test"][left],scores["test"][right])
            entry["runs"].append(run_result)
            test_scores[(representation,seed)] = {k:v.copy() for k,v in scores["test"].items()}
            for split in rows:
                frame = rows[split].copy()
                frame["split"],frame["representation"],frame["seed"] = split,representation,seed
                for name,values in scores[split].items():
                    frame[name] = values
                all_predictions.append(frame)
            (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
            print(json.dumps({"representation":representation,"seed":seed,"test_auc":{k:metrics(rows['test'].correct.to_numpy(),v)['roc_auc'] for k,v in scores['test'].items()},
                              "behavior_minus_correctness":run_result["paired_test_auc"]["behavior_dkt_minus_correctness_dkt"]}),flush=True)
        del designs
    for seed in seeds:
        report["paired_comparisons"].append({"seed":seed,"tags_minus_parts":{
            name:paired_auc(test_rows,test_scores[("tags",seed)][name],test_scores[("parts",seed)][name])
            for name in ["correctness_dkt","behavior_dkt","zero_telemetry_dkt","logistic","behavior_logistic"]}})
    pd.concat(all_predictions,ignore_index=True).to_csv(output/"predictions.csv.gz",index=False)
    (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,default=Path("data/processed/ednet/replication/interactions.csv"))
    p.add_argument("--manifest",type=Path,default=Path("data/processed/ednet/replication/manifest.json"))
    p.add_argument("--previous",type=Path,default=Path("data/processed/ednet/pilot/interactions.csv"))
    p.add_argument("--output",type=Path,default=Path("data/processed/ednet/skill_replication"))
    p.add_argument("--seeds",type=int,nargs="+",default=[42,43,44])
    p.add_argument("--epochs",type=int,default=10)
    a = p.parse_args()
    if a.epochs<1 or len(set(a.seeds)) != len(a.seeds):
        p.error("Use positive epochs and unique seeds")
    manifest = json.loads(a.manifest.read_text())
    if manifest["output_sha256"] != sha256(a.input) or manifest["exclude_input_sha256"] != sha256(a.previous):
        p.error("Cohort or exclusion input differs from its manifest")
    report = run(pd.read_csv(a.input),manifest,pd.read_csv(a.previous),a.output,a.seeds,a.epochs)
    report["split_learner_counts"] = {k:len(v) for k,v in report.pop("split_learners").items()}
    snapshot = Path("docs/results/ednet_skill_replication.json")
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    snapshot.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(f"Completed. Results: {snapshot}; artifacts: {a.output}")


if __name__ == "__main__":
    main()
