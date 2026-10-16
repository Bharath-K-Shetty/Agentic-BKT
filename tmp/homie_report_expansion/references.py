from pathlib import Path
import re
p=Path('output/latex/homie_report/main.tex');s=p.read_text()
s=s.replace('The interface presents a short finding with inspectable evidence. Separate modules handle collection, features, inference, transfer checks and receipt storage, allowing each to be maintained independently.','The interface provides concise findings with inspectable evidence. Separate modules support collection, inference, transfer checks and receipt storage.')
s=s.replace('Invalid input is rejected before network calls. RPC unavailability yields an incomplete check rather than a successful result. A missing history snapshot can prevent ML scoring while leaving the nature of the network check explicit. A different transaction message, even from the same sender, is insufficient to attach a receipt. Changing the blockhash changes the message and requires a fresh observation.','Invalid inputs are rejected before RPC calls. Unavailable RPC or history data produces an explicit incomplete result. Receipts must match the checked message; a changed blockhash requires a new observation.')
s=s.replace('The presentation connects user input, network findings, model output and the stored decision. Historical results and local receipts provide supporting evidence. Live findings are displayed as returned.','The presentation connects inputs, findings and the stored decision, supported by historical results and local receipts.')
# Precise citations for methods and implementation, rather than uncited bibliography padding.
repls={
'These referenced accounts are not necessarily people or wallets.':r'These referenced accounts are not necessarily people or wallets~\cite{accounts,transactions}.',
'Histogram gradient boosting combines successive decision trees to reduce classification loss.':r'Histogram gradient boosting combines successive decision trees to reduce classification loss, following the gradient boosting framework~\cite{friedman}.',
'A stronger comparison uses an SGD logistic learner with role-tagged identities and read-only templates hashed into $2^{20}$ dimensions.':r'A stronger comparison uses an SGD logistic learner~\cite{sgd} with role-tagged identities and read-only templates hashed into $2^{20}$ dimensions. Feature hashing provides a fixed-dimensional representation of large categorical spaces~\cite{hashing}.',
'A separate operational follow-up fits isotonic calibration on early cold-history validation data and chooses thresholds on later validation data.':r'A separate operational follow-up fits isotonic calibration~\cite{isotonic,niculescu} on early cold-history validation data and chooses thresholds on later validation data.',
'This is why accuracy alone is unsuitable for judging the research question.':r'This is why accuracy alone is unsuitable for judging the research question. Precision--recall analysis is particularly informative for imbalanced binary tasks~\cite{saito}.',
'where $P_k$ and $R_k$ are precision and recall as the score threshold changes.':r'where $P_k$ and $R_k$ are precision and recall as the score threshold changes~\cite{ap}.',
'assesses the numerical predictions against binary outcomes; lower values are better.':r'assesses the numerical predictions against binary outcomes; lower values are better~\cite{brier}.',
'Using the current transaction\'s error message would make failure prediction trivial after execution.':r"Using the current transaction's error message would make failure prediction trivial after execution. Leakage of unavailable information can invalidate an ML evaluation~\cite{leakage}.",
'The implemented SQLite store uses a decision table, a receipt table and an abstention table.':r'The implemented SQLite store uses a decision table, a receipt table and an abstention table. SQLite triggers support rejecting updates and deletions of protected records~\cite{sqlite}.',
'The FastAPI application provides historical replay':r'The FastAPI application~\cite{fastapi} provides historical replay',
'The backend reconstructs plain SOL transfer messages, handles exact lamport amounts and queries Solana RPC.':r'The backend reconstructs plain SOL transfer messages, handles exact lamport amounts and queries Solana RPC. It obtains a recent blockhash~\cite{blockhash}, requests a fee quote for the constructed message~\cite{feequote} and reads the sender balance~\cite{balance}.',
'Only outcomes aged at least one hour enter history.':r'Public blocks are retrieved using the documented block RPC~\cite{getblock}. Only outcomes aged at least one hour enter history.',
'An unrelated receipt cannot be used as evidence for a decision.':r'The receipt is retrieved through the transaction RPC~\cite{gettransaction}. An unrelated receipt cannot be used as evidence for a decision.',
'Data processing&Python, pandas, NumPy and PyArrow for archive extraction and features':r'Data processing&Python, pandas~\cite{pandas}, NumPy~\cite{numpy} and PyArrow for archive extraction and features',
'Machine learning&scikit-learn histogram gradient boosting;':r'Machine learning&scikit-learn~\cite{sklearn} histogram gradient boosting;'
}
for a,b in repls.items():
 assert a in s,a
 s=s.replace(a,b)
