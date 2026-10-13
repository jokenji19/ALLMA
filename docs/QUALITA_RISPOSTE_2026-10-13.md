# Qualità delle risposte — 13 ottobre 2026

Intervento sulle priorità emerse dal benchmark Rapida: formato esplicito, distinzione fra esperienza dell'utente e ALLMA, correttezza e attesa iniziale.

## Modifiche

- La generazione finale può essere vincolata tramite grammatica nativa a sì/no, numero o JSON quando il messaggio richiede esplicitamente quel formato. Il ragionamento precedente resta libero. Il vincolo JSON garantisce la sintassi, non uno schema o la verità dei valori.
- Un controllo conservativo rileva alcune risposte in prima persona che copiano le esperienze dichiarate dall'utente. Queste risposte vengono segnalate come non valide, escluse dall'apprendimento e bloccate anche nel recupero di vecchie risposte confermate. Non vengono riscritte silenziosamente né rigenerate con retry.
- Lo stesso controllo protegge le frasi durante la visualizzazione progressiva. Citazioni e richieste di riscrittura sono escluse; il controllo lessicale non copre ogni errore semantico e può avere falsi positivi o negativi.
- Le richieste brevi di numero o sì/no hanno un budget di ragionamento di 32 token, mantenendo i budget superiori per i casi complessi. Non è un incremento dimostrato della velocità generale.
- Nuove metriche distinguono attesa del lock e preparazione del prompt. Corretto il rilevamento del livello batteria nel benchmark.
- Il prompt richiede di verificare termini e cause e di distinguere l'esperienza dell'utente. Nessuna risposta del benchmark è inserita nel codice. La correttezza scientifica resta da valutare.

I vincoli riguardano il percorso generativo e il recupero di risposte apprese; alcuni percorsi diretti, come le risposte identitarie, mantengono la loro gestione dedicata.

## Verifica

Suite completa: **788 superati, 15 saltati, 9 warning**, 33,29 secondi. I test includono formato, budget, esclusione dall'apprendimento e protezione dello streaming. Sul Mac la libreria llama è un ELF Android: le grammatiche native richiedono collaudo sul dispositivo.

`pack_brain.py` eseguito; build Android completata; verifica APK con payload corrispondente al sorgente e librerie arm64-v8a.

APK: `bin/allma_prime-0.56-arm64-v8a-debug.apk`.

SHA256: `c3a7e076ca095f1d4e1a8a84549fd3981e00567d507eb8ad7f48fb44f3d77cf7`.

Installazione `adb install -r` riuscita, senza cancellazione dei dati. Hash sul telefono identico. App avviata, processo 27931, modello caricato con successo. Nei log iniziali esaminati non risultano traceback; le segnalazioni OpenCL indicano un limite già presente di accesso al driver GPU.

## Collaudo nativo successivo e accesso al benchmark

Recuperato il report completo `report_c0f990b67e344e3fae474f4be6b0f16d.json`, sessione 19:58:26–19:59:50. Le grammatiche native sono attive: N1 produce `no`, N2 `42`, N3 JSON con totale 8 e pari true. Tutti e tre i controlli automatici passano e il ragionamento resta presente.

N4 è bloccata con `subject_mismatch`: il controllo protegge l'utente e l'apprendimento, ma il modello continua a confondere la prospettiva. N5 contiene spiegazioni scientificamente infondate e il termine inesistente «glii»: il prompt aggiunto non risolve la correttezza. N6 non inventa una preferenza, ma è prolissa e generica. Nessun aumento percentuale della qualità può essere sostenuto.

Media 13,10 s contro 19,28 s del precedente Rapida (−32,0% in queste due esecuzioni); attesa iniziale media 4,77 s. È un confronto osservativo, non una stima robusta: budget, lunghezze e condizioni differiscono, e una risposta è stata rifiutata. La batteria è in carica, temperatura iniziale/finale 39,4 °C. Il campo battery_level deriva dall'energia interna del sistema e non costituisce una lettura diretta del livello Android. Il lock misura meno di 0,003 ms e la preparazione 8–16 ms: non spiegano l'attesa iniziale di secondi.

Un secondo report parziale `report_1a964e9721d94331a323b9a5ff78d9eb.json` conferma sì/no e numero, poi l'utente interrompe durante N3. Non viene usato per confrontare la qualità complessiva.

Il comando di avvio era chiamato «Esegui Benchmark Cognitivo» e nascosto nelle impostazioni avanzate; la schermata Diagnostica separata non aveva collegamenti. Ora esiste un pulsante nativo HTML «Avvia benchmark» in cima alle Impostazioni e «Apri benchmark» in Diagnostica. Configurazione unica, senza duplicare il selettore. Verificati entrambi i percorsi nel browser locale e salvata la schermata; due test mirati passati, sintassi JavaScript e diff verificati.

Nuova APK con questa correzione UI: SHA256 `0748b2c7567a3a1be487f9bf7e022e95b3c7624e9600947b0243068794cebc82`, payload verificato; installazione `-r` riuscita.
