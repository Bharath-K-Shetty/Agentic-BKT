"""Create the plain-language viva guide using the bundled document runtime."""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[2]
doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.68)
sec.left_margin=sec.right_margin=Inches(.8)
sec.header_distance=sec.footer_distance=Inches(.3)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
    style=doc.styles[name]
    style.font.name='Calibri';style.font.color.rgb=RGBColor(0,0,0)
normal=doc.styles['Normal'];normal.font.size=Pt(11)
normal.paragraph_format.space_after=Pt(7)
normal.paragraph_format.line_spacing=1.08
doc.styles['Title'].font.size=Pt(23)
doc.styles['Title'].paragraph_format.space_after=Pt(10)
doc.styles['Heading 1'].font.size=Pt(18)
doc.styles['Heading 1'].paragraph_format.space_before=Pt(0)
doc.styles['Heading 1'].paragraph_format.space_after=Pt(13)
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
header=sec.header.paragraphs[0];header.text='SOLANA TRANSACTION STUDY  |  VIVA GUIDE'
header.runs[0].font.size=Pt(8)
footer=sec.footer.paragraphs[0];footer.alignment=2
run=footer.add_run('Page ');run.font.size=Pt(8)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)

def p(text):
    return doc.add_paragraph(text)

def qa(question,answer):
    para=doc.add_paragraph()
    para.paragraph_format.keep_with_next=True
    para.paragraph_format.space_after=Pt(3)
    para.add_run(question).bold=True
    answer_p=p(answer)
    answer_p.paragraph_format.keep_together=True

def page(title,first=False):
    if not first:doc.add_page_break()
    doc.add_paragraph(title,'Title' if first else 'Heading 1')

def table(headers,rows,widths):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    for col,width in zip(t.columns,widths):col.width=Inches(width)
    for cell,width in zip(t.rows[0].cells,widths):cell.width=Inches(width)
    for cell,text in zip(t.rows[0].cells,headers):
        cell.text=text
        for r in cell.paragraphs[0].runs:r.bold=True
    for row in rows:
        cells=t.add_row().cells
        for cell,text,width in zip(cells,row,widths):cell.width=Inches(width);cell.text=text
    props=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    props.append(borders)
    for i,row in enumerate(t.rows):
        for cell in row.cells:
            cell.vertical_alignment=1
            tcpr=cell._tc.get_or_add_tcPr()
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),'95');e.set(qn('w:type'),'dxa');margins.append(e)
            tcpr.append(margins)
            if i==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'EAEDE8');tcpr.append(shade)
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(2)
                for run in para.runs:run.font.size=Pt(10)
    p('')

page('Solana project viva guide',True)
p('Simple answers for explaining our idea, technology, experiments and demo. Start with this page, then practise the questions in each section. The project is a research prototype, not a deployed transaction-warning service.')
qa('Our idea in one sentence',
   'We use machine learning to estimate transaction failure risk on Solana when wallet history is unavailable, using earlier outcomes involving other accounts in the transaction.')
qa('A short introduction you can say aloud',
   'Our project studies blockchain transaction reliability. A transaction can fail even after reaching a block. Usually a wallet’s past activity provides useful clues, but that history may be missing in our data. We test whether the other accounts involved can provide additional clues. We compare two machine-learning models on real historical records. Shared-account history improved failure ranking in reserved tests, although false alarms still need work.')
qa('A simple analogy',
   'Imagine a new customer using a payment service. We know little about that customer, but we may know how the service performed earlier. That shared history gives us another clue. In our project, the customer represents the wallet and the service represents accounts the transaction touches. This is an analogy, not a claim that blockchain accounts are literally payment services.')
qa('Why does the problem matter',
   'Applications may need to assess reliability even when a signer’s earlier outcomes are unavailable. Better ranking could help decide which transactions deserve additional checking. We have not yet shown live fee savings or prevented failures.')
