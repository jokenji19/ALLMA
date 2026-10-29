# ALLMA 0.9.1.1

Aggiornamento del 29 ottobre 2026. Versione Android `0.9.1.1`, versionCode `102593`, package `org.allma.allma_prime`, ARM64, API minima 24. Aggiornare l'installazione esistente senza disinstallarla per conservare i dati.

## Modifiche rispetto a 0.9.1

- Archivi della conversazione e dell'apprendimento su SQLite, caricamento iniziale limitato, indice incrementale e lettura paginata delle storie precedenti. Gestione di correzioni, revoche, ripresa dopo interruzioni e archivi danneggiati.
- Backup portabile, controlli di integrità, preferenze esplicite e migrazioni; messaggi proattivi persistenti e sensori con provenienza e validità temporale.
- Runtime nativo coerente per CPU, OpenCL e Hexagon opzionale: accelerazione Qwen sulla GPU del dispositivo verificato, Decider opzionale su NPU compatibile, isolamento dei dispositivi nativi, cancellazione e ripristino dopo aggiornamenti.
- Migliore convivenza tra inferenza e interfaccia: consegna dei flussi, riduzione degli aggiornamenti grafici superflui, controllo del carico e della temperatura Android.
- Obiettivi persistenti, proposte di piano, verifica dei passi e apprendimento dagli esiti riferiti. Le proposte del modello non certificano il successo di un'azione.
- Continuità e pertinenza del dialogo, provenienza delle informazioni, controllo del contributo nuovo e recupero mirato delle risposte non valide. Collegamento contestuale fra domande dell'assistente e risposte dell'utente, anche con parole e frasi nuove.
- Ricerca Internet opzionale e disattivabile: consenso, rinuncia per singolo turno, fonti pubbliche distinte dai ricordi, indicatore visivo del suo utilizzo, accessi limitati e cancellabili.
- Protezione del collegamento fra interfaccia e motore, delle risorse WebView, dei download e della memoria visiva; eliminazione del caricamento automatico di vecchi file pickle.
- Migliore avvio iniziale e diagnostiche estese, con cause di interruzione distinte e campioni termici espliciti.

## Verifiche e limiti

La suite completa locale del 29 ottobre ha superato 3.296 casi senza fallimenti, con 15 esclusioni già presenti. Dopo la correzione del rapporto diagnostico sono stati verificati nuovamente 84 casi dedicati, di cui tre nuovi: **3.299 casi distinti superati**, nessun fallimento. I test ripetuti non sono sommati due volte. I conteggi misurano scenari software e non l'intelligenza o l'affidabilità universale.

La build applicativa 102592 contiene lo stesso codice funzionale di questa release: qui sono aggiornati nome e numero di versione. L'APK è ricompilata e verificata prima della pubblicazione. Il più recente collaudo del dialogo con il modello reale è stato fermato prima delle richieste dalla protezione termica Android: zero risposte eseguite, non un test di qualità superato. Restano validi i risultati Android documentati delle precedenti prove specifiche, con i rispettivi dispositivi e protocolli.

L'accelerazione è stata verificata su Samsung Galaxy S25 Ultra: disponibilità di librerie nel pacchetto non equivale a supporto GPU/NPU universale. CPU e percorsi di ripiego restano necessari. La qualità semantica dipende anche dal modello; alcune risposte possono essere sbagliate, ripetitive o trattenute dai controlli. La visione continua, l'apprendimento acustico personale, una distribuzione Play e una garanzia di conservazione per tempi indefiniti non sono completati.

## Allegati e sorgenti

L'APK è una **build debug firmata per il collaudo**, non una build Google Play. I modelli e le voci opzionali sono scaricati separatamente. Verificare `SHA256SUMS.txt`. Le licenze dei componenti incorporati rimangono applicabili; gli allegati riportano le dipendenze native e le fonti corrispondenti. Il paper retrospettivo e il relativo dossier saranno aggiunti alla stessa release dopo la sua preparazione.

Gli archivi personali, i log grezzi delle conversazioni e le credenziali locali non sono allegati alla pubblicazione.
