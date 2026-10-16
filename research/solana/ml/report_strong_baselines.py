"""Summarize the stronger baseline experiment and external compatibility audit."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    r = json.loads((ROOT / 'docs/results/solana_strong_baselines.json').read_text())
    audit = json.loads((ROOT / 'docs/results/solana_external_period_audit.json').read_text())
    primary = next(c for c in r['comparisons'] if c['primary'])
    delta, (lo, hi) = primary['ap']['weighted_delta'], primary['ap']['ci95']
    lines = ['# Stronger Solana baselines and independent-period audit', '',
             f"Selected {r['sampled']:,} additional tokens, excluding all 18,000 earlier sample ranks. "
             f"{r['eligible']:,} have usable 300-second prefixes and have not migrated by the decision. "
             f"Observed overlap with earlier cohorts: **{r['prior_token_overlap']}**.", '',
             f"Compare **{r['feature_count']['pilot_27']} versus {r['feature_count']['enriched']} features**, "
             'with the same model-family tuning budget, validation-only configuration selection and three-seed '
             'ensembles. Richer features are ordinary summaries of early buyers, holdings, observed co-participation, '
             'trade sizes, fees, price changes and six fixed activity bins. They do not introduce a new algorithm.', '',
             f"Primary RF comparison: period-weighted AP change **{delta:+.4f}**, paired day-block 95% interval "
             f"**[{lo:+.4f}, {hi:+.4f}]**.", '',
             ('The richer RF features improve the primary comparison within this historical cohort.' if lo > 0 else
              'The richer features do not establish a consistent RF improvement in the primary comparison.' if hi >= 0 else
              'The richer RF features reduce performance in the primary comparison.'), '',
             'This is evidence about a stronger baseline, not a novelty or publication-readiness result. '
             'The model and feature definitions were specified after earlier exploration, before this run. '
             'No public preregistration or independent market-cycle validation is claimed.', '',
             '## Results', '',
             '| Test period | Model | Inputs | Test n | Prevalence | AP | AUROC | Recall | FPR |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for s in r['results']:
        for m in s['models']:
            t = m['test']; c = s['counts']['test']
            lines.append(f"| {s['period']} | {m['model']} | {m['scope']} | {c['n']} | {c['prevalence']:.1%} | "
                         f"{t['ap_positive']:.3f} | {t['auroc']:.3f} | {t['recall']:.1%} | {t['fpr']:.1%} |")
    lines += ['', 'The threshold is selected on validation at an empirical 5% FPR budget. '
              'Test FPR is reported without adjustment. AUROC chance level is 0.5; constant-score AP equals '
              'test prevalence. Outcomes must mature before the next training/validation boundary.', '',
              'Exclusions from the selected tokens:', '']
    lines += [f'- {reason}: {count:,}.' for reason, count in r['skipped'].items()]
    lines += ['', '## Separate period: what was actually checked', '',
              '[PumpFun Launch-to-Graduation Corpus](https://huggingface.co/datasets/Slinky21/Pumpfun_Memecoin_Corpus), '
              f"revision `{audit['revision']}`. Downloaded and inspected three linked Parquet tables plus one "
              'trade shard. Data remains local and is not redistributed.', '',
              '| Check | Observed |', '|---|---:|']
    o = audit['observations']; t = audit['single_trade_shard_probe']
    for name, value in [('Migration records', o['migrations']), ('Post-migration snapshot rows', o['snapshot_rows']),
                        ('First post-migration native-price median delay (seconds)', round(o['first_price_seconds_quantiles']['0.5'],2)),
                        ('Tokens with first native-price snapshot within 5 seconds', o['first_price_at_or_before_5s']),
                        ('Tokens with observed early start and late end in 20-minute window', o['early_start_and_late_end_observed']),
                        ('Synthetic/backfilled pool records', o['synthetic_or_backfilled_pool_records']),
                        ('Inspected trade-shard rows', t['rows']), ('Missing prices in inspected shard', t['missing_price_rows']),
                        ('Shard mints joining migration records', t['mints_matching_migration_table']),
                        ('Post-migration first-20-minute trades in inspected shard', t['post_migration_first_20minute_rows'])]:
        lines.append(f'| {name} | {value:,} |')
    lines += ['', '**Exact external validation remains incomplete.** The current label is a minimum over '
              'transaction prices, while these post-migration tables provide periodic prices. A short collapse '
              'can happen between observations. The outcome table supplies a USD migration-price anchor, '
              'not the native-unit anchor needed to match our existing price ratio. Missing or incomplete '
              'follow-up is not evidence of a safe token.', '',
              'The inspected trade shard covers an early collection interval and has no usable post-migration '
              '20-minute trades in the three mints that join the migration table. That does not establish '
              'absence across the 17 uninspected shards. It also does not resolve the documented missing-price '
              'and unit-consistency issues. No external model accuracy has been measured.', '',
              'Using a snapshot endpoint would require an explicit new target and reconstructing that same '
              'target in both sources. That is a separate study, not silent validation of this endpoint.', '',
              '## Research decision', '',
              'A more complex graph or uncertainty method must now be compared against the stronger baseline. '
              'The richer-feature result cannot itself be presented as an invented method: early features '
              'and coordination already overlap [MELT](https://arxiv.org/html/2602.13480v2) and '
              '[the closest public comparison](https://github.com/Gauravpoudel7/AI_RugPull_Prediction). '
              'No global novelty or publication acceptance is established.', '']
    lines += [f'- {limit}' for limit in r['limits']]
    lines += ['', '[Exact baseline settings](../research/solana/ml/strong_baseline_protocol.json) · '
              '[Baseline metrics and hashes](results/solana_strong_baselines.json) · '
              '[External audit](results/solana_external_period_audit.json)', '',
              'Attribution: MELT, Hu et al., CC BY-NC 4.0. The external corpus card names Slink Dev and '
              'has conflicting MIT metadata / CC BY 4.0 prose; no redistribution is performed.', '']
    out = ROOT / 'docs/SOLANA_STRONG_BASELINE_RESULTS.md'
    out.write_text('\n'.join(lines)); print(out)


if __name__ == '__main__':
    main()