extra=r'''
\section{Boosting, calibration and evaluation literature}
Friedman formulates gradient boosting as stage-wise function approximation~\cite{friedman}. This provides the methodological foundation for building a predictor through successive corrections. HOMIE uses an existing histogram boosting implementation, so the algorithm is credited as established prior work rather than presented as the project's invention.

XGBoost by Chen and Guestrin describes a scalable tree-boosting system~\cite{xgboost}. LightGBM by Ke et al. develops efficient gradient boosted decision-tree training~\cite{lightgbm}. These are relevant alternatives in the tree-ensemble literature. The current study uses scikit-learn's histogram classifier; XGBoost and LightGBM results are not claimed as implemented comparisons. Their inclusion identifies the wider algorithm family and potential future benchmark alternatives.

Niculescu-Mizil and Caruana examine predicted probabilities and calibration across supervised learners~\cite{niculescu}. Their distinction between a discriminative score and a reliable probability motivates reporting calibration alongside ranking. HOMIE's isotonic follow-up is evaluated on chronological validation data and does not erase the need to inspect performance on later dates.

Saito and Rehmsmeier discuss precision--recall plots for imbalanced binary classification~\cite{saito}. The relevance is direct: failures form a minority of the reserved first-appearance group, and an always-success classifier would have high accuracy while missing every failure. Reporting AP, recall and false positives makes this trade-off visible.

Kapoor and Narayanan discuss leakage and reproducibility problems in ML-based science~\cite{leakage}. In HOMIE, chronology, delayed labels and exclusion of current execution outputs are safeguards against this class of error. These safeguards define what information the model can use; they do not replace external validation.

\begin{table}[htbp]\centering\caption{Methodological literature and its use in the project}
\small\begin{tabularx}{\textwidth}{p{30mm}YY}\toprule Work&Relevant concept&Use in HOMIE\\\midrule
Friedman~\cite{friedman}&Gradient boosting&Foundation of the fitted classifier\\
Chen and Guestrin~\cite{xgboost}; Ke et al.~\cite{lightgbm}&Efficient tree ensembles&Related methods, not claimed experiments\\
Weinberger et al.~\cite{hashing}&Feature hashing&Fixed-dimensional identity representation\\
Niculescu-Mizil and Caruana~\cite{niculescu}&Probability calibration&Separating ranking from numerical reliability\\
Saito and Rehmsmeier~\cite{saito}&Imbalanced evaluation&Precision--recall interpretation\\
Kapoor and Narayanan~\cite{leakage}&Leakage and reproducibility&Information-availability safeguards\\\bottomrule\end{tabularx}\end{table}
'''
s=s.replace(r'\chapter{SYSTEM REQUIREMENTS}',extra+'\n'+r'\chapter{SYSTEM REQUIREMENTS}')
refs=[
('friedman',r"""J. H. Friedman, ``Greedy function approximation: A gradient boosting machine,'' \emph{The Annals of Statistics}, vol. 29, no. 5, pp. 1189--1232, 2001. \url{https://doi.org/10.1214/aos/1013203451}."""),
('xgboost',r"""T. Chen and C. Guestrin, ``XGBoost: A Scalable Tree Boosting System,'' 2016. \url{https://arxiv.org/abs/1603.02754}."""),
('lightgbm',r"""G. Ke et al., ``LightGBM: A Highly Efficient Gradient Boosting Decision Tree,'' \emph{Advances in Neural Information Processing Systems}, vol. 30, 2017. \url{https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html}."""),
('hashing',r"""K. Weinberger, A. Dasgupta, J. Attenberg, J. Langford and A. Smola, ``Feature Hashing for Large Scale Multitask Learning,'' 2009. \url{https://arxiv.org/abs/0902.2206}."""),
('niculescu',r"""A. Niculescu-Mizil and R. Caruana, ``Predicting Good Probabilities With Supervised Learning,'' in \emph{Proceedings of ICML}, 2005. \url{https://doi.org/10.1145/1102351.1102430}."""),
('saito',r"""T. Saito and M. Rehmsmeier, ``The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets,'' \emph{PLOS ONE}, vol. 10, no. 3, e0118432, 2015. \url{https://doi.org/10.1371/journal.pone.0118432}."""),
('leakage',r"""S. Kapoor and A. Narayanan, ``Leakage and the Reproducibility Crisis in ML-based Science,'' arXiv:2207.07048, 2022. \url{https://arxiv.org/abs/2207.07048}."""),
('sklearn',r"""F. Pedregosa et al., ``Scikit-learn: Machine Learning in Python,'' \emph{Journal of Machine Learning Research}, vol. 12, pp. 2825--2830, 2011. \url{https://jmlr.org/papers/v12/pedregosa11a.html}."""),
('numpy',r"""C. R. Harris et al., ``Array programming with NumPy,'' \emph{Nature}, vol. 585, pp. 357--362, 2020. \url{https://doi.org/10.1038/s41586-020-2649-2}."""),
('pandas',r"""W. McKinney, ``Data Structures for Statistical Computing in Python,'' in \emph{Proceedings of the 9th Python in Science Conference}, pp. 56--61, 2010. \url{https://doi.org/10.25080/Majora-92bf1922-00a}.""")]
for key,title,path in [('accounts','Accounts','core/accounts'),('transactions','Transactions','core/transactions'),('getblock','getBlock','rpc/http/getblock'),('gettransaction','getTransaction','rpc/http/gettransaction'),('feequote','getFeeForMessage','rpc/http/getfeeformessage'),('balance','getBalance','rpc/http/getbalance'),('blockhash','getLatestBlockhash','rpc/http/getlatestblockhash')]:
 refs.append((key,'Solana Foundation, ``'+title+",'' official documentation. \\url{https://solana.com/docs/"+path+'}. Accessed October 16, 2026.'))
