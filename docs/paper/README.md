# Studio scientifico e dossier tecnico di ALLMA

`ALLMA_STUDIO.md` è il testo modificabile del rapporto. I sette grafici sono generati da `misure.json`; un ulteriore diagramma rappresenta l'architettura. I file SVG in `grafici/` sono esportabili. Il PDF finale comprende il testo, le figure e cinque appendici con documenti, criticità, file Python, modifiche e casi di test.

Gli inventari descrivono lo snapshot `c95708470db236b49810037bee343839ea5c91c3`, successivo al tag della build `a3cfc33f4bbc4688bd7a3ad0e252a5a904707094`. I percorsi applicativi non cambiano fra i due commit. I documenti storici sono collegati al commit fissato; non tutte le loro conclusioni intermedie descrivono la versione finale.

## Riprodurre le figure e il PDF

Da questa cartella di progetto, con Python e `matplotlib` disponibili: `python3 docs/paper/crea_grafici.py`. Con Python e `reportlab` disponibili: `python3 docs/paper/crea_pdf.py`. Il risultato è in `output/pdf/ALLMA_STUDIO_0.8.4.2_0.9.1.1.pdf`. I PNG intermedi vengono scritti in `../analisi/2026-11-12/paper/figure/`; gli SVG sono in questa cartella.

Gli inventari CSV sono già inclusi, quindi per ricreare il PDF non occorrono i log di test. `crea_inventari.py` può ricrearli solo su una macchina che possieda le evidenze JUnit locali: i parametri dei test vengono sostituiti da impronte brevi. La presenza di un modulo nell'inventario è un dato statico e non dimostra che sia eseguito. Il report non comprende conversazioni personali, log grezzi o pesi dei modelli.

Il registro delle 43 criticità è curato separatamente in `crea_registro.py`, e rimanda ai rapporti storici. Le voci chiuse sono limitate ai casi di test riportati; ogni voce conserva una verifica successiva o un limite aperto.

Per cambiare lo snapshot dello studio occorre riesaminare documenti e misure, aggiornare il manoscritto, i commit, gli inventari e i dati dei grafici: non basta cambiare automaticamente il numero di versione.
