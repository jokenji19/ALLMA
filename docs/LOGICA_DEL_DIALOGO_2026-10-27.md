> Aggiornamento: il collaudo del 28 ottobre e la build successiva sono documentati in [Collaudo logica del dialogo](COLLAUDO_LOGICA_DIALOGO_2026-10-28.md). Le informazioni di installazione sotto descrivono lo stato del 27 ottobre.

# Logica del dialogo e revisione delle risposte — 27 ottobre 2026

## Problema osservato

Nella conversazione recente, ALLMA ha riproposto lunghi passaggi già generati, anche dopo una richiesta di approfondimento. Sono presenti affermazioni storiche errate e formule sulla verifica delle fonti ripetute al posto di contenuti utili. In un seguito il testo cambiava introduzione, mantenendo quasi tutto il corpo precedente. La soglia di somiglianza esatta non copriva questo caso.

Il controllo precedente poteva rilevare un problema a generazione terminata e sostituire la risposta con una frase tecnica in prima persona. Rilevare l’errore e rispondere alla domanda erano due percorsi separati.

La lettura ha riguardato la conversazione visibile e i log tecnici disponibili. Nessuna esportazione completa dell’archivio personale, nessuna modifica ai messaggi storici.

## Percorso introdotto

1. Gli strumenti esatti e i richiami documentati continuano a essere eseguiti dal sistema ALLMA. In assenza di Decider, una forma esplicita di spiegazione generale non avvia automaticamente il recupero personale; richieste personali e riferimenti ambigui conservano la ricerca nei ricordi. Le prove includono il recupero semantico di un oggetto descritto con parole diverse.
2. Uno spazio di lavoro temporaneo rappresenta richiesta attuale, scopo del turno e domanda dell’utente cui si riferisce un approfondimento. Segue anche una catena di richieste brevi fino al soggetto originario.
3. Negli approfondimenti il prompt conserva l’ultima risposta per sapere cosa è già stato detto e la domanda originaria come riferimento. Gli altri turni restano nell’archivio, senza essere riproposti in blocco al modello.
4. La valutazione verifica identità, attribuzione delle esperienze, formato, ripetizioni, fonte dichiarata e avanzamento rispetto al turno precedente. Il riutilizzo richiesto, le conferme e i risultati brevi identici restano possibili.
5. Un candidato che non completa il compito può ricevere **una revisione mirata**, con lo stesso modello e i dati disponibili. Il prompt della revisione non contiene il testo scartato né vecchie affermazioni del modello come prove. Può produrre una nuova risposta o chiedere il dato specifico che manca.
6. Dopo la revisione vengono ripetuti i controlli. Il testo scartato non entra nell’apprendimento. Una revisione accettata prosegue nello stesso percorso di archivio, riscontri e apprendimento delle altre risposte del modello: viene osservata come candidato, con le conferme ancora necessarie al recupero automatico. Non diventa un fatto verificato per il solo fatto di essere stata rielaborata.
7. Se il turno resta irrisolto, la sua registrazione contiene esito e metadati, senza una battuta preconfezionata attribuita ad ALLMA. L’interfaccia mostra uno stato tecnico discreto e permette di modificare la domanda. La voce non legge esiti non validi.

Gli approfondimenti e le correzioni attendono la revisione completa prima della pubblicazione. Le normali risposte valide richiedono una sola generazione. La revisione aggiunge latenza soltanto quando viene eseguita; ha un limite di token, un tetto di ammissione rispetto all’attesa già trascorsa e rispetta cancellazione e protezioni termiche. I benchmark comparativi esistenti conservano il contratto di una richiesta per caso.

## Origine e osservabilità

La voce Origine distingue una risposta generata normalmente da una **rielaborata dopo un controllo**. Non attribuisce alla revisione una certificazione dei fatti. I metadati `turn_review` registrano scopo, impronte dei riferimenti, problemi rilevati, tentativi ed esito. I log tecnici non contengono il testo scartato.

Gli eventi della visualizzazione del cervello seguono le reali fasi di modello e controllo. Lo spazio di lavoro viene ricostruito dalla storia: non introduce un nuovo archivio autobiografico concorrente.

## Limiti da misurare

Questa integrazione permette ad ALLMA di governare un ciclo di riesame. La valutazione disponibile non riconosce ogni errore scientifico o ogni parafrasi ripetuta. Una risposta che supera i controlli può essere fattualmente sbagliata. La revisione usa lo stesso modello e può fallire; la qualità richiede una lettura delle risposte effettive.

I limiti termici possono impedire una seconda generazione. La cronologia precedente resta documentata, con i suoi eventuali errori: non viene riscritta per apparire corretta.

## Evidenze

Directory di lavoro: `/Users/erikahu/ALLMA/analisi/2026-10-27/logica-dialogo`.

Verifiche finali: **3,067 test superati**, 15 saltati, nessun fallimento o errore residuo nei risultati finali. Il totale conta casi distinti per classe/nome, senza sommare le ri-esecuzioni. La suite è stata eseguita in 16 gruppi di processi isolati e i casi modificati sono stati rieseguiti. L’esecuzione monolitica interrotta/arrestata non è considerata superata. Gli esiti iniziali restano nei log.

Controlli JavaScript separati: 12 per lo stato irrisolto/modifica domanda, 11 per cancellazione e 11 per continuazione. Sono controlli dell’interfaccia in ambiente simulato, non un’ispezione visiva Android.

Il percorso voce è verificato anche nei casi senza risposta e con eccezione: nessuna lettura del testo scartato, rilascio del turno e ritorno dell’interfaccia in attesa. Una revisione valida può ricevere il riscontro dell’utente e diventare un candidato al recupero; la bozza scartata non viene registrata fra le risposte apprese.

**APK 102582, versione 0.9.1, compilata e verificata**. Il codice versione è confermato leggendo il manifest dell’APK. I 10 sorgenti/asset controllati corrispondono al payload; motori nativi e asset di avvio risultano coerenti. SHA-256: `cd58009ec8619afed82edd1dc472e4c0ef5a3d74a36407acf976a49c655a3c84`.

**Non installata sul telefono in questo intervento:** il controllo finale ADB non rileva alcun dispositivo. La prova del modello reale resta da eseguire; non viene dedotta dai test con modelli simulati. È disponibile il profilo «Dialogo e revisione · 4 scenari»: tre turni naturali e un caso che inietta esplicitamente una bozza ripetuta, facendo eseguire la revisione al modello reale. Eventuali revisioni aumentano il numero di inferenze rispetto ai quattro scenari. Usa archivi sintetici separati, conserva modello/backend selezionati e richiede valutazione umana dei contenuti.

Modifiche salvate localmente. Nessun commit o caricamento GitHub eseguito in questo intervento. Evidenze riassunte in `final-summary.json`, `test-summary.json`, `source-pack-check.json`, `apk-package.txt` e nei rapporti dei test della directory di lavoro.