for key,title in [('sgd','linear_model.SGDClassifier'),('isotonic','isotonic.IsotonicRegression'),('ap','metrics.average_precision_score'),('brier','metrics.brier_score_loss')]:
 refs.append((key,'scikit-learn developers, ``'+title.split('.')[-1].replace('_',r'\_')+",'' API documentation. \\url{https://scikit-learn.org/stable/modules/generated/sklearn."+title+'.html}. Accessed October 16, 2026.'))
refs.extend([("sqlite",r"""SQLite developers, ``CREATE TRIGGER,'' SQL language documentation. \url{https://www.sqlite.org/lang_createtrigger.html}. Accessed October 16, 2026."""),("fastapi",r"""FastAPI contributors, ``FastAPI,'' official documentation. \url{https://fastapi.tiangolo.com/}. Accessed October 16, 2026.""")])
# Collect existing entries and reorder all entries by first in-text citation.
head=s[:s.index(r'\begin{thebibliography}')]
old=dict(re.findall(r'\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\})',s,re.S))
allrefs={**old,**dict(refs)}
keys=[]
for group in re.findall(r'\\cite\{([^}]+)\}',head):
 for key in group.split(','):
  if key not in keys:keys.append(key)
assert len(allrefs)==30,len(allrefs)
assert set(keys)==set(allrefs),(set(allrefs)-set(keys),set(keys)-set(allrefs))
bib=r'\begin{thebibliography}{99}\addcontentsline{toc}{chapter}{References}'+'\n'+r'\small\raggedright\setlength{\itemsep}{7pt}'+'\n'
for key in keys:bib+='\\bibitem{'+key+'} '+allrefs[key].strip()+'\n'
s=head+bib+'\\end{thebibliography}\n\\end{document}\n'
p.write_text(s)
print('References',len(allrefs),'all cited in text')
