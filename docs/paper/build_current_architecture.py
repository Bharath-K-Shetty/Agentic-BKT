"""Editable vector diagram of the implemented research and live prototype."""
from pathlib import Path
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor, white

ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'output/diagrams';out.mkdir(parents=True,exist_ok=True)
d=Drawing(1280,850)
ink=HexColor('#272d28');muted=HexColor('#697266');line=HexColor('#c6cdc1');green=HexColor('#34553e')
d.add(Rect(0,0,1280,850,fillColor=HexColor('#f6f5f1'),strokeColor=None))
d.add(String(40,800,'Solana transaction study architecture',fontName='Helvetica-Bold',fontSize=28,fillColor=ink))
d.add(String(40,772,'Historical ranking research, experimental live inference and independently verified fee evidence',fontName='Helvetica',fontSize=15,fillColor=muted))

def box(x,y,w,title,lines):
    d.add(Rect(x,y,w,84,rx=4,ry=4,fillColor=white,strokeColor=line,strokeWidth=1))
    d.add(String(x+18,y+59,title,fontName='Helvetica-Bold',fontSize=17,fillColor=ink))
    for i,text in enumerate(lines):d.add(String(x+18,y+37-i*18,text,fontName='Helvetica',fontSize=13,fillColor=muted))

def arrow(x1,y1,x2,y2):
    d.add(Line(x1,y1,x2,y2,strokeColor=green,strokeWidth=1.4))
    if x1==x2:points=[x2,y2,x2-4,y2+8,x2+4,y2+8]
    else:points=[x2,y2,x2-8,y2-4,x2-8,y2+4]
    d.add(Polygon(points,fillColor=green,strokeColor=None))

d.add(String(40,726,'HISTORICAL RESEARCH',fontName='Helvetica-Bold',fontSize=13,fillColor=green))
d.add(String(680,726,'INTEGRATED LIVE PROTOTYPE',fontName='Helvetica-Bold',fontSize=13,fillColor=green))
left=[('Public transaction archive',['SolArchive records, declared roles and execution outcomes']),
      ('Chronological account histories',['One-hour outcome delay; no current receipt features']),
      ('Matched trained models',['Histogram gradient boosting with and without writable history']),
      ('Held-out evaluation',['Ranking, calibration, false alarms and cost sensitivity'])]
right=[('Proposed plain SOL transfer',['Sender, recipient, amount and selected network']),
       ('Current network checks',['Balance, fee quote and unsigned simulation; no submission']),
       ('Fresh history and actual ML inference',['Sample mature RPC blocks; reuse the research extractor',
                                             'Experimental scores, freshness and input-range diagnostics']),
       ('Combined result and recorded decision',['Show network result and ML limits; never block using ML'])]
for i,((a,b),(c,e)) in enumerate(zip(left,right)):
    y=620-i*110
    box(40,y,550,a,b);box(680,y,550,c,e)
    if i<3:arrow(315,y,315,y-26);arrow(955,y,955,y-26)
arrow(590,442,680,442)
d.add(String(605,459,'models',fontName='Helvetica',fontSize=11,fillColor=muted))
box(40,102,550,'Controlled local fee experiment',[
    'Signed test transactions and confirmed balance/fee receipts',
    'Proves fee mechanism; does not prove an ML advantage'])
box(680,102,550,'Prospective study and receipt verification',[
    'Save message, feature, history and model hashes before outcome',
    'Accept only a matching later receipt; missing outcomes stay unknown'])
arrow(955,290,955,186)
d.add(String(40,53,'Implemented now: real inference and checks. Still unproven: live predictive validity, added benefit over preflight, fee and time savings.',
             fontName='Helvetica',fontSize=13,fillColor=muted))
path=out/'solana_current_architecture.svg'
renderSVG.drawToFile(d,str(path))
import fitz
svg=fitz.open(path)
pdf=fitz.open('pdf',svg.convert_to_pdf())
pdf[0].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(out/'solana_current_architecture.png')
print(path)
