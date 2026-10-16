from pathlib import Path
p=Path('output/latex/homie_report/main.tex');s=p.read_text()
s=s.replace('The first two questions are evaluated through chronological experiments. The third is examined through calibration and a retrospective cost audit, supported by a separate local fee-mechanism test. Keeping these questions separate avoids treating a ranking improvement as automatic evidence of economic benefit.','Chronological experiments address the first two questions. Calibration and a cost audit address the third, with fee behaviour verified separately on a local validator.')
s=s.replace('The interface presents a short finding before technical details. A user can inspect the evidence when needed without interpreting every feature to understand an insufficient-balance result. Model output is separated from simulation status because they answer different questions.\n\nImplementation responsibilities are divided across data collection, feature construction, model inference, transfer checking and receipt storage. This permits a change to the page layout without changing the research model, and a change to a history collector without replacing the receipt verification rules.','The interface presents a short finding with inspectable evidence. Separate modules handle collection, features, inference, transfer checks and receipt storage, allowing each to be maintained independently.')
s=s.replace('The presentation should show the input, returned network finding, model output and stored decision as one connected flow. A second example can demonstrate a concrete error. The historical evaluation and local receipts then show how the research result and fee-mechanism evidence were produced. A changing RPC result is displayed as returned rather than replaced by a prerecorded successful response.','The presentation connects user input, network findings, model output and the stored decision. Historical results and local receipts provide supporting evidence. Live findings are displayed as returned.')
s=s.replace('minimum height=10mm,font=\\small','minimum height=8mm,font=\\small').replace('node distance=6mm,b/.style','node distance=4mm,b/.style')
s=s.replace(r'\section{Failure handling}',r'\section{Failure handling}')
# Include a directly editable results figure; all values already reported in tables.
marker=r'\section{Ranking versus warning decisions}'
chart=r'''\begin{figure}[htbp]\centering
\begin{tikzpicture}[x=23cm,y=1cm,font=\small]
\foreach \v in {0,0.1,0.2,0.3}{\draw[gray!25] (\v,0)--(\v,3.6);\node[below] at (\v,0){\v};}
\draw[->] (0,0)--(.31,0);
\fill[gray!55] (0,2.6) rectangle (.1688,2.95);
\fill[institution] (0,2.15) rectangle (.2004,2.5);
\fill[gray!55] (0,1.3) rectangle (.2207,1.65);
\fill[institution] (0,.85) rectangle (.2393,1.2);
\node[left] at (0,2.55){Dec. 1};\node[left] at (0,1.25){Dec. 5};
\node[right] at (.1688,2.78){0.1688};\node[right] at (.2004,2.32){0.2004};
\node[right] at (.2207,1.48){0.2207};\node[right] at (.2393,1.02){0.2393};
\node at (.15,-.65){Average precision (higher is better)};
\fill[gray!55] (.01,3.4) rectangle (.023,3.55);\node[right] at (.025,3.48){Baseline};
\fill[institution] (.14,3.4) rectangle (.153,3.55);\node[right] at (.155,3.48){Writable context};
\end{tikzpicture}
\caption{Identity-controlled first-appearance AP on two test dates. The plot shows ranking performance, not classification accuracy.}
\end{figure}
'''
s=s.replace(marker,chart+marker)
s=s.replace('``BRIGHT -- Graph Neural Networks in Real-Time Fraud Detection,\\textquotedblright\\ 2022.',"``BRIGHT -- Graph Neural Networks in Real-Time Fraud Detection,'' 2022.")
p.write_text(s)
