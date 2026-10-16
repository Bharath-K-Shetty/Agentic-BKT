"""Build the two-column publication copy; source prose remains in the draft.

Run with .venv/bin/python docs/paper/build_cold_signer_publication.py.
Author details are inherited from the earlier project manuscript, pending review.
"""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, NextPageTemplate, PageBreak, BalancedColumns
from reportlab.graphics.shapes import Drawing, Rect, Line, String

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 612, 792
LEFT, RIGHT, TOP, BOTTOM, GAP = 54, 52, 54, 54, 16
CW = (WIDTH-LEFT-RIGHT-GAP)/2

def clean(s):
    return s.replace('—', '-').replace('–', '-').replace('−', '-').replace('’', "'").replace('×', ' x ').replace('approximately', 'approximately')

def rich(s):
    s = clean(s)
    s = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'\1', s)
    s = escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*', r'<i>\1</i>', s)
    s = re.sub(r'`([^`]+)`', r'\1', s)
    return s

BODY = ParagraphStyle('Body', fontName='Times-Roman', fontSize=10, leading=12.1,
                      alignment=TA_JUSTIFY, spaceAfter=6, splitLongWords=True)
HEAD = ParagraphStyle('Head', parent=BODY, fontName='Times-Bold', alignment=TA_CENTER,
                      spaceBefore=9, spaceAfter=6, keepWithNext=True)
SUB = ParagraphStyle('Sub', parent=BODY, fontName='Times-Italic', spaceBefore=5, keepWithNext=True)
SMALL = ParagraphStyle('Small', parent=BODY, fontSize=8, leading=9.6, alignment=TA_LEFT, spaceAfter=4)
CAP = ParagraphStyle('Caption', parent=SMALL, alignment=TA_CENTER, fontSize=8, leading=9.4)
TITLE = ParagraphStyle('Title', parent=BODY, fontName='Times-Bold', fontSize=14, leading=16.5, alignment=TA_CENTER)

class Paper(BaseDocTemplate):
    def afterFlowable(self, flow):
        if isinstance(flow, Paragraph) and flow.style.name == 'Head':
            self.canv.bookmarkPage(flow.getPlainText())
            self.canv.addOutlineEntry(flow.getPlainText(), flow.getPlainText(), level=0)

def title_block(canvas, doc):
    canvas.saveState()
    parts = [
        Paragraph('Evaluating Transaction Failure Risk for Solana Signers<br/>Without Available History', TITLE),
        Paragraph('Bharath Kumar Shetty, Deepthi P. Salian, Shreya Shetty, and Swaroop Nellitheertha',
                  ParagraphStyle('Authors',parent=BODY,alignment=TA_CENTER,fontSize=10.5,leading=13)),
        Paragraph('Department of Artificial Intelligence and Machine Learning<br/>Mangalore Institute of Technology and Engineering, Moodabidri, Karnataka, India',
                  ParagraphStyle('Affiliation',parent=SMALL,alignment=TA_CENTER)),
    ]
    y=HEIGHT-TOP
    for i,p in enumerate(parts):
        _,h=p.wrap(WIDTH-LEFT-RIGHT,90)
        p.drawOn(canvas,LEFT,y-h)
        y-=h+(7 if i==0 else 3)
    canvas.restoreState()

def frames(top):
    return [Frame(LEFT,BOTTOM,CW,top-BOTTOM,id='L',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),
            Frame(LEFT+CW+GAP,BOTTOM,CW,top-BOTTOM,id='R',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]

def table(caption, headers, rows, widths):
    style=ParagraphStyle('Cell',parent=SMALL,fontSize=7.4,leading=8.7,spaceAfter=0)
    headstyle=ParagraphStyle('Cellhead',parent=style,fontName='Times-Bold')
    cells=[[Paragraph(rich(str(c)),headstyle) for c in headers]]
    cells.extend([[Paragraph(rich(str(c)),style) for c in row] for row in rows])
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='CENTER')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,0),.6,colors.black),
        ('LINEBELOW',(0,0),(-1,0),.4,colors.black),('LINEBELOW',(0,-1),(-1,-1),.6,colors.black),
        ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    return KeepTogether([Paragraph(caption,CAP),Spacer(1,3),t,Spacer(1,8)])

