"""Render the ALLMA paper and complete, privacy-conscious inventories.

Run after crea_grafici.py, using a Python environment with reportlab.
The stored CSV inventories make this step independent of private test logs.
"""
from pathlib import Path
import csv
import hashlib
import html
import json
import re
import unicodedata
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER,TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,PageBreak,
    Image,KeepTogether,CondPageBreak,Table,TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.utils import ImageReader

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FIGURES=ROOT.parent/'analisi/2026-11-12/paper/figure'
OUTPUT=ROOT/'output/pdf/ALLMA_STUDIO_0.8.4.2_0.9.1.1.pdf'
SNAPSHOT='c95708470db236b49810037bee343839ea5c91c3'
pdfmetrics.registerFont(TTFont('Inter',str(ROOT/'assets/web/fonts/Inter-Regular.ttf')))
pdfmetrics.registerFont(TTFont('InterSemi',str(ROOT/'assets/web/fonts/Inter-Semibold.ttf')))
pdfmetrics.registerFontFamily('Inter',normal='Inter',bold='InterSemi',italic='Inter',boldItalic='InterSemi')
available=set(pdfmetrics.getFont('Inter').face.charWidths)
navy=colors.HexColor('#16293d');blue=colors.HexColor('#2463ad');muted=colors.HexColor('#5e6e7e');line=colors.HexColor('#dbe3ed')

styles={
 'title':ParagraphStyle('paper_title',fontName='InterSemi',fontSize=27,leading=34,textColor=navy,spaceAfter=12),
 'subtitle':ParagraphStyle('paper_subtitle',fontName='Inter',fontSize=13,leading=19,textColor=muted,spaceAfter=13),
 'h1':ParagraphStyle('paper_h1',fontName='InterSemi',fontSize=15,leading=20,textColor=navy,spaceBefore=17,spaceAfter=7,keepWithNext=True),
 'h2':ParagraphStyle('paper_h2',fontName='InterSemi',fontSize=11.1,leading=15,textColor=blue,spaceBefore=11,spaceAfter=5,keepWithNext=True),
 'body':ParagraphStyle('paper_body',fontName='Inter',fontSize=9.4,leading=14.1,textColor=navy,spaceAfter=7,splitLongWords=True),
 'caption':ParagraphStyle('paper_caption',fontName='Inter',fontSize=8,leading=11,textColor=muted,spaceAfter=11),
 'index':ParagraphStyle('paper_index',fontName='Inter',fontSize=8,leading=11.4,textColor=navy,spaceAfter=3,splitLongWords=True),
 'tiny':ParagraphStyle('paper_tiny',fontName='Inter',fontSize=7.3,leading=10,textColor=navy,spaceAfter=1,splitLongWords=True),
 'toc':ParagraphStyle('paper_toc',fontName='Inter',fontSize=9.2,leading=14,textColor=navy,leftIndent=3,firstLineIndent=0,spaceBefore=3),
 'cover_small':ParagraphStyle('cover_small',fontName='InterSemi',fontSize=9,leading=13,textColor=blue,spaceAfter=10),
}

def clean(text):
    text=unicodedata.normalize('NFKC',str(text)).replace('\u00a0',' ')
    text=''.join('-' if unicodedata.category(c)=='Pd' else c for c in text)
    return ''.join(c if c in '\n\t' or ord(c)<128 or ord(c) in available else '' for c in text if c in '\n\t' or ord(c)>=32)

def markup(text):
    text=clean(text).replace('**','').replace('`','')
    text=html.escape(text,quote=False)
    # URLs are drawn as normal, selectable text and remain clickable.
    pattern=r'https?://[^\s<>]+'
    return re.sub(pattern,lambda m:'<link href="'+html.escape(m.group(0).rstrip('.,;'),quote=True)+'" color="#2463ad">'+m.group(0).rstrip('.,;')+'</link>'+m.group(0)[len(m.group(0).rstrip('.,;')):],text)

def rows(name):
    with (HERE/name).open(encoding='utf-8',newline='') as stream:return list(csv.DictReader(stream))

class Paper(SimpleDocTemplate):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.section_count=0
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and getattr(flowable,'toc_title',None):
            title=flowable.toc_title;key='sec-'+hashlib.sha1(title.encode()).hexdigest()[:15]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title,key,0,False)
            self.notify('TOCEntry',(0,title,self.page,key))

def page(canvas,doc):
    canvas.saveState();width,height=A4
    if doc.page>1:
        canvas.setStrokeColor(line);canvas.line(19*mm,height-16*mm,width-19*mm,height-16*mm)
        canvas.setFont('Inter',7.3);canvas.setFillColor(muted)
        canvas.drawString(19*mm,height-13*mm,'ALLMA  |  STUDIO RETROSPETTIVO')
        canvas.drawRightString(width-19*mm,height-13*mm,'0.8.4.2  -  0.9.1.1')
    canvas.setStrokeColor(line);canvas.line(19*mm,16*mm,width-19*mm,16*mm)
    canvas.setFont('Inter',7.3);canvas.setFillColor(muted)
    canvas.drawString(19*mm,11*mm,'Documento tecnico  |  12 novembre 2026')
    canvas.drawRightString(width-19*mm,11*mm,str(doc.page))
    canvas.restoreState()

