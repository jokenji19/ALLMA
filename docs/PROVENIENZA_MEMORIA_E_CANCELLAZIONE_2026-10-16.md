# Provenienza dei ricordi e cancellazione dei turni — 16 ottobre 2026

## Problemi osservati

La build 102483 ricorda LUNA-483 anche dopo riavvio del processo e nuova chat, ma risponde «in questa sessione». Il prompt recuperava le dichiarazioni senza conservare esplicitamente la distinzione fra chat corrente e conversazione di origine.

Nel primo tentativo di quella prova il WebView invia `cancel_generation` circa 1,4 s dopo la domanda. Il decisore termina come cancellato; non si tratta di un crash o di un errore di recupero. I log non permettono di attribuire il gesto a una persona o all’automazione: nessuna causa specifica è stata dimostrata. Invio e interruzione occupano però la stessa zona del compositore e il vecchio comando di annullamento non identificava il turno.

## Modifiche della build 102484

- Il prompt di memoria conserva per ciascuna delle due dichiarazioni compatte la provenienza: conversazione corrente, conversazione precedente oppure origine non disponibile. Non mostra UUID al modello e non inventa date.
- I testi sono serializzati come dati JSON e descritti come dichiarazioni dell’utente, non istruzioni o fatti verificati. La distinzione resta nel prompt nativo e in quello legacy.
- La pressione su Invia non sposta preventivamente il focus dal campo: evita che il compositore si riposizioni prima del click a causa della chiusura della tastiera. Il campo viene comunque sfocato quando la funzione di invio viene eseguita.
- Per un click da puntatore su Interrompi, la pressione deve essere iniziata sul pulsante per la medesima richiesta attiva. Pointer cancel disarma il gesto; tastiera e attivazione accessibile senza puntatore restano ammesse.
- Interruzione disabilitata finché il backend non ha assegnato l’identificativo della richiesta, durante una nuova chat e dopo il primo comando di cancellazione. Nessun ritardo temporale arbitrario.
- Il comando contiene `request_id`. Il backend controlla identificativo e tipo sotto il lock della sessione prima di cancellare. Un comando obsoleto, duplicato o senza identificativo non ferma la generazione né STT/TTS del turno corrente.
- La nuova chat conserva la cancellazione e l’attesa del rilascio del modello. I chiamanti interni di ChatSession possono ancora annullare direttamente il turno in fase di chiusura.

Queste protezioni non impediscono una pressione intenzionale e distinta su Interrompi. Non dimostrano retroattivamente l’origine dell’annullamento osservato. Le istruzioni di provenienza migliorano l’informazione disponibile al modello, ma non garantiscono che ogni sua formulazione sia corretta.

## Test e artefatti

Risultati salvati in `/Users/erikahu/ALLMA/analisi/2026-10-16/provenienza-interruzione/`.

- 112 test Python mirati passati; includono sessione, core delle azioni, memoria, decisore, continuità, fonti e asset.
- Due test ulteriori del ramo reale del gestore WebView passati: cancellazione obsoleta/senza ID e nuova chat durante un turno.
- 11 controlli JavaScript della cancellazione passati e 11 dei comandi di continuazione passati. Esecuzione Node VM, senza navigazione browser o accesso alla WebView.
- Sintassi Python e JavaScript verificata; `git diff --check` senza errori.

- Suite ampia del core: 171 test passati in 49,93 s, comprendenti persistenza cognitiva, benchmark, sogni, selezione modelli ed evoluzione emotiva. Include i due nuovi casi che verificano la provenienza nel prompt nativo e i precedenti casi del ciclo di memoria.
- APK 102484 compilata e verificata: payload coerente, runtime ARM64 llama-cpp-python 0.3.36, supporto qwen35. SHA256 `1b571330b64b4abb8a4eb16b99f483942e56b585f3ded955fe20dff8ffddd31d`.

Installazione `adb install -r` completata con Success; sul telefono confermato versionCode 102484. Nuovo processo 8412: inizializzazione nativa e caricamento del modello riusciti. Durante la preparazione del collaudo visivo il telefono è passato al pannello impostazioni Android; richiesta disponibilità dell’interfaccia prima di inviare nuove domande. Le prove live della formulazione e dell’annullamento di questa build restano da completare; non sono sostituite dai test automatici.

## Ulteriore difetto emerso dal collaudo e correzione 102485

Il primo invio dalla tastiera aperta nella 102484 è arrivato al core con un solo tocco e senza cancellazioni registrate. Tuttavia la domanda di richiamo, nella nuova chat senza messaggi precedenti, riceve una risposta che non restituisce LUNA-483. Esito negativo conservato in `android-provenance.json`: non viene dichiarata superata la prova della nuova formulazione.

Analisi e riproduzione: quando una domanda identica viene memorizzata più volte, ha similarità massima con la query successiva e può occupare i tre risultati ammessi; il prompt ne usa due. La dichiarazione originaria può rimanere esclusa. Riprodotto in un database sintetico con dodici domande identiche; il caso fallisce con la selezione ordinaria.

La build 102485 aggiunge `exclude_query_replays` al recupero. Il filtro, applicato prima del limite dei risultati sia nel motore vettoriale sia nel fallback TF-IDF, esclude soltanto una vecchia domanda identica alla domanda corrente. Non elimina record, non esclude tutte le domande e conserva dichiarazioni ripetute e valori differenti. Non certifica la rilevanza semantica di tutti gli altri risultati.