qa('What have we actually built',
   'A historical research pipeline and an integrated live transfer-check prototype. The live page fetches balance and fee information, simulates a plain SOL transfer, runs trained models on fresh historical features and records the observation. It never signs or submits a payment. A separate local-validator script verifies real test transactions and their fees.')
qa('The sentence to remember',
   'Even when wallet history is missing, the accounts involved can provide useful historical clues about failure risk.')

page('Blockchain terms in plain language')
qa('What is a blockchain',
   'A shared record maintained by a network of computers. It records transactions and their outcomes. Our project analyses those records; it does not build a new blockchain.')
qa('What is Solana',
   'The blockchain whose transaction records we study. We chose a question that uses its declared account roles: which accounts sign, which may change, and which are read only.')
qa('What is a wallet and a signer',
   'A wallet helps a user manage keys and authorize transactions. A signer is an account that signs to authorize an operation. Our experiment follows the first declared signer. An address is not proof of a unique person.')
qa('What is a transaction',
   'A request to carry out one or more blockchain instructions, such as transferring tokens or interacting with an application. Our label records whether the included transaction succeeded or failed.')
qa('What is a block',
   'A group of transaction records added to the blockchain. Our archive contains transactions that reached blocks. Attempts that never reached a block are outside this study.')
qa('What are accounts in this project',
   'On Solana, an account may hold funds, application data or executable program information. A transaction declares the accounts it needs. They are not all human users or wallets.')
qa('What do writable and read only mean',
   'Writable means the transaction is allowed to change that account. Read only means it can read the account without changing it. Our added features summarize earlier outcomes involving non-signer writable accounts.')
qa('What is shared account history',
   'Past transactions may have used an account that appears again in the current transaction. We summarize those earlier available outcomes. Sharing an account does not prove common ownership or identify the cause of failure.')
qa('Does missing history mean a brand new wallet',
   'No. It means our sampled data has no available earlier outcomes for that signer. The address may have activity elsewhere. First appearance also means first appearance in our sampled replay, not on the entire blockchain.')
qa('Is a failed transaction always a bad or malicious transaction',
   'No. A protective check may correctly reject an operation. We predict observed execution failure, not fraud, theft, user knowledge or financial loss.')

page('Our contribution and novelty')
qa('What is the research question',
   'Does historical participation of writable accounts improve failure ranking for transactions with unavailable signer history, beyond transaction structure, signer history and read-only account information?')
qa('What is our novelty claim',
   'Our candidate contribution is a specific empirical benchmark and finding: we evaluate missing signer history explicitly and test the extra signal from writable-account history under delayed feedback and strong controls. We have supporting results on reserved data.')
qa('Did we invent a new machine learning algorithm',
   'No. We use established algorithms. The contribution is the question, account-role representation, evaluation and measured finding. Using an existing algorithm can still support an empirical research contribution.')
qa('Has related work already been done',
   'Yes. Solana failure characteristics, blockchain prediction and relational learning have all been studied. Our reviewed sources did not evaluate this exact cold-signer account-role benchmark. That does not prove nobody anywhere has studied an equivalent idea.')
qa('What is the baseline model',
   'Our comparison model already receives transaction structure, signer history and read-only account and template history. It is not merely a wallet-history model. The candidate adds writable-account history while keeping the learning algorithm and data splits the same.')
qa('Why do we also test account identity',
   'A model might just learn that particular account addresses are associated with failures. We learn an additional identity-based score and supply it to both models. Then we check whether explicit writable history still adds useful ranking signal.')
qa('How does this differ from contract auditing or DKT',
   'It predicts execution outcomes from blockchain records. It does not inspect smart-contract source code for vulnerabilities and does not trace students’ knowledge. Earlier education and auditing work is separate from this study.')
qa('Can we call it publishable',
   'We have an implemented research candidate and evidence worth presenting or submitting for review. Acceptance and worldwide originality are not guaranteed. The manuscript still needs venue-specific preparation and stronger generalization evidence.')