def heading(text,style='h1',toc=True):
    p=Paragraph(markup(text),styles[style]);p.toc_title=clean(text) if toc else None
    return p

def figure(name,caption):
    path=FIGURES/(name+'.png');iw,ih=ImageReader(str(path)).getSize();w=170*mm;h=w*ih/iw
    image=Image(str(path),width=w,height=h)
    return KeepTogether([Spacer(1,3*mm),image,Paragraph(markup(caption),styles['caption'])])

FIGURES_AFTER={
 '2. Metodo, riproducibilità e qualità dell\'evidenza': [('06_test','Figura 1. Numero di casi software distinti superati nelle due raccolte. Le suite non coincidono: il grafico non misura il miglioramento generale di affidabilità. Fonti: RELEASE_V0.9.1.md e DIALOGO_CONTESTUALE_2026-10-29.md.')],
 '4. Architettura e autorità del sistema': [('00_architettura','Schema funzionale: le frecce rappresentano rapporti possibili fra responsabilità, non l’attivazione obbligatoria di tutti i moduli a ogni turno. I percorsi deterministici possono concludersi senza generazione del modello.')],
 '5. Persistenza, memoria e continuità': [('03_memoria','Figura 2. Apertura di un archivio sintetico di 4.096 unità: tre aperture per modalità, mediane sotto tracemalloc. MB di allocazioni Python, non RAM complessiva. Il tempo aumenta nella prova paginata. Fonte: PUNTI_4_8_2026-10-27.md.')],
 '12. CPU, GPU e NPU': [('01_gpu','Figura 3. Prototipo Qwen nativo su un Samsung SM-S938B: stessa continuazione guidata di 64 token, escluso il caricamento. Mediane: tre repliche per prompt 128 e due per prompt 512. Non è latenza della chat completa. Fonte: INTEGRAZIONE_OPENCL_2026-10-24.md.'),('02_npu','Figura 4. Decider sullo stesso dispositivo: mediana di due ripetizioni per gli otto casi brevi e per un caso lungo. Scala logaritmica. Non misura la durata totale delle risposte. Fonte: INTEGRAZIONE_NPU_DECIDER_2026-10-24.md.')],
 '13. Finestra di contesto e risposta iniziale': [('04_contesto','Figura 5. Percorso nativo Qwen, caso lungo: mediane di due sole repliche. Le finestre maggiori conservano prompt più lunghi; 8K contiene circa 4,1K token. Fonte: CONFRONTO_CONTESTO_REALE_102574.md.')],
 '14. Sessione lunga, risorse e cancellazione': [('05_cancel','Figura 6. Attesa dopo il segnale di annullamento: una singola coppia di richieste CPU con stesso prompt e seed. Scala logaritmica; non rappresenta il guadagno sulla generazione ordinaria. Fonte: PUNTI_4_8_2026-10-27.md.')],
 '16. Benchmark iniziale e limiti della misura': [('07_benchmark','Figura 7. Due report storici di sei richieste comunicati il 1 ottobre. Budget e condizioni differiscono; due risposte erano assenti nel primo report. Il confronto non identifica un effetto causale e non misura la qualità semantica. Fonte: MIGLIORAMENTI_PRESTAZIONI_2026-10-01.md.')],
}

