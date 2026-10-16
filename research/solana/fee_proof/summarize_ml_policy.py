"""Retain every inspected period; never promote a favourable date to proof."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    periods = []
    sources = []
    for cohort in ['pilot', 'confirmation', 'extension', 'prospective', 'fresh']:
        path = ROOT/('docs/results/solana_ml_fee_policy.json' if cohort == 'fresh'
                     else f'docs/results/solana_ml_fee_policy_{cohort}.json')
        r = json.loads(path.read_text())
        sources.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        periods.append({'cohort': cohort, 'test_date': r['test_date'], 'rows': r['rows'], 'failures': r['failures'],
                        'deployed_policy': r['models'],
                        'cost_based_policies': r['exploratory_cost_based_thresholds']})
    assert len({p['test_date'] for p in periods}) == len(periods)
    rows = sum(p['rows'] for p in periods)
    failures = sum(p['failures'] for p in periods)
    pooled = {}
    for name in ['payer_readonly_hgb', 'context_hgb']:
        pooled[name] = {}
        for ratio in ['1','5','10']:
            counts = [p['cost_based_policies'][name][ratio] for p in periods]
            tp = sum(c['flagged_failures'] for c in counts)
            fp = sum(c['flagged_successes'] for c in counts)
            pooled[name][ratio] = {'flagged_failures': tp, 'flagged_successes': fp,
                'missed_failures': failures-tp, 'precision': tp/(tp+fp) if tp+fp else None,
                'failure_recall': tp/failures,
                'hypothetical_net_units_at_matching_cost_ratio': tp-int(ratio)*fp,
                'positive_net_periods': sum(c['hypothetical_net_units'][ratio] > 0 for c in counts),
                'negative_net_periods': sum(c['hypothetical_net_units'][ratio] < 0 for c in counts)}
    result = {'status': 'Additional retrospective diagnostic; not independent prospective evidence',
              'sources': sources, 'rows': rows, 'failures': failures, 'periods': periods,
              'pooled_cost_scenarios': pooled,
              'verdict': 'Current evidence does not establish ML-driven fee savings. Do not use these models to automatically block transfers.',
              'proof_status': {'failed_execution_can_charge_fee': 'Proven on isolated local validator',
                               'check_and_stop_avoids_that_local_paid_attempt': 'Proven in matched local comparison',
                               'ML_improves_failure_ranking': 'Supported by existing held-out AP comparisons, with stated sampling limits',
                               'ML_saves_fees_beyond_normal_preflight': 'Not proven: preflight and paid fees absent from historical evaluation',
                               'ML_policy_reliably_improves_economic_utility': 'Not established: false alarms and period instability'},
              'next_required_experiment': {
                  'design': 'Shadow-mode prospective study on authorised transaction candidates; no ML-triggered automatic blocking',
                  'record_before_outcome': ['Candidate signed-message hash', 'Model and history snapshot hashes',
                       'Available-history timestamp', 'ML probability and fixed threshold',
                       'Standard preflight result, slot and timestamp'],
                  'record_after_outcome': ['Submitted signature if any', 'Confirmed receipt error and fee',
                       'Pre/post balances', 'Actual submission/confirmation times',
                       'Reason a candidate was not submitted; never label it successful or failed without observation'],
                  'primary_population': 'Candidates that pass standard preflight; assess whether ML predicts subsequent paid failures',
                  'comparison': 'Fixed preflight-only policy versus fixed preflight-plus-ML policy, with false-warning costs reported',
                  'limits': 'Shadow-mode predictions alone cannot establish causal savings. A subsequent authorised policy comparison is required.'}}
    output = ROOT/'docs/results/solana_ml_fee_policy_summary.json'
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'rows': rows, 'failures': failures, 'pooled_cost_scenarios': pooled,
                      'verdict': result['verdict']}, indent=2))


if __name__ == '__main__':
    main()