page('Technology and algorithms')
table(['Technology','What we use it for'],[
    ['Python','Data processing, feature construction and model training'],
    ['pandas and NumPy','Working with transaction tables and numerical features'],
    ['PyArrow and Parquet','Reading and storing the public transaction data'],
    ['scikit-learn','Boosting, logistic regression, calibration and metrics'],
    ['FastAPI Uvicorn and SQLite','Local application API and recorded study observations'],
    ['HTML CSS and JavaScript','The browser demo and result-reveal interaction'],
    ['pytest','Tests for history timing, calibration boundaries and replay behaviour'],
],[2.0,4.9])
qa('Which main algorithm do we use',
   'Histogram Gradient Boosting for classification, through scikit-learn’s HistGradientBoostingClassifier. It combines small decision trees to estimate the chance of the failure class.')
qa('How does gradient boosting work',
   'It builds trees in sequence. Later trees help correct errors remaining from earlier trees. The combined model learns patterns between our input features and transaction outcomes.')
qa('What does histogram mean here',
   'Numerical feature values are grouped into bins when searching for tree splits. This makes training more efficient. It does not mean our project is a charting application.')
qa('What other algorithms do we use',
   'SGD logistic regression learns a comparison score from account identities. Isotonic regression adjusts score-to-probability mapping in a separate calibration follow-up. Calibration does not create new transaction evidence.')
qa('Why use trees instead of deep learning',
   'Our inputs are structured numerical history features, so boosted trees are a practical baseline. We have not established that they beat every neural network. The research question is whether additional account history helps, not whether a complex architecture looks impressive.')
qa('Important settings if asked',
   'The original boosting model uses 150 iterations, at most 15 leaves, a minimum leaf size of 40 and L2 regularization of 5, with early stopping disabled. Settings remain fixed across the reported windows.')

page('Data training and fair testing')
qa('Where does the data come from',
   'SolArchive, a public archive of real Solana transactions, released under CC BY 4.0. We pin the source version and record extraction hashes. We analyse selected row groups, not the whole chain or a verified random sample.')
qa('What are our inputs and output',
   'Inputs include account counts, signer and writable roles, and summaries of earlier failure rates and participation counts. The output is a failure-risk estimate. The observed label is success = 0 or failure = 1.')
qa('What does the pipeline do',
   'Read selected records; verify statuses and duplicates; put them in time order; build features from available earlier outcomes; train the models; choose thresholds on validation data; evaluate on a later test date; save results for replay.')
qa('How do we split the data',
   'Each window has a training day, then a validation day, then a test day. Training learns model parameters. Validation sets thresholds or calibrates scores. Testing measures performance after those choices are fixed. The first six training hours build history.')
qa('How do we prevent the model from seeing the answer',
   'We build the current features before adding the current label. Earlier outcomes become available only after an assumed one-hour delay. Current errors, execution logs, actual compute used, balances and paid fees are excluded from prediction inputs.')
qa('Does the model use information from the test period',
   'Its histories can use earlier test outcomes after they mature. The fitted boosting model is not retrained on the test day. This is a stated online-feedback replay, not an evaluation with completely frozen histories.')
qa('What is a cold-history transaction',
   'Its first signer has no earlier outcome available in the sampled replay. It may have another transaction still waiting for its label. First appearance is stricter: the signer has not previously appeared as first signer in that replay.')
qa('How much data did we use',
   'The paper’s original four windows contain 1,588,408 raw sampled rows across twelve dates, before deduplication and exclusions. A later fifth window is reported separately. Do not say all 1.59 million rows were training data or independent wallets.')

page('Results and numbers you should understand')
table(['Evaluation','Baseline AP','Our AP','Test group'],[
    ['Paper reserved test','0.1688','0.2004','17,904 first appearances'],
    ['Later unused-date test','0.2207','0.2393','19,515 first appearances'],
],[2.4,1.0,1.0,2.5])
p('Both rows compare models that receive an account-identity score. The later result appears in the updated paper as a separate follow-up. Keep these populations distinct when explaining the results.')
qa('What result should I say in the viva',
   'On the paper’s reserved first-appearance test, writable-account history improved average precision from 0.1688 to 0.2004 after the identity control. A later unused-date test also showed a positive gain. This supports better failure ranking, not reliable live prevention.')
