# Grafica senza logo e primo audit dei sogni — 6 ottobre 2026

Il marchio grafico Terra/stelle è stato rimosso da avvio nativo, intestazione, menu, chat vuota, etichetta assistente e voce. Rimane il nome ALLMA. La sfera della modalità vocale resta un visualizzatore di stato. Font Inter e palette esistenti conservati. Eliminati il widget CosmicPlanet e gli stili del logo inutilizzati.

## Problemi corretti nel percorso attivo

- Una parola («relazione») assegnava una confidenza arbitraria dell'85% e attivava apprendimento HIGH, cambiamenti della personalità e notifiche. Le generazioni diventano ora **ipotesi non verificate**: nessuna promozione automatica a fatti, ricordi personali o conferme del cache.
- In assenza di generazione il TreeOfThoughts restituiva l'input come insight; anche un'interruzione poteva conservare risultati parziali. Ora restituisce una lista vuota e scarta i risultati interrotti.
- Il controllo dell'attività utente avveniva soltanto prima della chiamata al modello. Il wrapper riceve ora un segnale di cancellazione controllato durante la generazione. Disattivazione sogni, pausa e chiusura richiedono l'interruzione; la chiusura attende brevemente il worker.
- Lo stato `is_dreaming` veniva impostato dentro il thread, permettendo avvii concorrenti e cambi dell'utente corrente. Ora l'ammissione è protetta da lock e prenota lo stato prima dell'avvio.
- Un errore del monitor prima del blocco protetto poteva lasciare il sistema bloccato nello stato sogno. Tutti gli esiti ripristinano lo stato e rilasciano il wake lock se acquisito.
- Il trigger manuale e quello lucido aggiravano i controlli di batteria e temperatura. Il percorso comune richiede monitor disponibile, alimentazione, batteria >=72% e temperatura batteria <=40 °C. Ricontrolla le condizioni prima di ogni esperienza; non è una misurazione continua della temperatura della CPU.
- Ogni ciclo elaborava un numero potenzialmente elevato di memorie, con tre passaggi per memoria. Ora esplora al massimo tre esperienze recenti, un passaggio ciascuna, con 128 token complessivi e 32 riservati al ragionamento per chiamata. Non equivale a una misura del risparmio energetico sul dispositivo.
- Le ipotesi in attesa erano volatili. La coda viene salvata atomicamente accanto al diario (`dream_journal.json.pending.json`), limitata a 50 elementi, associata all'utente e ripristinata all'avvio. Il diario ha un limite e viene letto tramite una copia protetta da lock.
- Le memorie candidate escludono altri utenti, ruoli assistente e record esplicitamente invalidi. Il percorso temporale cerca le ultime 24 ore e sceglie le tre esperienze più recenti.
- La generazione automatica di varianti di risposte apprese è sospesa finché manca una verifica di equivalenza: una parafrasi del modello non vale come nuova conferma dell'utente. Risposte apprese e dati preesistenti non vengono cancellati.
- Il messaggio di fine ciclo indica quante ipotesi sono state prodotte; non dichiara più un'evoluzione non misurata. Lo stato UI viene spento prima della pausa dello scheduler.

## Limiti emersi: lavoro successivo

1. TreeOfThoughts genera un singolo nodo per passo e usa uno score costante: non è ancora una ricerca con vere alternative e valutazione. Le riflessioni sono creative, non prove di deduzione o verità.
2. Manca un checkpoint delle esperienze già esplorate: gli stessi input possono essere riesaminati nei cicli successivi. La coda evita ipotesi identiche per lo stesso utente, ma non elimina il costo di rigenerazione.
3. La coda di verifica ora persiste, ma il percorso attivo non chiama `get_and_clear_pending_verification`: manca un flusso completo di revisione, rifiuto/conferma e consolidamento supportato da evidenze. Non viene simulato un apprendimento automatico in sua assenza.
4. Il servizio Android dichiarato in buildozer.spec è un percorso separato e obsoleto: usa un vecchio modello Qwen2.5 in un vecchio percorso e istanze di memoria proprie. Non è stata trovata una chiamata di avvio nel frontend attuale. Non va abilitato finché non condivide impostazioni, dati e gestione del modello con il percorso principale.
5. Il cosiddetto NREM non implementava una vera consolidazione: era una semplice pausa senza generazione. Ora il ciclo non parte senza le condizioni energetiche richieste; non viene presentato come un processo di consolidamento realmente implementato.
6. Le vecchie funzioni di curiosità e notifica restano codice legacy fuori dal ciclo attivo. Il sogno lucido ora usa il percorso comune; senza esperienze recenti non fabbrica una storia personale.
7. Lo scheduler controlla condizioni e attività, ma l'orario attuale esclude soltanto 07–09: non definisce da solo un riposo notturno o un intervallo minimo di inattività.
8. Eventuali conoscenze prodotte da vecchie versioni non sono state rimosse automaticamente: serve una migrazione basata sulla provenienza per evitare di cancellare dati validi.

## Verifica

Test di regressione con modello e sensori simulati: avvio esclusivo, interruzione per conversazione/disattivazione, scarto di risultati falliti, persistenza e separazione per utente, nessun apprendimento HIGH, soglia termica, limite delle chiamate e filtro delle memorie.

Anteprima nativa Kivy e chat nel browser controllate visivamente. APK compilata e verificata prima dell'aggiornamento con `install -r`, senza cancellazione dei dati. Esiti finali nei log in `analisi/2026-10-06/senza-logo`.

Non effettuato un ciclo onirico prolungato sul telefono: resta da misurare comportamento in inattività, temperatura, ripresa della conversazione e qualità delle ipotesi. I test simulati non dimostrano efficacia cognitiva o risparmio energetico reale.
