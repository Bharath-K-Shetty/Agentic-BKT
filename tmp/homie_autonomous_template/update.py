from pathlib import Path
import re,zipfile
root=Path('output/latex/homie_report'); p=root/'main.tex'; old=p.read_text(); Path('tmp/homie_autonomous_template/main-before.tex').write_text(old)
with zipfile.ZipFile('/Users/biks/Downloads/UG_Phase-II_Project_Report_Sample_Filled_Template_Autonomous_2023 Scheme.docx') as z:
 (root/'assets/mite_autonomous.jpeg').write_bytes(z.read('word/media/image1.jpeg'))
# Preserve existing substantive sections, moving them into the template structure.
parts=re.split(r'\\chapter\{([^}]+)\}',old)
chap={parts[i]:parts[i+1] for i in range(1,len(parts),2)}
def secs(name):
 a=re.split(r'\\section\{([^}]+)\}',chap[name]); return {a[i]:a[i+1] for i in range(1,len(a),2)}
I=secs('INTRODUCTION');L=secs('LITERATURE SURVEY');R=secs('SYSTEM REQUIREMENTS');D=secs('SYSTEM DESIGN');M=secs('METHODOLOGY AND IMPLEMENTATION');T=secs('TESTING');V=secs('RESULTS AND DISCUSSION');C=secs('CONCLUSION AND FUTURE SCOPE')
def s(title,body): return '\\section{'+title+'}\n'+body.strip()+'\n\n'
def sub(title,body): return '\\subsection{'+title+'}\n'+body.strip()+'\n\n'
def ch(title,body): return '\\chapter{'+title+'}\n'+body
pre=old.split('\\begin{document}')[0]
pre=pre.replace('margin=28mm,top=27mm,bottom=25mm,headheight=16pt','left=1.25in,right=1in,top=.75in,bottom=.75in,footskip=10mm')
pre=pre.replace('\\setstretch{1.15}','\\onehalfspacing')
a=pre.index('\\pagestyle{fancy}');b=pre.index('\\captionsetup',a)
pre=pre[:a]+r'''\pagestyle{fancy}\fancyhf{}
\fancyfoot[C]{\small Page \thepage}
\renewcommand{\headrulewidth}{0pt}\renewcommand{\footrulewidth}{0pt}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\small Page \thepage}}
\titleformat{\chapter}[display]{\centering\bfseries\fontsize{18}{22}\selectfont}{CHAPTER \thechapter}{10pt}{}
\titlespacing*{\chapter}{0pt}{8pt}{18pt}
\titleformat{\section}{\bfseries\fontsize{16}{20}\selectfont}{\thesection}{.7em}{}
\titleformat{\subsection}{\bfseries\fontsize{14}{17}\selectfont}{\thesubsection}{.7em}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}
\titlespacing*{\subsection}{0pt}{10pt}{4pt}
\widowpenalty=10000\clubpenalty=10000
''' +pre[b:]
pre=re.sub(r'\\newcommand\{\\PageBorder\}.*\n','',pre)
pre+=r'''\newcommand{\CourseCode}{23AISE409}
\newcommand{\PageBorder}{\begin{tikzpicture}[remember picture,overlay]\draw[line width=.6pt] ([xshift=10mm,yshift=-10mm]current page.north west) rectangle ([xshift=-10mm,yshift=10mm]current page.south east);\end{tikzpicture}}
\newcommand{\Masthead}{{\fontsize{16}{19}\selectfont\bfseries MANGALORE INSTITUTE OF\par TECHNOLOGY \& ENGINEERING\par}\vspace{2mm}{\fontsize{9}{11}\selectfont (A Unit of Rajalaxmi Education Trust \textregistered, Mangalore)\par Autonomous Institute Affiliated to V.T.U, Belagavi, Approved by AICTE, New Delhi\par Accredited by NAAC with A+ Grade \& ISO 9001:2015 Certified Institution\par}}
\newcommand{\Department}{ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING}
\renewcommand{\contentsname}{TABLE OF CONTENTS}
\renewcommand{\listfigurename}{LIST OF FIGURES}
\renewcommand{\listtablename}{LIST OF TABLES}
'''
front=r'''\begin{document}
\begin{titlepage}\PageBorder\centering\setstretch{1}\setlength{\parskip}{0pt}
\Masthead\vspace{4mm}
\includegraphics[height=28mm]{assets/mite_autonomous.jpeg}\par\vspace{4mm}
\textbf{PROJECT REPORT}\par\vspace{3mm}
\textbf{\CourseCode\ PROJECT PHASE -- II}\par\vspace{5mm}
{\fontsize{18}{22}\selectfont\bfseries ``HOMIE: MACHINE LEARNING-BASED TRANSACTION RISK ASSESSMENT ON SOLANA''\par}\vspace{5mm}
Submitted in partial fulfilment of the requirements for the award of the degree of\par\vspace{3mm}
\textbf{BACHELOR OF ENGINEERING}\par\vspace{2mm}in\par\vspace{2mm}
\textbf{\Department}\par\vspace{4mm}by\par\vspace{3mm}
\AuthorTable\par\vspace{6mm}
Under the Guidance of\par\textbf{\GuideName}\par
% Guide designation not supplied; leave unset.
\vspace{7mm}\textbf{DEPARTMENT OF\par\Department}\par\vfill
\textbf{\AcademicYear}\par
\end{titlepage}
\pagenumbering{roman}
\begingroup\setstretch{1.15}\thispagestyle{empty}\PageBorder
\begin{center}\Masthead\vspace{5mm}
\includegraphics[height=28mm]{assets/mite_autonomous.jpeg}\par\vspace{4mm}
\textbf{DEPARTMENT OF\par\Department}\par\vspace{8mm}
{\fontsize{18}{22}\selectfont\bfseries CERTIFICATE}\end{center}\vspace{5mm}
This is to certify that the Project Phase -- II (\textbf{\CourseCode}) work entitled \textbf{``\ProjectTitle''} is the project work carried out by the following students in partial fulfilment of the requirements for the award of the Bachelor of Engineering degree in Artificial Intelligence and Machine Learning at Mangalore Institute of Technology \& Engineering (Autonomous), affiliated to Visvesvaraya Technological University, Belagavi, during the academic year \AcademicYear.
\begin{center}\AuthorTable\end{center}
The report is submitted for examination under the guidance of \textbf{\GuideName}.
% Unsigned certificate form for institutional review and signatures.
\vspace{13mm}
\begin{tabularx}{\textwidth}{Y >{\raggedleft\arraybackslash}X}
\hrulefill&\hrulefill\\
\GuideName&Head of Department\\Project Guide&AI\&ML
\end{tabularx}
\vspace{15mm}\begin{center}\rule{45mm}{.4pt}\\Principal\end{center}
\clearpage\endgroup
\chapter*{DECLARATION}\thispagestyle{empty}\PageBorder
We declare that the Project Phase -- II (\CourseCode) report entitled \textbf{``\ProjectTitle''}, submitted in partial fulfilment of the requirements for the Bachelor of Engineering degree in Artificial Intelligence and Machine Learning, presents our project work carried out under the guidance of \textbf{\GuideName}. Sources of data, software and published research used in the work are acknowledged in the report. This report has not been submitted by us for the award of another degree.
\vspace{12mm}
\begin{tabularx}{\textwidth}{|c|Y|p{28mm}|}\hline
\textbf{Sr. No.}&\textbf{Name and USN}&\textbf{Signature}\\\hline
1&Bharath Kumar Shetty (4MT23AI013)&\\[5mm]\hline
2&Deepthi P. Salian (4MT23AI017)&\\[5mm]\hline
3&Shreya Shetty (4MT23AI051)&\\[5mm]\hline
4&Swaroop Nellitheertha (4MT23AI056)&\\[5mm]\hline
\end{tabularx}
\vspace{12mm}\par Place: Moodbidri\par Date: \rule{35mm}{.4pt}
\chapter*{ACKNOWLEDGEMENTS}\thispagestyle{empty}\PageBorder
We express our gratitude to our project guide, \GuideName, for guidance during Project Phase -- II. We thank the Head of Department, Principal and management of Mangalore Institute of Technology \& Engineering for providing the academic environment for this work. We also thank the faculty of the Department of Artificial Intelligence and Machine Learning for their support.

We acknowledge the maintainers of SolArchive for making blockchain records publicly accessible, and the developers of Solana, scikit-learn and the open-source tools used in the implementation. We thank our families and classmates for their encouragement and support.
\vspace{12mm}\begin{flushright}Bharath Kumar Shetty (4MT23AI013)\\Deepthi P. Salian (4MT23AI017)\\Shreya Shetty (4MT23AI051)\\Swaroop Nellitheertha (4MT23AI056)\end{flushright}
\chapter*{ABSTRACT}\thispagestyle{empty}\PageBorder
HOMIE assesses Solana transaction execution risk when the signer has no available outcome history. It constructs chronological features from public SolArchive records and compares histogram gradient boosting models with and without non-signer writable-account history. A one-hour outcome delay restricts features to earlier available labels. Both models also receive a learned identity score in the stronger comparison. On 17,904 reserved first-appearance transactions, average precision increases from 0.1688 to 0.2004; a further test on 19,515 transactions increases it from 0.2207 to 0.2393. The application supports historical replay, fitted-model inference, live transfer checks and decision-to-receipt recording. A local-validator experiment verifies that a landed execution failure can incur a fee while normal preflight can reject the same error without a fee. The results demonstrate additional historical failure-ranking signal; measured ML-driven fee savings are not claimed.
\par\vspace{4mm}\textbf{Keywords:} Solana, histogram gradient boosting, account history, transaction failure, temporal evaluation.
\tableofcontents\listoffigures\listoftables
\chapter*{ABBREVIATIONS / NOTATIONS}
\begin{tabularx}{\textwidth}{p{30mm}Y}\toprule Abbreviation&Meaning\\\midrule
AI&Artificial intelligence\\ML&Machine learning\\HGB&Histogram gradient boosting\\AP&Average precision\\AUROC&Area under the receiver operating characteristic curve\\FPR&False-positive rate\\TP / FP&True positive / false positive\\TN / FN&True negative / false negative\\RPC&Remote procedure call\\SOL&Native currency unit of Solana\\SGD&Stochastic gradient descent\\API&Application programming interface\\HTTP&Hypertext Transfer Protocol\\JSON&JavaScript Object Notation\\SQL&Structured Query Language\\CI&Confidence interval\\\bottomrule\end{tabularx}
\clearpage\pagenumbering{arabic}
'''
intro=s('Background',I['Project overview']+I['Background concepts'])+s('Problem Statement',I['Problem statement'])+s('Motivation / Need for the Project',I['Why missing signer history matters'])+s('Objectives',I['Objectives'])+s('Scope of the Project',I['Scope and contribution'])+s('Significance and Expected Contribution',I['Illustrative use case'])+s('Organization of the Report','Chapter 2 reviews relevant literature. Chapter 3 describes the proposed system, requirements and architecture. Chapter 4 explains the research methodology. Chapter 5 presents implementation and experimental verification. Chapter 6 reports results and analysis. Chapter 7 concludes the work and identifies future scope. References and a reproducibility appendix follow.')
lit=s('Introduction','This chapter reviews Solana execution studies, relational learning and the methodological foundations used in HOMIE.')+s('Review of Existing Work',L['Related work and technical foundations']+sub('Temporal Relational Learning',L['Temporal relational learning'])+sub('Boosting, Calibration and Evaluation',L['Boosting, calibration and evaluation literature']))+s('Comparative Analysis',L['Existing approaches and design choices'])+s('Research and Design Gap',L['Research position'])+s('Summary',L['Study contribution and research questions'])
req=s('Problem Formulation',I['Problem statement'])+s('Proposed Solution','HOMIE combines a historical ML comparison with a transfer-checking application. The extended model adds writable-account participation history to the baseline. Network checks and recorded outcomes are displayed separately from model scores.')+s('Requirements',sub('Functional and Non-Functional Requirements',R['Functional requirements']+R['Reliability requirements']+R['Input and output requirements'])+sub('Hardware and Operating Requirements',R['Operating requirements'])+sub('Software Requirements',R['Software used']))+s('System Architecture / Block Diagram',D['Architecture']+sub('Transaction-Check Workflow',D['Transaction-check workflow'])+sub('Data and Responsibility Boundaries',D['Data and responsibility boundaries']))+s('Functional / System Components',D['Module responsibilities']+R['User roles and supported tasks'])+s('Scope and Constraints',R['Data quality and reproducibility requirements']+R['Usability and maintainability']+D['Failure handling'])
method=s('Objective of the Study','The study tests whether writable-account history adds failure-ranking information when signer history is unavailable, including a stronger comparison with a shared identity score.')+s('Method / Approach',M['Data collection and labels'])+s('Measurement / Evaluation Parameters',M['Evaluation windows'])+s('Tools, Equipment and Resources','Python, pandas, NumPy and PyArrow prepare chronological tables. Scikit-learn fits classifiers and computes metrics. Public SolArchive data supports the historical study; a Solana local validator supports the separate fee experiment.')+s('Experimental Procedure',D['Logical data-flow design'])+s('Model Architecture',M['Learning algorithm']+sub('Identity Control and Calibration',M['Identity control and calibration']))+s('Error Sources and Mitigation','Temporal leakage, repeated signers and identity memorisation can distort an apparent improvement. Delayed labels, a first-appearance endpoint and a shared identity control address these risks. Sparse sampling and changing network conditions remain limits of the evaluation.')+s('Data Processing and Analysis',M['Chronological features'])
impl=s('Implementation Environment','The application uses FastAPI and Uvicorn, browser-based HTML, CSS and JavaScript, and SQLite for observation storage. Research outputs and fitted model artifacts are loaded from the project workspace.')+s('Module-wise Implementation',M['Application implementation']+sub('Decision Storage',D['Decision storage design'])+sub('Receipt Verification',D['Receipt verification sequence']))+s('Experimental Setup and Test Cases',T['Detailed test scenarios']+sub('Local Experiment Procedure',T['Local experiment procedure']))+s('Prototype / System Implementation',T['Integration and presentation checks'])+s('Testing and Validation',T['Verification strategy']+sub('Fee-Mechanism Experiment',T['Fee-mechanism experiment']))
results=s('Results',V['Historical ranking results']+sub('Fee-Policy and Local Results',V['Fee-policy and local results']))+s('Analysis',V['Detailed interpretation of the primary result']+V['Ranking versus warning decisions'])+s('Discussion',V['Coverage and individual examples'])+s('Comparison with Existing Approaches','The baseline and writable-context models use matched classifier settings and chronological periods. The identity-controlled comparison supplies the same learned score to both. These within-dataset comparisons isolate the added feature group. Literature methods using different targets and datasets are not claimed as directly outperformed.')+s('Significance and Implications',V['What the practical system establishes'])+s('Potential Applications','The prototype can support research inspection, prioritisation of transactions for review, and diagnosis of supported native SOL transfer problems. Balance and simulation findings can guide a user before submission. Automatic transaction blocking or economic savings require separate policy evaluation.')
con=s('Summary of Work',C['Conclusion'])+s('Conclusions','Writable-account history improves the reported first-appearance AP on two chronological tests with a shared identity control. The warning-policy audit shows that ranking improvement alone does not guarantee favourable cost utility.')+s('Contributions','The project integrates chronological participation features, controlled model comparisons, a working inference interface and a decision-to-receipt workflow. A separate local experiment verifies execution-fee behaviour.')+s('Utility / Applications','HOMIE provides an inspectable system for studying transaction failure and checking supported transfers. It makes model predictions, current network checks and later execution outcomes available as separate observations.')+s('Limitations',V['Practical interpretation and limitations'])+s('Scope for Future Work',C['Future scope'].replace('\\appendix',''))
append=chap['REPRODUCIBILITY AND USER GUIDE'].split('\\renewcommand{\\bibname}')[0]
bib='\\renewcommand{\\bibname}'+old.split('\\renewcommand{\\bibname}')[1]
bib=bib.replace('Revision specified in Chapter 5.','Revision specified in Chapter 4.').replace('\\end{document}','')
body=front+ch('INTRODUCTION',intro)+ch('LITERATURE REVIEW',lit)+ch('PROPOSED SYSTEM AND SCOPE',req)+ch('METHODOLOGY',method)+ch('IMPLEMENTATION AND EXPERIMENTAL WORK',impl)+ch('RESULTS, ANALYSIS AND DISCUSSION',results)+ch('CONCLUSION AND FUTURE SCOPE',con)
# Reorder references by their first citation in the reorganised report.
entries=re.findall(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})',bib,re.S); lookup=dict(entries); order=[]
for group in re.findall(r'\\cite\{([^}]+)\}',body+append):
 for key in group.split(','):
  if key not in order: order.append(key)
assert set(order)==set(lookup),(set(lookup)-set(order))
bib=bib[:bib.index('\\bibitem')]+''.join('\\bibitem{'+key+'}'+lookup[key] for key in order)+'\\end{thebibliography}\n'
p.write_text(pre+body+bib+'\\appendix\n'+ch('REPRODUCIBILITY AND USER GUIDE',append)+'\\end{document}\n')
Path('tmp/homie_autonomous_template/artifact.md').write_text('Template: supplied Autonomous 2023 Scheme DOCX, preserved unchanged.\nOutput: editable LaTeX plus PDF and Overleaf ZIP.\nA4 with template checklist margins (left 1.25in, right 1in, top/bottom .75in); Times 12pt, 1.5 spacing; headings 18/16/14pt. Normalize accidental mixed source page sizes.\nMITE masthead and original embedded logo; single frontmatter border; centered Page footer. Seven chapters, declaration, acknowledgements, <=150-word abstract, contents, lists, abbreviations, references before appendix. Retain automatic navigable contents instead of manually typed sample page numbers.\nCourse 23AISE409; guide designation unconfirmed and unset. No sample author names, CNN content, placeholder notes or unsupported approvals copied. Existing experimental numbers retained.\n')