qa('What is average precision or AP',
   'It summarizes how well failures appear near the top of a model’s risk ranking across thresholds. Higher is better on the same test group. AP of 0.2004 does not mean 20.04% classification accuracy.')
qa('What is the difference between risk and accuracy',
   'Risk is the model’s estimate for one transaction, such as 30.8% failure risk. Accuracy is the fraction of correct class decisions across a set of transactions at a chosen threshold. A higher displayed risk is not a better model score.')
qa('What are precision recall and false alarms',
   'Precision asks how many flagged transactions actually failed. Recall asks how many actual failures were flagged. The false-positive rate asks how many successful transactions were wrongly flagged. Threshold changes trade off these quantities.')
qa('Why is accuracy alone not enough',
   'Most transactions in our first-appearance groups succeed. Always predicting success could therefore produce high accuracy while catching no failures. We report ranking and warning metrics rather than claiming one accuracy number proves usefulness.')
qa('What is our strongest limitation in the paper result',
   'At the inherited threshold, the context model had a 28.65% false-positive rate on the reserved first-appearance group. Better ranking did not make that warning threshold reliable. Calibration results also vary by period.')
qa('What do the uncertainty intervals mean',
   'The paper’s AP gain is +0.0316 with an hourly bootstrap 95% interval of +0.0168 to +0.0501. The later gain is +0.0186 with interval +0.0095 to +0.0288. These describe uncertainty for sampled fixed predictions; they are not a guarantee for every future day.')

page('How to explain the demo')
qa('What should I say before clicking',
   'This is a replay of real historical transactions. Both models produce estimates using earlier available records. I will reveal the actual recorded outcome after comparing them. No live payment is made.')
qa('What does no available wallet history mean',
   'Our sample has no matured earlier outcome for this signer. We may still have outcomes involving other accounts the transaction touches. Those accounts provide the extra context we study.')
qa('What does 100 percent shared-account history mean',
   'All of the relevant writable accounts have earlier available outcomes in the sample. It measures coverage, not safety, prediction accuracy or confidence that the transaction will succeed.')
qa('Why do 41 point 5 percent and 30 point 8 percent differ',
   'The two models estimate the same event: execution failure. They use different input histories. In that example the baseline estimates 41.5% risk and the context model estimates 30.8%. Lower means less estimated risk, not lower accuracy.')
qa('Why is one flagged and the other not flagged',
   'Each model has its own warning threshold chosen on validation data. Its risk estimate is compared with that threshold. The threshold is not automatically 50%, and it is not selected using the example’s outcome.')
qa('Which prediction is correct',
   'Reveal the recorded outcome first. If the transaction fails and our model did not flag it, that is a missed failure. If it succeeds and the baseline flagged it, that is a false alarm. A single outcome cannot validate either exact probability.')
qa('What should I demonstrate',
   'Show one correctly flagged failure, one unflagged success, a false alarm and a missed failure. The first four named examples were selected to illustrate these cases. Other examples follow time order. Use the full test results when discussing performance.')
qa('Is this live model inference on a new wallet',
   'There are three modes. The replay displays saved historical estimates. The prediction page runs the trained models on a held-out historical row. The live page constructs fresh history features and runs the models for a new plain SOL transfer. Live scores are experimental and are not validated failure probabilities. None of these pages submits a payment.')
qa('A simple closing line',
   'The demo shows how extra history changes a prediction and lets us inspect both correct decisions and mistakes. Our experiments, rather than selected examples, provide the research evidence.')

page('Live demo and fee evidence')
qa('How do we demonstrate the integrated application',
   'Open /live, choose a devnet example and click Run check and models. Explain the network result first, then the experimental ML scores. Show the stored observation and message hash. If a matching transaction was submitted separately, enter its signature to verify its receipt. No receipt means the outcome is unknown.')
