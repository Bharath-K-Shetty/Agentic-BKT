"""Produce an evidence-led research decision from saved replay results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    r = json.loads((ROOT / 'docs/results/solana_delayed_replay.json').read_text())
    p = next(c for c in r['comparisons'] if c['primary'])
    def effect(metric):
        d = p[metric]
        return f"{100*d['weighted_delta']:+.2f} percentage points (95% paired day-block interval {100*d['ci95'][0]:+.2f} to {100*d['ci95'][1]:+.2f})"
    lines = ['# Delayed-outcome Solana warning experiment', '',
        f"Selected 8,000 tokens at hash ranks 28,000–35,999 before evaluation; {r['eligible']:,} have usable "
        'five-minute prefixes before migration. No overlap with earlier token cohorts. Test windows reuse the '
        'same historical calendar periods; this is not a new market period.', '',
        '**Question:** does outcome-dependent label maturity bias online warning calibration, and does '
        'a simple observation-delay correction improve the warning tradeoff?', '',
        'A fixed RF with 120 prefix features is trained on the previous cohort, with its previous '
        'validation-selected parameters and three-seed average. No model or replay setting is tuned on '
        'the new test outcomes. Labels enter the prospective replay only at migration + one hour. '
        'This is a conservative assumed operational schedule, not a verified publication timestamp. '
        'The target is released 20-minute price-collapse min_ratio < 0.3, not verified fraud.', '',
        '## Primary result', '', f"Recall change versus the identical unweighted recent pool: **{effect('recall_delta')}**.", '',
        f"False-positive-rate change: **{effect('fpr_delta')}**.", '',
        '**Prespecified success gate: ' + ('passed.** Independent confirmation and novelty review are still required.' if r['primary_success'] else
        'not passed.** The correction is not established as a useful new method. Do not rename this result as algorithmic novelty.'), '',
        'The success gate requires the recall interval above zero, no FPR increase by its interval, '
        'and observed candidate FPR at or below 5% in each period. Secondary controls are exploratory. '
        'Intervals condition on fitted models and do not account for shared wallet operators.', '',
        '## Operating results', '', '| Period | Method | Recall | FPR | Alerts | Static fallback |',
        '|---|---|---:|---:|---:|---:|']
    for s in r['results']:
        for name, m in s['methods'].items():
            d = m['diagnostics']
            fallback = d.get('fallback_count', 0) / d['decisions']
            lines.append(f"| {s['period']} (n={s['test_n']}) | {name} | {m['recall']:.2%} | {m['fpr']:.2%} | {m['alert_fraction']:.2%} | {fallback:.1%} |")
    lines += ['', 'All methods use identical model scores, so calibration does not improve their AUROC or AP. '
        'Recent and weighted pools use 48 hours of decision history; fewer than 20 available negatives '
        'trigger the static negative-tail fallback. The arrival-order control uses the last 128 revealed '
        'negatives. The buffer control uses a 48-hour cohort ending 36 hours earlier. The oracle uses '
        'past-decision labels before maturity and is **invalid for deployment**; it does not use the current '
        'token or labels from simultaneous decisions.', '',
        'The weighted correction estimates delay CDFs in three model-score bins from older validation '
        'negatives, uses smoothed inverse observation probabilities clipped at 10, and adds unit '
        'pseudo-observation mass to the upper tail. This is an experimental weighting heuristic, '
        'not a proved conformal procedure. Weighting also changes the relative pseudo-observation mass; '
        'any benefit cannot be attributed solely to correcting selection without a mass-matched control. '
        'That control was not part of this locally fixed experiment. Static negative-tail validity requires exchangeability, '
        'which calendar drift can violate. The 36-hour buffer is audited on this data, not a universal '
        'upper bound on future label delay.', '',
        '## Outcome-dependent maturity', '',
        '| Outcome | n | Median assumed delay | Available by 6h | Available by 24h | Delay >36h |',
        '|---|---:|---:|---:|---:|---:|']
    for label, d in r['delay_by_outcome'].items():
        lines.append(f"| {'Collapse' if label == '1' else 'Non-collapse'} | {d['n']} | {d['median_hours']:.2f}h | {d['available_at_6h']:.1%} | {d['available_at_24h']:.1%} | {d['exceeds_buffer']} |")
    lines += ['', 'These diagnostics include all eligible new tokens, including decisions outside the evaluated '
        'calendar test windows. They describe this selected eventual-migrant archive. Tokens that never '
        'migrate are absent, so this cannot establish all-launch deployment performance or a general '
        'delay distribution.', '', '## Relationship to prior work', '',
        '[Delayed ACI (September 2026)](https://arxiv.org/abs/2609.07251) analyzes adaptive conformal '
        'updates with fixed forecast delay and dependence. [HAPS (May 2026)](https://arxiv.org/abs/2605.06581) '
        'already uses inverse censoring weights and time-varying histories for event-time prediction. '
        '[Delayed-feedback label correction (2023)](https://arxiv.org/abs/2307.12756) already addresses '
        'delayed conversion observations. Our implementation is not an exact reproduction of these '
        'algorithms. [Causal Label Recovery in Payment Networks (May 2026)](https://arxiv.org/abs/2605.29272) '
        'also studies biased financial labels and the tradeoff between label maturity and model freshness '
        '(abstract reviewed here; theory not independently verified). Applying established weighting ideas to irregular token outcomes alone is not a '
        'novel algorithm.', '',
        'A possible empirical contribution is a reproducible evaluation of label maturity and warning '
        'tradeoffs in blockchain ML, if the effect is substantial, stable and not already reported. '
        'This experiment does not establish global novelty or publication readiness. Exact '
        'independent-period validation remains unresolved in the external-source audit.', '',
        '## Reproduce', '', '```sh',
        'OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python research/solana/ml/delayed_replay.py',
        '.venv/bin/python research/solana/ml/report_delayed_replay.py', '```', '',
        '[Fixed local protocol](../research/solana/ml/delayed_protocol.json) · '
        '[Metrics and provenance hashes](results/solana_delayed_replay.json) · '
        '[External-source audit](SOLANA_STRONG_BASELINE_RESULTS.md)', '',
        'Attribution: MELT, Hu et al., CC BY-NC 4.0. Raw data and derived per-token files remain local.', '']
    out = ROOT / 'docs/SOLANA_DELAYED_REPLAY_RESULTS.md'
    out.write_text('\n'.join(lines))
    print(out)


if __name__ == '__main__':
    main()
