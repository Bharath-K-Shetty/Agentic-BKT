"""Rebuild report tables/figures from saved experiments; does not retrain or retune."""
import json, hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score, confusion_matrix, brier_score_loss
from sklearn.metrics import precision_recall_curve
from sklearn.calibration import calibration_curve
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/latex/homie_report'; AS=OUT/'assets'; SEC=OUT/'sections'
SEC.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
colors=['#74839a','#19765b']
def read(name):return json.loads((ROOT/'docs/results'/name).read_text())
def esc(s):return str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def table(caption,headers,rows,widths=None):
 spec=widths or ('Y'*len(headers))
 return '\\begin{table}[H]\\centering\\small\\caption{'+caption+'}\n\\begin{tabularx}{\\textwidth}{'+spec+'}\\toprule\n'+' & '.join(headers)+r'\\\midrule'+'\n'+'\n'.join(' & '.join(str(v) for v in row)+r'\\' for row in rows)+'\n'+r'\bottomrule\end{tabularx}\end{table}'+'\n'
def fig(file,caption):return '\\begin{figure}[H]\\centering\\includegraphics[width=\\textwidth]{assets/'+file+'}\\caption{'+caption+'}\\end{figure}\n'
manifest={'purpose':'Regenerated reporting from existing artifacts; no refitting or threshold tuning','files':{},'checks':{}}
cohorts=['pilot','confirmation','extension','prospective','fresh']; datasets=[]; partitions=[]; skips=[]
frames={}
for c in cohorts:
 r=read(f'solana_transaction_risk_{c}.json');f=pd.read_parquet(ROOT/f'data/processed/solana_ml/transaction_features_{c}.parquet');frames[c]=f
 raw=sum(s['n'] for s in r['sources']);datasets.append([c,f'{raw:,}',f'{len(f):,}',f'{int(f.label.sum()):,}',f'{100*f.label.mean():.2f}\\%'])
 skips.append(c+': '+(str(r['skipped']) if r['skipped'] else 'none'))
 p=r['protocol'];start=lambda d:int(pd.Timestamp(d,tz='UTC').timestamp())
 train=f[f.date.eq(p['train_date']) & (f.decision_ts-f.decision_ts.min()>=21600)&(f.decision_ts+3600<start(p['validation_date']))]
 val=f[f.date.eq(p['validation_date'])&(f.decision_ts+3600<start(p['test_date']))];test=f[f.date.eq(p['test_date'])]
 for label,g in [('Train',train),('Validation',val),('Test',test)]:partitions.append([c,label,f'{len(g):,}',f'{int(g.label.sum()):,}',f'{100*g.label.mean():.2f}\\%'])
 manifest['checks'][c]={'raw':raw,'processed':len(f),'skipped':r['skipped'],'train':len(train),'validation':len(val),'test':len(test)}