def render():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    doc=Paper(str(OUTPUT),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=23*mm,bottomMargin=23*mm,
        title='ALLMA - Studio retrospettivo 0.8.4.2 - 0.9.1.1',author='Progetto ALLMA',
        subject='Architettura, valutazione, sicurezza, risultati e limiti')
    story=[Spacer(1,39*mm),Paragraph('STUDIO DI INGEGNERIA SPERIMENTALE',styles['cover_small']),
        Paragraph('ALLMA',styles['title']),
        Paragraph('Evoluzione di un’architettura cognitiva locale per Android',styles['subtitle']),
        Spacer(1,4*mm),Paragraph('Dalla baseline 0.8.4.2 alla release 0.9.1.1',styles['h2']),
        Spacer(1,12*mm),Paragraph('Memoria, apprendimento, dialogo, sicurezza, CPU, GPU e NPU',styles['body']),
        Paragraph('Risultati misurati, casi negativi, limiti e inventari completi delle evidenze disponibili',styles['body']),
        Spacer(1,20*mm),Paragraph('12 novembre 2026  |  Versione documentale 1.0',styles['caption']),
        Paragraph('Rapporto tecnico retrospettivo, non sottoposto a revisione paritaria.',styles['caption']),PageBreak(),
        Paragraph('Indice',styles['h1'])]
    toc=TableOfContents();toc.levelStyles=[styles['toc']];story.extend([toc,PageBreak()])
    active=None;buffer=[]
    def flush():
        if buffer:story.append(Paragraph(markup(' '.join(buffer)),styles['body']));buffer.clear()
    def add_figures():
        for name,caption in FIGURES_AFTER.get(active,[]):story.append(figure(name,caption))
    lines=(HERE/'ALLMA_STUDIO.md').read_text(encoding='utf-8').splitlines()
    for raw in lines:
        text=raw.strip()
        if text.startswith('# ') or text.startswith('## Studio '):continue
        if text.startswith('## '):
            flush();add_figures();active=text[3:].strip();story.append(heading(active));continue
        if text.startswith('### '):
            flush();story.append(heading(text[4:].strip(),'h2',False));continue
        if not text:flush();continue
        if re.match(r'^\d+\.\s',text):
            flush();story.append(Paragraph(markup(text),styles['body']));continue
        buffer.append(text)
    flush();add_figures()
    story.extend([PageBreak(),heading('Appendice A. Registro completo dei documenti'),
        Paragraph(markup('Documenti Markdown presenti nello snapshot '+SNAPSHOT+'. L’elenco comprende rapporti storici e proposte successive: una voce storica non prova che lo stesso stato sia ancora attuale. La tabella CSV associata conserva hash e URL di ogni documento. Gli archivi personali non sono riprodotti.'),styles['body'])])
    for item in rows('inventario_documenti.csv'):
        title=html.escape(clean(item['file']),quote=False);url=html.escape(item['url'],quote=True)
        text='<link href="'+url+'" color="#2463ad">'+title+'</link>  |  SHA-256 '+item['sha256'][:16]+'...'
        story.append(Paragraph(text,styles['index']))
        if item['sezioni']:story.append(Paragraph(markup('Sezioni: '+item['sezioni']),styles['tiny']))
    story.extend([PageBreak(),heading('Appendice B. Registro delle criticità e degli interventi'),
        Paragraph(markup('Registro ragionato delle 43 voci dei due audit e delle verifiche successive. Ogni stato si riferisce al perimetro dei casi documentati; le indicazioni aperte non sono garanzia che non esistano altri difetti.'),styles['body'])])
    for item in rows('registro_criticita.csv'):
        story.append(heading(item['id']+' - '+item['problema'],'h2',False))
        story.append(Paragraph(markup('Stato: '+item['stato']+'. Intervento: '+item['intervento']+'. Prossima verifica: '+item['prossima_verifica']+'. Fonte: docs/'+item['fonte']+'.'),styles['index']))
    story.extend([PageBreak(),heading('Appendice C. Inventario statico dei file Python'),
        Paragraph(markup('Per ogni file Python tracciato sotto allma_model nello snapshot: righe, classi e funzioni rilevate con AST. Sono inclusi 48 file nella directory tests. Questi numeri descrivono struttura statica, non raggiungibilità, copertura o operatività effettiva. Hash completi nel CSV allegato.'),styles['body'])])
    for item in rows('inventario_moduli.csv'):
        text=f"{item['file']}  |  {item['righe']} righe  |  {item['classi']} classi  |  {item['funzioni']} funzioni"
        story.append(Paragraph(markup(text),styles['tiny']))
    story.extend([PageBreak(),heading('Appendice D. Elenco delle modifiche rispetto alla baseline'),
        Paragraph(markup('Confronto fra la baseline e lo snapshot, senza rilevamento delle rinomine: un file spostato appare come rimozione e aggiunta. I file generati e gli archivi rimossi alterano i conteggi di righe; il volume del diff non è una misura di qualità. A=aggiunto, M=modificato, D=rimosso.'),styles['body'])])
    for item in rows('inventario_modifiche.csv'):
        story.append(Paragraph(markup(item['stato']+'  '+item['file']),styles['tiny']))
    story.extend([PageBreak(),heading('Appendice E. Registro dei casi software'),
        Paragraph(markup('3.314 casi distinti nelle verifiche combinate: 3.299 superati e 15 saltati. Le riesecuzioni sono consolidate per identificativo. Sono riportati gruppo, nome base, impronta breve e stato; i valori dei parametri e i log grezzi sono esclusi. L’impronta è un riferimento tecnico e non è una garanzia di anonimizzazione.'),styles['body'])])
    last=None
    for item in rows('inventario_test.csv'):
        if item['gruppo']!=last:
            last=item['gruppo'];story.append(heading(last,'h2',False))
        story.append(Paragraph(markup(item['id_caso']+'  '+item['test']+'  -  '+item['esito']),styles['tiny']))
    story.extend([Spacer(1,9*mm),Paragraph('Fine del dossier. I dati e i metodi dei grafici sono disponibili nei file allegati alla release.',styles['caption'])])
    doc.multiBuild(story,onFirstPage=page,onLaterPages=page)
    print('PDF creato:',OUTPUT)

if __name__=='__main__':render()
