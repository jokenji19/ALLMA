# Capacità operative e continuità — 13 ottobre 2026

Il collaudo precedente aveva confermato calcolo e nome senza modello, ma «Cosa sai fare allma?» riceveva una descrizione inesatta e «Solo questi sai fare?» produceva una duplicazione bloccata dopo circa 40 secondi.

## Correzioni

La descrizione diretta delle capacità passa ora da `runtime_capabilities.py`: consulta i componenti configurati nel core, distingue il modello linguistico dalla memoria e dal recupero di risposte confermate, esplicita che non aggiorna i pesi GGUF. I sogni vengono elencati solo quando abilitati. Non viene caricata un'altra istanza del modello per questa risposta. La prima richiesta di ampliamento dopo una descrizione operativa riceve una spiegazione dei limiti e l'invito a proporre un compito, invece di ricopiare l'elenco. La risoluzione è limitata alla conversazione e all'utente correnti. Domande creative, citazioni e follow-up su altri argomenti restano nel percorso linguistico.

Questa descrizione è un inventario dei componenti collegati, non una certificazione dell'efficienza di ogni modulo o dei servizi esterni. Non deduce dal vecchio VoiceSystem nel core che STT/TTS Android siano funzionanti: i motori vocali reali sono gestiti dalla UI. Il loro stato andrà esposto tramite un contratto dedicato prima di certificarli in questo inventario.

I follow-up generativi chiedono esplicitamente ampliamento e limiti, evitando di riprodurre la risposta precedente. Il controllo conservativo delle ripetizioni resta attivo e le ripetizioni richieste esplicitamente restano permesse. Non si promette di eliminare ogni ripetizione semantica del modello.

I soli brevi saluti sociali ricevono 32 token di ragionamento invece di 64; i compiti complessi mantengono il budget precedente. Non si disattiva il ragionamento. La riduzione del budget non misura automaticamente un guadagno di latenza: il prefill e il calore possono dominare il tempo reale.

I log distinguono ora errori di inferenza da risposte fermate per ripetizioni, formato o altri controlli. Questi ultimi riportano lo status preciso come warning; non vengono più descritti come guasti del modello.

## Verifica

Il primo gruppo di test aveva 69 successi e un errore nella nuova verifica della forma «spiegare meglio», correggendo il riconoscimento del follow-up. Suite completa finale: **856 superati, 15 saltati, 7 warning**, 147,54 s, offline con OMP/MKL limitati a un thread sul Mac. Il primo tentativo completo è stato interrotto dopo 58 successi per il rallentamento nel caricamento Torch legacy; non viene contato come suite completata. Nessun fallimento nella suite finale. Build Android compilata, payload corrispondente ai sorgenti, arm64-v8a. SHA256 `3d3bec7064a45748fd4ef941d5250312d0c3118fc80ae45b5ca954089625bf31`. L'importazione PyTorch nel sandbox abortisce: i test completi vengono eseguiti offline fuori sandbox, come nelle verifiche precedenti.

Nessuna cancellazione della cronologia personale e nessun commit/push richiesto in questo intervento. Nessuna percentuale di qualità o di risparmio energetico stimata.

Installazione `adb install -r` riuscita; hash dell’APK sul telefono identico. ALLMA avviata, processo 15562. Le nuove risposte operative sono verificate nei test; il collaudo manuale è completato, con gli esiti sotto.

## Collaudo reale completato

Nella conversazione di prova del processo 15562, alle 21:45:24 «Cosa sai fare Allma?» riceve l’inventario operativo con limiti espliciti; alle 21:45:41 «Solo questi sai fare?» riceve una risposta distinta sui limiti e sui compiti concreti. Entrambe hanno source=runtime_capabilities e llm_used=false. Nessuna generazione LLM per queste due richieste.

Intervalli tra registrazione della domanda e risposta: 58,49 ms e 41,51 ms; eventi WebView → log di risposta: circa 101 ms e 72 ms. Non includono la misura del completamento del rendering sullo schermo. Nel precedente collaudo le corrispondenti richieste avevano impiegato 25,29 s e 40,32 s con descrizione inesatta e duplicazione bloccata. Questo confronto documenta il vantaggio del percorso operativo su queste richieste specifiche, non un incremento generale dell’intelligenza o una misura diretta di consumo energetico.
