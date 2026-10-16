"""Render saved confirmation outcomes without retraining or choosing new models."""
import json
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total)) / denominator
    half = z * sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return [center-half, center+half]


def main():
    path = ROOT / "docs/results/solana_confirmation.json"
    report = json.loads(path.read_text())
    primary = next(r for r in report["comparisons"] if r["primary"])
    delta, (lo, hi) = primary["ap"]["weighted_delta"], primary["ap"]["ci95"]
    predictions = [json.loads(l) for l in
                   (ROOT / "data/processed/solana_ml/confirmation_predictions.jsonl").read_text().splitlines()]
    fpr_checks = []
    for section in report["results"]:
        for m in section["models"]:
            rows = [r for r in predictions if r["horizon"] == section["horizon"]
                    and r["period"] == section["period"] and r["model"] == m["model"] and r["scope"] == m["scope"]]
            negatives = [r for r in rows if r["label"] == 0]
            false = sum(r["probability"] >= m["threshold"] for r in negatives)
            interval = wilson(false, len(negatives))
            fpr_checks.append({"horizon": section["horizon"], "period": section["period"],
                               "model": m["model"], "scope": m["scope"], "false_positives": false,
                               "negatives": len(negatives), "wilson_ci95": interval,
                               "point_above_budget": false / len(negatives) > .05,
                               "lower_ci_above_budget": interval[0] > .05})
    diagnostics = {"fpr_checks": fpr_checks,
                   "interpretation": "Marginal binomial intervals, not adjusted across models or periods and not wallet-cluster aware"}
    (ROOT / "docs/results/solana_confirmation_diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    lines = ["# Solana ML confirmation results", "",
             "Executed confirmation of the first pilot, using a protocol specified locally before this run. "
             "The protocol followed pilot exploration; it is not a public preregistration.", "",
             f"Primary comparison: adding six same-transaction co-participation summaries to random forest "
             f"at the 300-second horizon changes period-weighted average precision by **{delta:+.4f}**, "
             f"with paired day-block 95% interval **[{lo:+.4f}, {hi:+.4f}]**.", "",
             ("This does not support a consistent improvement in the primary comparison."
              if lo <= 0 <= hi else
              "The primary comparison supports an improvement within this source cohort. This is not proof of novelty."
              if lo > 0 else "The added features reduce performance in the primary comparison."), "",
             f"Selected {report['audit']['selected_tokens']:,} new sample tokens, excluding the 6,000 pilot ranks. "
             f"Verified pilot/confirmation token overlap: **{report['pilot_token_overlap']}**. "
             "Both cohorts come from the same historical MELT release, not independent market cycles.", "",
             "Target: price below 30% of migration price within 20 minutes after migration. "
             "Only eventual migrants are represented. This is collapse prediction, not proof of fraud.", "",
             "## Calendar-period results", "",
             "Predictions average three tree seeds (one deterministic logistic fit). Base has 21 prefix "
             "activity/holding features; coord adds six observed co-participation summaries. "
             "Each threshold is selected using validation labels only under a 5% FPR budget.", "",
             "| Prefix | Test period | Model | Features | Test n | AP | AUROC | Recall | FPR | Brier |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for s in report["results"]:
        for m in s["models"]:
            t = m["test"]
            lines.append(f"| {s['horizon']}s | {s['period']} | {m['model']} | {m['scope']} | "
                         f"{s['counts']['test']['n']} | {t['ap_positive']:.3f} | {t['auroc']:.3f} | "
                         f"{t['recall']:.1%} | {t['fpr']:.1%} | {t['brier']:.3f} |")
    lines += ["", "Chance AUROC is 0.5. Constant-score AP equals class prevalence. "
              "AUPRC/AP cannot be compared across periods without accounting for prevalence:", "",
              "| Prefix | Test period | Train n | Validation n | Test n | Positive prevalence |",
              "|---|---|---:|---:|---:|---:|"]
    for s in report["results"]:
        counts = s["counts"]
        lines.append(f"| {s['horizon']}s | {s['period']} | {counts['train']['n']} | "
                     f"{counts['validation']['n']} | {counts['test']['n']} | {counts['test']['prevalence']:.1%} |")
    above = sum(c["point_above_budget"] for c in fpr_checks)
    clear = sum(c["lower_ci_above_budget"] for c in fpr_checks)
    lines += ["", "## Threshold transfer and wallet overlap", "",
              f"Test FPR exceeds the nominal 5% budget in {above}/{len(fpr_checks)} model/period/horizon "
              f"comparisons. In {clear}, the marginal 95% Wilson lower bound also exceeds 5%. "
              "These are exploratory diagnostics; intervals are not adjusted for multiple comparisons "
              "or correlated wallets. A point estimate above the budget alone is not proof of a systematic failure.", "",
              "| Prefix | Test period | RF features | Higher novelty n | Higher novelty AUROC | Lower novelty n | Lower novelty AUROC |",
              "|---|---|---|---:|---:|---:|---:|"]
    for s in report["results"]:
        for m in s["models"]:
            if m["model"] != "random_forest":
                continue
            a, b = m["subgroups"]["high_wallet_novelty"], m["subgroups"]["low_wallet_novelty"]
            def auc(group):
                return f"{group['metrics']['auroc']:.3f}" if group["metrics"] is not None else "unavailable"
            lines.append(f"| {s['horizon']}s | {s['period']} | {m['scope']} | {a['n']} | {auc(a)} | {b['n']} | {auc(b)} |")
    lines += ["", "Wallet novelty means absent from labeled training prefixes. The subgroup threshold is "
              "the median validation share, fixed without test outcomes. It does not prove previously unseen "
              "operators, and subgroup outcomes may differ in prevalence or token activity.", "",
              "## What this adds, and what remains", "",
              "This supplies a reproducible, token-disjoint confirmation across three expanding calendar "
              "folds with outcome-maturity purging, seed averaging, paired uncertainty and an explicit "
              "operating-point check. It does not introduce a new learning algorithm. Calendar evaluation, "
              "calibration and coordination are already present in prior research; a distinct publication "
              "contribution remains unestablished.", ""]
    lines += [f"- {limit}" for limit in report["limits"]]
    lines += ["", "The next decision is to test a narrowly scoped intervention against stronger "
              "coordination baselines and an independent data period. Increasing model complexity without "
              "demonstrating a specific benefit would not address these limitations.", "",
              "[Protocol](SOLANA_CONFIRMATION_PROTOCOL.md) · "
              "[Detailed results](results/solana_confirmation.json) · "
              "[FPR diagnostics](results/solana_confirmation_diagnostics.json) · "
              "[Reproduction code](../research/solana/ml/robustness.py)", "",
              "Data attribution: Hu et al., [MELT](https://arxiv.org/html/2602.13480v2), "
              "[author release](https://github.com/git-disl/MELT), CC BY-NC 4.0. "
              "Results are our own experiments; published benchmarks have not been independently reproduced.", ""]
    out = ROOT / "docs/SOLANA_CONFIRMATION_RESULTS.md"
    out.write_text("\n".join(lines))
    print(out)


if __name__ == "__main__":
    main()