def architecture():
    d=Drawing(CW,192)
    labels=[('Public Solana archive','Signature, timestamp, declared account roles'),
            ('Chronological replay','Release earlier outcomes after one hour'),
            ('Role-separated history','Signer / read-only / writable / template'),
            ('Matched ML comparison','Structure + read-only vs. + writable context'),
            ('Evaluation by signer availability','Cold history and first appearances')]
    for i,(a,b) in enumerate(labels):
        y=157-i*37
        d.add(Rect(3,y,CW-6,30,strokeColor=colors.black,fillColor=colors.white,strokeWidth=.6))
        d.add(String(CW/2,y+18,a,fontName='Times-Bold',fontSize=8,textAnchor='middle'))
        d.add(String(CW/2,y+7,b,fontName='Times-Roman',fontSize=7.1,textAnchor='middle'))
        if i<4:
            d.add(Line(CW/2,y,CW/2,y-7,strokeWidth=.6))
            d.add(Line(CW/2,y-7,CW/2-2,y-4,strokeWidth=.6))
            d.add(Line(CW/2,y-7,CW/2+2,y-4,strokeWidth=.6))
    return KeepTogether([d,Paragraph('Fig. 1. Implemented replay and matched account-context evaluation. Current execution metadata never enters the feature extractor.',CAP),Spacer(1,7)])

def intervals():
    d=Drawing(CW,139)
    x0,x1=50,CW-8
    def x(v):return x0+(v+.02)/.12*(x1-x0)
    for v in [-.02,0,.04,.08,.10]:
        d.add(Line(x(v),24,x(v),130,strokeColor=colors.HexColor('#cccccc'),strokeWidth=.4))
        d.add(String(x(v),12,f'{v:.2f}',fontName='Times-Roman',fontSize=7,textAnchor='middle'))
    d.add(Line(x(0),24,x(0),130,strokeColor=colors.black,strokeWidth=.8))
    for i,c in enumerate(['pilot','confirmation','extension','prospective']):
        r=json.loads((ROOT/f'docs/results/solana_transaction_risk_{c}.json').read_text())
        a=next(v for v in r['comparisons'] if v['primary'])['ap'];y=118-i*27
        d.add(String(0,y-2,r['protocol']['test_date'][5:],fontName='Times-Roman',fontSize=8))
        lo,hi=a['ci95'];d.add(Line(x(lo),y,x(hi),y,strokeWidth=1))
        d.add(Rect(x(a['weighted_delta'])-2,y-2,4,4,fillColor=colors.black,strokeColor=colors.black))
    return KeepTogether([d,Paragraph('Fig. 2. Original cold-history AP difference and paired hourly 95% intervals. November 24 includes zero; this is not the refined identity-controlled endpoint.',CAP),Spacer(1,7)])

