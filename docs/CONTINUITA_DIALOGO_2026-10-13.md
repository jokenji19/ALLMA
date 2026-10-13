# Continuità del dialogo — 13 ottobre 2026

Intervento sulla ripetizione identica osservata dopo «Bene, tu?» e dopo la correzione dell'utente.

## Comportamento

Il contesto ora richiede di proseguire dal turno corrente, usare le informazioni già date, evitare nuovi saluti e domande già soddisfatte, limitare orario e dati tecnici alle richieste pertinenti. Quando riconosce una segnalazione esplicita di ripetizione, richiede di accogliere la correzione e di rileggere la cronologia senza inventare dettagli.

Il nuovo DialogueContinuity confronta il testo normalizzato con l'ultima risposta valida della stessa conversazione e dello stesso utente. Blocca duplicati lunghi quando la richiesta cambia, mantenendo ammesse richieste identiche, ripetizioni esplicite, traduzioni e riscritture. Le risposte brevi identiche, come numeri o sì/no, sono ammesse. Per una correzione esplicita la soglia è più bassa.

Lo streaming trattiene soltanto un prefisso che coincide con la risposta precedente; appena diverge rilascia le frasi disponibili. Un duplicato integrale non viene visualizzato. Il risultato rifiutato ha status=dialogue_repetition e is_valid=False, viene escluso dall'apprendimento e dalla cronologia utile delle risposte future. Anche il recupero di una risposta confermata passa il controllo prima dell'uso. L'archivio precedente non viene cancellato.

La prima prova sul telefono ha mostrato «Come ti va?» dopo «Bene, tu?», quindi è stato aggiunto un controllo circoscritto alle domande sul benessere nei sei turni recenti. Riconosce varianti brevi come «Come stai?», «Come ti senti?» e «Come ti va?», senza classificare «Come va il progetto?» come domanda sul benessere. Se quella domanda è già stata affrontata, la risposta finale viene validata integralmente prima della visualizzazione. Richieste esplicite di rifare la domanda, esempi, riscritture e citazioni restano ammesse. Il controllo non interpreta ogni sinonimo o cambio reale dello stato dell'utente; non sostituisce una comprensione semantica generale.

Nessuna seconda generazione, retry, chiamata esterna o modifica dei pesi GGUF. Il prompt è leggermente più lungo: non si può promettere un aumento della velocità. Il controllo non prova che il modello abbia compreso la correzione e non rileva tutte le ripetizioni semantiche con parole diverse. Una risposta lunga identica legittima a richieste formulate diversamente può essere rifiutata: è un limite conservativo da valutare su conversazioni nuove.

## Verifica

38 test mirati superati: duplicato non mostrato né appreso, guida alla correzione presente nel prompt, singola generazione, richieste di ripetizione/riscrittura/traduzione e numeri identici preservati, rilascio dello streaming dopo divergenza. La prima raccolta della suite completa nel sandbox si è interrotta nell'import nativo PyTorch; riesecuzione locale offline fuori sandbox: **800 superati, 15 saltati, 4 warning**, 157,76 s.

APK compilata e verificata, payload_matches=true, arm64-v8a. SHA256: `9205eaaed3ecdeaad754bbfed9a542b4927ee243a0d0de43df7b790f4f5f039c`.

Installazione `adb install -r` riuscita mantenendo i dati; hash sul telefono identico; app avviata, processo 19051. Prova della conversazione sul telefono in attesa del messaggio manuale dell'utente.

Nella prima prova reale il modello ha ancora riproposto la domanda sul benessere con parole diverse, ripetendola dopo un successivo «Bene». Questo ha motivato il controllo aggiuntivo sopra descritto; non viene conteggiato come successo generativo. Dopo l'aggiunta passano 42 test mirati; aggiunto anche un caso che preserva la richiesta esplicita di chiedere di nuovo. Suite completa finale: **805 superati, 15 saltati, 4 warning**, 140,27 s.

Seconda build finale verificata e installata con `-r`, hash sul telefono corrispondente: `a54aca82070097fc636f33df7c420c8f27c49a7cb2a1e6a0a00c1ce2b8332c9d`. Processo 23463, modello caricato e due risposte reali completate senza traceback nei log esaminati.

Nella nuova conversazione `8eb3199e-e921-4539-8420-ce9899a4e44a`, dopo il saluto e «Bene, tu?» il modello non ripropone la domanda sul benessere. Non è stato necessario il messaggio di blocco. Restano un saluto superfluo, una presentazione generica e una chiusura mal formulata. Alla successiva domanda «Cosa sai fare» risponde al nuovo argomento, senza duplicare integralmente il messaggio precedente, ma riusa una chiusura simile. Questa ripetizione parziale non è intercettata dal confronto integrale: resta un limite.

I tempi osservati sono 32,86 s e 19,87 s, con batteria rilevata 42,7–43,4 °C e dispositivo in carica: nessun miglioramento delle prestazioni dimostrato. In entrambi i casi il controllo sul benessere già affrontato forza la verifica della risposta completa; questo aggiunge attesa visibile rispetto allo streaming progressivo ed è una scelta protettiva circoscritta alla finestra recente. La correzione esplicita suggerita all'utente non compare ancora nella nuova conversazione esaminata, quindi il suo esito nativo resta da verificare. I test automatici ne verificano guida e blocco dei duplicati; non garantiscono una formulazione naturale del modello reale.