text=r'''\subsection{Dataset profile and retained records}
Each row represents a recorded included transaction. The label is 1 for \texttt{Fail} and 0 for \texttt{Success}. The selected raw fields are signature, account list (public key, signer flag and writable flag), block timestamp, block slot and execution status. Signatures identify records; time and slot establish order, while current status supplies the target only.

The five processed windows contain '''+f'{sum(len(f) for f in frames.values()):,}'+r''' rows in total. These include warm-up, training, validation and test records; they are not all evaluation examples. Each date uses one selected Parquet row group. The pilot and confirmation use first-shard selection; later windows use the recorded alternate-shard selection protocols. Sampling is sparse and does not establish chain-wide representativeness.
'''
text+=table('Raw and processed records by experimental window',['Window','Raw rows','Retained rows','Failures','Failure rate'],datasets)
text+='The recorded preprocessing exclusions are: '+'15 identical duplicate transactions removed in the pilot; no recorded row exclusions in the other four windows'+'. Conflicting duplicate payloads, unknown statuses and date mismatches cause an error rather than an automatic repair.\n'
text+=r'''\subsection{Actual training, validation and test populations}
Training excludes the initial six-hour warm-up and outcomes crossing the validation boundary. Validation excludes outcomes crossing the test boundary. Test rows are retained for chronological prediction. The counts below are recomputed from the saved feature tables using these rules. Failures are included in the row totals.
'''
text+=table('Partition sizes after warm-up and boundary purging',['Window','Partition','Rows','Failures','Failure rate'],partitions)
row=frames['prospective'].iloc[0]
text+=table('One retained feature record (warm-up example, not a fitted training row)',['Field','Value'],[['Date',row.date],['Target label',int(row.label)],['Declared account entries',int(row.structure_account_count)],['Unique declared signers',int(row.structure_signer_count)],['Declared writable entries',int(row.structure_writable_count)],['Eligible non-signer writable accounts',int(row.structure_nonpayer_writable_count)],['Signer matured observations','0'],['Writable coverage',f'{row.writable_seen_fraction:.1f}'],['Signer smoothed rate',f'{row.payer_risk:.2f}']])
text+=r'''This initial example has no matured observations, so the smoothed prior is 0.5. That number is a default history statistic, not evidence that this individual transaction has a true 50\% failure probability. The full signature is retained in the feature file; this table omits the long identifier for readability.
'''
(SEC/'dataset_evidence.tex').write_text(text)
# Reproduce the existing audit's exact first-appearance mask.
firstsets={};results=[];cmrows=[];ablation=[]
figpr,axes=plt.subplots(1,2,figsize=(9,3.7))
for ax,c in zip(axes,['prospective','fresh']):
 f=frames[c];r=read(f'solana_transaction_risk_{c}.json');audit=read(f'solana_transaction_audit_{c}.json');payer={}
 for src in r['sources']:
  for batch in pq.ParquetFile(ROOT/src['path']).iter_batches(columns=['signature','accounts'],batch_size=8192):
   for v in batch.to_pylist():payer[v['signature']]=v['accounts'][0]['pubkey']
 signers=f.signature.map(payer);assert signers.notna().all()
 mask=pd.DataFrame({'signature':f.signature,'first':~signers.duplicated()})
 pred=pd.read_parquet(ROOT/f'data/processed/solana_ml/transaction_identity_predictions_{c}.parquet').merge(mask,on='signature',validate='one_to_one');pred=pred[pred['first']];firstsets[c]=pred
 assert len(pred)==audit['first_appearance_n']
 ir=read(f'solana_transaction_identity_{c}.json');thresholds={v['model']:v['threshold'] for v in ir['results']}
 for i,(name,label) in enumerate([('readonly_identity_hgb','Baseline'),('context_identity_hgb','Context')]):
  y=pred.label.to_numpy();s=pred[name].to_numpy();m=audit['first_appearance_identity_results'][name]
  assert abs(average_precision_score(y,s)-m['ap_positive'])<1e-12
  precision,recall,_=precision_recall_curve(y,s);ax.step(recall,precision,where='post',color=colors[i],label=f'{label} AP={m["ap_positive"]:.4f}')
  tn,fp,fn,tp=confusion_matrix(y,s>=thresholds[name],labels=[0,1]).ravel()
  assert abs(tp/(tp+fn)-m['recall'])<1e-12
  results.append([r['protocol']['test_date'],label,*[f'{m[k]:.4f}' for k in ['ap_positive','auroc','precision','recall','fpr','brier']]])
  cmrows.append([r['protocol']['test_date'],label,f'{thresholds[name]:.4f}',f'{tn:,}',f'{fp:,}',f'{fn:,}',f'{tp:,}'])
 ax.axhline(y.mean(),linestyle=':',color='#ae6f28',label=f'Prevalence {y.mean():.3f}');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Recall',ylabel='Precision',title=r['protocol']['test_date']);ax.legend(fontsize=8)
 a=audit['first_appearance_results'];b=audit['first_appearance_identity_results']
 ablation.extend([[r['protocol']['test_date'],'No identity',f'{a["payer_readonly_hgb"]["ap_positive"]:.4f}',f'{a["context_hgb"]["ap_positive"]:.4f}'],[r['protocol']['test_date'],'Shared identity',f'{b["readonly_identity_hgb"]["ap_positive"]:.4f}',f'{b["context_identity_hgb"]["ap_positive"]:.4f}']])
