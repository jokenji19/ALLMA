# Continuità e pertinenza — 26 ottobre 2026

## Causa verificata e correzione

La richiesta «Il mio dubbio è questo: perché la Luna cambia forma durante il mese?» conteneva il possessivo *mio*. Il controllo obbligatorio della memoria lo interpretava come riferimento autobiografico, anche quando Decider proponeva di ragionare su conoscenza generale. Il recupero vuoto aggiungeva avvertenze sui ricordi. Istruzioni generiche su esperienze e stati personali non distinguevano inoltre esplicitamente le dichiarazioni di ALLMA da ciò che l'utente sta esprimendo nel messaggio attuale.

`task_content` riconosce alcune cornici conversazionali delimitate e usa la domanda effettiva per la scelta delle risorse. Il messaggio originale resta nel modello e nella cronologia. I riferimenti personali dentro la domanda mantengono il recupero obbligatorio, anche quando Decider propone di evitarlo. I test distinguono la domanda sulla Luna da quella sulla propria passeggiata o su qualcosa raccontato prima.

Il contratto identitario continua a richiedere eventi documentati per esperienze, preferenze e stati personali di ALLMA. Il messaggio attuale dell'utente è una fonte di ciò che sta esprimendo, senza diventare una verifica esterna della sua situazione.

## Memoria di lavoro del dialogo

Il sistema di continuità esistente ricava una vista temporanea dalla cronologia circoscritta all'utente e alla chat: richiesta, precisazione, conferma, approfondimento, correzione, continuazione, ripetizione richiesta, nuovo tentativo o dettaglio fornito dopo un chiarimento.

I metadati contengono modalità e impronte dei riferimenti. Non costituiscono un secondo archivio autobiografico né nuove prove per autorizzare azioni. Dopo un tentativo fallito, una conferma o un approfondimento si riferiscono alla domanda rimasta senza risposta, anziché al saluto o a una risposta valida più vecchia. Un nuovo argomento ha una nuova vista attiva.

## Risposte e ripetizioni

- Il controllo delle ripetizioni ammette conferme esplicite, riassunti, traduzioni e altre ripetizioni richieste. Ammette anche contenuto precedente seguito da informazioni nuove.
- Riconosce la riproposizione integrale di frasi già date anche quando vengono riordinate o precedute da un breve riempitivo. È un controllo di riuso testuale, non un classificatore universale di equivalenza semantica. Negazioni, numeri e nuovo contenuto non vengono ignorati.
- Una proiezione conservativa può omettere frasi autonome che commentano l'esecuzione delle istruzioni, come «Non ho verificato se l'utente ha detto di avere dubbi reali o solo ipotizzativi». Testi richiesti, citazioni, codice, JSON e clausole miste non vengono eliminati.
- Le frasi fattuali rimaste sono conservate senza riscrittura; non vengono certificate come vere. Streaming e testo salvato seguono la stessa proiezione.
- Una risposta modificata ha sorgente `model_excerpt`, conserva impronte delle frasi omesse e segnala che il candidato originale non era interamente valido. Non alimenta l'apprendimento automatico delle risposte o dello stile.
- Il formato viene validato sul testo effettivo: un commento estraneo non può riempire artificialmente il requisito di due frasi. Una risposta composta soltanto da commenti non viene presentata come risposta alla domanda.

## Verifiche

- **2.752 test desktop passati**, 15 saltati; i sei scenari di arresto improvviso sono eseguiti separatamente.
- 24 scenari sintetici condivisi fra desktop e Android. Comprendono recupero, ambito dei ricordi, continuità dopo un errore, conferme, correzioni del tema, estrazioni, formato e coerenza dello streaming.
- Diagnostica aggiornata a «Continuità del dialogo · 24 scenari e 5 turni»: apertura locale e quattro richieste al modello su spiegazione, conferma, precisazione e nuovo argomento. Il report conserva separatamente candidato, risposta consegnata, eventuale estrazione, stato del dialogo, tempi e condizioni del dispositivo.

## Risultato intermedio su Android — 102566

60/60 scenari generali e 24/24 scenari di dialogo superati. La conversazione completa è terminata e tutti i testi validi mostrati progressivamente coincidono con quelli salvati. Nei quattro candidati del modello non compaiono i commenti sulla verifica del dubbio; nessuna estrazione è stata necessaria.

Il primo turno sostanziale ha però violato il requisito di due frasi e conteneva una spiegazione errata delle fasi lunari. La risposta su Venere conteneva errori scientifici; quella sulle foglie era incompleta e imprecisa. Questi esiti non vengono conteggiati come correttezza semantica superata. I controlli software di ALLMA non sono un verificatore generale della conoscenza del modello.