def main():
    source=(ROOT/'docs/paper/SOLANA_COLD_SIGNER_DRAFT.md').read_text()
    sections={}
    for block in source.split('\n## ')[1:]:
        name,content=block.split('\n',1);sections[name.strip()]=content.strip()
    story=[]
    abstract=Paragraph('<b>Abstract-</b>'+rich(sections['Abstract']),ParagraphStyle('Abstract',parent=BODY,fontName='Times-Bold'))
    story+=[abstract,Paragraph('<b>Index Terms-</b>Solana, transaction reliability, machine learning, cold start, delayed feedback, account context.',BODY)]
    def paras(text):
        for p in text.split('\n\n'):
            if p.strip():story.append(Paragraph(rich(p.replace('\n',' ')),BODY))
    def head(s):story.append(Paragraph(s,HEAD))
    head('I. INTRODUCTION');paras(sections['Introduction'])
    head('II. RELATED WORK')
    paras('Zheng et al. analyze failure initiators, programs, errors and temporal patterns on Solana [1]. Alizadeh and Khabbazian study its transfer-network structure and failed transfers [4]. These studies motivate reliability analysis, while our comparison tests execution-outcome ranking for signers without available history.\n\nRelational risk transfer is established. BRIGHT exploits historical entity context for real-time fraud learning [2]. Our task concerns execution reliability and tabular participation summaries; neither relational learning nor restrictions on future information are new contributions.\n\nChaudhary et al. evaluate Ethereum multisignature anomaly triage after execution, using receipt-derived features [5]. Our inputs exclude current execution receipts and our target is the observed Solana success/failure outcome. The contribution is a narrower evaluation setting and empirical result, rather than the first blockchain classifier or a new boosting method.')
    story.append(table('TABLE I. CLOSEST WORK AND TASK DISTINCTIONS',['Work','Established focus','Present distinction'],[
        ['Zheng et al. [1]','Solana failure characterization','Missing-history predictive evaluation'],
        ['Lu et al. [2]','Relational fraud learning','Execution outcome rather than fraud'],
        ['Alizadeh et al. [4]','Transfer-network analysis','Declared-role history ablation'],
        ['Chaudhary et al. [5]','Post-execution anomaly triage','Exclude current receipt features']], [CW*.24,CW*.35,CW*.41]))
    head('III. PROBLEM DEFINITION AND DATA');paras(sections['Data and task definitions'])
    head('IV. SYSTEM ARCHITECTURE AND MODELS');story.append(architecture());paras(sections['Models and information availability'])
    head('V. MATHEMATICAL FORMULATION')
    paras('Let transaction i have checkpoint time t_i, outcome y_i in {0,1}, and declared account-role sets. The available history at t contains only transactions with t_i + 3,600 <= t. For role r and key a, let n_r(a,t) be its available participation count and f_r(a,t) its failure count. The smoothed estimate is:')
    story.append(Paragraph('q<sub>r</sub>(a,t) = [f<sub>r</sub>(a,t) + 20 b(t)] / [n<sub>r</sub>(a,t) + 20]    (1)',ParagraphStyle('Eq',parent=SMALL,alignment=TA_CENTER)))
    paras('Here b(t) = [F(t) + 1] / [N(t) + 2] is the smoothed global failure rate. The candidate augments baseline feature vector x with summaries of q over non-signer writable accounts. Both models use the same matured outcomes and, in the identity-controlled comparison, the same prequential identity score.\n\nThe principal ranking contrast is Delta AP = AP(y, s_context) - AP(y, s_baseline), evaluated on the identical subgroup. Average precision aggregates precision at positive-label recall increments. A gain is a ranking result; it does not guarantee calibration or better recall at a shared false-positive rate. Brier loss is the mean squared difference between predicted probability and y; lower values are better.')
    head('VI. EXPERIMENTAL METHODOLOGY')
    method=sections['Evaluation protocol']
    table_start=method.index('| Window');table_end=method.index('\n\n',table_start)
    paras(method[:table_start])
    rows=[]
    for c in ['pilot','confirmation','extension','prospective']:
        r=json.loads((ROOT/f'docs/results/solana_transaction_risk_{c}.json').read_text())
        p=r['protocol'];n=r['partition_counts']
        rows.append([p['test_date'][5:],f"{n['train']['n']:,}",f"{n['validation']['n']:,}",f"{n['test']['n']:,}"])
    story.append(table('TABLE II. CHRONOLOGICAL PARTITION SIZES',['Test date','Train','Validation','Test'],rows,[CW*.24,CW*.25,CW*.26,CW*.25]))
    paras('All dates are in 2025. Each training and validation day immediately precedes its test day. Full windows are November 1-3, November 8-10, November 22-24, and November 29-December 1.')
    paras(method[table_end:])
    head('VII. RESULTS AND ANALYSIS')
    results=sections['Results'];start=results.index('| Test date');end=results.index('\n\n',start)
    paras(results[:start])
    rows=[]
    for c in ['pilot','confirmation','extension','prospective']:
        r=json.loads((ROOT/f'docs/results/solana_transaction_risk_{c}.json').read_text());m={v['model']:v for v in r['results']}
        a=m['payer_readonly_hgb']['subgroups']['cold_payer'];b=m['context_hgb']['subgroups']['cold_payer']
        rows.append([r['protocol']['test_date'][5:],f"{a['n']:,}",f"{a['ap_positive']:.4f}",f"{b['ap_positive']:.4f}"])
    story.append(table('TABLE III. ORIGINAL COLD-HISTORY RANKING',['Date','Cold rows','Base AP','Context AP'],rows,[CW*.19,CW*.29,CW*.26,CW*.26]))
    story.append(intervals());paras(results[end:])
    a=json.loads((ROOT/'docs/results/solana_transaction_audit_prospective.json').read_text())['first_appearance_identity_results']
    b=a['readonly_identity_hgb'];c=a['context_identity_hgb']
    story.append(table('TABLE IV. RESERVED FIRST-APPEARANCE TEST',['Metric','Baseline + ID','Context + ID'],[
        ['Average precision',f"{b['ap_positive']:.4f}",f"{c['ap_positive']:.4f}"],
        ['AUROC',f"{b['auroc']:.4f}",f"{c['auroc']:.4f}"],
        ['Brier loss',f"{b['brier']:.4f}",f"{c['brier']:.4f}"],
        ['False-positive rate',f"{b['fpr']:.2%}",f"{c['fpr']:.2%}"],
        ['Recall',f"{b['recall']:.2%}",f"{c['recall']:.2%}"]],[CW*.40,CW*.30,CW*.30]))
    head('VIII. IMPLEMENTATION AND OPERATIONAL FOLLOW-UP');paras(sections['Implementation and operational follow-up'])
    head('IX. DISCUSSION AND LIMITATIONS');paras(sections['Discussion and threats to validity'])
    head('X. CONCLUSION AND FUTURE WORK');paras(sections['Conclusion'])
    head('REPRODUCIBILITY')
    paras('Data from SolArchive.org [3], CC BY 4.0, pinned revision 6588cad2832e62be03972ac80d69c6af11d631c8. Local code, protocols, dependency versions and reports accompany this manuscript in the project repository. Raw transaction files remain local. An immutable public artifact URL remains to be supplied for submission. Source hashes and code hashes are recorded per experiment.')
    head('REFERENCES')
    refs=[
        '[1] X. Zheng, Z. Wan, D. Lo, D. Xie, and X. Yang, "Why Does My Transaction Fail? A First Look at Failed Transactions on the Solana Blockchain," Proc. ACM Softw. Eng., vol. 2, ISSTA, Art. ISSTA066, 2025, doi: 10.1145/3728943.',
        '[2] M. Lu et al., "BRIGHT - Graph Neural Networks in Real-Time Fraud Detection," arXiv:2205.13084, 2022. Available: https://arxiv.org/abs/2205.13084.',
        '[3] SolArchive, "Public Solana transaction archive," dataset, CC BY 4.0. Available: https://huggingface.co/datasets/solarchive/solarchive. Pinned revision specified in the reproducibility statement.',
        '[4] S. Alizadeh and M. Khabbazian, "Solana\'s transaction network: analysis, insights, and comparison," EPJ Data Science, vol. 14, Art. 48, 2025, doi: 10.1140/epjds/s13688-025-00561-x.',
        '[5] U. M. D. Chaudhary, H. Arshad, S. Iqbal, A. A. Alaulamie, M. A. Raza, and A. Iqbal, "Explainable Anomaly Scoring for Ethereum Multisignature Transactions Using Temporal Validation and LightGBM," Computers, Materials & Continua, vol. 89, no. 2, 2026, doi: 10.32604/cmc.2026.084774.',
    ]
    for ref in refs:story.append(Paragraph(rich(ref),SMALL))
    pdf=OUT/'solana_cold_signer_paper.pdf'
    doc=Paper(str(pdf),pagesize=(WIDTH,HEIGHT),leftMargin=LEFT,rightMargin=RIGHT,
              title='Evaluating Transaction Failure Risk for Solana Signers Without Available History',
              author='Bharath Kumar Shetty; Deepthi P. Salian; Shreya Shetty; Swaroop Nellitheertha')
    doc.addPageTemplates([PageTemplate(id='First',frames=frames(HEIGHT-155),onPage=title_block,autoNextPageTemplate='Body'),
                          PageTemplate(id='Body',frames=frames(HEIGHT-TOP)),
                          PageTemplate(id='Last',frames=[Frame(LEFT,BOTTOM,WIDTH-LEFT-RIGHT,HEIGHT-TOP-BOTTOM,id='LastFull',
                              leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)])])
    doc.build(story)
    print(pdf)

if __name__=='__main__':main()