figpr.tight_layout();figpr.savefig(AS/'first_appearance_pr.pdf');plt.close(figpr)
figci,ax=plt.subplots(figsize=(7,2.7))
for i,c in enumerate(['prospective','fresh']):
 a=read(f'solana_transaction_audit_{c}.json')['first_appearance_identity_hour_bootstrap'];d=a['weighted_delta'];lo,hi=a['ci95'];ax.errorbar(d,i,xerr=[[d-lo],[hi-d]],fmt='o',capsize=5,color=colors[1])
ax.axvline(0,color='gray',linestyle='--');ax.set(yticks=[0,1],yticklabels=['2025-12-01','2025-12-05'],xlabel='AP difference: context minus baseline',ylim=(-.5,1.5));figci.tight_layout();figci.savefig(AS/'ap_gain_intervals.pdf');plt.close(figci)
t=r'''\subsection{Complete operating metrics for the primary comparison}
The following metrics refer only to first-appearance signers and the shared-identity comparison. Precision, recall and false-positive rate use each model's inherited validation threshold, not a threshold selected on these test outcomes. AP and AUROC are threshold-independent summaries. The thresholded comparison does not hold the test false-positive rate constant.
'''
t+=table('Identity-controlled first-appearance evaluation',['Date','Model','AP','AUROC','Precision','Recall','FPR','Brier'],results,'l l r r r r r r')
t+=fig('first_appearance_pr.pdf','Precision--recall curves reconstructed from the exact saved first-appearance predictions. The dotted lines show failure prevalence; curves are not inferred from AP summaries.')
t+=fig('ap_gain_intervals.pdf',r'AP gains with the saved paired-hour 95\% bootstrap intervals (500 valid draws). These intervals are conditional on the sampled periods and fitted models.')
t+=r'''\subsection{Warning errors at the recorded thresholds}
TN denotes an unflagged success, FP a flagged success, FN an unflagged failure and TP a flagged failure. Counts are computed directly from saved scores and the original validation thresholds. They are not reconstructed from rounded percentages.
'''+table('Confusion-matrix counts at inherited validation thresholds',['Date','Model','Threshold','TN','FP','FN','TP'],cmrows,'l l r r r r r')
t+=r'''The context model catches additional failures on the reserved day but also generates additional false alarms. This prevents an interpretation of the AP gain as a demonstrated reduction in failed transactions or user costs.
\subsection{Feature comparison on matched first appearances}
'''+table('Writable-history comparison with and without identity control',['Date','Control','Baseline AP','Context AP'],ablation)
t+=r'''Within each row, the classifier settings and evaluated population are matched and the added feature group is writable history. Across rows, the representation changes by adding the shared identity score. This is not a benchmark against every possible identity learner, neural network or boosting library.
'''
(SEC/'ranking_evidence.tex').write_text(t)
# Reliability: use actual saved fresh calibration artifact on its held-out cold cohort.
saved=joblib.load(ROOT/'data/processed/solana_ml/demo_models.joblib');assert saved['cohort']=='fresh'
f=frames['fresh'];f=f[f.date.eq(saved['test_date']) & f.cold_payer]
calreport=read('solana_transaction_calibration_followup_fresh.json');figcal,axes=plt.subplots(1,2,figsize=(9,3.7));calrows=[]
for i,(name,a) in enumerate(saved['models'].items()):
 raw=a['model'].predict_proba(f[a['inputs']])[:,1];cal=a['calibrator'].predict(raw);y=f.label.to_numpy()
 expected=next(v for v in calreport['cohorts'][0]['results'] if v['model']==name)
 assert abs(brier_score_loss(y,cal)-expected['followup_cold']['brier'])<1e-12
 for scores,label,color in [(raw,'Raw',colors[0]),(cal,'Calibrated',colors[1])]:
  observed,mean=calibration_curve(y,scores,n_bins=10,strategy='quantile');axes[i].plot(mean,observed,'o-',label=label,color=color)
 axes[i].plot([0,1],[0,1],'--',color='gray',label='Ideal');axes[i].set(xlim=(0,1),ylim=(0,1),xlabel='Mean model score',ylabel='Observed failure fraction',title='Baseline' if name.startswith('payer') else 'Writable context');axes[i].legend(fontsize=8)
 for label,k in [('Raw','original_cold'),('Calibrated','followup_cold')]:
  m=expected[k];calrows.append(['Baseline' if name.startswith('payer') else 'Context',label,f'{m["ap_positive"]:.4f}',f'{m["brier"]:.4f}',f'{100*m["fpr"]:.2f}\\%',f'{100*m["recall"]:.2f}\\%'])