Corretto inoltre l’adattatore del fallback per ammettere punteggi numerici reali NumPy finiti e normalizzarli a float, continuando a rifiutare booleani e valori non validi. Il prompt distingue l’attribuzione di una dichiarazione dell’utente dalla verifica indipendente del suo contenuto: per riferire un codice dichiarato dall’utente non occorre una verifica nel mondo esterno.

Il tentativo della prova di cancellazione sulla 102484 non è valido: al momento dell’interazione il telefono era passato a un’altra app. Nessun esito positivo di cancellazione Android è dichiarato. Le protezioni sono coperte dai test automatici; serve ancora il collaudo live.

### Verifica finale e installazione 102485

- Suite aggiornata: 181 test passati in 90,97 s.
- Selezione mirata: 114 test passati in 0,47 s; comprende casi già verificati in altre selezioni, non sommare automaticamente.
- 27 test di recupero/persistenza/provenienza passati dopo aver ristretto il filtro alle sole domande identiche alla query.
- Un ulteriore test di integrazione del core con database vettoriale reale e dodici domande ripetute è passato: il dato LUNA-483 e la provenienza precedente raggiungono il prompt nativo. Questo test verifica il contesto fornito, non la qualità di una generazione reale.
- 11 controlli JavaScript di cancellazione e 11 di continuazione passati.
- Installazione della 102485 completata con Success, versione verificata sul telefono. SHA256 `485e538aea265000dd56903bf168c3856a92d1b4e5815aba5cb3a147d3b09919`; payload corrispondente ai sorgenti, ARM64 e supporto qwen35 verificati.

Richiesto al proprietario di eseguire direttamente i due casi finali (richiamo in nuova chat e Interrompi volontario), per evitare sovrapposizioni con altri usi del telefono. La prova live della 102485 è distinta da quella negativa della 102484 e dai test automatici.

### Esito reale 102485 e diagnostica 102486

Anche il richiamo nella nuova chat della 102485 fallisce: il modello afferma di non avere ricevuto il codice. L’esito è conservato in `android-provenance-final.json` e non viene sostituito con una risposta corretta. Decider si astiene, il ciclo restituisce tre risultati; il conteggio non dimostra quali testi abbiano raggiunto Qwen. Il controllo dei soli messaggi sintetici conferma che dichiarazione originale e domande appartengono allo stesso utente (confronto tramite hash), quindi in questo caso non emerge un cambio di proprietario dei dati.

Per evitare ulteriori modifiche al prompt senza evidenza, la 102486 aggiunge `decision.memory_evidence`: hash SHA256 dei tre record selezionati, provenienza corrente/precedente/sconosciuta e indicazione dei primi due previsti nel prompt. Non vengono registrati i testi né gli UUID delle conversazioni in questa telemetria. Gli hash consentono confronto con la dichiarazione sintetica attesa; non costituiscono anonimizzazione o prova della correttezza di un contenuto. Il dato sintetico atteso ha SHA256 `41e818a63a7f96ecacbdc6f6ac73c8debb5b9c562c5b121426494cf0aa89a57e`.

102486: 30 test mirati passati e quattro integrazioni del core passate; la precedente suite ampia finale della correzione del recupero ha passato 181 test. L’ultima aggiunta riguarda soltanto telemetria di provenienza, senza nuovo retry o modifica delle soglie del modello. APK verificata e installata con Success: SHA256 `2758a1d3466a1d1a208b2b40069c17de12c94603adffea3053bb72edb03c92ff`. Richiesto un solo ulteriore richiamo per distinguere errore di selezione da dato ricevuto e ignorato dal modello.

Nei log della prova precedente non compare ancora un comando di cancellazione per la descrizione della città; richiesta conferma all’utente di aver premuto Interrompi. Non dichiarato riuscito un test senza quell’evidenza.

### Collaudo 102486 completato per il richiamo

Nuova chat `1da049a2-189b-4976-a2a4-1cbf766240a4`, zero messaggi precedenti. La risposta restituisce LUNA-483 e non attribuisce il dato alla sessione corrente. L’hash della dichiarazione originale compare al primo posto con `provenance=previous` e `included_in_prompt=true`. Il ciclo di memoria richiede 37,36 ms, Qwen genera in 17,365 s; Decider si astiene e richiede 6,995 s compreso il caricamento. Report completo: `android-evidence.json`.

Questo è un risultato positivo singolo, non una dimostrazione di affidabilità stabile. La 102486 aggiunge soltanto telemetria rispetto alla 102485: il passaggio da risposta sbagliata a corretta non va attribuito a quella telemetria come se fosse un miglioramento cognitivo. I seed e le conversazioni differiscono, e le precedenti prove non registravano gli hash dell’evidenza. Rimane da valutare sistematicamente la fedeltà di Qwen ai ricordi forniti.

L’utente conferma di aver ripetuto la domanda e non ricorda esattamente quando abbia premuto Interrompi. Nessun comando di cancellazione relativo alla descrizione della città risulta nei log selezionati: prova live dell’interruzione non conclusiva. Al termine del richiamo il telefono ha spento lo schermo; non sono state inviate altre richieste o pressioni. L’APK 102486 rimane installata, con dati conservati. Nessun commit/push effettuato.
