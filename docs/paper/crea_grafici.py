"""Generate reproducible figures from the study's explicitly bounded data."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PNG=ROOT.parent/'analisi/2026-11-12/paper/figure'
SVG=HERE/'grafici'
PNG.mkdir(parents=True,exist_ok=True);SVG.mkdir(exist_ok=True)
DATA=json.loads((HERE/'misure.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,
    'axes.spines.right':False,'svg.fonttype':'none','savefig.facecolor':'white'})
BLUE='#2463ad';DARK='#23364b';MUTED='#96abc1'

def save(name,fig):
    fig.savefig(PNG/(name+'.png'),dpi=180,bbox_inches='tight')
    fig.savefig(SVG/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)

def pair(ax,labels,a,b,unit,label_a,label_b,log=False):
    x=np.arange(len(labels));w=.31
    bars_a=ax.bar(x-w/2,a,w,label=label_a,color=MUTED);bars_b=ax.bar(x+w/2,b,w,label=label_b,color=BLUE)
    if log:ax.set_yscale('log')
    ax.set_xticks(x,labels);ax.set_ylabel(unit);ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    ax.legend(frameon=False,loc='upper left',fontsize=8,ncol=2)
    for bar in [*bars_a,*bars_b]:
        h=bar.get_height();ax.annotate(f'{h:,.2f}'.replace(',',' '),(bar.get_x()+bar.get_width()/2,h),
            xytext=(0,3),textcoords='offset points',ha='center',fontsize=7)
    if not log:ax.set_ylim(top=max(max(a),max(b))*1.33)
    else:ax.set_ylim(top=max(max(a),max(b))*3.5)

def main():
    fig,ax=plt.subplots(figsize=(7,3.7),layout='constrained');ax.set_xlim(0,10);ax.set_ylim(0,7);ax.axis('off')
    boxes=[(3.55,6.05,2.9,.65,'Interfaccia e voce'),(3.55,4.55,2.9,.8,'Core ALLMA\ncontesto e politiche'),
        (.15,2.6,2.75,.85,'Memoria, identità\ne apprendimento'),(3.6,2.6,2.8,.85,'Strumenti, fonti\ne obiettivi'),
        (7.0,2.6,2.85,.85,'Motori locali\nQwen / Decider'),(3.35,.7,3.3,.85,'Controllo, origine\ne consegna')]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.06,rounding_size=.12',
            linewidth=1,edgecolor='#9cb5d1',facecolor='#edf4fb'))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8.5,color=DARK)
    for start,end in [((5,6.03),(5,5.42)),((4.1,4.52),(1.55,3.5)),((5,4.52),(5,3.52)),
                      ((5.9,4.52),(8.4,3.5)),((1.6,2.55),(4,1.58)),((5,2.55),(5,1.58)),
                      ((8.4,2.55),(6,1.58))]:
        ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=10,linewidth=1.0,color=BLUE))
    ax.set_title('Schema funzionale sintetico',loc='left',fontweight='bold',color=DARK)
    save('00_architettura',fig)
    d=DATA['gpu'];fig,ax=plt.subplots(figsize=(7,3.1),layout='constrained')
    pair(ax,['128 token','512 token'],d['cpu_s'],d['gpu_s'],'Secondi, mediana','CPU','OpenCL GPU')
    ax.set_title('Qwen: prototipo nativo, prompt + 64 token guidati',loc='left',fontweight='bold',color=DARK)
    save('01_gpu',fig)
    d=DATA['npu'];fig,ax=plt.subplots(figsize=(7,3.1),layout='constrained')
    pair(ax,d['cases'],d['cpu_ms'],d['npu_ms'],'Millisecondi, mediana (scala log)','CPU','Hexagon NPU',True)
    ax.set_title('Decider: tempi dei casi brevi e del caso lungo',loc='left',fontweight='bold',color=DARK)
    save('02_npu',fig)
    d=DATA['pagination'];fig,axs=plt.subplots(1,2,figsize=(7,3.1),layout='constrained')
    pair(axs[0],['Memoria trattenuta','Picco'],[v/1e6 for v in (d['python_resident_bytes'][0],d['python_peak_bytes'][0])],
        [v/1e6 for v in (d['python_resident_bytes'][1],d['python_peak_bytes'][1])],'MB Python (scala log)','Prima','Pagine',True)
    axs[1].bar(['Prima','Pagine'],d['milliseconds'],color=[MUTED,BLUE]);axs[1].set_ylabel('Millisecondi, mediana')
    axs[1].set_ylim(0,225);axs[1].grid(axis='y',alpha=.16);axs[1].set_axisbelow(True)
    for i,v in enumerate(d['milliseconds']):axs[1].text(i,v+4,f'{v:.1f}',ha='center',fontsize=8)
    fig.suptitle('Archivio sintetico: memoria e tempo di apertura',x=.01,ha='left',fontweight='bold',color=DARK)
    save('03_memoria',fig)
    d=DATA['context'];fig,ax=plt.subplots(figsize=(7,3.1),layout='constrained')
    pair(ax,['2K / 1.824','4K / 3.840','8K / 4.116'],d['first_text_long_s'],d['complete_long_s'],
        'Secondi, mediana','Primo testo','Completamento')
    ax.set_xlabel('Finestra / token nel prompt lungo');ax.set_title('Storia lunga: più contesto e latenza',loc='left',fontweight='bold',color=DARK)
    save('04_contesto',fig)
    d=DATA['cancellation'];fig,ax=plt.subplots(figsize=(7,3.1),layout='constrained')
    ax.bar(['Controllo fra token','Callback nativo CPU'],d['wait_after_signal_ms'],color=[MUTED,BLUE]);ax.set_yscale('log')
    ax.set_ylabel('Attesa dopo il segnale, ms (scala log)');ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    for i,v in enumerate(d['wait_after_signal_ms']):ax.text(i,v*1.12,f'{v:,.2f} ms'.replace(',',' '),ha='center',fontsize=8)
    ax.set_ylim(top=50000);ax.set_title('Cancellazione CPU: una coppia controllata',loc='left',fontweight='bold',color=DARK)
    save('05_cancel',fig)
    d=DATA['test_suites'];fig,ax=plt.subplots(figsize=(7,3.1),layout='constrained')
    values=[d['passed_091'],d['passed_0911']];ax.bar(['0.9.1','0.9.1.1'],values,color=[MUTED,BLUE]);ax.set_ylim(0,4100)
    for i,v in enumerate(values):ax.text(i,v+75,f'{v:,}'.replace(',','.'),ha='center',fontsize=9)
    ax.set_ylabel('Casi software distinti superati');ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    ax.set_title('Dimensioni delle raccolte: insiemi diversi',loc='left',fontweight='bold',color=DARK)
    save('06_test',fig)
    d=DATA['initial_benchmark'];fig,ax=plt.subplots(figsize=(7,3.1),layout='constrained')
    ax.bar(['Primo report','Report 14:28'],d['mean_seconds'],color=[MUTED,BLUE]);ax.set_ylim(0,105)
    for i,v in enumerate(d['mean_seconds']):ax.text(i,v+2,f'{v:.2f} s / {d["responses"][i]}/6 risposte',ha='center',fontsize=8)
    ax.set_ylabel('Secondi medi per turno');ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    ax.set_title('Due esecuzioni storiche, protocolli diversi',loc='left',fontweight='bold',color=DARK)
    save('07_benchmark',fig)
    print('Diagramma e grafici PNG e SVG creati:',8)

if __name__=='__main__':main()