qa('Where do the fresh features come from',
   'A collector reads sampled public blocks across earlier hours. It uses declared signer and writable roles and earlier execution outcomes. The same feature extractor as the research pipeline builds the input row. Outcomes must be at least one hour old. Stale, insufficient or wrong-network history causes the model to withhold a score.')
qa('Are live scores trustworthy probabilities',
   'Not yet. We run the actual trained models, but fresh sampling and network conditions differ from training. We show raw scores for research observation and flag input-range differences. We do not use these scores to automatically block a payment.')
qa('Can failed Solana transactions charge fees',
   'Yes, failures during on-chain execution can still pay fees. Our local test measured 5,000 lamports, or 0.000005 test SOL. The recipient received nothing. A simulation that is not submitted costs no on-chain fee, and normal preflight rejected this example for free too.')
qa('Have we proved our ML saves fees',
   'No. The local experiment proves the fee mechanism, not an ML advantage. Across 102,443 historical cold-history transactions, warning reliability changed between periods. The stricter 83.3% rule warned on 107 failures and 60 successful transactions, while missing 6,303 failures. Historical preflight results and paid fees are absent.')
qa('What is recorded for future validation',
   'Before an outcome, we save the checked message hash, model and history hashes, fresh features, simulation result and time. A receipt must match that exact message and occur later. Observed fees are kept separate from savings; observation duration is kept separate from time saved.')

page('Practical value limitations and final viva answers')
qa('Is it useful in the real world',
   'The problem is real, and account context is a plausible input for transaction reliability screening. We demonstrated a historical ranking benefit. Real-world usefulness still needs live-arrival data, calibration and comparison with existing simulation tools.')
qa('Why not just simulate every transaction',
   'Simulation is an important existing approach. We have not shown our model is better than it. A useful future experiment would test whether history adds information beyond simulation, particularly when conditions change between simulation and execution.')
qa('What are the main limitations',
   'One archive provider, sparse samples, limited dates, missing actual submission times and missing attempts that never land in a block. Thresholds drift, calibration is mixed, and account identities do not identify independent people.')
qa('What did the calibration follow-up achieve',
   'It adjusted probabilities using early validation rows and chose thresholds on later validation rows. On the later unused-date context-model test, recall rose from 6.61% to 29.87% and false alarms rose from 0.32% to 3.18%. Other periods were less successful, including a period with no alerts. This is a tradeoff, not a universal fix.')
qa('What would we improve next',
   'Use the new study recorder to collect predictions and signed preflight results before outcomes, then analyse candidates that passed preflight. Test new periods without tuning on their outcomes. Improve calibration and sampling, and measure false-warning costs before claiming fee savings.')
qa('Are we using a smart contract or a large language model',
   'The replay demo does not deploy a smart contract or require a language model. It uses ordinary ML on blockchain records. The broader repository contains earlier experiments, but those are not the current research contribution.')
qa('What should we never claim',
   'Do not claim the first blockchain failure predictor, a newly invented boosting algorithm, guaranteed transaction success, a fraud detector, proven fee savings, or publication acceptance. Do not report failure-risk percentages as accuracy.')
qa('If an examiner asks for a detail I do not know',
   'State what the experiment establishes, then offer to check the exact protocol or report. Do not guess a metric, explain a correlation as a cause, or invent a personal contribution.')
qa('Where can I verify the answers',
   'The paper draft and results report are in docs/paper and docs/SOLANA_TRANSACTION_RISK_RESULTS.md. Later findings and the demo walkthrough are in webapp/README.md. Exact parameters and outputs are in research/solana/ml and docs/results/solana_transaction_*.json. Public source: huggingface.co/datasets/solarchive/solarchive.')

out=ROOT/'output/docs/solana_viva_guide.docx';out.parent.mkdir(parents=True,exist_ok=True)
doc.core_properties.title='Solana project viva guide'
doc.core_properties.subject='Plain language questions and answers for the project viva'
doc.core_properties.author='Bharath Kumar Shetty, Deepthi P. Salian, Shreya Shetty, Swaroop Nellitheertha'
doc.save(out)
print(out)
