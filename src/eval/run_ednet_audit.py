"""Exploratory telemetry sensitivity experiment; see docs/EDNET_AUDIT_PROTOCOL.md.

python -m src.eval.run_ednet_audit
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader

from src.data_collection.fetch_ednet import sha256
from src.eval.run_learning import learner_split, metrics, prior_rates, validate_interactions
from src.models.dkt import DKTDataset, _collate, normalize_behavior, train_dkt

BEHAVIOR = ["duration_ms", "revision_count"]
VARIANTS = {
    "correctness_dkt": [], "duration_dkt": ["duration_ms"],
    "revision_dkt": ["revision_count"], "behavior_dkt": BEHAVIOR,
    "zero_telemetry_dkt": BEHAVIOR,
}
DEVELOPMENT = ["duration_round_1s", "duration_plus_5s", "revisions_binary"]
UNSEEN = ["duration_plus_30s", "revisions_minus_one", "telemetry_missing_zero"]
SCENARIOS = ["identity", *DEVELOPMENT, *UNSEEN]


def perturb(df, scenario):
    changed = df.copy()
    if scenario == "duration_round_1s":
        changed["duration_ms"] = np.floor(changed.duration_ms / 1000 + .5) * 1000
    elif scenario == "duration_plus_5s":
        changed["duration_ms"] += 5000
    elif scenario == "duration_plus_30s":
        changed["duration_ms"] += 30000
    elif scenario == "revisions_binary":
        changed["revision_count"] = changed.revision_count.clip(upper=1)
    elif scenario == "revisions_minus_one":
        changed["revision_count"] = (changed.revision_count - 1).clip(lower=0)
    elif scenario == "telemetry_missing_zero":
        changed[BEHAVIOR] = 0
    elif scenario != "identity":
        raise ValueError(f"Unknown scenario: {scenario}")
    protected = [c for c in df if c not in BEHAVIOR]
    if not changed[protected].equals(df[protected]):
        raise AssertionError("Recording scenarios must preserve answers and order")
    return changed


def design(df, n_skills, priors):
    """All-category features and observed-prefix candidate masks.

    At index t, only records <= t inform predictions for response t+1.
    Logistic history features match run_learning's historical_features.
    """
    df = df.reset_index(drop=True)
    rows, plain, enriched, candidates = [], [], [], []
    normalized = normalize_behavior(df, BEHAVIOR)
    for student, group in df.groupby("student_id", sort=True):
        history_n = np.zeros(n_skills, dtype=int)
        history_correct = np.zeros(n_skills, dtype=int)
        total, telemetry_sum = 0, np.zeros(len(BEHAVIOR))
        records = group.to_dict("records")
        for t, current in enumerate(records[:-1]):
            skill, correct = int(current["skill_id"]), int(current["correct"])
            history_n[skill] += 1
            history_correct[skill] += correct
            total += correct
            behavior = normalized[group.index[t]]
            telemetry_sum += behavior
            same_rate = (history_correct + 2 * priors) / (history_n + 2)
            extra = np.column_stack([history_n, same_rate, np.full(n_skills,t+1),
                                     np.full(n_skills,(total+1)/(t+3)), np.full(n_skills,correct)])
            features = np.column_stack([np.eye(n_skills), extra])
            telemetry = np.tile(np.r_[behavior, telemetry_sum/(t+1)], (n_skills,1))
            plain.append(features)
            enriched.append(np.column_stack([features,telemetry]))
            candidates.append(history_n > 0)
            target = records[t+1]
            rows.append({"student_id":student,"timestamp":target["timestamp"],
                         "skill_id":int(target["skill_id"]),"correct":int(target["correct"])})
    return pd.DataFrame(rows), np.asarray(plain), np.asarray(enriched), np.asarray(candidates)


def neural_vectors(model, df, n_skills, columns):
    model.eval()
    vectors = []
    with torch.no_grad():
        for x, _, _, mask, lengths in DataLoader(DKTDataset(df,n_skills,columns),batch_size=32,collate_fn=_collate):
            vectors.append(torch.sigmoid(model(x,lengths))[mask.bool()].numpy())
    return np.concatenate(vectors)


def choose(vectors, candidates):
    allowed = candidates.sum(axis=1) >= 2
    ordered = np.sort(np.where(candidates, vectors, np.inf),axis=1)
    margin = np.zeros(len(vectors))
    margin[allowed] = ordered[allowed,1] - ordered[allowed,0]
    choice = np.argmin(np.where(candidates,vectors,np.inf),axis=1)
    choice[~allowed] = -1
    return choice, margin, allowed


def paired_auc(rows, left, right, seed=42, draws=200):
    groups = [g.index.to_numpy() for _,g in rows.reset_index(drop=True).groupby("student_id",sort=True)]
    y = rows.correct.to_numpy()
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        idx = np.concatenate([groups[i] for i in rng.integers(len(groups),size=len(groups))])
        if len(np.unique(y[idx])) == 2:
            values.append(roc_auc_score(y[idx],left[idx])-roc_auc_score(y[idx],right[idx]))
    return {"point_difference":float(roc_auc_score(y,left)-roc_auc_score(y,right)),
            "paired_95pct_interval":np.quantile(values,[.025,.975]).tolist() if values else None,
            "valid_resamples":len(values)}


def flip_summary(rows, clean_choice, changed_choice, accepted, draws=200):
    accepted = np.asarray(accepted,dtype=bool)
    flips = (clean_choice != changed_choice) & accepted
    per = pd.DataFrame({"student_id":rows.student_id,"accepted":accepted,"flips":flips}).groupby("student_id").sum()
    totals = per[["accepted","flips"]].to_numpy()
    rng = np.random.default_rng(42)
    rates = []
    for _ in range(draws):
        sample = totals[rng.integers(len(totals),size=len(totals))].sum(axis=0)
        if sample[0]:
            rates.append(sample[1]/sample[0])
    n = int(accepted.sum())
    return {"recommendations":n,"flips":int(flips.sum()),"flip_rate":float(flips.sum()/n) if n else None,
            "learner_bootstrap_95pct_interval":np.quantile(rates,[.025,.975]).tolist() if rates else None}


def audit_policy(rows_by_split, vectors, candidates):
    choices, margins, allowed = {}, {}, {}
    for split in ["validation","test"]:
        choices[split] = {}
        for scenario, values in vectors[split].items():
            decision, gap, eligible = choose(values,candidates[split])
            choices[split][scenario] = decision
            if scenario == "identity":
                margins[split], allowed[split] = gap, eligible
    accepted = {s:allowed[s] & np.all(np.column_stack([choices[s][name] == choices[s]["identity"] for name in DEVELOPMENT]),axis=1)
                for s in choices}
    val_eligible = allowed["validation"]
    coverage = float(accepted["validation"].sum()/val_eligible.sum()) if val_eligible.any() else 0.0
    threshold = float(np.quantile(margins["validation"][val_eligible],1-coverage)) if val_eligible.any() else None
    report = {"margin_threshold_from_validation":threshold,"validation_gate_coverage":coverage,
              "gate_development_scenarios":DEVELOPMENT,"unseen_evaluation_scenarios":UNSEEN,"splits":{}}
    for split in choices:
        eligible = allowed[split]
        margin_accept = eligible & (margins[split] >= threshold) if threshold is not None else np.zeros(len(eligible),dtype=bool)
        policies = {"always":eligible,"consistency_gate":accepted[split],"margin_control":margin_accept}
        report["splits"][split] = {"decision_points":len(eligible),"eligible_points":int(eligible.sum()),
                                  "excluded_single_category_prefixes":int((~eligible).sum()),"policies":{}}
        for policy, mask in policies.items():
            report["splits"][split]["policies"][policy] = {
                "coverage_among_eligible":float(mask.sum()/eligible.sum()) if eligible.any() else 0.0,
                "scenarios":{name:flip_summary(rows_by_split[split],choices[split]["identity"],choices[split][name],mask)
                             for name in SCENARIOS}}
    return report


def run(df, manifest, output, seeds=(42,43,44), epochs=10):
    n_skills = manifest["n_skills"]
    df = validate_interactions(df,n_skills)
    normalize_behavior(df,BEHAVIOR)
    splits, ids = learner_split(df,42)
    splits = {k:v.reset_index(drop=True) for k,v in splits.items()}
    priors = prior_rates(splits["train"],n_skills)
    print("Building past-only logistic features",flush=True)
    designs = {key:design(value,n_skills,priors) for key,value in splits.items()}
    train_rows, plain, enriched, _ = designs["train"]
    indices = np.arange(len(train_rows)), train_rows.skill_id.to_numpy()
    logistics = {}
    for name, features in [("logistic",plain),("behavior_logistic",enriched)]:
        model = make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=42))
        model.fit(features[indices],train_rows.correct)
        logistics[name] = model
    rows = {s:designs[s][0] for s in ["validation","test"]}
    candidates = {s:designs[s][3] for s in rows}
    changed = {s:{name:perturb(splits[s],name) for name in SCENARIOS} for s in rows}
    logistic_vectors = {name:{s:{} for s in rows} for name in logistics}
    for split in rows:
        for scenario in SCENARIOS:
            if scenario == "identity":
                plain, enriched = designs[split][1:3]
            else:
                _,plain,enriched,_ = design(changed[split][scenario],n_skills,priors)
            for name, features in [("logistic",plain),("behavior_logistic",enriched)]:
                logistic_vectors[name][split][scenario] = logistics[name].predict_proba(features.reshape(-1,features.shape[-1]))[:,1].reshape(-1,n_skills)
    report = {"protocol":"docs/EDNET_AUDIT_PROTOCOL.md","dataset_provenance":manifest,
              "split_seed":42,"model_seeds":list(seeds),"epochs":epochs,"n_skills":n_skills,
              "split_learners":{k:list(v) for k,v in ids.items()},"runs":[],
              "logistic_repeated_across_seeds":True,"limitations":[
                  "Exploratory follow-up on an already inspected test split", "Synthetic recording scenarios, not observed EdNet failures",
                  "Coarse TOEIC categories and selected learner subset", "Hypothetical practice policy; no educational utility validation",
                  "Gate agreement on included scenarios is true by construction; only unseen scenarios test generalization",
                  "No novelty, causal cognition-invariance or DeFi learning-benefit claim"]}
    predictions = []
    output.mkdir(parents=True,exist_ok=True)
    for seed in seeds:
        vectors = dict(logistic_vectors)
        losses, parameters = {}, {}
        for name, columns in VARIANTS.items():
            print(f"Seed {seed}: training {name} ({epochs} epochs)",flush=True)
            train = splits["train"].copy()
            if name == "zero_telemetry_dkt":
                train[BEHAVIOR] = 0
            model, history = train_dkt(train,n_skills,epochs=epochs,hidden_dim=32,seed=seed,behavior_columns=columns)
            losses[name] = history["loss"]
            parameters[name] = sum(p.numel() for p in model.parameters())
            vectors[name] = {s:{} for s in rows}
            for split in rows:
                for scenario in SCENARIOS:
                    if not columns and scenario != "identity":
                        values = vectors[name][split]["identity"]
                    else:
                        frame = changed[split][scenario].copy()
                        if name == "zero_telemetry_dkt":
                            frame[BEHAVIOR] = 0
                        values = neural_vectors(model,frame,n_skills,columns)
                    vectors[name][split][scenario] = values
            torch.save({"state_dict":model.state_dict(),"n_skills":n_skills,"hidden_dim":32,
                        "behavior_columns":columns,"source":"ednet_telemetry_audit","bank_version":"ednet-parts-v1",
                        "model_seed":seed,"zero_telemetry":name=="zero_telemetry_dkt"},output/f"{name}_seed{seed}.pt")
        run_report = {"seed":seed,"training_loss":losses,"parameter_counts":parameters,"models":{},"paired_test_auc":{}}
        clean_scores = {}
        for name in vectors:
            entry = {"prediction":{},"sensitivity":{},"policy":audit_policy(rows,vectors[name],candidates)}
            for split in rows:
                target = rows[split].skill_id.to_numpy()
                clean = vectors[name][split]["identity"]
                clean_score = clean[np.arange(len(target)),target]
                if split == "test":
                    clean_scores[name] = clean_score
                entry["prediction"][split] = metrics(rows[split].correct.to_numpy(),clean_score)
                entry["sensitivity"][split] = {}
                for scenario, values in vectors[name][split].items():
                    score = values[np.arange(len(target)),target]
                    delta = np.abs(values-clean)
                    entry["sensitivity"][split][scenario] = {"prediction":metrics(rows[split].correct.to_numpy(),score),
                        "mean_abs_target_probability_change":float(np.abs(score-clean_score).mean()),
                        "max_abs_any_category_probability_change":float(delta.max()),
                        "target_threshold_flip_rate":float(((score>=.5)!=(clean_score>=.5)).mean())}
                    if scenario == "identity" and np.any(delta):
                        raise AssertionError("Identity control must produce exact equality")
                frame = rows[split].copy()
                frame["split"], frame["seed"], frame["model"], frame["probability"] = split,seed,name,clean_score
                predictions.append(frame)
            run_report["models"][name] = entry
        for left,right in [("behavior_dkt","correctness_dkt"),("behavior_dkt","zero_telemetry_dkt"),
                           ("behavior_dkt","behavior_logistic"),("behavior_logistic","logistic")]:
            run_report["paired_test_auc"][f"{left}_minus_{right}"] = paired_auc(rows["test"],clean_scores[left],clean_scores[right])
        report["runs"].append(run_report)
        (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
        print(json.dumps({"seed":seed,"test_auc":{name:entry["prediction"]["test"]["roc_auc"] for name,entry in run_report["models"].items()},
                          "behavior_minus_correctness":run_report["paired_test_auc"]["behavior_dkt_minus_correctness_dkt"]}),flush=True)
    pd.concat(predictions,ignore_index=True).to_csv(output/"clean_predictions.csv.gz",index=False)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,default=Path("data/processed/ednet/pilot/interactions.csv"))
    p.add_argument("--manifest",type=Path,default=Path("data/processed/ednet/pilot/manifest.json"))
    p.add_argument("--output",type=Path,default=Path("data/processed/ednet/telemetry_audit"))
    p.add_argument("--seeds",type=int,nargs="+",default=[42,43,44])
    p.add_argument("--epochs",type=int,default=10)
    args = p.parse_args()
    if args.epochs < 1 or len(set(args.seeds)) != len(args.seeds):
        p.error("Use positive epochs and unique model seeds")
    manifest = json.loads(args.manifest.read_text())
    if manifest["output_sha256"] != sha256(args.input) or manifest.get("dataset") != "EdNet-KT2":
        p.error("Input does not match EdNet preprocessing manifest")
    report = run(pd.read_csv(args.input),manifest,args.output,args.seeds,args.epochs)
    # Keep aggregate metrics, not participant IDs or model binaries, in the repo.
    report["split_learner_counts"] = {k:len(v) for k,v in report.pop("split_learners").items()}
    snapshot = Path("docs/results/ednet_telemetry_audit.json")
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    snapshot.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(f"Completed. Artifacts: {args.output}; aggregate snapshot: {snapshot}")


if __name__ == "__main__":
    main()