Questa prova ha anche mostrato un riferimento di lavoro agganciato al saluto dopo un errore: corretto nella build 102567 e coperto da sei regressioni aggiuntive e dallo scenario Android `working_references`.

I risultati definitivi e la verifica dell'APK sono raccolti in `/Users/erikahu/ALLMA/analisi/2026-10-26/continuita_dialogo/`. Le percentuali delle batterie si riferiscono soltanto ai casi dichiarati; non misurano l'intelligenza complessiva di ALLMA. Il modello GGUF e i backend CPU/GPU/NPU restano quelli configurati.

## Discrepanza dello streaming emersa nella 102567

La prova richiesta sul dispositivo ha completato 60/60 scenari generali, 24/24 scenari di continuità e tutti e cinque i turni. Il riferimento della conferma era collegato alla domanda corretta. Tuttavia, in una risposta ammessa, il testo progressivo differiva da quello finale: il controllo conclusivo ha quindi segnalato un fallimento, senza dichiarare superato l'intero collaudo.

La riproduzione deterministica ha isolato una causa nel modulo espressivo: con `under_duress=True`, la modulazione successiva alla generazione accorpava i paragrafi. Il testo già trasmesso manteneva invece la separazione originale. Alcune trasformazioni espressive potevano inoltre togliere formule di incertezza come «mi sembra».

Nella build **102568** il modulo espressivo propone un'indicazione di tono prima della generazione. Le preferenze apprese dell'utente hanno priorità. La pipeline della chat valida il testo preservandolo: non applica modulazioni dopo la consegna e rifiuta una riparazione strutturale che richiederebbe una riscrittura silenziosa. La proiezione conservativa dei commenti estranei resta condivisa da streaming e risposta finale, con provenienza distinta.

Verifiche sui sorgenti aggiornati: **2.759 test passati nella suite**, **6 test separati di arresto improvviso passati**, **15 saltati**; totale **2.765 passati**. Coperti stato di stress, semplificazione, paragrafi, incertezza, preferenze esplicite e indisponibilità dell'indicazione di tono opzionale. I report di riproduzione prima/dopo sono conservati nella cartella delle analisi.

La prova della 102567 contiene ancora errori scientifici e affermazioni premature sul fatto che il dubbio dell'utente sia risolto. Questi rimangono difetti della qualità delle risposte, non vengono trasformati in successi software. La 102568 è compilata e verificata; il suo collaudo Android richiede il ricollegamento del telefono.

## Collaudo finale Android — 102568

La build **102568 è installata** sul Samsung SM-S938B. Il collaudo con archivi sintetici è terminato: **60/60 scenari generali**, **24/24 scenari di dialogo**, **5/5 turni completati**. Tutte e cinque le risposte ammesse coincidono con il testo trasmesso, ignorando soltanto gli spazi esterni: i paragrafi interni sono conservati. La riproduzione di `under_duress=True` passa anche nello scenario software eseguito sul dispositivo.

La conferma sulla Luna mantiene l'impronta della domanda precedente corretta; il cambio di argomento sulle foglie azzera il riferimento attivo. I casi di riferimento dopo una risposta fallita sono coperti dalla batteria sintetica. L'apertura «Bene, ma ho un dubbio» riceve la richiesta di precisazione senza inferenza in **32,6 ms** in questa singola prova. Il processo è rimasto attivo; il tempo di spegnimento dello schermo è stato riportato ai **60 secondi** iniziali. Nessuna conversazione personale è stata usata nel collaudo.

La qualità fattuale non è certificata: la prima risposta continua ad attribuire alla Terra un cambiamento di forma apparente nella spiegazione delle fasi lunari. Compaiono ancora affermazioni non richieste come «Il tuo dubbio è stato chiarito» e «Questa spiegazione è corretta». La risposta su Venere resta errata o incompleta. La correzione dello streaming non equivale alla soluzione di questi difetti.

### Backend effettivamente osservati

Il report e i log di avvio concordano: **Qwen usa CPU**, con motivo `previous_gpu_operation_incomplete`; **Decider usa Hexagon**. Il medesimo backend CPU era presente nei report 102566 e 102567. La protezione nativa ha rilevato un'operazione GPU precedente rimasta incompleta e ha selezionato il ripiego CPU. La causa dell'interruzione precedente non è determinata da questa prova: il marcatore, da solo, non dimostra un guasto della GPU. I risultati attuali non costituiscono una misura delle prestazioni OpenCL.

Evidenze finali: `android-results-102568.json`, `android-dialogue-report-102568.json` e `summary.json` nella cartella delle analisi indicata sopra. Rimangono **2.765 test desktop passati** e **15 saltati** per i sorgenti di questa build; nessuna modifica ulteriore al codice di esecuzione è stata necessaria durante il collaudo finale.
