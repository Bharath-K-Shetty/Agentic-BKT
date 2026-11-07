"""Generate original, print-readable architecture figures for the HOMIE report."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[3] / 'output/latex/homie_report/assets'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
COLORS = {
    'data': ('#E8F0FC', '#315F97'),
    'features': ('#E1F2EF', '#24776D'),
    'control': ('#FFF1D7', '#98702B'),
    'baseline': ('#E9EDF3', '#52657D'),
    'context': ('#D9EFE8', '#20735E'),
    'output': ('#EEE7F6', '#71548A'),
}

def canvas(height):
    fig, ax = plt.subplots(figsize=(7.1, height))
    ax.set(xlim=(0, 100), ylim=(0, 100))
    ax.axis('off')
    return fig, ax

def box(ax, x, y, w, h, title, detail='', kind='data', size=10.5):
    fill, edge = COLORS[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.25,rounding_size=1.2',
                              facecolor=fill, edgecolor=edge, linewidth=1.3))
    ax.text(x+w/2, y+h*(.70 if detail else .5), title, ha='center', va='center',
            fontsize=11.5, fontweight='bold', color=edge)
    if detail:
        ax.text(x+w/2, y+h*.32, detail, ha='center', va='center',
                fontsize=size, color='#202D3D', linespacing=1.4)

def arrow(ax, p, q):
    ax.annotate('', xy=q, xytext=p, arrowprops={'arrowstyle': '-|>', 'color': '#526171', 'lw': 1.4})

def save(fig, name):
    fig.tight_layout(pad=.6)
    fig.savefig(OUT/(name+'.png'), dpi=300, facecolor='white')
    fig.savefig(OUT/(name+'.pdf'), facecolor='white')
    plt.close(fig)

fig, ax = canvas(7.5)
box(ax,3,87,44,11,'Current transaction','Declared account roles',kind='data')
box(ax,54,87,43,11,'Earlier outcomes','One-hour maturity delay',kind='data')
box(ax,8,71,84,10,'Information boundary','Exclude current and immature outcomes',kind='control')
arrow(ax,(25,87),(30,81));arrow(ax,(75,87),(70,81))
box(ax,3,52,44,13,'Account-history features','Rates, counts and coverage\nby account role',kind='features')
box(ax,54,52,43,13,'Shared identity learner','SGD logistic · 2²⁰ hash bins\n10-minute update batches',kind='features')
arrow(ax,(30,71),(25,65));arrow(ax,(70,71),(75,65))
box(ax,8,37,84,9,'Common input: 27 features + 1 identity score',kind='control')
arrow(ax,(25,52),(30,46));arrow(ax,(75,52),(70,46))
box(ax,3,17,44,13,'BASELINE · 28 inputs','Common input only\nHistogram gradient boosting',kind='baseline')
box(ax,54,17,43,13,'HOMIE · 35 inputs','Common input + 7 writable\naccount-history features',kind='context')
arrow(ax,(30,37),(25,30));arrow(ax,(70,37),(75,30))
box(ax,3,4,44,7,'Baseline failure score',kind='output')
box(ax,54,4,43,7,'HOMIE failure score',kind='output')
arrow(ax,(25,17),(25,11));arrow(ax,(75,17),(75,11))
ax.text(50,.2,'Matched HGB: 150 iterations · learning rate 0.1 · at most 15 leaves',ha='center',fontsize=9.5,color='#344354')
save(fig,'primary_architecture')

fig, ax = canvas(6.3)
box(ax,8,85,84,12,'Transaction input','Historical replay or qualifying live history',kind='data')
box(ax,8,66,84,12,'Build time-respecting features','One-hour delay; live network, freshness and history checks',kind='features',size=10)
arrow(ax,(50,85),(50,78))
box(ax,3,45,44,14,'BASELINE · 27 inputs','Structure, signer, read-only\nand template history',kind='baseline')
box(ax,54,45,43,14,'HOMIE · 34 inputs','Baseline + 7 writable\naccount-history features',kind='context')
arrow(ax,(28,66),(25,59));arrow(ax,(73,66),(75,59))
box(ax,3,25,44,13,'Isotonic calibration','Baseline mapping\nEarlier validation data',kind='control')
box(ax,54,25,43,13,'Isotonic calibration','HOMIE mapping\nEarlier validation data',kind='control')
arrow(ax,(25,45),(25,38));arrow(ax,(75,45),(75,38))
box(ax,8,7,84,11,'Scores and review decisions','Separate thresholds from later purged validation data',kind='output',size=10)
arrow(ax,(25,25),(30,18));arrow(ax,(75,25),(70,18))
ax.text(50,1,'Exported variant: no identity score. Live scores are experimental.\nBalance and simulation checks run separately.',ha='center',va='center',fontsize=9.5,color='#344354')
save(fig,'demo_architecture')