figcal.tight_layout();figcal.savefig(AS/'calibration_reliability.pdf');plt.close(figcal)
t=r'''\subsection{Calibration follow-up on the additional December test}
This analysis uses the exported 27-input baseline and 34-input context models on cold-history transactions from December 5. It excludes the learned identity score and is separate from the primary first-appearance experiment. Isotonic mappings were fitted on the earlier half of cold validation observations; warning thresholds were chosen on the later purged half. No calibration fit uses these test labels.
'''+table('Fresh cold-history calibration evaluation',['Model','Scores','AP','Brier','FPR','Recall'],calrows)
t+=fig('calibration_reliability.pdf','Reliability diagrams on the December 5 cold-history test set. Up to ten quantile bins are used; tied scores may merge bins. Points compare mean scores with observed failure frequencies. Sparse or merged bins are descriptive, not a live calibration guarantee.')
t+=r'''Calibration can reduce squared error without improving every ranking or operating metric. Isotonic mappings can create tied scores, so AP can change. Reliability on one later sampled day does not establish reliability under live RPC sampling or future network conditions.
'''
(SEC/'calibration_evidence.tex').write_text(t)
# Deliberately selected replay cases, not the primary endpoint.
bundle=json.loads((ROOT/'data/processed/solana_ml/replay_demo.json').read_text());rows=[];caseinfo=[]
for c in bundle['cases']:
 if c['illustration']=='Chronological sample':continue
 a=c['scores']['payer_readonly_hgb'];b=c['scores']['context_hgb'];rows.append([esc(c['illustration']),f'{100*c["history"]["writable_seen_fraction"]:.1f}\\%',f'{100*a["calibrated"]:.1f}\\%',f'{100*b["calibrated"]:.1f}\\%','Yes' if a['alert'] else 'No','Yes' if b['alert'] else 'No',c['outcome']]);caseinfo.append(c)
t=r'''\subsection{Recorded examples and error analysis}
The following December 1 replay examples were deliberately selected after evaluation to illustrate successful warnings and mistakes. They are not a random performance sample. Scores come from the separate calibration follow-up without identity control. ``Flag'' means the score crosses that model's validation-selected threshold.
'''+table('Selected replay cases: both predictions and the observed outcome',['Case','Seen','Base','Context','B flag','C flag','Outcome'],rows,'p{22mm} r r r c c l')
for i,c in enumerate(caseinfo,1):
 a=c['scores']['payer_readonly_hgb'];b=c['scores']['context_hgb'];failed=c['outcome']=='Failed'
 verdict=lambda s:('caught the failure' if s['alert'] else 'missed the failure') if failed else ('raised a false alarm' if s['alert'] else 'correctly left the successful transaction unflagged')
 t+='\\textbf{Case '+str(i)+': '+esc(c['illustration'])+'}. At '+esc(c['checkpoint'])+', the baseline '+verdict(a)+' and the context model '+verdict(b)+'. '
 t+='The coverage statistic describes earlier account participation; it does not prove a causal explanation for this outcome. Replay case ID: \\texttt{'+c['id']+'}.\\par\n'
t+=r'''The cases demonstrate why a higher or lower individual score cannot establish model superiority. Warning errors and aggregate ranking are evaluated separately; no unobserved fee saving is assigned to an unflagged or stopped candidate.
'''
(SEC/'case_evidence.tex').write_text(t)
for path in [*SEC.glob('*evidence.tex'),*AS.glob('*.pdf')]:manifest['files'][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT/'docs/results/solana_report_evidence_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Generated dataset, PR/CI, exact confusion counts, reliability and recorded cases. All AP/recall/Brier cross-checks passed.')
