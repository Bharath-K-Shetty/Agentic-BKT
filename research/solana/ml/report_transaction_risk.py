"""Build the evidence report from saved experiments, retaining failed controls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    rows, identity_rows, audit_rows, counts, refined_rows = [], [], [], [], []
    refined_verdict = 'The refined reserved comparison has not completed.'
    for cohort in ['pilot', 'confirmation', 'extension', 'prospective']:
        path = ROOT / f'docs/results/solana_transaction_risk_{cohort}.json'
        if not path.exists():
            continue
        report = json.loads(path.read_text())
        models = {r['model']: r for r in report['results']}
        payer = models['payer_history']
        base = models['payer_readonly_hgb']['subgroups']['cold_payer']
        candidate = models['context_hgb']['subgroups']['cold_payer']
        comparison = next(r for r in report['comparisons'] if r['primary'])['ap']
        lo, hi = comparison['ci95']
        date = report['protocol']['test_date']
        rows.append(f"| {date} ({cohort}) | {base['n']:,} | {payer['test']['ap_positive']:.3f} / {payer['subgroups']['cold_payer']['ap_positive']:.3f} | {base['ap_positive']:.3f} | {candidate['ap_positive']:.3f} | {comparison['weighted_delta']:+.3f} [{lo:+.3f}, {hi:+.3f}] |")
        counts.append(f"- {cohort}: train {report['partition_counts']['train']['n']:,}, validation {report['partition_counts']['validation']['n']:,}, test {report['partition_counts']['test']['n']:,}; test cold prevalence {candidate['prevalence']:.2%}; candidate global test FPR {models['context_hgb']['test']['fpr']:.2%}.")
        identity_path = ROOT / f'docs/results/solana_transaction_identity_{cohort}.json'
        if identity_path.exists():
            diagnostic = json.loads(identity_path.read_text())
            by_name = {r['model']: r for r in diagnostic['results']}
            delta = diagnostic['cold_ap_comparison']
            lo, hi = delta['ci95']
            identity_rows.append(f"| {cohort} | {by_name['identity_logistic']['cold_payer']['ap_positive']:.3f} | {by_name['readonly_identity_hgb']['cold_payer']['ap_positive']:.3f} | {by_name['context_identity_hgb']['cold_payer']['ap_positive']:.3f} | {delta['weighted_delta']:+.3f} [{lo:+.3f}, {hi:+.3f}] |")
        audit_path = ROOT / f'docs/results/solana_transaction_audit_{cohort}.json'
        if audit_path.exists():
            audit = json.loads(audit_path.read_text())
            delta = audit['cold_signer_bootstrap']
            fdelta = audit['first_appearance_hour_bootstrap']
            audit_rows.append(f"| {cohort} | {audit['cold_unique_signers']:,} | {audit['cold_max_rows_one_signer']:,} | [{delta['ci95'][0]:+.3f}, {delta['ci95'][1]:+.3f}] | {audit['first_appearance_n']:,} | {fdelta['weighted_delta']:+.3f} [{fdelta['ci95'][0]:+.3f}, {fdelta['ci95'][1]:+.3f}] |")
            if 'first_appearance_identity_hour_bootstrap' in audit:
                refined = audit['first_appearance_identity_hour_bootstrap']
                status = ('PASS' if audit['refined_success'] else 'FAIL') if 'refined_success' in audit else 'Exploratory'
                refined_rows.append(f"| {cohort} | {refined['weighted_delta']:+.3f} [{refined['ci95'][0]:+.3f}, {refined['ci95'][1]:+.3f}] | {status} |")
                if 'refined_success' in audit:
                    outcome = 'passed' if audit['refined_success'] else 'failed'
                    refined_verdict = (f"The reserved refined comparison **{outcome}** on {audit['first_appearance_n']:,} first appearances: "
                        f"AP gain {refined['weighted_delta']:+.4f}, 95% hour-bootstrap interval "
                        f"[{refined['ci95'][0]:+.4f}, {refined['ci95'][1]:+.4f}]. This evaluates ranking, not deployment calibration.")
                    if 'first_appearance_identity_results' in audit:
                        scores = audit['first_appearance_identity_results']
                        base_score, candidate_score = scores['readonly_identity_hgb'], scores['context_identity_hgb']
                        refined_verdict += (f"\n\nFirst-appearance AP is {base_score['ap_positive']:.4f} versus {candidate_score['ap_positive']:.4f}. "
                            f"At the inherited global-validation thresholds, subgroup FPR is {base_score['fpr']:.2%} versus "
                            f"{candidate_score['fpr']:.2%}, and Brier loss is {base_score['brier']:.4f} versus "
                            f"{candidate_score['brier']:.4f}. These poor calibration/operating results prevent describing "
                            f"the candidate as an overall better or deployment-ready risk model.")
    document = '''# Beyond the wallet: cold-signer execution-risk screening on Solana

## Research claim and status

**Candidate empirical contribution:** a declared-account, delayed-feedback ML
benchmark that separates transactions with available signer history from those
without it, and tests how much non-signer account context recovers the missing
signal. We have executed this question on real public blockchain records. This
is a specific, evidence-backed research direction; global originality and paper
acceptance are not established. Ordinary aggregation and boosting are not a new
algorithm.

**Pitch:** We study how ML can assess Solana transaction failure risk when the
signer's history is unavailable, using the accounts the transaction touches and
testing whether strong aggregate accuracy hides a cold-signer blind spot.

The narrower practical use is reliability screening for wallets, dApps and
transaction infrastructure. We have not demonstrated safer trades, prevented
failures, fee savings, or improvement over live transaction simulation. A failure
can be an intentional protective rejection, not a bug or an attack.

## Primary results

Average precision (AP) measures failure ranking across thresholds; it is not
accuracy. The cold subgroup has approximately 6–7% failures in the first two
test periods. Compare models on the same subgroup, not cold AP against aggregate
AP as if prevalence were identical.

| Test date | Cold transactions | Signer history AP: all / cold | Strong read-only baseline AP | Writable-context AP | Paired cold AP gain, 95% hour interval |
|---|---:|---:|---:|---:|---|
''' + '\n'.join(rows) + '''

The baseline includes structure, signer history, read-only participation and
exact read-only-template history. The candidate adds non-signer writable-account
participation. Both receive the same available past outcomes. Pilot parameters
were specified before model results; the November 8–10 confirmation retained
them. The November 22–24 extension was specified after those results and uses
different source shards selected by a fixed date/seed hash, without outcomes.
It is additional evidence, not retrospective preregistration.

''' + '\n'.join(counts) + '''

## Stronger account-identity diagnostic

A hashed logistic learner receives role-tagged account identities and read-only
templates. It updates chronologically using outcomes at least one hour old,
in ten-minute batches. Its prequential score is added to both nonlinear models.
The comparison then tests writable history after both models also receive that
identity score. Fixed diagnostic settings were specified after the first two
primary results; these are post-result diagnostics, not untouched confirmations.

| Cohort | Identity-only AP | Read-only history + identity AP | Writable context + identity AP | Additional writable gain, 95% hour interval |
|---|---:|---:|---:|---|
''' + '\n'.join(identity_rows) + '''

An interval crossing zero means the gain is not established in that period.
The uncertain second-period identity-control result prevents claiming that
writable history universally adds value beyond account memorization. The linear
identity baseline is not an exhaustive search over identity architectures.
Its batching introduces up to ten minutes extra feedback delay; this mismatch
must accompany any comparison. The primary ranking result remains separate.

## Dependence and strict first-appearance checks

Primary cold means no *matured outcome* for the first signer in sampled history.
It can include repeated transactions during the first hour. The diagnostic below
also restricts to the signer's first appearance in the sample and bootstraps the
primary cold comparison by declared signer address. Addresses are not independent
operators; neither check establishes operator independence.

| Cohort | Cold signer addresses | Largest cold signer count | Cold gain signer-bootstrap interval | First appearances | First-appearance AP gain, hour interval |
|---|---:|---:|---|---:|---|
''' + '\n'.join(audit_rows) + '''

## Reserved confirmation of the refined first-appearance question

After the first three periods, the November 29–December 1 dates and alternate
shards were reserved before inspecting their transaction outcomes. The refined
primary comparison is writable history versus read-only history **with the same
delayed account-identity score supplied to both**, restricted to first signer
appearances in the sampled replay. Its locally fixed success condition requires
a positive AP gain and a paired-hour interval entirely above zero. Model and
history parameters are unchanged. It is a reserved historical evaluation, not
a live prospective trial or public preregistration.

| Cohort | First-appearance gain after identity control, 95% hour interval | Refined gate |
|---|---|---|
''' + '\n'.join(refined_rows) + '\n\n' + refined_verdict + '''

Earlier first-appearance comparisons remain exploratory. A failed refined gate
must remain visible; it cannot be replaced with a favorable secondary result.

## Difference from reviewed prior work

| Reviewed primary source | Existing contribution | Our narrower question |
|---|---|---|
| [Zheng et al., ISSTA 2025](https://zhiyuan-wan.github.io/assets/publications/zheng_issta_25_solana.pdf) | Large-scale descriptive study of Solana failure initiators, programs, errors and temporal patterns | Cold-signer execution-outcome ranking from declared account roles and delayed historical outcomes |
| [Oliveira et al., 2021](https://www.researchgate.net/publication/351723407_Analyzing_Transaction_Confirmation_in_Ethereum_Using_Machine_Learning_Techniques) | Ethereum execution-outcome classification with gas and inclusion-related attributes | Exclude current execution receipts and explicitly evaluate missing signer-history transfer |
| [Solana's transaction network, EPJ Data Science 2025](https://link.springer.com/article/10.1140/epjds/s13688-025-00561-x) | Transfer-graph structure and descriptive failed-transfer analysis | Chronological predictive benchmark with matched structure/read-only controls |
| [Chaudhary et al., CMC 2026](https://www.techscience.com/cmc/v89n2/68773/html) | Temporally evaluated Ethereum multisig anomaly triage after execution | Observed Solana success/failure labels, exclude current logs/compute use, cold-signer breakdown |
| [Blockchain platforms and computational evaluation, AIA](https://ojs.bonviewpress.com/index.php/AIA/article/view/6923) | Platform review and TRON transaction success/failure simulation | Public Solana records, available-label replay and account-role ablation |
| [BRIGHT, 2022](https://arxiv.org/abs/2205.13084) | Real-time fraud learning using graph entity context | Execution reliability rather than fraud; relational transfer itself is established |

The literature search did not locate this exact benchmark question in the
reviewed sources. Absence from a search is not proof of worldwide novelty.
We cannot claim the first blockchain failure classifier, the first contextual
risk learner, or a new temporal-validation technique. Commercial reliability
tools, including [Belay](https://devpost.com/software/belay-1i4kjo), also advertise
failure prediction; their existence rules out a broad first-product claim.
The detailed search and rejected directions are retained in
[the search log](SOLANA_NOVELTY_SEARCH_LOG.md).

## Data and information boundary

Data from [SolArchive.org](https://huggingface.co/datasets/solarchive/solarchive),
CC BY 4.0, pinned HF revision
`6588cad2832e62be03972ac80d69c6af11d631c8`. One Parquet row group per date is
sampled, not the entire chain. Byte ranges and derived files have recorded hashes;
the original full-file SHA256 has not been independently verified. The archived
inventory is discontinuous, so continuous-history coverage is not assumed.

Inputs are declared account roles/counts and history of outcomes at least one
hour earlier. Current status, logs, errors, consumed compute, balances, paid fees,
block position and inclusion timestamp are excluded from model inputs. Actual
submission times are absent. Block time supplies the retrospective checkpoint,
so this is **conditional on eventual block inclusion**, not validated live
pre-submission prediction. Unlanded transactions are absent. Account resolution
is assumed possible before execution; actual runtime availability is not tested.

All seven primary models use identical date partitions. Initial six hours build
history; fitting and threshold calibration purge labels unavailable before the
next split. Test-time histories update from earlier matured test outcomes. No
current or pending labels update features. Identical selected-payload duplicate
signatures count once; conflicting duplicates and partition mismatches abort.
Three HGB seeds are averaged, but deterministic fitting does not make them three
independent empirical replications. The independent time windows matter more.

Alert thresholds use a global validation FPR budget of 5%. Test FPR drifts, and
the same threshold may be unsuitable for cold signers. A positive AP gain does
not prove better recall at a common test false-positive rate or a guaranteed
budget. The hour bootstrap uses fixed predictions within one test day per
cohort, excluding retraining and longer-regime uncertainty.

## Publication assessment and next evidence

This is an implemented blockchain ML research candidate with a narrower gap
and measured results, rather than a novelty promise. A paper should center its
benchmark and cold-history evaluation, retain the identity-control uncertainty,
and avoid selling an invented algorithm. Submission readiness still requires
broader periods/source samples, a tuned but independently tested identity
baseline, feedback-delay sensitivity and an independent data collection or
live-arrival validation. Comparisons with simulation require collecting actual
submission and simulation results; this archive cannot supply that evidence.

All numeric tables come from saved JSON reports. Run
`research/solana/ml/report_transaction_risk.py` to regenerate this document.
Reproduction commands and source-download details are in
[the ML workspace README](../research/solana/ml/README.md).
'''
    (ROOT / 'docs/SOLANA_TRANSACTION_RISK_RESULTS.md').write_text(document)


if __name__ == '__main__':
    main()
