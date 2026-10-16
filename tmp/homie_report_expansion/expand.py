from pathlib import Path
p=Path('output/latex/homie_report/main.tex');s=p.read_text()
def before(marker,text):
 global s
 assert s.count(marker)==1,marker
 s=s.replace(marker,text+'\n'+marker)
before(r'\chapter{LITERATURE SURVEY}',r'''
\section{Background concepts}
\subsection{Wallets, signers and accounts}
A wallet helps a user manage signing keys and approve transactions. The signer is the address whose signature authorises a transaction. The primary signer used in this study is the first signer in the sampled record. A transaction may also reference accounts holding balances, program state or other data. These referenced accounts are not necessarily people or wallets.

The distinction matters because the proposed model uses the history of \emph{participation} in transactions. If an account repeatedly appears in failed operations, that pattern may be informative about a later operation involving it. The model does not infer that the account owner caused those failures or acted maliciously.
\subsection{Writable and read-only account roles}
A writable account is declared as an account whose state may be changed by the transaction. A read-only account may be read without modification. These declarations describe access permissions, not a guarantee that an account will actually change. The project separates the primary signer from other writable accounts to avoid treating the signer's own history as new contextual evidence.

Read-only templates in this project are sets of declared read-only account addresses. They can capture recurring transaction contexts, but are not verified lists of programs invoked by each transaction. This definition follows the fields available in the selected archive.
\subsection{Failure, rejection and unknown outcome}
An execution failure is a recorded unsuccessful execution outcome. A candidate may instead be rejected before submission, or an attempted transaction may never appear in the observed archive. These cases must not be merged into the same label. The historical model is evaluated on included transactions with recorded outcomes. The application separately records simulation results and receipt availability.
\section{Why missing signer history matters}
A model that depends mainly on signer history can perform well on repeat participants while providing little information for a signer without earlier outcomes. Reporting only the aggregate score can hide this weakness. HOMIE therefore measures performance on a defined missing-history subgroup as well as examining the broader dataset.

Two subgroups are distinguished. A cold-history transaction has no matured primary-signer outcome available at its checkpoint. A first-appearance transaction is the first observed primary-signer occurrence in the sampled replay. A signer can appear repeatedly within the one-hour outcome delay and still remain cold. First-appearance evaluation reduces this particular source of repetition.
\section{Illustrative use case}
Consider a signer with no available history that submits an operation referencing accounts A and B. Earlier transactions from other signers have involved these accounts. The baseline sees transaction structure and read-only context. The extended model additionally receives summaries of earlier outcomes involving writable A and B. It may assign a different score because these summaries supply evidence that the signer-only history lacks.

This example explains the mechanism; it is not an additional measured result. The model can increase or decrease a score depending on the learned pattern. A lower score alone does not prove an improvement. The recorded outcome and performance across the test set determine whether the predictions are useful.
\section{Organisation of the report}
Chapter 2 positions the work relative to prior research. Chapter 3 specifies system requirements. Chapter 4 describes the architecture and data flow. Chapter 5 explains the dataset, feature engineering, algorithms and implementation. Chapters 6 and 7 present verification and experimental results. Chapter 8 concludes the report, followed by a reproducibility appendix and terminology guide.
''')
before(r'\chapter{SYSTEM REQUIREMENTS}',r'''
\section{Temporal relational learning}
BRIGHT, proposed by Lu et al., addresses real-time fraud detection using graph neural networks~\cite{bright}. It explicitly prevents future transactions from sending information into predictions about earlier transactions and separates historical computation from real-time inference. The relevant lesson for HOMIE is the importance of an information boundary when relationships between entities are used as predictors.

HOMIE uses tabular participation summaries rather than a graph neural network. Its target is Solana execution failure rather than e-commerce fraud. BRIGHT is therefore related methodological work, not a directly evaluated baseline. No claim of outperforming BRIGHT is made because the datasets, labels and operating conditions differ.
\section{Existing approaches and design choices}
\subsection{Signer-based prediction}
Signer history can summarise repeated behaviour efficiently. Its weakness in this study is absence of evidence for some signers at prediction time. Replacing missing history with a global average supplies a reasonable default but does not distinguish otherwise similar cold-history transactions. Shared-account features are tested as a way to add information in that setting.
\subsection{Identity-based learning}
A model may learn that particular addresses recur with particular outcomes. This can explain apparent benefits from contextual features. The identity-control experiment gives both compared models a score learned from role-tagged account identities, including writable identities. The remaining comparison asks whether explicit historical summaries help beyond that learned score.
\subsection{Execution simulation}
Simulation evaluates a candidate transaction against a network state. It can identify a concrete error without needing a statistical training set. Historical ML could be complementary if it captured useful residual information, but demonstrating that requires observations beyond a retrospective archive. HOMIE includes both mechanisms in the application while evaluating their findings separately.
\section{Study contribution and research questions}
The report addresses three questions. First, does writable context improve failure ranking for sampled cold-history transactions? Second, does the improvement remain for first appearances when both models receive an identity score? Third, what happens when historical scores are turned into practical warning policies?

The first two questions are evaluated through chronological experiments. The third is examined through calibration and a retrospective cost audit, supported by a separate local fee-mechanism test. Keeping these questions separate avoids treating a ranking improvement as automatic evidence of economic benefit.
''')
before(r'\chapter{SYSTEM DESIGN}',r'''
\section{User roles and supported tasks}
\begin{table}[htbp]\centering\caption{Users and supported activities}
\begin{tabularx}{\textwidth}{p{29mm}YY}\toprule User&Activity&System output\\\midrule
Researcher&Compare baseline and context predictions&Metric tables, saved predictions and provenance\\
Project evaluator&Inspect a historical example&Features, model scores and revealed recorded result\\
Transfer user&Check a proposed native SOL transfer&Balance, fee quote, simulation finding and experimental score\\
Study operator&Link a later transaction receipt&Verified matching outcome or explicit rejection\\\bottomrule\end{tabularx}\end{table}
\section{Input and output requirements}
The live flow accepts the selected network, sender address, recipient address and transfer amount. Addresses must be valid public keys. Amounts are parsed exactly into lamports; arbitrary floating-point rounding must not alter the intended transfer. The supported candidate is a plain native SOL transfer. Arbitrary token swaps and multi-instruction DeFi transactions are outside this implemented checker.

Outputs include a clear current-network finding, the quoted fee, the amount-plus-fee requirement and any balance shortfall. When valid history and model artifacts are available, the response also contains actual model scores and provenance. It records whether simulation occurred and whether signature verification was enabled. Each saved observation has an identifier for later lookup.
\section{Data quality and reproducibility requirements}
The historical workflow records extraction settings and derived-file hashes. Conflicting records or date mismatches must not be silently repaired into convenient data. Training, validation and test boundaries are defined chronologically. Feature columns and model settings are retained so exported inference consumes the same type and order of inputs used during fitting.

The live collector and model scorer must agree on the network. A mainnet-trained experiment may be inspected on devnet for functional testing, but devnet output is not evidence of equivalent predictive performance. A snapshot's collection timestamp and the maturity of its rows are checked separately.
\section{Usability and maintainability}
The interface presents a short finding before technical details. A user can inspect the evidence when needed without interpreting every feature to understand an insufficient-balance result. Model output is separated from simulation status because they answer different questions.

Implementation responsibilities are divided across data collection, feature construction, model inference, transfer checking and receipt storage. This permits a change to the page layout without changing the research model, and a change to a history collector without replacing the receipt verification rules.
''')
before(r'\chapter{METHODOLOGY AND IMPLEMENTATION}',r'''
\section{Module responsibilities}
\begin{table}[htbp]\centering\caption{Implemented modules and responsibilities}
\small\begin{tabularx}{\textwidth}{p{36mm}YY}\toprule Module&Input&Responsibility\\\midrule
Archive extraction&Selected date and shard&Retrieve selected columns and record provenance\\
Participation history&Chronological account roles and matured labels&Produce structural and contextual features\\
Model training&Training and validation feature tables&Fit controlled classifiers and retain artifacts\\
Live history&Public RPC blocks&Prepare network-specific mature snapshots\\
Transfer checker&Addresses, amount and network&Construct message; check balance, fee and simulation\\
Study store&Decision payload and later signature&Preserve observation; verify matching receipt\\
Web interface&User selection or transfer input&Display results and inspection links\\\bottomrule\end{tabularx}\end{table}
\section{Logical data-flow design}
The research path transforms archive records into a feature table, then into fitted models and held-out predictions. Test labels are used to evaluate those predictions and to update later history only after the defined delay. They are not used to refit the gradient boosting model during the test day.
\begin{figure}[htbp]\centering
\begin{tikzpicture}[node distance=8mm,b/.style={draw,align=center,text width=105mm,minimum height=11mm,font=\small},a/.style={-{Latex},thick}]
\node[b](a){Selected archive columns and recorded execution labels};
\node[b,below=of a](b){Chronological validation and delayed-outcome history queue};
\node[b,below=of b](c){Structural, signer, read-only and writable feature groups};
\node[b,below=of c](d){Date-based training / validation / test partitions};
\node[b,below=of d](e){Matched model fitting and fixed test-day prediction};
\node[b,below=of e](f){Ranking metrics, operating metrics and paired-hour intervals};
\foreach \x/\y in {a/b,b/c,c/d,d/e,e/f}\draw[a](\x)--(\y);
\end{tikzpicture}\caption{Historical research data flow.}\end{figure}
\clearpage
\section{Decision storage design}
The implemented SQLite store uses a decision table, a receipt table and an abstention table. A decision has a generated identifier, serialised payload, payload hash and recording timestamp. The payload contains the candidate and the relevant check and model observations. Receipts are stored separately so a later outcome cannot overwrite what was known at prediction time.
\begin{table}[htbp]\centering\caption{Study-store entities}
\small\begin{tabularx}{\textwidth}{p{25mm}YY}\toprule Entity&Main fields&Relationship or constraint\\\midrule
Decisions&id, payload, payload hash, recorded time&Primary record; update and delete triggers prevent mutation\\
Receipts&decision ID, signature, payload, recorded time&At most one receipt per decision; unique signature; immutable record\\
Abstentions&decision ID, reason, recorded time&Optional record associated with a decision\\\bottomrule\end{tabularx}\end{table}
An abstention is a recorded decision not to proceed; by itself it cannot establish what would have happened. Similarly, the lack of an attached receipt does not establish success, failure or avoided fees. Application-level immutability and hashes improve traceability, but do not make a local database immune to a privileged administrator replacing its files.
\section{Receipt verification sequence}
\begin{figure}[htbp]\centering
\begin{tikzpicture}[node distance=6mm,b/.style={draw,align=center,text width=108mm,minimum height=10mm,font=\small},a/.style={-{Latex},thick}]
\node[b](a){Load the original decision and verify its payload hash};
\node[b,below=of a](b){Fetch the supplied signature's confirmed receipt};
\node[b,below=of b](c){Validate supported transfer encoding and exact message hash};
\node[b,below=of c](d){Require a later slot and a compatible recording timestamp};
\node[b,below=of d](e){Verify signature association and fee / balance consistency};
\node[b,below=of e](f){Attach a unique receipt; otherwise retain the original decision};
\foreach \x/\y in {a/b,b/c,c/d,d/e,e/f}\draw[a](\x)--(\y);
\end{tikzpicture}\caption{Checks before a receipt becomes an observed outcome.}\end{figure}
\section{Failure handling}
Invalid input is rejected before network calls. RPC unavailability yields an incomplete check rather than a successful result. A missing history snapshot can prevent ML scoring while leaving the nature of the network check explicit. A different transaction message, even from the same sender, is insufficient to attach a receipt. Changing the blockhash changes the message and requires a fresh observation.
''')
before(r'\section{Learning algorithm}',r'''
\subsection{Worked history example}
Suppose an account has participated in ten matured observations, including two failures, and the global available failure rate is 0.05. With smoothing strength 20, its rate is
\begin{equation}q=\frac{2+20(0.05)}{10+20}=0.10.\end{equation}
With no account observations, the same rule returns the global rate. This avoids assigning an extreme rate to an account solely because one observed transaction failed. The example uses illustrative counts to explain the implemented formula; it is not a result sampled from the evaluation.
\subsection{Feature groups}
\begin{table}[htbp]\centering\caption{Feature groups and their interpretation}
\small\begin{tabularx}{\textwidth}{p{29mm}YY}\toprule Group&Examples&What it describes\\\midrule
Structure&Account, signer and writable counts; duplicates&Declared transaction composition\\
Signer history&Smoothed failure rate and log count&Available outcomes for the primary signer\\
Read-only history&Seen fraction, counts and rate summaries&Prior participation of read-only accounts\\
Read-only template&Template rate and count&Recurring declared account set\\
Writable history&Seen fraction and rate/count summaries&Prior participation of non-signer writable accounts\\
Infrastructure&Presence indicators&Common infrastructure accounts without pooled context histories\\\bottomrule\end{tabularx}\end{table}
Seen fraction is a coverage measure: a value of 14.3\% means that proportion of the relevant accounts has earlier available observations. It is not an accuracy score or a failure probability. The failure rates and coverage variables give the model both a pattern and information about how much history supports it.
\subsection{Leakage prevention}
Using the current transaction's error message would make failure prediction trivial after execution. HOMIE therefore excludes current logs, errors, consumed compute, balances, paid fees and block position from its historical model inputs. Time controls chronology and information availability but is not supplied as a numeric predictor.

Consider a transaction included at 10:20. Under the study's one-hour delay, its label cannot contribute to a 10:45 prediction. It becomes eligible at 11:20. The delay is an explicit research assumption. Inclusion timestamps do not reconstruct the exact information available at historical submission time.
\subsection{Replay procedure}
For each chronological record, the feature builder first releases eligible earlier labels from the pending queue. It then resolves the current account roles and computes features from that available history. Only after the feature row is produced is the current outcome scheduled for release one hour later. This order is reused across the research and live-history extraction paths.
''')
before(r'\section{Identity control and calibration}',r'''
\subsection{How boosting produces a score}
The classifier learns a sequence of trees. Each new tree contributes a correction to the model's current decision function. In binary classification, the decision function $z(x)$ is mapped to a score through a logistic link:
\begin{equation}z_M(x)=z_0+\eta\sum_{m=1}^{M}h_m(x),\qquad s(x)=\frac{1}{1+e^{-z_M(x)}}.\end{equation}
Here $h_m$ is a fitted tree and $\eta$ is the learning-rate parameter. Training reduces binary log loss, which penalises confident incorrect predictions. A probability-shaped output from this function still requires calibration assessment before being interpreted as an accurate event frequency in a new population.
\subsection{Why a tabular model fits this implementation}
The input is a fixed-length numeric representation of transaction structure and account history. A tree ensemble can learn non-linear combinations, such as different effects of a historical rate at low and high observation counts. It does not require a sequence of natural-language queries or a language model. The implemented method also allows a controlled feature ablation with the same learner on both sides.

Deep learning and graph models are possible extensions, but their inclusion would require a defined representation, training procedure and fair comparison. They are not necessary to describe the actual implemented contribution. The report therefore identifies histogram gradient boosting as the main algorithm and distinguishes the logistic identity control from it.
''')
before(r'\section{Application implementation}',r'''
\subsection{Metrics and interpretation}
Let TP denote flagged failures, FP flagged successes, FN missed failures and TN unflagged successes. For a fixed warning threshold,
\begin{align}
\mathrm{Precision}&=\frac{TP}{TP+FP}, &\mathrm{Recall}&=\frac{TP}{TP+FN},\\
\mathrm{FPR}&=\frac{FP}{FP+TN}, &\mathrm{Accuracy}&=\frac{TP+TN}{TP+FP+FN+TN}.
\end{align}
A classifier that always predicts success has accuracy equal to the success prevalence. On the reserved first-appearance group with 5.88\% failures, that simple rule would have about 94.12\% accuracy but identify no failures. This is why accuracy alone is unsuitable for judging the research question.

Average precision summarises the precision--recall curve as $\sum_k(R_k-R_{k-1})P_k$, where $P_k$ and $R_k$ are precision and recall as the score threshold changes. AUROC describes ranking across positive and negative cases. Brier loss, $N^{-1}\sum_i(s_i-y_i)^2$, assesses the numerical predictions against binary outcomes; lower values are better.
\subsection{Uncertainty and experimental discipline}
The paired-hour bootstrap samples hourly blocks and computes the difference between both models on the same resampled observations. Pairing preserves their direct comparison. Grouping by hour accounts for some temporal clustering rather than treating every transaction as independent. The resulting interval is conditional on the fitted models and sampled periods; it does not measure all possible deployment uncertainty.

The reserved refined endpoint was specified after earlier exploratory diagnostics and before inspecting the fourth window's outcomes. It is a reserved historical test, not a publicly preregistered live trial. The further December window supplies another chronological comparison. This distinction makes the development of the research question clear without presenting exploratory choices as fixed from the start.
''')
before(r'\chapter{TESTING}',r'''
\subsection{Balance, fee and amount calculation}
For balance $B$, requested amount $A$ and quoted fee $F$, the checker calculates
\begin{equation}\mathrm{required}=A+F,\qquad \mathrm{shortfall}=\max(0,A+F-B).\end{equation}
For example, if a recorded check has a balance of 0.5120009 SOL, a requested transfer of 1 SOL and a quoted fee of 0.000005 SOL, the shortfall is 0.4880041 SOL. This corresponds to the saved insufficient-balance verification case. A sufficient balance passes this arithmetic check but may still encounter a separate simulation error.
\subsection{Simulation modes}
The standard web check creates an unsigned candidate and calls simulation with signature verification disabled. This allows a user to inspect supported execution conditions without supplying a private key. The result concerns the candidate at the checked state, not whether a valid signature will later be provided.

A separate signed-observation route accepts an already signed plain transfer, preserves its blockhash and enables signature verification during simulation. It still does not submit the transaction. The two modes are labelled separately because an unsigned check and signed simulation do not establish the same facts.
\subsection{Model provenance and range checks}
The stored response includes hashes identifying the model artifact, history snapshot and feature values. These support later inspection of which inputs produced the score. Live input values are compared with central training ranges as a diagnostic. A value within those ranges is not proof that a new transaction has the same outcome distribution as the training set.

Changing the amount may change the balance or simulation finding while leaving the ML score unchanged, because the current ML features do not encode the amount. This behaviour follows the feature definition and is useful to explain during a demonstration. The model assesses account context; the network checker assesses the constructed amount-specific candidate.
''')
before(r'\chapter{RESULTS AND DISCUSSION}',r'''
\section{Detailed test scenarios}
\begin{table}[htbp]\centering\caption{Test inputs and expected safeguards}
\small\begin{tabularx}{\textwidth}{p{12mm}YY}\toprule ID&Scenario&Expected response\\\midrule
T01&Current label supplied to replay&Current prediction excludes that outcome\\
T02&History timestamp is in the future&Reject invalid history\\
T03&Snapshot older than one hour&Withhold ML score and request refresh\\
T04&Mainnet request with devnet history&Do not score using the wrong network\\
T05&Amount exceeds balance plus fee budget&Return the exact shortfall\\
T06&Simulation reports rent-related error&Return an actionable current-state finding\\
T07&Receipt belongs to another message&Reject outcome attachment\\
T08&Receipt predates recorded observation&Reject retrospective attachment\\
T09&No confirmed receipt is returned&Keep outcome and paid fee unknown\\
T10&Attempt to overwrite stored decision&Database trigger rejects mutation\\
T11&Unsigned input sent to signed observer&Reject unsupported signed observation\\
T12&Repeated history-refresh request&Reuse the running job rather than duplicate it\\\bottomrule\end{tabularx}\end{table}
These scenarios are grounded in the implemented tests and recorded checks. Network-dependent examples are observations from their recorded run; their outputs can change as balances and chain state change. Unit tests exercise controlled inputs so that key invariants can be repeated independently of public RPC availability.
\section{Local experiment procedure}
The verification script starts its own loopback validator and creates throwaway test accounts funded through local airdrops. It constructs an invalid transfer whose execution violates an account minimum-balance requirement. The checker observes the error. The experiment then compares a stopped candidate, ordinary preflight rejection and a deliberately forced execution failure with preflight disabled only inside the isolated test.

For the executed case, the script retrieves the confirmed receipt and compares the reported fee with the payer's before-and-after balance. The failed transfer does not deliver the requested principal, but the execution fee is observed. A valid transfer separately verifies that the sender's balance decreases by principal plus fee. The script stops the validator instance it started.
\section{Integration and presentation checks}
The recorded integration checks include a small transfer, insufficient balance, a rent-related failure and a read-only mainnet case. The system returns current findings and, where historical inputs qualify, actual fitted-model inference. HTTP success alone is insufficient: the response content and the absence of a broadcast path are also inspected.

The presentation should show the input, returned network finding, model output and stored decision as one connected flow. A second example can demonstrate a concrete error. The historical evaluation and local receipts then show how the research result and fee-mechanism evidence were produced. A changing RPC result is displayed as returned rather than replaced by a prerecorded successful response.
''')
before(r'\section{Practical interpretation and limitations}',r'''
\section{Detailed interpretation of the primary result}
On December 1, the AP difference is $0.2004-0.1688=0.0316$, or about 3.16 AP percentage points. Relative to the baseline AP, this is approximately an 18.7\% increase. This relative change is a ranking comparison; it must not be described as 18.7\% fewer failed transactions or an 18.7\% reduction in fees.

On December 5, the corresponding difference is approximately 0.0186. Both first-appearance intervals exclude zero under the specified paired-hour analysis. The second test has a smaller gain, which is consistent with the usefulness of context changing across sampled dates. Neither result implies correct predictions for every individual transaction.
\section{Coverage and individual examples}
The interface displays the fraction of relevant accounts with available history so the user can see the amount of contextual coverage. A high coverage fraction means the model has earlier observations for more of those accounts. It does not imply high-quality or representative observations, and it does not guarantee confidence in the prediction.

Two models may give different scores to the same transaction because one has additional features. For the earlier example with scores 41.5\% and 30.8\%, a threshold can flag one and not the other. If the transaction succeeds, the lower score may be more consistent with that single outcome; if it fails, the higher score may be. Aggregate ranking, calibration and operating metrics are needed to judge which approach is better overall.
\section{What the practical system establishes}
The project establishes that the fitted models can be executed on constructed features, current network checks can be performed for supported transfers, and an observation can be preserved before a matching receipt is attached. The fee experiment establishes that the stage at which a transaction fails matters for fee accounting. These are separate, inspectable engineering outcomes.

The policy audit also provides an informative negative finding: the tested ranking gains do not translate automatically into favourable pooled cost utility. A useful final-year research report includes that result because it identifies the actual deployment problem. Calibrating a score, choosing a warning threshold and evaluating the cost of delaying a successful transaction are distinct from fitting the classifier.
''')
before(r'\renewcommand{\bibname}{REFERENCES}',r'''
\appendix
\chapter{REPRODUCIBILITY AND USER GUIDE}
\section{Project components}
The active research implementation is under \texttt{research/solana/ml}. The current web application uses \texttt{webapp/backend/replay.py}. Older project prototypes remain in the repository; they are not the implementation described by this report. The model artifact and processed features must exist before live inference can run.
\begin{table}[htbp]\centering\caption{Evidence and implementation locations}
\small\begin{tabularx}{\textwidth}{p{38mm}Y}\toprule Purpose&Location relative to the project root\\\midrule
Research scripts&\path{research/solana/ml/}\\
Local fee verification&\path{research/solana/fee_proof/}\\
Live feature construction&\path{webapp/backend/live_history.py}\\
Transfer checking&\path{webapp/backend/transfer_check.py}\\
Decision and receipt store&\path{webapp/backend/prospective.py}\\
Saved experimental reports&\path{docs/results/}\\
Model and derived data&\path{data/processed/solana_ml/}\\\bottomrule\end{tabularx}\end{table}
\section{Running the application}
From the repository root, activate the project Python environment and use the documented model export after preparing the processed training data. Collect a recent history for the desired network. Start the current FastAPI application with:
\begin{quote}\small\ttfamily
.venv/bin/python -m uvicorn\\
webapp.backend.replay:app --host 127.0.0.1 --port 8430
\end{quote}
The command is shown over two lines for readability; enter it as one shell command. Open \url{http://127.0.0.1:8430/live}. Refresh historical inputs if the page reports a stale snapshot. Public RPC availability affects collection and live checks.
\section{Suggested demonstration sequence}
\begin{enumerate}
\item Open the historical replay and explain the missing-history problem.
\item Select a transaction, compare the two models and reveal its recorded outcome.
\item Open the live checker and enter a supported transfer on the intended network.
\item Explain the balance, quoted fee and simulation result before the experimental ML score.
\item Inspect the saved observation and its model/history provenance.
\item Show the local fee receipts and the chronological research results.
\end{enumerate}
This sequence demonstrates both the research pipeline and the implemented system. A live model score is not presented as a new evaluated accuracy figure, and the absence of submission is not counted as a measured saving.
\section{Terms used during the viva}
\begin{description}[style=nextline]
\item[Execution failure] A transaction with a recorded unsuccessful execution outcome.
\item[Cold history] No matured primary-signer outcome available in the sampled history.
\item[First appearance] The signer's first observed occurrence in the replay.
\item[Shared-account context] Earlier participation of accounts referenced by the current transaction.
\item[Baseline] The comparison model before adding writable-history summaries.
\item[Ablation] A controlled comparison where a feature group is added or removed.
\item[Calibration] Agreement between numerical scores and observed event frequencies.
\item[False positive] A successful transaction incorrectly flagged by a warning policy.
\item[Preflight] Checks associated with submission that may reject a candidate before it is sent for execution.
\item[Receipt] A retrieved record of a transaction's observed execution outcome and fee.
\end{description}
\section{Short explanation of the contribution}
HOMIE asks whether a transaction can be assessed when its signer has no usable history. It learns from earlier transactions involving other accounts used by that operation. The project compares models fairly over time, finds additional ranking signal in the studied data, and implements a system that displays predictions alongside current transfer checks and recorded outcomes.
''')
s=s.replace(r'\begin{thebibliography}{9}',r'\begin{thebibliography}{9}')
s=s.replace(r'\bibitem{archive}',r'\bibitem{bright} M. Lu et al., ``BRIGHT -- Graph Neural Networks in Real-Time Fraud Detection,\textquotedblright\ 2022. \url{https://arxiv.org/abs/2205.13084}.'+'\n'+r'\bibitem{archive}')
# More useful section navigation in a longer report; avoid listing every subsection.
s=s.replace(r'\setlist{nosep,leftmargin=*}',r'\setlist{nosep,leftmargin=*}'+'\n'+r'\setcounter{tocdepth}{1}')
p.write_text(s)
print('Source words:',len(s.split()))
