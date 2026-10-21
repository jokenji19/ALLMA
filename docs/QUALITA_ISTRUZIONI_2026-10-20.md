# Qualità delle risposte: istruzioni e formato — 20 ottobre 2026

Il controllo del formato ora considera il comando a cui il vincolo appartiene. Una parola nell’argomento della domanda non sceglie più da sola la grammatica della risposta. La correzione appartiene ad ALLMA e resta indipendente dal modello linguistico collegato.

## Problemi corretti

- «Il testo JSON contiene quattro lettere? Rispondi solo sì o no» richiede sì/no, non JSON.
- «Rispondi solo con un numero: quante lettere contiene JSON?» richiede un numero. Le parole JSON, numero e sì/no presenti nei dati non sostituiscono il comando.
- Istruzioni citate con virgolette, caporali o backtick, anche con caratteri di escape e su più righe, restano dati da discutere. Vengono riconosciute le opzioni letterali «sì» e «no» in una vera richiesta di scelta.
- Negazioni circoscritte come «Non usare JSON, ma rispondi solo con un numero» non eliminano il successivo comando positivo.
- «Anzi, solo un numero» può sostituire una precedente richiesta esplicita di JSON nello stesso messaggio. Vincoli diversi e incompatibili, privi di una revisione esplicita, non vengono risolti scegliendo arbitrariamente una grammatica.
- Forme dirette come «Rispondimi», «Puoi rispondermi», «Potresti rispondere» e alcuni equivalenti inglesi possono attivare i vincoli supportati.
- Una richiesta di aggiungere una spiegazione non viene trattata come output esclusivamente numerico solo perché contiene la parola «solo».

Non vengono introdotte risposte preconfezionate ai quesiti né tentativi automatici aggiuntivi. Il ragionamento del modello e i controlli di attribuzione rimangono separati. Il riconoscimento è deliberatamente delimitato: numero, sì/no e JSON, con contesto locale dei comandi. Non è un interprete universale di ogni istruzione naturale e, nei casi non riconosciuti o conflittuali, non impone una nuova grammatica. La validità sintattica del JSON non dimostra correttezza dei valori né conformità a qualunque schema richiesto.

Lo stesso criterio viene usato nella generazione, nella validazione e nel richiamo delle risposte confermate. Le risposte nel formato errato non vengono ammesse all’apprendimento né pubblicate come risposte valide. Una risposta corretta non viene ritagliata o riscritta per farla passare.

## Misure e verifiche

Prima della modifica sono stati fissati 36 casi: **12 superati e 24 falliti**. Con i sorgenti finali passano tutti e 36: 24 condizioni recuperate, nessuna regressione in questo campione di sviluppo. Il piano, i sorgenti delle prove iniziali e gli esiti sono conservati separatamente. Il passaggio dal 33,3% al 100% riguarda questi casi noti e non è una percentuale d’intelligenza o di affidabilità globale.

- **391 test di integrazione superati**: core, generazione, ragionamento separato, vincoli, flusso progressivo, continuità, apprendimento e richiamo. Le prove del core usano un generatore simulato; non misurano l’abilità del GGUF.
- **60/60 scenari operativi standard** sul Mac, dati sintetici e modello simulato.
- Controllati anche **93 messaggi dei benchmark già presenti**: nessun cambiamento nel formato precedentemente riconosciuto. Durante il lavoro è stata intercettata e corretta una regressione su «un oggetto JSON» prima della consegna.
- Le prove nuove aggiungono turni reali del core: selezione del vincolo corretto, emissione singola della risposta ammessa, mancata pubblicazione/apprendimento di un oggetto JSON quando l’utente richiede sì/no e persistenza del richiamo di una risposta corretta.
- Costo indicativo sul Mac, mediana di cinque giri sugli stessi 36 messaggi: circa **3,92 μs prima e 7,40 μs dopo** per riconoscimento. Il controllo è più articolato e costa circa 3,5 μs aggiuntivi nel campione. Non si tratta di un’accelerazione della generazione. Un testo sintetico di 75.000 caratteri con 100 comandi viene esaminato in circa 6,5 ms; i contesti cercati sono limitati per evitare scansioni quadratiche dell’intero testo precedente.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-20/qualita-istruzioni`. I conteggi dei ricontrolli non si sommano come nuovi casi distinti.

La correttezza fattuale delle nuove risposte del modello resta da misurare sul dispositivo. Questo intervento elimina errori del sistema di controllo: non modifica i pesi del modello e non dimostra un miglioramento percentuale della sua intelligenza. Nessun nuovo commit, push o rilascio GitHub in questo intervento.

## Consegna Android

Build **102529** compilata, verificata e installata senza disinstallare l’app. Le impronte del nuovo controllo del formato e degli altri componenti verificati sul telefono coincidono con i sorgenti locali. Modello, WebView e transizione di avvio risultano pronti; nessuno degli indicatori tecnici di errore cercati è presente nel controllo di avvio. Non sono state copiate le conversazioni personali.

SHA-256 APK: `99707f4b8fe71bb144e9eb847b5ca75ef97e6d7ca4a8d346d303baad4315afc4`. Richiesta una prova manuale di due domande nuove nella chat per osservare il GGUF reale; gli esiti non sono ancora disponibili e non vengono considerati successi. La verifica Android effettuata qui riguarda installazione e avvio, non l’esecuzione sul telefono dei 391 test Mac.

## Esito della prova con modello reale

L’utente ha riferito «sì» al primo quesito e «26» al secondo. I log permettono di riconoscere entrambe le richieste: nella prima «si» era scritto senza accento. Sono due generazioni della stessa conversazione. Formato **2/2**; correttezza delle risposte riferite **1/2**. Questi due casi non stimano l’affidabilità generale.

La seconda generazione dura 20,45 s, con attesa iniziale di 17,89 s, e termina con `stop`: non risulta un taglio al limite. Il controllo numerico ammette 26 perché non verifica il conteggio. Il percorso aritmetico esatto non riconosce questa operazione testuale; la riproduzione della pipeline lascia invariato il candidato 26. Non sono stati copiati il prompt completo o la cronologia personale. Il candidato grezzo della generazione normale non è conservato.

Il risultato rivela una lacuna distinta dal difetto di formato appena corretto: occorre un’operazione generale verificabile di conteggio su testo esplicito. Le risposte non verificate del modello restano escluse dalla conoscenza incrementale verificata; il richiamo di risposte confermate conserva la propria soglia di conferme. Nessun nuovo cambiamento al codice applicativo o APK durante questa analisi.
